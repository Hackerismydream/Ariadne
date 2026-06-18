from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.application.evidence_projection import EvidenceProjectionService
from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import ExecutionResult
from ariadne_ltb.storage import AriadneStore


def test_evidence_projection_redacts_local_execution_details(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_execution_result(
        ExecutionResult(
            id="exec_1",
            ticket_id="ticket_1",
            backend_name="codex",
            dry_run=False,
            blocked=True,
            block_reason="external execution disabled",
            command="codex exec --cd /tmp/repo --prompt-file /tmp/.ariadne/handoff.md",
            command_template="codex exec --cd {target_repo} --prompt-file {handoff_file}",
            command_template_env_var="ARIADNE_CODEX_COMMAND_TEMPLATE",
            exit_code=1,
            stdout="secret stdout",
            stderr="secret stderr",
            changed_files=["src/app.py"],
            git_diff="diff --git a/src/app.py b/src/app.py",
            test_command="pytest",
            test_exit_code=0,
            test_stdout="test stdout",
            test_stderr="test stderr",
            handoff_file="/tmp/repo/.ariadne/handoffs/ARI-003.md",
            provider_failure_evidence="api_key=sk-test",
        )
    )

    payload = EvidenceProjectionService(store).snapshot().model_dump_json()

    assert "exec_1" in payload
    assert "src/app.py" in payload
    assert "secret stdout" not in payload
    assert "secret stderr" not in payload
    assert "codex exec" not in payload
    assert "ARIADNE_CODEX_COMMAND_TEMPLATE" not in payload
    assert ".ariadne/handoffs" not in payload
    assert "sk-test" not in payload


def test_http_evidence_projection_is_redacted(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_execution_result(
        ExecutionResult(
            id="exec_2",
            ticket_id="ticket_2",
            backend_name="claude-code",
            dry_run=False,
            command="claude --print < /tmp/.ariadne/handoff.md",
            exit_code=0,
            stdout="raw provider output",
            stderr="",
            changed_files=["README.md"],
        )
    )

    response = TestClient(create_app(tmp_path)).get("/api/evidence")

    assert response.status_code == 200, response.text
    assert response.json()["schema_version"] == "ariadne.evidence-projection.v1"
    assert "README.md" in response.text
    assert "raw provider output" not in response.text
    assert "claude --print" not in response.text
