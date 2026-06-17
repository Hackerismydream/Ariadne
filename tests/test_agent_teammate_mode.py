from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from ariadne_ltb.cli import app
from ariadne_ltb.daemon import LocalDaemonWorker
from ariadne_ltb.ingest import ingest_sources
from ariadne_ltb.journal import build_resume_plan
from ariadne_ltb.local_safety import DirectoryLock, list_locks
from ariadne_ltb.models import (
    AssignmentStatus,
    ArtifactType,
    CommentKind,
    RuntimeEvent,
)
from ariadne_ltb.storage import AriadneStore


ROOT = Path(__file__).resolve().parents[1]
SOURCE_FIXTURES = sorted((ROOT / "examples" / "sources").glob("*.md"))


def test_default_agent_profiles_and_cli_list(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    profiles = store.ensure_default_agent_profiles()
    profile_ids = {profile.id for profile in profiles}

    assert {"build-lead", "fake-codex", "codex", "claude-code", "reviewer", "memory"}.issubset(
        profile_ids
    )
    assert store.resolve_agent_profile("fake-codex").backend_name == "fake-codex"

    result = CliRunner().invoke(app, ["--root", str(tmp_path), "agent", "list"])

    assert result.exit_code == 0, result.output
    assert "fake-codex" in result.output
    assert "claude-code" in result.output


def test_default_build_team_and_cli_show(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    teams = store.ensure_default_build_teams()
    runner = CliRunner()

    listing = runner.invoke(app, ["--root", str(tmp_path), "team", "list"])
    show = runner.invoke(app, ["--root", str(tmp_path), "team", "show", "build-team"])

    assert {team.id for team in teams} == {"build-team"}
    assert listing.exit_code == 0, listing.output
    assert "Ariadne Build Team" in listing.output
    assert "implementer=codex" in listing.output
    assert show.exit_code == 0, show.output
    assert "lead: build-lead" in show.output
    assert "backend: codex" in show.output


def test_ticket_assign_creates_assignment_comment_and_journal(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )

    ticket = store.resolve_ticket("ARI-003")
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    comments = store.list_comments(ticket.id)
    events = store.list_runtime_events_for_ticket(ticket.id)

    assert result.exit_code == 0, result.output
    assert "Assignment created" in result.output
    assert assignment is not None
    assert assignment.status is AssignmentStatus.QUEUED
    assert ticket.metadata["assigned_agent_id"] == "fake-codex"
    assert ticket.metadata["latest_assignment_id"] == assignment.id
    assert any(comment.kind is CommentKind.ASSIGNMENT for comment in comments)
    assert any(event.stage == "assignment" and event.event_type == "queued" for event in events)
    assert all(event.idempotency_key for event in events)


def test_ticket_assign_to_build_team_routes_before_assignment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "build-team"],
    )

    ticket = store.resolve_ticket("ARI-003")
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    artifacts = [store.load_artifact(artifact_id) for artifact_id in ticket.artifact_ids]
    route_artifacts = [
        artifact for artifact in artifacts if artifact.artifact_type is ArtifactType.ROUTE_DECISION
    ]
    route_json = json.loads(Path(route_artifacts[-1].path).read_text(encoding="utf-8"))
    comments = store.list_comments(ticket.id)
    events = store.list_runtime_events_for_ticket(ticket.id)
    board = (store.board_dir / "index.md")

    assert result.exit_code == 0, result.output
    assert "Build Team routed: build-team" in result.output
    assert assignment is not None
    assert assignment.agent_id == "codex"
    assert assignment.backend_name == "codex"
    assert assignment.assigned_by == "Build Lead"
    assert assignment.metadata["build_team_id"] == "build-team"
    assert ticket.metadata["assigned_team_id"] == "build-team"
    assert ticket.metadata["latest_route_decision_artifact_id"] == route_artifacts[-1].id
    assert route_json["build_team_id"] == "build-team"
    assert route_json["selected_agent_id"] == "codex"
    assert route_json["backend_name"] == "codex"
    assert route_json["team_role_agent_ids"]["reviewer"] == "reviewer"
    assert route_json["team_role_agent_ids"]["memory"] == "memory"
    assert any(comment.kind is CommentKind.ROUTE for comment in comments)
    assert any(event.stage == "route" and event.event_type == "succeeded" for event in events)

    from ariadne_ltb.board import export_board

    export_board(store)
    board_text = board.read_text(encoding="utf-8")
    assert "## Build Teams" in board_text
    assert "Build Team: `build-team`" in board_text
    assert "Selected agent: `codex`" in board_text


def test_daemon_runs_build_team_assignment(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    assign = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "build-team"],
    )
    assert assign.exit_code == 0, assign.output

    result = LocalDaemonWorker(store).run_once()
    ticket = store.resolve_ticket("ARI-003")
    assignment = store.find_latest_assignment_for_ticket(ticket.id)

    assert result.did_work is True
    assert result.ticket_run_result is not None
    assert assignment is not None
    assert assignment.status is AssignmentStatus.BLOCKED
    assert result.ticket_run_result.backend_name == "codex"


def test_human_comment_cli_and_ticket_comments(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    runner = CliRunner()

    add = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "comment", ticket.key, "please prioritize this"],
    )
    show = runner.invoke(app, ["--root", str(tmp_path), "ticket", "comments", ticket.key])

    assert add.exit_code == 0, add.output
    assert show.exit_code == 0, show.output
    assert "please prioritize this" in show.output
    assert store.list_comments(ticket.id)[-1].kind is CommentKind.COMMENT


def test_daemon_run_once_claims_assignment_and_writes_teammate_trace(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ingest_sources(store, SOURCE_FIXTURES)
    runner = CliRunner()
    assign = runner.invoke(
        app,
        ["--root", str(tmp_path), "ticket", "assign", "ARI-003", "--to", "fake-codex"],
    )
    assert assign.exit_code == 0, assign.output

    result = runner.invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])

    ticket = store.resolve_ticket("ARI-003")
    assignment = store.find_latest_assignment_for_ticket(ticket.id)
    comments = store.list_comments(ticket.id)
    events = store.list_runtime_events_for_ticket(ticket.id)
    board = (tmp_path / ".ariadne" / "board" / "index.md").read_text(encoding="utf-8")

    assert result.exit_code == 0, result.output
    assert "Assignment claimed" in result.output
    assert "reviewer verdict: pass" in result.output
    assert assignment is not None
    assert assignment.status is AssignmentStatus.DONE
    assert any(comment.kind is CommentKind.PROGRESS for comment in comments)
    assert any(comment.kind is CommentKind.REVIEW for comment in comments)
    assert any(comment.kind is CommentKind.MEMORY for comment in comments)
    assert any(event.stage == "claim" and event.event_type == "claimed" for event in events)
    assert any(event.stage == "board" and event.event_type == "succeeded" for event in events)
    assert "## Agent Assignment" in board
    assert "## Comments" in board
    assert "## Runtime Journal" in board
    assert "## Daemon / Worker" in board


def test_daemon_run_once_reports_no_work(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["--root", str(tmp_path), "daemon", "run-once"])

    assert result.exit_code == 0, result.output
    assert "no work" in result.output.lower()


def test_daemon_blocks_assignment_when_backend_blocks(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    result = LocalDaemonWorker(store).run_once()

    comments = store.list_comments(ticket.id)
    updated = store.load_assignment(assignment.id)

    assert result.assignment_id == assignment.id
    assert updated.status in {AssignmentStatus.BLOCKED, AssignmentStatus.FAILED}
    assert any(comment.kind is CommentKind.BLOCKER for comment in comments)


def test_runtime_journal_and_recovery_plan(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    event = RuntimeEvent(
        id="event_test",
        ticket_id=ticket.id,
        ticket_key=ticket.key,
        assignment_id=assignment.id,
        runtime_id="local",
        stage="claim",
        event_type="claimed",
        actor="fake-codex",
        idempotency_key="claim:test",
    )
    store.append_runtime_event(event)

    events = store.list_runtime_events_for_ticket(ticket.id)
    plan = build_resume_plan(store, ticket)
    output = CliRunner().invoke(app, ["--root", str(tmp_path), "runtime", "journal", "--limit", "5"])

    assert events[-1].idempotency_key == "claim:test"
    assert plan.ticket_id == ticket.id
    assert plan.recommended_command is not None
    assert output.exit_code == 0, output.output
    assert "claim" in output.output


def test_runtime_recover_and_ticket_resume_are_conservative(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    ticket = ingest_sources(store, [SOURCE_FIXTURES[0]])[0]
    assignment = store.create_assignment(ticket, store.resolve_agent_profile("fake-codex"))
    assignment = assignment.mark_claimed("local")
    store.save_assignment(assignment)
    runner = CliRunner()

    recover = runner.invoke(app, ["--root", str(tmp_path), "runtime", "recover"])
    resume = runner.invoke(app, ["--root", str(tmp_path), "ticket", "resume", ticket.key])

    assert recover.exit_code == 0, recover.output
    assert "recommended: ari ticket resume" in recover.output
    assert resume.exit_code == 2
    assert "blocked" in resume.output.lower()
    assert any(comment.kind is CommentKind.RECOVERY for comment in store.list_comments(ticket.id))


def test_runtime_locks_detects_stale_and_requires_force(tmp_path: Path) -> None:
    store = AriadneStore(tmp_path)
    target = tmp_path / "repo"
    target.mkdir()
    lock = DirectoryLock(store, target, runtime_id="local", ticket_id="ticket", assignment_id="assign")
    lock.acquire()
    metadata = json.loads(lock.lock_path.read_text(encoding="utf-8"))
    metadata["heartbeat_at"] = "2000-01-01T00:00:00Z"
    lock.lock_path.write_text(json.dumps(metadata), encoding="utf-8")

    locks = list_locks(store)
    no_force = CliRunner().invoke(app, ["--root", str(tmp_path), "runtime", "locks"])

    assert locks[0].stale is True
    assert no_force.exit_code == 0, no_force.output
    assert lock.lock_path.exists()
    forced = CliRunner().invoke(
        app,
        ["--root", str(tmp_path), "runtime", "locks", "--force-stale-locks"],
    )
    assert forced.exit_code == 0, forced.output
    assert not lock.lock_path.exists()
