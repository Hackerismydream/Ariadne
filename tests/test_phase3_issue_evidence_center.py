from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ariadne_ltb.interfaces.http.app import create_app
from ariadne_ltb.models import (
    ArtifactType,
    BuildDecision,
    BuildTicket,
    ExecutionResult,
    FailureReason,
    HandoffPacket,
    MemoryRecord,
    ReviewReport,
    ReviewVerdict,
    RouteDecision,
    SourceArtifact,
    SourceDocument,
    SourceEvidence,
    SourceType,
    TicketStatus,
    stable_id,
)
from ariadne_ltb.storage import AriadneStore


def _seed_issue_with_evidence(store: AriadneStore) -> BuildTicket:
    source = SourceDocument(
        id="source-mini-agent",
        source_type=SourceType.GITHUB_REPO,
        title="mini-SWE-agent repository",
        path_or_url="https://github.com/SWE-agent/mini-SWE-agent",
        content_hash="source-hash",
        summary="Small coding agent with trajectory, environment, and edit loop patterns.",
    )
    store.save_source_document(source)
    artifact = store.save_source_artifact(
        SourceArtifact(
            id="source-artifact-mini-agent",
            source_document_id=source.id,
            artifact_type="repository_understanding",
            payload_hash="",
            payload_path="",
            evidence_ids=[],
        ),
        {
            "architecture": "agent loop reads repo state, edits files, and records trajectory",
            "transferable_patterns": ["trajectory capture", "test command contract"],
        },
    )
    evidence = SourceEvidence(
        id="source-evidence-trajectory",
        source_document_id=source.id,
        artifact_id=artifact.id,
        locator="README.md#trajectory",
        quote_or_summary="mini-SWE-agent records the agent trajectory and execution results.",
        claim="Trajectory evidence should be visible in Ariadne issue detail.",
        confidence=0.91,
        content_hash="evidence-hash",
    )
    store.save_source_evidence(evidence)
    store.save_source_evidence(
        SourceEvidence(
            id="source-evidence-unrelated",
            source_document_id=source.id,
            artifact_id=artifact.id,
            locator="README.md#unrelated",
            quote_or_summary="This claim belongs to the same source but not this ticket.",
            claim="Unrelated source claims must not appear in this issue detail.",
            confidence=0.5,
            content_hash="unrelated-evidence-hash",
        )
    )

    ticket = BuildTicket(
        id="ticket-phase3",
        key="M0TR-003",
        title="Show run evidence in issue detail",
        description="Issue detail must explain source grounding, execution, review, memory, and next tickets.",
        source_type="github_repo",
        source_ref=source.path_or_url,
        status=TicketStatus.PLANNING,
        priority="P0",
        metadata={
            "target_project_id": "target-mini-agent",
            "source_document_id": source.id,
            "source_artifact_ids": [artifact.id],
            "evidence_refs": [evidence.id],
            "acceptance_criteria": ["Evidence center lists source claims.", "Execution artifacts can be opened."],
            "affected_modules": ["frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx"],
        },
    )
    store.save_ticket(ticket)
    next_ticket = BuildTicket(
        id="ticket-phase3-next",
        key="M0TR-004",
        title="Follow-up evidence repair",
        description="Repair any invalid evidence refs.",
        source_type="review_feedback",
        source_ref=ticket.key,
        status=TicketStatus.SUPERSEDED,
        priority="P1",
        metadata={"generated_from_ticket_key": ticket.key},
    )
    store.save_ticket(next_ticket)

    agent = store.resolve_agent_profile("codex")
    assignment = store.create_assignment(ticket, agent)
    route = RouteDecision(
        id=stable_id("route", ticket.id, assignment.id),
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        planner_name="deterministic",
        backend_name="codex",
        target_repo_path=str(store.root / "target"),
        build_decision=BuildDecision.CODE_TASK,
        reason="Phase 3 evidence-center test route.",
        selected_agent_id=agent.id,
        selected_agent_name=agent.name,
        skill_refs=["codex-handoff"],
    )
    store.save_route_decision(route)
    packet = store.save_handoff_packet(
        HandoffPacket(
            id=stable_id("handoff_packet", ticket.id, route.id),
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            route_decision_id=route.id,
            target_project_id="target-mini-agent",
            target_repo_path=str(store.root / "target"),
            allowed_paths=["ariadne_ltb/application/workbench_artifacts.py"],
            forbidden_actions=["commit", "push"],
            acceptance_criteria=["Evidence center lists source claims."],
            test_command="pytest tests/test_phase3_issue_evidence_center.py",
            evidence_refs=[evidence.id],
            markdown_path="",
            packet_hash="packet-hash",
        ),
        "# Handoff\n\nSource claim: Trajectory evidence should be visible.\n",
    )
    assignment = assignment.model_copy(
        deep=True,
        update={
            "metadata": assignment.metadata
            | {
                "route_decision_id": route.id,
                "handoff_packet_id": packet.id,
            }
        },
    )
    store.save_assignment(assignment)

    log_artifact = store.write_artifact(
        ticket.id,
        "run-phase3",
        ArtifactType.EXECUTION_LOG,
        "execution_log.json",
        '{"status":"blocked","reason":"external execution disabled"}\n',
        "Execution log",
        metadata={"stale": True, "stale_reason": "Superseded by a later execution attempt."},
    )
    empty_diff_artifact = store.write_artifact(
        ticket.id,
        "run-phase3",
        ArtifactType.GIT_DIFF,
        "diff.patch",
        "",
        "Empty diff artifact",
    )
    execution = ExecutionResult(
        id="execution-phase3",
        ticket_id=ticket.id,
        backend_name="codex",
        target_repo_path=str(store.root / "target"),
        dry_run=False,
        blocked=True,
        block_reason="external execution disabled",
        failure_reason=FailureReason.EXTERNAL_EXECUTION_BLOCKED,
        command="codex exec --prompt-file handoff.md",
        exit_code=1,
        stdout="",
        stderr="external execution disabled",
        changed_files=["README.md"],
        git_status_before="?? old_user_file.py\n",
        git_status_after="?? old_user_file.py\n",
        diff_artifact_id=empty_diff_artifact.id,
        execution_log_artifact_id=log_artifact.id,
        test_command="pytest",
        test_exit_code=None,
        assignment_id=assignment.id,
        handoff_file=packet.markdown_path,
    )
    store.save_execution_result(execution)
    dirty_execution = ExecutionResult(
        id="execution-dirty-base",
        ticket_id=ticket.id,
        backend_name="codex",
        target_repo_path=str(store.root / "target"),
        dry_run=False,
        blocked=True,
        block_reason="dirty base checkout",
        failure_reason=FailureReason.DIRTY_BASE_CHECKOUT,
        command="codex exec",
        exit_code=1,
        git_status_before="?? old_user_file.py\n",
        git_status_after="?? old_user_file.py\n",
    )
    store.save_execution_result(dirty_execution)
    store.save_review_report(
        ReviewReport(
            id="review-phase3",
            ticket_id=ticket.id,
            verdict=ReviewVerdict.BLOCKED,
            failed_checks=["External execution gate blocked before code changed."],
            warnings=["No diff can be credited to the agent."],
        )
    )
    store.save_memory_record(
        MemoryRecord(
            id="memory-phase3",
            ticket_id=ticket.id,
            title=ticket.title,
            decision_log_entry="Blocked run must be visible as blocked evidence.",
            build_summary="No code changed because external execution was gated.",
            review_summary="Reviewer blocked the run.",
            source_refs=[source.id],
            artifact_refs=[log_artifact.id],
            next_actions=["Enable gated execution or repair the blocker."],
        )
    )
    return ticket


def test_issue_detail_projects_categorized_evidence_center(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = _seed_issue_with_evidence(store)
    client = TestClient(create_app(tmp_path))

    response = client.get(f"/api/issues/{ticket.key}")

    assert response.status_code == 200, response.text
    issue = response.json()["issue"]
    assert issue["acceptance_criteria"] == [
        "Evidence center lists source claims.",
        "Execution artifacts can be opened.",
    ]
    assert issue["affected_modules"] == ["frontend/ariadne-workbench/src/pages/issues/IssueDetail.tsx"]
    sections = {section["category"]: section for section in issue["evidence_sections"]}
    assert {"source", "handoff", "route", "execution", "review", "memory", "next_ticket"} <= set(sections)
    source_text = "\n".join(item["excerpt"] for item in sections["source"]["items"])
    assert "Trajectory evidence should be visible" in source_text
    assert "Unrelated source claims must not appear" not in source_text
    execution_validities = {item["validity"] for item in sections["execution"]["items"]}
    assert "empty" in execution_validities
    assert "dirty_before_run" in execution_validities
    assert "stale" in execution_validities
    assert any(item["validity"] == "stale" for item in sections["next_ticket"]["items"])


def test_issue_evidence_detail_endpoint_opens_readable_content(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = _seed_issue_with_evidence(store)
    client = TestClient(create_app(tmp_path))
    issue = client.get(f"/api/issues/{ticket.key}").json()["issue"]
    evidence_item = next(
        item
        for section in issue["evidence_sections"]
        for item in section["items"]
        if item["ref_type"] == "handoff_packet"
    )

    response = client.get(f"/api/issues/{ticket.key}/evidence/{evidence_item['id']}")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema_version"] == "ariadne.issue-evidence.v1"
    assert payload["issue_key"] == ticket.key
    assert payload["evidence"]["id"] == evidence_item["id"]
    assert "Source claim" in payload["content_excerpt"]


def test_issue_evidence_reader_bounds_large_artifacts_and_blocks_outside_store(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = _seed_issue_with_evidence(store)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("secret-outside-store", encoding="utf-8")
    external_artifact = store.write_artifact(
        ticket.id,
        "run-phase3",
        ArtifactType.EXECUTION_LOG,
        "external-pointer.txt",
        "placeholder",
        "Unsafe external pointer",
    )
    store._write_model(  # noqa: SLF001 - test intentionally corrupts artifact pointer.
        store.artifact_index_dir / f"{external_artifact.id}.json",
        external_artifact.model_copy(update={"path": str(outside)}),
    )
    large_artifact = store.write_artifact(
        ticket.id,
        "run-phase3-large",
        ArtifactType.EXECUTION_LOG,
        "large-execution.log",
        "x" * 20_000,
        "Large execution log",
    )
    execution = ExecutionResult(
        id="execution-large-log",
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        blocked=False,
        command="codex exec",
        exit_code=0,
        execution_log_artifact_id=large_artifact.id,
    )
    store.save_execution_result(execution)
    unsafe_execution = ExecutionResult(
        id="execution-unsafe-log",
        ticket_id=ticket.id,
        backend_name="codex",
        dry_run=False,
        blocked=False,
        command="codex exec",
        exit_code=0,
        execution_log_artifact_id=external_artifact.id,
    )
    store.save_execution_result(unsafe_execution)
    client = TestClient(create_app(tmp_path))
    issue = client.get(f"/api/issues/{ticket.key}").json()["issue"]
    large_item = next(
        item
        for section in issue["evidence_sections"]
        for item in section["items"]
        if item["ref_id"] == large_artifact.id
    )
    unsafe_item = next(
        item
        for section in issue["evidence_sections"]
        for item in section["items"]
        if item["ref_id"] == external_artifact.id
    )

    large_response = client.get(f"/api/issues/{ticket.key}/evidence/{large_item['id']}")
    unsafe_response = client.get(f"/api/issues/{ticket.key}/evidence/{unsafe_item['id']}")

    assert large_response.status_code == 200, large_response.text
    assert len(large_response.json()["content_excerpt"]) <= 8_000
    assert unsafe_response.status_code == 200, unsafe_response.text
    assert unsafe_response.json()["evidence"]["validity"] == "missing"
    assert "secret-outside-store" not in unsafe_response.json()["content_excerpt"]
