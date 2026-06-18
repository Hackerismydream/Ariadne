from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from ariadne_ltb.application.errors import ApplicationError
from ariadne_ltb.interfaces.http.errors import application_error_handler
from ariadne_ltb.interfaces.http.routes import router


def create_app(root: str | Path = ".") -> FastAPI:
    app = FastAPI(title="Ariadne Local Control Plane", version="1.0.0")
    app.state.root = str(Path(root).resolve())
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.include_router(router)
    return app
