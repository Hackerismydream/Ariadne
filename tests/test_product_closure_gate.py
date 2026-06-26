from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ariadne_ltb.models import ExecutionResult
from ariadne_ltb.product_closure import (
    BLOCKED_WITH_EVIDENCE,
    NOT_CLOSED,
    OFFLINE_REGRESSION,
    evaluate_closure_packet,
    product_closure_snapshot,
)
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]


def test_verify_dogfood_result_packet_rejects_fake_real_closed(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / ".git").mkdir()
    packet = tmp_path / "closure-result.json"
    packet.write_text(
        json.dumps(
            {
                "schema_version": "ariadne.browser_dogfood_closure.v1",
                "status": "REAL_CLOSED",
                "mode": "real",
                "target_path": str(target),
                "workbench_url": "http://127.0.0.1:8766/#issues/MCA-001",
                "execution_evidence_text": "fake-codex demo full succeeded with dry-run evidence",
                "recorded_at": "2026-06-26T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_dogfood_result_packet.py"), str(packet)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "dogfood closure rejected: OFFLINE_REGRESSION" in result.stderr
    assert "fake-codex" in result.stderr


def test_product_closure_snapshot_marks_fake_execution_offline_regression(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_execution_result(
        ExecutionResult(
            id="execution_fake_success",
            ticket_id="ticket_ari_003",
            backend_name="fake-codex",
            dry_run=False,
            blocked=False,
            command="fake-codex",
            exit_code=0,
            changed_files=["demo_todo/cli.py"],
            test_command="pytest",
            test_exit_code=0,
        )
    )

    snapshot = product_closure_snapshot(store)

    assert snapshot["status"] == OFFLINE_REGRESSION
    assert snapshot["mode"] == "offline_regression"
    assert "offline regression" in snapshot["summary"].lower()


def test_real_backend_success_without_browser_packet_is_not_closed(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    store.save_execution_result(
        ExecutionResult(
            id="execution_codex_cli_only",
            ticket_id="ticket_ari_003",
            backend_name="codex",
            dry_run=False,
            blocked=False,
            command="codex exec --cd target --prompt-file handoff.md",
            exit_code=0,
            changed_files=["mini_code_agent/cli.py"],
            test_command="pytest",
            test_exit_code=0,
        )
    )

    snapshot = product_closure_snapshot(store)

    assert snapshot["status"] == NOT_CLOSED
    assert snapshot["mode"] == "cli_only_success"
    assert "not browser closure" in snapshot["reason"]


def test_closure_packet_mode_blocked_is_diagnostic_not_real_closed(tmp_path: Path) -> None:
    packet = {
        "schema_version": "ariadne.browser_dogfood_closure.v1",
        "status": "REAL_CLOSED",
        "mode": "blocked-ok",
        "target_path": str(tmp_path),
        "workbench_url": "http://127.0.0.1:8766/#issues/MCA-001",
        "execution_evidence_text": "Codex CLI blocked by ARIADNE_ENABLE_EXTERNAL_EXECUTION",
        "recorded_at": "2026-06-26T00:00:00Z",
    }

    snapshot = evaluate_closure_packet(packet)

    assert snapshot["status"] == BLOCKED_WITH_EVIDENCE
    assert snapshot["mode"] == "blocked_diagnostic"
    assert "blocked before REAL_CLOSED" in snapshot["reason"]
