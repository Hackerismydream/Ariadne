from __future__ import annotations

import pytest

from ariadne_ltb.domain.runtime_policy import (
    resolve_runtime_profile,
    runtime_profile_values,
    validate_backend_for_source,
)


def test_runtime_profile_auto_uses_production_for_real_backends() -> None:
    assert resolve_runtime_profile("auto", "codex") == "production"
    assert resolve_runtime_profile("auto", "claude-code") == "production"
    assert runtime_profile_values("production").agent_runtime == "llm"


def test_runtime_profile_auto_uses_deterministic_for_fallback() -> None:
    assert resolve_runtime_profile("auto", "fake-codex") == "deterministic"
    assert runtime_profile_values("deterministic").agent_runtime == "deterministic"


def test_http_rejects_shell_fake_codex_and_dry_run() -> None:
    for backend in ["shell", "fake-codex", "dry-run"]:
        with pytest.raises(ValueError):
            validate_backend_for_source("http", backend)


def test_test_source_allows_deterministic_fallback_backends() -> None:
    validate_backend_for_source("test", "fake-codex")
    validate_backend_for_source("test", "dry-run")
