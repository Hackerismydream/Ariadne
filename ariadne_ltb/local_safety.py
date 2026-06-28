from __future__ import annotations

import os
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from ariadne_ltb.models import FailureReason, utc_now
from ariadne_ltb.storage import AriadneStore


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


class LockInfo(BaseModel):
    path: str
    pid: int | None = None
    runtime_id: str = "local"
    target_path: str = ""
    ticket_id: str | None = None
    assignment_id: str | None = None
    created_at: str = ""
    heartbeat_at: str = ""
    stale: bool = False


class DirectoryLock:
    def __init__(
        self,
        store: AriadneStore,
        target_path: str | Path,
        runtime_id: str = "local",
        ticket_id: str | None = None,
        assignment_id: str | None = None,
    ) -> None:
        self.store = store
        self.target_path = Path(target_path).resolve()
        digest = __import__("hashlib").sha256(str(self.target_path).encode("utf-8")).hexdigest()[:16]
        self.lock_path = store.locks_dir / f"{digest}.lock"
        self.runtime_id = runtime_id
        self.ticket_id = ticket_id
        self.assignment_id = assignment_id
        self._held = False

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            existing = _read_lock(self.lock_path)
            if is_stale_lock(existing):
                self.lock_path.unlink(missing_ok=True)
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else:
                msg = f"target directory is locked: {self.target_path}"
                raise RuntimeError(msg) from exc
        metadata = {
            "pid": os.getpid(),
            "runtime_id": self.runtime_id,
            "target_path": str(self.target_path),
            "ticket_id": self.ticket_id,
            "assignment_id": self.assignment_id,
            "created_at": utc_now(),
            "heartbeat_at": utc_now(),
        }
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2)
            handle.write("\n")
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


def list_locks(store: AriadneStore, stale_after_seconds: int = 3600) -> list[LockInfo]:
    locks: list[LockInfo] = []
    for path in sorted(store.locks_dir.glob("*.lock")):
        info = _read_lock(path)
        info.stale = is_stale_lock(info, stale_after_seconds=stale_after_seconds)
        locks.append(info)
    return locks


def is_stale_lock(info: LockInfo, stale_after_seconds: int = 3600) -> bool:
    if info.pid is not None and not _pid_is_alive(info.pid):
        return True
    if not info.heartbeat_at:
        return True
    try:
        heartbeat = datetime.fromisoformat(info.heartbeat_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (datetime.now(UTC) - heartbeat).total_seconds() > stale_after_seconds


def _pid_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def clear_stale_locks(store: AriadneStore, force: bool = False) -> list[LockInfo]:
    cleared: list[LockInfo] = []
    for info in list_locks(store):
        if not info.stale:
            continue
        if not force:
            continue
        Path(info.path).unlink(missing_ok=True)
        cleared.append(info)
    return cleared


def _read_lock(path: Path) -> LockInfo:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        lines = path.read_text(encoding="utf-8").splitlines()
        data = {
            "pid": int(lines[0]) if lines and lines[0].isdigit() else None,
            "runtime_id": "unknown",
            "target_path": lines[1] if len(lines) > 1 else "",
            "created_at": "",
            "heartbeat_at": "",
        }
    return LockInfo(path=str(path), **data)
