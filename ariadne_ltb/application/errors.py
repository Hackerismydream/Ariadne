from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ApplicationError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        return self.message


class NotFoundError(ApplicationError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("not_found", message, 404, details)


class ValidationAppError(ApplicationError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("validation_error", message, 422, details)


class ConflictError(ApplicationError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("conflict", message, 409, details)


class BlockedError(ApplicationError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("blocked", message, 403, details)
