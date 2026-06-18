from __future__ import annotations

from pathlib import Path

from fastapi import Request

from ariadne_ltb.storage import AriadneStore


def get_store(request: Request) -> AriadneStore:
    root = Path(request.app.state.root)
    return AriadneStore(root)
