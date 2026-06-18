from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ariadne_ltb.application.errors import ApplicationError
from ariadne_ltb.interfaces.http.errors import application_error_handler
from ariadne_ltb.interfaces.http.routes import router


def create_app(
    root: str | Path = ".",
    *,
    serve_workbench: bool = False,
    frontend_dist: str | Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Ariadne Local Control Plane", version="1.0.0")
    app.state.root = str(Path(root).resolve())
    app.add_exception_handler(ApplicationError, application_error_handler)

    @app.middleware("http")
    async def enforce_local_api_contract(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method in {"POST", "PUT", "PATCH"}:
            content_type = request.headers.get("content-type", "")
            if "application/json" not in content_type:
                return JSONResponse(
                    status_code=415,
                    content={"error": {"code": "unsupported_media_type", "message": "JSON body required"}},
                )
            content_length = int(request.headers.get("content-length") or "0")
            if content_length > 256_000:
                return JSONResponse(
                    status_code=413,
                    content={"error": {"code": "request_too_large", "message": "request body too large"}},
                )
        return await call_next(request)

    app.include_router(router)
    if serve_workbench:
        dist = Path(frontend_dist) if frontend_dist is not None else default_frontend_dist()
        if not dist.exists():
            msg = (
                f"Ariadne workbench frontend dist does not exist: {dist}. "
                "Run `cd frontend/ariadne-workbench && npm run build` first."
            )
            raise FileNotFoundError(msg)
        app.mount("/", StaticFiles(directory=dist, html=True), name="workbench")
    return app


def default_frontend_dist() -> Path:
    return Path(__file__).resolve().parents[3] / "frontend" / "ariadne-workbench" / "dist"
