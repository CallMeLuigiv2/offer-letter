"""FastAPI app factory: routes under /api, the websocket at /ws, and the built web app when present."""

from __future__ import annotations

import asyncio
import random
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import Settings
from .db import Database
from .director import Director
from .errors import ApiError
from .events import EventBus
from .routes import build_router
from .stages import backfill
from .services import CommandRunner, Services, run_command
from .teammates.governor import Governor
from .teammates.runner import AuthStatus, ClaudeRunner, DisabledRunner, GovernedRunner, TeammateRunner, check_auth


def create_app(settings: Settings, runner: TeammateRunner | None = None, command: CommandRunner = run_command,
               rng: random.Random | None = None) -> FastAPI:
    """`runner` replaces the real Claude runner (tests pass a FakeRunner and skip the sign-in check)."""
    db = Database(settings.db_path)
    backfill(db, settings)  # V3: every ticket row gets its own stage list; staged kits get plan.json / plan_key.json
    bus = EventBus()
    governor = Governor(db, bus)
    # The real runner needs the sign-in check, which runs at startup; until then teammates say so.
    governed = GovernedRunner(runner or DisabledRunner("Teammates are still starting up."), governor)
    svc = Services(settings=settings, db=db, bus=bus, governor=governor, runner=governed,
                   director=Director(db, bus, settings, governed, governor, rng=rng),
                   auth=AuthStatus(runner is not None, runner is not None, "claude.ai" if runner else None, ""),
                   version=__version__, command=command)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if runner is None:
            svc.auth = await asyncio.to_thread(check_auth)
            governed.inner = ClaudeRunner(settings.teammates_dir) if svc.auth.ok else DisabledRunner(svc.auth.message)
        yield
        await svc.director.idle()
        db.close()

    app = FastAPI(title="Offer Letter", version=__version__, lifespan=lifespan)
    app.include_router(build_router(svc), prefix="/api")

    @app.exception_handler(ApiError)
    async def api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse({"error": exc.message}, status_code=exc.status)

    index_html = settings.web_dist / "index.html" if settings.web_dist else None
    asset_exts = {"png", "webp", "jpg", "jpeg", "gif", "svg", "ico", "js", "mjs", "css", "map", "json",
                  "tmj", "tsj", "woff", "woff2", "ttf", "ogg", "mp3", "wav", "txt", "html"}

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse | FileResponse:
        # Client-side routes (/tickets/KLN-01, /channels/kilnworks.serving, /office) aren't files,
        # so a refresh or a deep link would 404. Hand those back to the single-page app; API and
        # asset misses stay 404. Channel ids contain dots, so check for real asset extensions.
        path = request.url.path
        ext = path.rsplit("/", 1)[-1].rpartition(".")[2].lower() if "." in path.rsplit("/", 1)[-1] else ""
        if (exc.status_code == 404 and request.method == "GET" and index_html and index_html.is_file()
                and not path.startswith(("/api/", "/ws", "/portraits/")) and ext not in asset_exts):
            return FileResponse(index_html, media_type="text/html")
        return JSONResponse({"error": str(exc.detail)}, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0]
        where = ".".join(str(p) for p in first["loc"] if p != "body")
        return JSONResponse({"error": f"Check the field {where or 'in your request'}: {first['msg']}."}, status_code=422)

    @app.websocket("/ws")
    async def websocket(ws: WebSocket) -> None:
        await ws.accept()
        queue = bus.subscribe()
        try:
            while True:
                await ws.send_json(await queue.get())
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            bus.unsubscribe(queue)

    portraits_root = (settings.content_dir / "companies").resolve()
    safe = re.compile(r"^[A-Za-z0-9_-]+$")

    @app.get("/portraits/{company}/{persona}/{expression}.{ext}")
    async def portrait(company: str, persona: str, expression: str, ext: str) -> FileResponse:
        """Persona portraits from the content pack; a plain 404 when missing (the web has a placeholder)."""
        if ext not in ("webp", "png") or not all(safe.match(part) for part in (company, persona, expression)):
            raise HTTPException(404, "No such portrait.")
        path = portraits_root / company / "portraits" / persona / f"{expression}.{ext}"
        if not path.is_file():
            raise HTTPException(404, "No such portrait.")
        return FileResponse(path, media_type=f"image/{ext}")

    if settings.office_dir and settings.office_dir.is_dir():
        app.mount("/office", StaticFiles(directory=settings.office_dir), name="office")
    if settings.web_dist and settings.web_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dist, html=True), name="web")
    app.state.services = svc
    return app
