from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from ariadne_ltb.application.errors import ApplicationError


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details or {},
            }
        },
    )
