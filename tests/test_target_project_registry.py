from __future__ import annotations

from pathlib import Path

import pytest

from ariadne_ltb.application.errors import NotFoundError, ValidationAppError
from ariadne_ltb.application.target_project_registry import TargetProjectRegistry
from ariadne_ltb.storage import AriadneStore
from ariadne_ltb.target_project import ensure_demo_target_project


def test_target_project_registry_registers_and_resolves_valid_git_directory(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    target = ensure_demo_target_project(tmp_path)

    registered = TargetProjectRegistry(store).register(target, "Demo Target", target_project_id="local-default")
    resolved = TargetProjectRegistry(store).resolve_path("local-default")

    assert registered.id == "local-default"
    assert registered.label == "Demo Target"
    assert registered.available is True
    assert resolved == str(target)


def test_target_project_registry_rejects_unknown_project(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)

    with pytest.raises(NotFoundError):
        TargetProjectRegistry(store).resolve_path("missing")


def test_target_project_registry_rejects_non_directory_path(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    file_path = tmp_path / "not-a-directory"
    file_path.write_text("x", encoding="utf-8")

    with pytest.raises(ValidationAppError):
        TargetProjectRegistry(store).register(file_path, "Invalid")
