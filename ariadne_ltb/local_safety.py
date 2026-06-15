from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.models import FailureReason


class TargetPathValidation(BaseModel):
    valid: bool
    path: str
    reason: str = ""
    failure_reason: FailureReason | None = None


def validate_target_repo_path(path: str | Path) -> TargetPathValidation:
    candidate = Path(path).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError:
        return TargetPathValidation(
            valid=False,
            path=str(candidate),
            reason="target path does not exist",
            failure_reason=FailureReason.INVALID_RESOURCE,
        )

    if not candidate.is_absolute():
        return TargetPathValidation(
            valid=False,
            path=str(candidate),
            reason="target path must be absolute",
            failure_reason=FailureReason.INVALID_RESOURCE,
        )
    if not resolved.is_dir():
        return TargetPathValidation(
            valid=False,
            path=str(resolved),
            reason="target path must be a directory",
            failure_reason=FailureReason.INVALID_RESOURCE,
        )
    blocked_roots = {
        Path("/").resolve(),
        Path("/tmp").resolve(),
        Path("/var").resolve(),
        Path("/etc").resolve(),
        Path("/usr").resolve(),
        Path("/opt").resolve(),
        Path("/Users").resolve() if Path("/Users").exists() else None,
        Path("/Users/Shared").resolve() if Path("/Users/Shared").exists() else None,
        Path.home().resolve(),
    }
    if resolved in {item for item in blocked_roots if item is not None}:
        return TargetPathValidation(
            valid=False,
            path=str(resolved),
            reason="target path cannot be a system root or whole user profile",
            failure_reason=FailureReason.INVALID_RESOURCE,
        )
    if not os.access(resolved, os.R_OK | os.W_OK):
        return TargetPathValidation(
            valid=False,
            path=str(resolved),
            reason="target path must be readable and writable",
            failure_reason=FailureReason.INVALID_RESOURCE,
        )
    return TargetPathValidation(valid=True, path=str(resolved))


class DirectoryLock:
    def __init__(self, store: AriadneStore, target_path: str | Path) -> None:
        self.store = store
        self.target_path = Path(target_path).resolve()
        digest = __import__("hashlib").sha256(str(self.target_path).encode("utf-8")).hexdigest()[:16]
        self.lock_path = store.locks_dir / f"{digest}.lock"
        self._held = False

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            msg = f"target directory is locked: {self.target_path}"
            raise RuntimeError(msg) from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"{os.getpid()}\n{self.target_path}\n")
        self._held = True

    def release(self) -> None:
        if not self._held:
            return
        try:
            self.lock_path.unlink()
        except FileNotFoundError:
            pass
        self._held = False

    def __enter__(self) -> DirectoryLock:
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.release()
