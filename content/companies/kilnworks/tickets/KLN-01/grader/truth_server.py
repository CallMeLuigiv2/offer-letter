"""A fake OpenAI-compatible inference server for local benchmark runs.

It streams tokens over SSE with a fixed prefill time and inter-token gap,
and can inject the failures we see in production:

- **engine pauses**: every ``pause_every_s`` seconds the whole engine
  stops for ``pause_s`` seconds. Every stream freezes and new requests
  wait. From outside this is what a long GC or a KV-cache compaction
  looks like (INC-2291).
- **stalls**: every ``stall_every``-th request waits an extra ``stall_s``
  seconds before its first token.
- **failures**: every ``fail_every``-th request gets HTTP 503.

Like kiln-gateway, it sends the response headers and an empty role delta
as soon as it admits a request, then the first content token after
prefill (see docs/decisions/0002).

Stdlib only. It speaks just enough HTTP/1.1 for httpx: keep-alive,
Content-Length request bodies, chunked responses. Run it with
``kiln-bench fake-server`` or ``python -m kiln_bench.fake_server``.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import random
import time
from dataclasses import dataclass

WORDS = (
    "the", "kiln", "fires", "at", "night", "and", "every", "token", "glows",
    "a", "little", "brighter", "than", "last", "one", "while", "queue", "waits",
)

_REASONS = {200: "OK", 400: "Bad Request", 404: "Not Found", 503: "Service Unavailable"}


@dataclass
class FakeServerConfig:
    host: str = "127.0.0.1"
    port: int = 8099
    model: str = "kiln-fake-1"
    prefill_ms: float = 30.0
    """Time from admission to the first content token."""
    itl_ms: float = 8.0
    """Gap between content tokens."""
    max_output_tokens: int = 256
    """Upper bound on tokens per response; requests ask for max_tokens."""
    pause_every_s: float = 0.0
    """Period of engine pauses. 0 turns them off."""
    pause_s: float = 0.0
    """Length of each engine pause. The first one starts after
    pause_every_s - pause_s seconds."""
    stall_every: int = 0
    stall_s: float = 2.0
    fail_every: int = 0


@dataclass
class _Request:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes


class FakeServer:
    """Use as ``async with FakeServer(config) as server: ... server.url``."""

    def __init__(self, config: FakeServerConfig | None = None) -> None:
        self.config = config or FakeServerConfig()
        self.requests_seen = 0
        self.started_at: float | None = None
        """Event-loop time (``loop.time()``) when the server started; pauses are
        scheduled from here."""
        self._engine_running = asyncio.Event()
        self._engine_running.set()
        self._server: asyncio.Server | None = None
        self._pauser: asyncio.Task[None] | None = None
        self._writers: set[asyncio.StreamWriter] = set()

    @property
    def url(self) -> str:
        if self._server is None:
            raise RuntimeError("server is not started")
        host, port = self._server.sockets[0].getsockname()[:2]
        return f"http://{host}:{port}"

    async def start(self) -> None:
        cfg = self.config
        self._server = await asyncio.start_server(self._handle_connection, cfg.host, cfg.port)
        self.started_at = asyncio.get_running_loop().time()
        if cfg.pause_every_s > 0 and cfg.pause_s > 0:
            if cfg.pause_s >= cfg.pause_every_s:
                raise ValueError("pause_s must be shorter than pause_every_s")
            self._pauser = asyncio.create_task(self._pause_loop())

    async def close(self) -> None:
        if self._pauser is not None:
            self._pauser.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pauser
        self._engine_running.set()
        if self._server is not None:
            self._server.close()
            # Python 3.12's wait_closed() waits for open connections too, so
            # close the keep-alive ones we still hold.
            for writer in list(self._writers):
                writer.close()
            await self._server.wait_closed()

    async def __aenter__(self) -> FakeServer:
        await self.start()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.close()

    # -- engine ---------------------------------------------------------

    async def _pause_loop(self) -> None:
        cfg = self.config
        loop = asyncio.get_running_loop()
        next_pause = self.started_at + cfg.pause_every_s - cfg.pause_s
        while True:
            await asyncio.sleep(max(0.0, next_pause - loop.time()))
            self._engine_running.clear()
            await asyncio.sleep(max(0.0, next_pause + cfg.pause_s - loop.time()))
            self._engine_running.set()
            next_pause += cfg.pause_every_s

    async def _prefill(self, extra_s: float) -> None:
        await asyncio.sleep(self.config.prefill_ms / 1000 + extra_s)
        await self._engine_running.wait()

    async def _next_token(self) -> None:
        await asyncio.sleep(self.config.itl_ms / 1000)
        await self._engine_running.wait()

    # -- HTTP -----------------------------------------------------------

    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._writers.add(writer)
        try:
            while True:
                request = await _read_request(reader)
                if request is None:
                    break
                keep_alive = request.headers.get("connection", "").lower() != "close"
                await self._route(request, writer, keep_alive)
                if not keep_alive:
                    break
        except (ConnectionError, asyncio.IncompleteReadError, asyncio.LimitOverrunError, ValueError):
            pass
        finally:
            self._writers.discard(writer)
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    async def _route(self, req: _Request, writer: asyncio.StreamWriter, keep_alive: bool) -> None:
        if req.method == "GET" and req.path in ("/health", "/healthz"):
            await _send_json(writer, 200, {"status": "ok", "model": self.config.model}, keep_alive)
        elif req.method == "POST" and req.path == "/v1/chat/completions":
            await self._chat(req, writer, keep_alive)
        else:
            error = {"error": {"message": f"no route for {req.method} {req.path}"}}
            await _send_json(writer, 404, error, keep_alive)

    async def _chat(self, req: _Request, writer: asyncio.StreamWriter, keep_alive: bool) -> None:
        cfg = self.config
        self.requests_seen += 1
        n = self.requests_seen
        try:
            body = json.loads(req.body or b"{}")
        except json.JSONDecodeError:
            await _send_json(writer, 400, {"error": {"message": "body is not JSON"}}, keep_alive)
            return
        if cfg.fail_every and n % cfg.fail_every == 0:
            error = {"error": {"message": "engine overloaded, retry later", "type": "overloaded"}}
            await _send_json(writer, 503, error, keep_alive)
            return

        rid = f"chatcmpl-fake-{n}"
        n_tokens = max(1, min(int(body.get("max_tokens") or 16), cfg.max_output_tokens))
        rng = random.Random(n)
        tokens = [" " + rng.choice(WORDS) for _ in range(n_tokens)]
        prompt_tokens = sum(len(str(m.get("content", "")).split()) for m in body.get("messages", []))
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": n_tokens,
            "total_tokens": prompt_tokens + n_tokens,
        }
        stall = cfg.stall_s if cfg.stall_every and n % cfg.stall_every == 0 else 0.0

        if not body.get("stream"):
            await self._prefill(stall)
            for _ in tokens[1:]:
                await self._next_token()
            message = {"role": "assistant", "content": "".join(tokens)}
            payload = {
                "id": rid,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": cfg.model,
                "choices": [{"index": 0, "message": message, "finish_reason": "length"}],
                "usage": usage,
            }
            await _send_json(writer, 200, payload, keep_alive)
            return

        include_usage = bool((body.get("stream_options") or {}).get("include_usage"))
        await _start_stream(writer, keep_alive, rid)
        await _send_chunk(writer, _sse(_delta(rid, cfg.model, {"role": "assistant", "content": ""})))
        await self._prefill(stall)
        for i, token in enumerate(tokens):
            if i:
                await self._next_token()
            await _send_chunk(writer, _sse(_delta(rid, cfg.model, {"content": token})))
        await _send_chunk(writer, _sse(_delta(rid, cfg.model, {}, finish_reason="length")))
        if include_usage:
            final = {"id": rid, "object": "chat.completion.chunk", "created": int(time.time()),
                     "model": cfg.model, "choices": [], "usage": usage}
            await _send_chunk(writer, _sse(final))
        await _send_chunk(writer, b"data: [DONE]\n\n")
        await _end_stream(writer)


def _delta(rid: str, model: str, delta: dict, finish_reason: str | None = None) -> dict:
    return {
        "id": rid,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


def _sse(payload: dict) -> bytes:
    return b"data: " + json.dumps(payload, separators=(",", ":")).encode() + b"\n\n"


async def _read_request(reader: asyncio.StreamReader) -> _Request | None:
    """Read one request. Returns None when the client closed the connection."""
    try:
        head = await reader.readuntil(b"\r\n\r\n")
    except asyncio.IncompleteReadError:
        return None
    request_line, *header_lines = head.decode("latin-1").split("\r\n")
    method, path, _version = request_line.split(" ", 2)
    headers = {}
    for line in header_lines:
        if line:
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    body = await reader.readexactly(length) if length else b""
    return _Request(method, path, headers, body)


def _connection_header(keep_alive: bool) -> str:
    return "keep-alive" if keep_alive else "close"


async def _send_json(writer: asyncio.StreamWriter, status: int, payload: dict, keep_alive: bool) -> None:
    body = json.dumps(payload).encode()
    head = (
        f"HTTP/1.1 {status} {_REASONS[status]}\r\n"
        "Content-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: {_connection_header(keep_alive)}\r\n"
        "\r\n"
    )
    writer.write(head.encode("latin-1") + body)
    await writer.drain()


async def _start_stream(writer: asyncio.StreamWriter, keep_alive: bool, request_id: str) -> None:
    head = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/event-stream\r\n"
        "Cache-Control: no-cache\r\n"
        "Transfer-Encoding: chunked\r\n"
        f"X-Request-Id: {request_id}\r\n"
        f"Connection: {_connection_header(keep_alive)}\r\n"
        "\r\n"
    )
    writer.write(head.encode("latin-1"))
    await writer.drain()


async def _send_chunk(writer: asyncio.StreamWriter, data: bytes) -> None:
    writer.write(b"%X\r\n%s\r\n" % (len(data), data))
    await writer.drain()


async def _end_stream(writer: asyncio.StreamWriter) -> None:
    writer.write(b"0\r\n\r\n")
    await writer.drain()


# -- running it -----------------------------------------------------------


def add_arguments(parser: argparse.ArgumentParser) -> None:
    d = FakeServerConfig()
    parser.add_argument("--host", default=d.host)
    parser.add_argument("--port", type=int, default=d.port, help="0 picks a free port")
    parser.add_argument("--model", default=d.model)
    parser.add_argument("--prefill-ms", type=float, default=d.prefill_ms, help="time to first token")
    parser.add_argument("--itl-ms", type=float, default=d.itl_ms, help="gap between tokens")
    parser.add_argument("--max-output-tokens", type=int, default=d.max_output_tokens)
    parser.add_argument("--pause-every", type=float, default=0.0, metavar="S",
                        help="pause the whole engine every S seconds (0 = never)")
    parser.add_argument("--pause-for", type=float, default=0.0, metavar="S",
                        help="length of each engine pause")
    parser.add_argument("--stall-every", type=int, default=0, metavar="N",
                        help="every Nth request waits --stall-for before its first token")
    parser.add_argument("--stall-for", type=float, default=d.stall_s, metavar="S")
    parser.add_argument("--fail-every", type=int, default=0, metavar="N",
                        help="every Nth request gets HTTP 503")


def config_from_args(args: argparse.Namespace) -> FakeServerConfig:
    return FakeServerConfig(
        host=args.host,
        port=args.port,
        model=args.model,
        prefill_ms=args.prefill_ms,
        itl_ms=args.itl_ms,
        max_output_tokens=args.max_output_tokens,
        pause_every_s=args.pause_every,
        pause_s=args.pause_for,
        stall_every=args.stall_every,
        stall_s=args.stall_for,
        fail_every=args.fail_every,
    )


async def serve_forever(config: FakeServerConfig) -> None:
    async with FakeServer(config) as server:
        # Scripts and tests read this line to find the port.
        print(f"fake server listening on {server.url}", flush=True)
        await asyncio.Event().wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m kiln_bench.fake_server", description=__doc__.splitlines()[0])
    add_arguments(parser)
    config = config_from_args(parser.parse_args(argv))
    from kiln_bench._platform import run

    with contextlib.suppress(KeyboardInterrupt):
        run(serve_forever(config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
