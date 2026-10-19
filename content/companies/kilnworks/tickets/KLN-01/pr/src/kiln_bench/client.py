"""Streaming client for OpenAI-compatible chat completion endpoints."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

from kiln_bench.records import RequestRecord
from kiln_bench.sse import DONE, iter_sse_data


class StreamClient:
    """Sends streaming chat completions and timestamps every content chunk.

    Share one client between all workers so connections are pooled. The
    pool must be at least as large as the number of requests you want in
    flight: if it is smaller, httpx queues requests internally and we never
    see that wait.
    """

    def __init__(
        self,
        base_url: str,
        *,
        model: str,
        clock: Callable[[], float],
        max_tokens: int = 32,
        max_connections: int = 64,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.clock = clock
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            # Runners enforce the per-request deadline. httpx only gets a
            # connect timeout so a dead host fails fast.
            timeout=httpx.Timeout(None, connect=10.0),
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_connections,
            ),
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> StreamClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    async def stream_chat(self, prompt: str, rec: RequestRecord) -> RequestRecord:
        """Send one request and fill in ``rec`` as the stream arrives.

        ``rec`` is filled in place, so a caller that cancels us (a timeout)
        still has every timestamp we got so far. Raises ``httpx.HTTPError``
        on transport errors and non-200 responses.
        """
        body = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        rec.sent_at = self.clock()
        async with self._http.stream("POST", "/v1/chat/completions", json=body) as resp:
            rec.status = resp.status_code
            if resp.status_code != 200:
                await resp.aread()
                resp.raise_for_status()
            async for data in iter_sse_data(resp.aiter_lines()):
                if data == DONE:
                    break
                chunk = json.loads(data)
                usage = chunk.get("usage")
                if usage:
                    rec.output_tokens = usage.get("completion_tokens", 0)
                for choice in chunk.get("choices", ()):
                    # kiln-gateway flushes an empty role delta as soon as it
                    # admits the request. That is not a token (decision 0002).
                    if choice.get("delta", {}).get("content"):
                        now = self.clock()
                        if rec.first_token_at is None:
                            rec.first_token_at = now
                        rec.token_times.append(now)
        rec.done_at = self.clock()
        if not rec.output_tokens:
            # Server sent no usage block: fall back to counting chunks.
            rec.output_tokens = len(rec.token_times)
        return rec
