from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.models import (
    ArtifactType,
    BacklogOperation,
    BacklogOperationType,
    BacklogPreview,
    BacklogUpdateTrigger,
    FeishuWriteResult,
    ReleaseEvidencePacket,
)
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))
SYNC_SCRIPT = ROOT / "frontend" / "ariadne-workbench" / "scripts" / "sync-local-data.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required for workbench data sync")
def test_workbench_data_sync_includes_ticket_production_evidence(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = next(ticket for ticket in ingest_sources(store, SOURCE_FIXTURES) if ticket.key == "ARI-003")
    store.write_artifact(
        ticket.id,
        "run_llm_sync",
        ArtifactType.LLM_AGENT_RESULT,
        "llm_build_lead.json",
        json.dumps(
            {
                "role": "build_lead",
                "succeeded": True,
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
                "usage": {"total_tokens": 123},
                "output_json": {"summary": "Build lead accepted the ticket.", "decision": "verify"},
            }
        ),
        "DeepSeek LLM build lead result",
        metadata={
            "llm_role": "build_lead",
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "succeeded": True,
        },
    )
    store.save_feishu_write_result(
        FeishuWriteResult(
            id="feishu_sync",
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            plan_id="feishu_plan_sync",
            ok=True,
            dry_run=False,
            document_url="https://example.feishu.cn/docx/sync",
            operation_summary="created doc",
        )
    )
    store.save_release_evidence_packet(
        ReleaseEvidencePacket(
            id="release_evidence_sync",
            root_path=str(tmp_path),
            product_readiness_status="action_required",
            production_acceptance_status="ready",
            run_gate_status="action_required",
        )
    )
    store.save_backlog_preview(
        BacklogPreview(
            id="backlog_preview_sync",
            trigger_type=BacklogUpdateTrigger.MEMORY_GAP,
            trigger_ref="memory_record_sync",
            idempotency_key="backlog_preview_sync_key",
            base_ticket_fingerprint="fingerprint_sync",
            applied_update_id="backlog_update_sync",
            applied_at="2026-06-18T00:00:00Z",
            operations=[
                BacklogOperation(
                    id="operation_sync",
                    operation_type=BacklogOperationType.ADD_TICKET,
                    reason="Memory records are written but not searchable.",
                    ticket_key="ARI-999",
                    title="Index memory records",
                    priority="high",
                    metadata={"suggestion": {"suggested_build_decision": "code_task"}},
                )
            ],
            rationale="Previewed memory-gap backlog changes for ARI-003.",
            evidence_refs=[ticket.id, "memory_record_sync"],
            created_at="2026-06-18T00:00:00Z",
        )
    )

    output_path = tmp_path / "workbench.json"
    subprocess.run(
        ["node", str(SYNC_SCRIPT)],
        check=True,
        cwd=ROOT / "frontend" / "ariadne-workbench",
        env={
            **os.environ,
            "ARIADNE_WORKBENCH_ARIADNE_ROOT": str(tmp_path / ".ariadne"),
            "ARIADNE_WORKBENCH_OUTPUT_PATH": str(output_path),
        },
    )
    data = json.loads(output_path.read_text(encoding="utf-8"))
    synced_ticket = next(item for item in data["tickets"] if item["key"] == "ARI-003")

    assert synced_ticket["llmAgents"][0]["role"] == "build_lead"
    assert synced_ticket["llmAgents"][0]["provider"] == "deepseek"
    assert synced_ticket["llmAgents"][0]["totalTokens"] == 123
    assert synced_ticket["feishu"]["documentUrl"] == "https://example.feishu.cn/docx/sync"
    assert synced_ticket["releaseEvidence"]["productionAcceptanceStatus"] == "ready"
    assert data["backlogMutationPreview"]["status"] == "applied"
    assert data["backlogMutationPreview"]["previewId"] == "backlog_preview_sync"
    assert data["backlogMutationPreview"]["triggerType"] == "memory_gap"
    assert data["backlogMutationPreview"]["added"] == 1
    assert data["backlogChanges"][0]["previewId"] == "backlog_preview_sync"
    assert data["backlogChanges"][0]["triggerType"] == "memory_gap"
    assert data["backlogChanges"][0]["operationType"] == "add_ticket"
    assert data["backlogChanges"][0]["ticketKey"] == "ARI-999"
    assert data["releaseEvidence"]["id"] == "release_evidence_sync"
