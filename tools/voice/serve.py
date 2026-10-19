"""Serve the blind voice test on http://127.0.0.1:8770 (stdlib only).

    uv run python tools/voice/serve.py

GET  /            the test page (tools/voice/blindtest/)
GET  /samples/*   rendered clips
GET  /manifest.json, /casting.json
POST /results     appends one run to tools/voice/results.json
"""

from __future__ import annotations

import json
import mimetypes
import time
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PAGE = HERE / "blindtest"
SAMPLES = HERE / "samples"
RESULTS = HERE / "results.json"
FIXED = {
    "/manifest.json": HERE / "manifest.json",
    "/casting.json": ROOT / "content/companies/kilnworks/voices/casting.json",
}
HOST, PORT = "127.0.0.1", 8770
MAX_BODY = 1_000_000

mimetypes.add_type("audio/ogg", ".ogg")


def safe_join(base: Path, rel: str) -> Path | None:
    target = (base / rel.lstrip("/")).resolve()
    return target if target.is_file() and base.resolve() in target.parents else None


class Handler(BaseHTTPRequestHandler):
    server_version = "voice-test"

    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = unquote(self.path.split("?", 1)[0])
        if path in ("/", ""):
            path = "/index.html"
        file = FIXED.get(path)
        if file is None and path.startswith("/samples/"):
            file = safe_join(SAMPLES, path[len("/samples/"):])
        elif file is None:
            file = safe_join(PAGE, path)
        if file is None or not file.is_file():
            return self._send(404, b"not found", "text/plain")
        ctype = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        self._send(200, file.read_bytes(), ctype)

    def do_POST(self) -> None:
        if self.path != "/results":
            return self._send(404, b"not found", "text/plain")
        origin = self.headers.get("Origin")
        if origin and origin not in (f"http://{HOST}:{PORT}", f"http://localhost:{PORT}"):
            return self._send(403, b"bad origin", "text/plain")
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            return self._send(400, b"bad length", "text/plain")
        try:
            run = json.loads(self.rfile.read(length))
        except ValueError:
            return self._send(400, b"bad json", "text/plain")
        runs = json.loads(RESULTS.read_text("utf-8")) if RESULTS.exists() else []
        runs.append({"saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"), **run} if isinstance(run, dict) else run)
        RESULTS.write_text(json.dumps(runs, indent=1), "utf-8")
        self._send(200, b'{"ok":true}', "application/json")

    def log_message(self, fmt: str, *args) -> None:
        if "/samples/" not in (args[0] if args else ""):
            super().log_message(fmt, *args)


def main() -> None:
    print(f"Voice test: open http://{HOST}:{PORT}  (Ctrl+C to stop)")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
