from __future__ import annotations

import json
import secrets
from hashlib import sha256
from pathlib import Path

from ariadne_ltb.application.errors import BlockedError
from ariadne_ltb.models import TicketAssignment, utc_now
from ariadne_ltb.storage import AriadneStore


class ConfirmationTokenService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store
        self.dir = store.base / "application" / "confirmation_tokens"
        self.dir.mkdir(parents=True, exist_ok=True)

    def issue_for_assignment(self, assignment: TicketAssignment) -> str:
        token = f"act_{secrets.token_urlsafe(24)}"
        payload = {
            "assignment_id": assignment.id,
            "ticket_id": assignment.ticket_id,
            "ticket_key": assignment.ticket_key,
            "target_project_id": assignment.metadata.get("target_project_id"),
            "backend_name": assignment.backend_name,
            "token_hash": _hash_token(token),
            "created_at": utc_now(),
            "used_at": None,
        }
        self._path(assignment.id).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return token

    def verify(self, assignment: TicketAssignment, token: str) -> None:
        path = self._path(assignment.id)
        if not path.exists():
            raise BlockedError("confirmation token is missing", {"assignment_id": assignment.id})
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = {
            "assignment_id": assignment.id,
            "target_project_id": assignment.metadata.get("target_project_id"),
            "backend_name": assignment.backend_name,
        }
        actual = {
            "assignment_id": data.get("assignment_id"),
            "target_project_id": data.get("target_project_id"),
            "backend_name": data.get("backend_name"),
        }
        if actual != expected or data.get("token_hash") != _hash_token(token):
            raise BlockedError("confirmation token does not match assignment", {"assignment_id": assignment.id})

    def _path(self, assignment_id: str) -> Path:
        return self.dir / f"{assignment_id}.json"


def _hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
