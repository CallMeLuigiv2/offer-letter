"""FastAPI app factory: routes under /api, the websocket at /ws, and the built web app when present."""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .config import Settings
from .db import Database
from .director import Director
from .errors import ApiError
from .events import EventBus
from .routes import build_router
from .services import CommandRunner, Services, run_command
from .teammates.governor import Governor
from .teammates.runner import AuthStatus, ClaudeRunner, DisabledRunner, GovernedRunner, TeammateRunner, check_auth


def create_app(settings: Settings, runner: TeammateRunner | None = None, command: CommandRunner = run_command,
               rng: random.Random | None = None) -> FastAPI:
    """`runner` replaces the real Claude runner (tests pass a FakeRunner and skip the sign-in check)."""
    db = Database(settings.db_path)
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

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
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

    if settings.web_dist and settings.web_dist.is_dir():
        app.mount("/", StaticFiles(directory=settings.web_dist, html=True), name="web")
    app.state.services = svc
    return app
