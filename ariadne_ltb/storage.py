from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from typing import Iterator
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from ariadne_ltb.models import (
    AgentRun,
    AgentHandoff,
    AgentProfile,
    Artifact,
    ArtifactType,
    AssignmentStatus,
    BacklogUpdate,
    BuildPacket,
    BuildTeam,
    BuildTicket,
    CommentAuthorType,
    CommentKind,
    ExecutionResult,
    FeishuWriteResult,
    FeishuWritePlan,
    GitHubIntegrationResult,
    MemoryRecord,
    ProjectResource,
    ProjectSpace,
    ReviewReport,
    RuntimeEvent,
    RunMessage,
    RunMessageType,
    RuntimeCapability,
    SourceDocument,
    TicketAssignment,
    TicketStatus,
    TicketComment,
    WorkerHeartbeat,
    WorktreeIsolation,
    stable_id,
    utc_now,
)

T = TypeVar("T", bound=BaseModel)


class AriadneStore:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root).resolve()
        self.base = self.root / ".ariadne"
        self.project_space_path = self.base / "project_space.json"
        self.agents_dir = self.base / "agents"
        self.agent_profiles_path = self.agents_dir / "profiles.json"
        self.build_teams_path = self.agents_dir / "teams.json"
        self.assignments_dir = self.base / "assignments"
        self.assignment_claim_lock_path = self.assignments_dir / ".claim.lock"
        self.comments_dir = self.base / "comments"
        self.journal_dir = self.base / "journal"
        self.journal_path = self.journal_dir / "events.jsonl"
        self.daemon_dir = self.base / "daemon"
        self.daemon_heartbeats_dir = self.daemon_dir / "heartbeats"
        self.daemon_state_path = self.daemon_dir / "state.json"
        self.handoffs_dir = self.base / "handoffs"
        self.tickets_dir = self.base / "tickets"
        self.runs_dir = self.base / "runs"
        self.build_packets_dir = self.base / "build_packets"
        self.sources_dir = self.base / "sources"
        self.skill_materializations_dir = self.base / "skills"
        self.execution_results_dir = self.base / "execution_results"
        self.memory_dir = self.base / "memory"
        self.project_dir = self.base / "project"
        self.runtimes_dir = self.base / "runtimes"
        self.locks_dir = self.base / "locks"
        self.worktrees_dir = self.base / "worktrees"
        self.worktree_records_dir = self.worktrees_dir / "records"
        self.backlog_dir = self.base / "backlog"
        self.backlog_updates_path = self.backlog_dir / "updates.jsonl"
        self.reviews_dir = self.base / "reviews"
        self.feishu_plans_dir = self.base / "feishu_plans"
        self.integrations_dir = self.base / "integrations"
        self.feishu_integrations_dir = self.integrations_dir / "feishu"
        self.github_integrations_dir = self.integrations_dir / "github"
        self.artifacts_dir = self.base / "artifacts"
        self.artifact_index_dir = self.base / "artifact_index"
        self.board_dir = self.base / "board"
        self.doctor_dir = self.base / "doctor"
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        for directory in [
            self.base,
            self.agents_dir,
            self.assignments_dir,
            self.comments_dir,
            self.journal_dir,
            self.daemon_dir,
            self.daemon_heartbeats_dir,
            self.handoffs_dir,
            self.tickets_dir,
            self.runs_dir,
            self.sources_dir,
            self.skill_materializations_dir,
            self.build_packets_dir,
            self.execution_results_dir,
            self.memory_dir,
            self.memory_dir / "tickets",
            self.memory_dir / "build_packets",
            self.memory_dir / "reviews",
            self.project_dir,
            self.runtimes_dir,
            self.locks_dir,
            self.worktrees_dir,
            self.worktree_records_dir,
            self.backlog_dir,
            self.reviews_dir,
            self.feishu_plans_dir,
            self.integrations_dir,
            self.feishu_integrations_dir,
            self.github_integrations_dir,
            self.artifacts_dir,
            self.artifact_index_dir,
            self.board_dir,
            self.doctor_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def _write_model(self, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            model.model_dump_json(indent=2, exclude_none=False) + "\n",
            encoding="utf-8",
        )

    def _read_model(self, path: Path, model_type: type[T]) -> T:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def save_project_space(self, project_space: ProjectSpace) -> None:
        self._write_model(self.project_space_path, project_space)

    def load_project_space(self) -> ProjectSpace:
        return self._read_model(self.project_space_path, ProjectSpace)

    def save_agent_profiles(self, profiles: list[AgentProfile]) -> None:
        self.agent_profiles_path.write_text(
            json.dumps(
                {"profiles": [profile.model_dump(mode="json") for profile in profiles]},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def load_agent_profiles(self) -> list[AgentProfile]:
        if not self.agent_profiles_path.exists():
            return []
        data = json.loads(self.agent_profiles_path.read_text(encoding="utf-8"))
        return [AgentProfile.model_validate(item) for item in data.get("profiles", [])]

    def ensure_default_agent_profiles(self) -> list[AgentProfile]:
        profiles = self.load_agent_profiles()
        existing = {profile.id: profile for profile in profiles}
        defaults = _default_agent_profiles()
        changed = False
        for profile in defaults:
            if profile.id not in existing:
                existing[profile.id] = profile
                changed = True
        merged = sorted(existing.values(), key=lambda profile: profile.id)
        if changed or not profiles:
            self.save_agent_profiles(merged)
        return merged

    def resolve_agent_profile(self, agent_id_or_name: str) -> AgentProfile:
        normalized = agent_id_or_name.lower()
        for profile in self.ensure_default_agent_profiles():
            if profile.id.lower() == normalized or profile.name.lower() == normalized:
                if not profile.enabled:
                    msg = f"agent profile is disabled: {agent_id_or_name}"
                    raise ValueError(msg)
                return profile
        msg = f"unknown agent profile: {agent_id_or_name}"
        raise FileNotFoundError(msg)

    def save_build_teams(self, teams: list[BuildTeam]) -> None:
        self.build_teams_path.write_text(
            json.dumps(
                {"teams": [team.model_dump(mode="json") for team in teams]},
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def load_build_teams(self) -> list[BuildTeam]:
        if not self.build_teams_path.exists():
            return []
        data = json.loads(self.build_teams_path.read_text(encoding="utf-8"))
        return [BuildTeam.model_validate(item) for item in data.get("teams", [])]

    def ensure_default_build_teams(self) -> list[BuildTeam]:
        teams = self.load_build_teams()
        existing = {team.id: team for team in teams}
        defaults = _default_build_teams()
        changed = False
        for team in defaults:
            if team.id not in existing:
                existing[team.id] = team
                changed = True
        merged = sorted(existing.values(), key=lambda team: team.id)
        if changed or not teams:
            self.save_build_teams(merged)
        return merged

    def resolve_build_team(self, team_id_or_name: str) -> BuildTeam:
        normalized = team_id_or_name.lower()
        for team in self.ensure_default_build_teams():
            if team.id.lower() == normalized or team.name.lower() == normalized:
                if not team.enabled:
                    msg = f"build team is disabled: {team_id_or_name}"
                    raise ValueError(msg)
                return team
        msg = f"unknown build team: {team_id_or_name}"
        raise FileNotFoundError(msg)

    def save_ticket(self, ticket: BuildTicket) -> None:
        self._write_model(self.tickets_dir / f"{ticket.id}.json", ticket)

    def load_ticket(self, ticket_id: str) -> BuildTicket:
        return self._read_model(self.tickets_dir / f"{ticket_id}.json", BuildTicket)

    def resolve_ticket(self, ticket_id_or_key: str) -> BuildTicket:
        direct_path = self.tickets_dir / f"{ticket_id_or_key}.json"
        if direct_path.exists():
            return self.load_ticket(ticket_id_or_key)
        normalized = ticket_id_or_key.upper()
        for ticket in self.list_tickets():
            if ticket.key.upper() == normalized:
                return ticket
        msg = f"unknown ticket: {ticket_id_or_key}"
        raise FileNotFoundError(msg)

    def list_tickets(self) -> list[BuildTicket]:
        tickets = [
            self._read_model(path, BuildTicket)
            for path in sorted(self.tickets_dir.glob("*.json"))
        ]
        return sorted(tickets, key=lambda ticket: ticket.key)

    def create_assignment(
        self,
        ticket: BuildTicket,
        agent: AgentProfile,
        backend_name: str | None = None,
        assigned_by: str = "human",
    ) -> TicketAssignment:
        assignment = TicketAssignment(
            id=stable_id("assignment", ticket.id, agent.id, utc_now()),
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            agent_id=agent.id,
            agent_name=agent.name,
            backend_name=backend_name or agent.backend_name,
            planner_name=agent.planner_name,
            priority=ticket.priority,
            assigned_by=assigned_by,
        )
        self.save_assignment(assignment)
        comment = TicketComment(
            id=stable_id("comment", ticket.id, assignment.id, "assignment"),
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            author_type=CommentAuthorType.SYSTEM,
            author="Ariadne",
            kind=CommentKind.ASSIGNMENT,
            body=f"Assignment created: {ticket.key} -> {agent.name}.",
            thread_id=assignment.id,
            payload_ref=assignment.id,
        )
        self.append_comment(comment)
        self.append_runtime_event(
            RuntimeEvent(
                id=stable_id("event", assignment.id, "assignment", "queued"),
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                assignment_id=assignment.id,
                runtime_id="local",
                stage="assignment",
                event_type="queued",
                actor="Ariadne",
                payload_ref=assignment.id,
                idempotency_key=f"assignment:{assignment.id}:queued",
            )
        )
        updated = ticket.model_copy(
            deep=True,
            update={
                "metadata": ticket.metadata
                | {
                    "assigned_agent_id": agent.id,
                    "assigned_agent_name": agent.name,
                    "latest_assignment_id": assignment.id,
                }
            },
        )
        self.save_ticket(updated)
        return assignment

    def save_assignment(self, assignment: TicketAssignment) -> None:
        self._write_model(self.assignments_dir / f"{assignment.id}.json", assignment)

    def load_assignment(self, assignment_id: str) -> TicketAssignment:
        return self._read_model(
            self.assignments_dir / f"{assignment_id}.json",
            TicketAssignment,
        )

    def list_assignments(self) -> list[TicketAssignment]:
        return [
            self._read_model(path, TicketAssignment)
            for path in sorted(self.assignments_dir.glob("*.json"))
        ]

    def list_assignments_for_ticket(self, ticket_id: str) -> list[TicketAssignment]:
        return sorted(
            [assignment for assignment in self.list_assignments() if assignment.ticket_id == ticket_id],
            key=lambda assignment: (assignment.attempt, assignment.created_at),
        )

    def list_open_assignments(self) -> list[TicketAssignment]:
        return [
            assignment
            for assignment in self.list_assignments()
            if assignment.status
            in {
                AssignmentStatus.QUEUED,
                AssignmentStatus.CLAIMED,
                AssignmentStatus.RUNNING,
            }
        ]

    def claim_next_assignment(
        self,
        runtime_id: str,
        lease_seconds: int = 600,
    ) -> TicketAssignment | None:
        with self._assignment_claim_lock():
            for assignment in sorted(self.list_assignments(), key=lambda item: item.created_at):
                if not self._claimable_assignment(assignment):
                    continue
                try:
                    ticket = self.load_ticket(assignment.ticket_id)
                except FileNotFoundError:
                    continue
                if ticket.status is TicketStatus.SUPERSEDED:
                    self.save_assignment(
                        assignment.mark_cancelled("Ticket is superseded and cannot be claimed.")
                    )
                    continue
                metadata = assignment.metadata
                if assignment.status in {AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING}:
                    metadata = metadata | {
                        "lease_reclaimed_at": utc_now(),
                        "lease_reclaimed_from_runtime_id": assignment.claimed_by_runtime_id,
                        "lease_reclaimed_from_status": assignment.status.value,
                    }
                claimed = assignment.mark_claimed(runtime_id, lease_seconds=lease_seconds)
                claimed = claimed.model_copy(
                    deep=True,
                    update={
                        "started_at": None,
                        "ended_at": None,
                        "blocker": None,
                        "failure_reason": None,
                        "metadata": metadata,
                    },
                )
                self.save_assignment(claimed)
                return claimed
        return None

    @contextmanager
    def _assignment_claim_lock(self) -> Iterator[None]:
        self.assignment_claim_lock_path.parent.mkdir(parents=True, exist_ok=True)
        with self.assignment_claim_lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.seek(0)
                handle.truncate()
                handle.write(json.dumps({"pid": __import__("os").getpid(), "locked_at": utc_now()}))
                handle.flush()
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _claimable_assignment(self, assignment: TicketAssignment) -> bool:
        if assignment.status is AssignmentStatus.QUEUED:
            return True
        if assignment.status in {AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING}:
            return is_assignment_lease_expired(assignment)
        return False

    def find_latest_assignment_for_ticket(self, ticket_id: str) -> TicketAssignment | None:
        assignments = self.list_assignments_for_ticket(ticket_id)
        if not assignments:
            return None
        return assignments[-1]

    def append_comment(self, comment: TicketComment) -> None:
        path = self.comments_dir / f"{comment.ticket_id}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(comment.model_dump_json(exclude_none=False) + "\n")

    def add_comment(
        self,
        ticket: BuildTicket,
        author_type: CommentAuthorType,
        author: str,
        kind: CommentKind,
        body: str,
        payload_ref: str | None = None,
        parent_comment_id: str | None = None,
        thread_id: str | None = None,
    ) -> TicketComment:
        parent = self.find_comment(ticket.id, parent_comment_id) if parent_comment_id else None
        if parent_comment_id and parent is None:
            msg = f"parent comment not found: {parent_comment_id}"
            raise ValueError(msg)
        if parent is not None and thread_id is not None and thread_id != parent.thread_id:
            msg = f"thread_id does not match parent thread: {thread_id}"
            raise ValueError(msg)
        created_at = utc_now()
        comment = TicketComment(
            id=stable_id("comment", ticket.id, author, kind.value, body, created_at),
            ticket_id=ticket.id,
            ticket_key=ticket.key,
            author_type=author_type,
            author=author,
            kind=kind,
            body=body,
            parent_comment_id=parent_comment_id,
            thread_id=parent.thread_id if parent else thread_id,
            payload_ref=payload_ref,
            created_at=created_at,
        )
        self.append_comment(comment)
        return comment

    def list_comments(
        self,
        ticket_id: str,
        since: str | None = None,
        tail: int | None = None,
    ) -> list[TicketComment]:
        path = self.comments_dir / f"{ticket_id}.jsonl"
        if not path.exists():
            return []
        comments = [
            TicketComment.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if since is not None:
            comments = [comment for comment in comments if comment.created_at > since]
        if tail is not None:
            comments = comments[-tail:]
        return comments

    def find_comment(self, ticket_id: str, comment_id: str | None) -> TicketComment | None:
        if comment_id is None:
            return None
        for comment in self.list_comments(ticket_id):
            if comment.id == comment_id:
                return comment
        return None

    def list_comment_roots(self, ticket_id: str) -> list[TicketComment]:
        return [comment for comment in self.list_comments(ticket_id) if comment.parent_comment_id is None]

    def list_comment_thread(self, ticket_id: str, thread_id_or_comment_id: str) -> list[TicketComment]:
        comments = self.list_comments(ticket_id)
        thread_id = thread_id_or_comment_id
        for comment in comments:
            if comment.id == thread_id_or_comment_id:
                thread_id = comment.thread_id or comment.id
                break
        return [comment for comment in comments if comment.thread_id == thread_id]

    def list_recent_comment_threads(self, ticket_id: str, limit: int = 5) -> list[list[TicketComment]]:
        grouped: dict[str, list[TicketComment]] = {}
        for comment in self.list_comments(ticket_id):
            grouped.setdefault(comment.thread_id or comment.id, []).append(comment)
        threads = sorted(
            grouped.values(),
            key=lambda thread: thread[-1].created_at if thread else "",
            reverse=True,
        )
        return threads[:limit]

    def append_runtime_event(self, event: RuntimeEvent) -> None:
        with self.journal_path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json(exclude_none=False) + "\n")

    def save_worker_heartbeat(self, heartbeat: WorkerHeartbeat) -> Path:
        path = self.daemon_heartbeats_dir / f"{heartbeat.runtime_id}.json"
        self._write_model(path, heartbeat)
        self._write_model(self.daemon_state_path, heartbeat)
        return path

    def load_worker_heartbeat(self, runtime_id: str) -> WorkerHeartbeat:
        return self._read_model(
            self.daemon_heartbeats_dir / f"{runtime_id}.json",
            WorkerHeartbeat,
        )

    def list_worker_heartbeats(self) -> list[WorkerHeartbeat]:
        heartbeats: list[WorkerHeartbeat] = []
        for path in sorted(self.daemon_heartbeats_dir.glob("*.json")):
            try:
                heartbeats.append(self._read_model(path, WorkerHeartbeat))
            except (ValidationError, OSError):
                continue
        return heartbeats

    def save_handoff(self, handoff: AgentHandoff) -> None:
        self._write_model(self.handoffs_dir / f"{handoff.id}.json", handoff)

    def load_handoff(self, handoff_id: str) -> AgentHandoff:
        return self._read_model(self.handoffs_dir / f"{handoff_id}.json", AgentHandoff)

    def list_handoffs_for_ticket(self, ticket_id: str) -> list[AgentHandoff]:
        handoffs = [
            self._read_model(path, AgentHandoff)
            for path in sorted(self.handoffs_dir.glob("*.json"))
        ]
        order = {
            ("Build Lead", "Planner"): 1,
            ("Planner", "Execution"): 2,
            ("Execution", "Reviewer"): 3,
            ("Reviewer", "Execution"): 4,
            ("Reviewer", "Memory"): 5,
            ("Memory", "Build Lead"): 6,
        }
        return sorted(
            [handoff for handoff in handoffs if handoff.ticket_id == ticket_id],
            key=lambda handoff: (
                handoff.created_at,
                order.get((handoff.from_agent, handoff.to_agent), 99),
                handoff.id,
            ),
        )

    def list_runtime_events(self) -> list[RuntimeEvent]:
        if not self.journal_path.exists():
            return []
        return [
            RuntimeEvent.model_validate_json(line)
            for line in self.journal_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def list_runtime_events_for_ticket(self, ticket_id: str) -> list[RuntimeEvent]:
        return [event for event in self.list_runtime_events() if event.ticket_id == ticket_id]

    def save_backlog_update(self, update: BacklogUpdate) -> None:
        with self.backlog_updates_path.open("a", encoding="utf-8") as handle:
            handle.write(update.model_dump_json(exclude_none=False) + "\n")

    def list_backlog_updates(self) -> list[BacklogUpdate]:
        if not self.backlog_updates_path.exists():
            return []
        updates: list[BacklogUpdate] = []
        for line in self.backlog_updates_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                updates.append(BacklogUpdate.model_validate_json(line))
            except ValueError:
                continue
        return updates

    def list_backlog_updates_for_ticket(self, ticket_id: str) -> list[BacklogUpdate]:
        return [
            update
            for update in self.list_backlog_updates()
            if ticket_id in update.created_ticket_ids
            or ticket_id in update.updated_ticket_ids
            or ticket_id in update.superseded_ticket_ids
            or any(change.ticket_id == ticket_id for change in update.ticket_changes)
        ]

    def save_run(self, run: AgentRun) -> None:
        self._write_model(self.runs_dir / f"{run.id}.json", run)

    def load_run(self, run_id: str) -> AgentRun:
        return self._read_model(self.runs_dir / f"{run_id}.json", AgentRun)

    def run_messages_path(self, run_id: str) -> Path:
        return self.runs_dir / run_id / "messages.jsonl"

    def _run_messages_lock_path(self, run_id: str) -> Path:
        return self.runs_dir / run_id / ".messages.lock"

    @contextmanager
    def _run_messages_lock(self, run_id: str) -> Iterator[None]:
        lock_path = self._run_messages_lock_path(run_id)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def reset_run_messages(self, run_id: str) -> None:
        with self._run_messages_lock(run_id):
            path = self.run_messages_path(run_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def append_run_message(
        self,
        run_id: str,
        stage: str,
        message_type: RunMessageType,
        content: str,
        artifact_ref: str | None = None,
        tool_name: str | None = None,
        result_ref: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunMessage:
        with self._run_messages_lock(run_id):
            messages = self.list_run_messages(run_id)
            next_seq = (messages[-1].seq + 1) if messages else 1
            message = RunMessage(
                run_id=run_id,
                seq=next_seq,
                stage=stage,
                message_type=message_type,
                content=content,
                artifact_ref=artifact_ref,
                tool_name=tool_name,
                result_ref=result_ref,
                metadata=metadata or {},
            )
            path = self.run_messages_path(run_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(message.model_dump_json(exclude_none=False) + "\n")
            return message

    def list_run_messages(self, run_id: str, since: int | None = None) -> list[RunMessage]:
        path = self.run_messages_path(run_id)
        if not path.exists():
            return []
        messages = [
            RunMessage.model_validate_json(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if since is None:
            return messages
        return [message for message in messages if message.seq > since]

    def save_build_packet(self, packet: BuildPacket) -> None:
        self._write_model(self.build_packets_dir / f"{packet.id}.json", packet)

    def load_build_packet(self, packet_id: str) -> BuildPacket:
        return self._read_model(self.build_packets_dir / f"{packet_id}.json", BuildPacket)

    def save_source_document(self, source: SourceDocument) -> None:
        self._write_model(self.sources_dir / f"{source.id}.json", source)

    def load_source_document(self, source_id: str) -> SourceDocument:
        return self._read_model(self.sources_dir / f"{source_id}.json", SourceDocument)

    def list_source_documents(self) -> list[SourceDocument]:
        return [
            self._read_model(path, SourceDocument)
            for path in sorted(self.sources_dir.glob("*.json"))
        ]

    def save_execution_result(self, result: ExecutionResult) -> None:
        self._write_model(self.execution_results_dir / f"{result.id}.json", result)

    def load_execution_result(self, result_id: str) -> ExecutionResult:
        return self._read_model(self.execution_results_dir / f"{result_id}.json", ExecutionResult)

    def save_memory_record(self, record: MemoryRecord) -> None:
        self._write_model(self.memory_dir / "tickets" / f"{record.ticket_id}.json", record)

    def load_memory_record(self, ticket_id: str) -> MemoryRecord:
        return self._read_model(self.memory_dir / "tickets" / f"{ticket_id}.json", MemoryRecord)

    def list_memory_records(self) -> list[MemoryRecord]:
        records = [
            self._read_model(path, MemoryRecord)
            for path in sorted((self.memory_dir / "tickets").glob("*.json"))
        ]
        return sorted(records, key=lambda record: record.created_at)

    def save_review_report(self, review_report: ReviewReport) -> None:
        self._write_model(self.reviews_dir / f"{review_report.id}.json", review_report)

    def load_review_report(self, review_report_id: str) -> ReviewReport:
        return self._read_model(self.reviews_dir / f"{review_report_id}.json", ReviewReport)

    def list_review_reports(self) -> list[ReviewReport]:
        return [
            self._read_model(path, ReviewReport)
            for path in sorted(self.reviews_dir.glob("*.json"))
        ]

    def save_feishu_write_plan(self, write_plan: FeishuWritePlan) -> None:
        self._write_model(self.feishu_plans_dir / f"{write_plan.id}.json", write_plan)

    def load_feishu_write_plan(self, write_plan_id: str) -> FeishuWritePlan:
        return self._read_model(self.feishu_plans_dir / f"{write_plan_id}.json", FeishuWritePlan)

    def save_feishu_write_result(self, result: FeishuWriteResult) -> Path:
        path = self.feishu_integrations_dir / result.ticket_key / f"{result.id}.json"
        self._write_model(path, result)
        return path

    def list_feishu_write_results(self, ticket_key: str | None = None) -> list[FeishuWriteResult]:
        base = self.feishu_integrations_dir / ticket_key if ticket_key else self.feishu_integrations_dir
        paths = sorted(base.glob("*.json")) if ticket_key else sorted(base.glob("*/*.json"))
        return sorted(
            [self._read_model(path, FeishuWriteResult) for path in paths],
            key=lambda result: result.created_at,
        )

    def save_github_integration_result(self, result: GitHubIntegrationResult) -> Path:
        path = self.github_integrations_dir / result.ticket_key / f"{result.id}.json"
        self._write_model(path, result)
        return path

    def list_github_integration_results(
        self,
        ticket_key: str | None = None,
    ) -> list[GitHubIntegrationResult]:
        base = self.github_integrations_dir / ticket_key if ticket_key else self.github_integrations_dir
        paths = sorted(base.glob("*.json")) if ticket_key else sorted(base.glob("*/*.json"))
        return sorted(
            [self._read_model(path, GitHubIntegrationResult) for path in paths],
            key=lambda result: (result.created_at, _github_operation_order(result.operation)),
        )

    def save_project_resources(self, resources: list[ProjectResource]) -> Path:
        path = self.project_dir / "resources.json"
        path.write_text(
            json.dumps(
                {
                    "project_id": resources[0].project_id if resources else "ariadne-local",
                    "resources": [
                        resource.model_dump(mode="json", exclude_none=False)
                        for resource in resources
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def load_project_resources(self) -> list[ProjectResource]:
        path = self.project_dir / "resources.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [ProjectResource.model_validate(item) for item in data.get("resources", [])]

    def save_runtime_capabilities(self, capabilities: list[RuntimeCapability]) -> Path:
        path = self.runtimes_dir / "capability_snapshot.json"
        path.write_text(
            json.dumps(
                {
                    "capabilities": [
                        capability.model_dump(mode="json", exclude_none=False)
                        for capability in capabilities
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def load_runtime_capabilities(self) -> list[RuntimeCapability]:
        path = self.runtimes_dir / "capability_snapshot.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [RuntimeCapability.model_validate(item) for item in data.get("capabilities", [])]

    def write_artifact(
        self,
        ticket_id: str,
        agent_run_id: str,
        artifact_type: ArtifactType,
        filename: str,
        content: str,
        summary: str,
        metadata: dict | None = None,
    ) -> Artifact:
        ticket_artifacts_dir = self.artifacts_dir / ticket_id
        ticket_artifacts_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = ticket_artifacts_dir / filename
        artifact_path.write_text(content, encoding="utf-8")
        artifact = Artifact(
            id=stable_id("artifact", ticket_id, agent_run_id, artifact_type.value, filename),
            ticket_id=ticket_id,
            agent_run_id=agent_run_id,
            artifact_type=artifact_type,
            path=str(artifact_path),
            summary=summary,
            metadata=metadata or {},
        )
        self._write_model(self.artifact_index_dir / f"{artifact.id}.json", artifact)
        return artifact

    def load_artifact(self, artifact_id: str) -> Artifact:
        return self._read_model(self.artifact_index_dir / f"{artifact_id}.json", Artifact)

    def list_artifacts_for_ticket(self, ticket_id: str) -> list[Artifact]:
        artifacts = [
            self.load_artifact(path.stem)
            for path in sorted(self.artifact_index_dir.glob("*.json"))
        ]
        return [artifact for artifact in artifacts if artifact.ticket_id == ticket_id]

    def read_artifact_text(self, artifact: Artifact) -> str:
        return Path(artifact.path).read_text(encoding="utf-8")

    def read_artifact_json(self, artifact: Artifact) -> dict:
        return json.loads(self.read_artifact_text(artifact))

    def worktree_record_path(self, ticket_key: str) -> Path:
        return self.worktree_records_dir / f"{ticket_key.lower()}.json"

    def worktree_path(self, ticket_key: str) -> Path:
        return self.worktrees_dir / ticket_key.lower()

    def save_worktree_isolation(self, record: WorktreeIsolation) -> Path:
        path = Path(record.record_path)
        self._write_model(path, record)
        return path

    def load_worktree_isolation(self, ticket_key: str) -> WorktreeIsolation:
        return self._read_model(self.worktree_record_path(ticket_key), WorktreeIsolation)


def _default_agent_profiles() -> list[AgentProfile]:
    return [
        AgentProfile(
            id="build-lead",
            name="Build Lead",
            role="router",
            description="Routes tickets and writes route decisions.",
            capabilities=["route", "plan", "delegate"],
        ),
        AgentProfile(
            id="fake-codex",
            name="Fake Codex",
            role="coding_agent",
            backend_name="fake-codex",
            description="Safe deterministic local coding agent for demos and tests.",
            capabilities=["execute", "diff", "tests"],
        ),
        AgentProfile(
            id="codex",
            name="Codex",
            role="coding_agent",
            backend_name="codex",
            description="Safety-gated real Codex backend adapter.",
            capabilities=["execute", "diff", "tests", "external"],
        ),
        AgentProfile(
            id="claude-code",
            name="Claude Code",
            role="coding_agent",
            backend_name="claude-code",
            description="Safety-gated Claude Code backend scaffold.",
            capabilities=["execute", "diff", "tests", "external"],
        ),
        AgentProfile(
            id="reviewer",
            name="Reviewer",
            role="reviewer",
            description="Conservative local result checker.",
            capabilities=["review", "acceptance_criteria"],
        ),
        AgentProfile(
            id="memory",
            name="Memory",
            role="memory",
            description="Writes local memory and Feishu dry-run plans.",
            capabilities=["memory", "feishu_dry_run", "next_tickets"],
        ),
    ]


def _default_build_teams() -> list[BuildTeam]:
    return [
        BuildTeam(
            id="build-team",
            name="Ariadne Build Team",
            description=(
                "Local Build Lead routing team: route ticket to implementer, "
                "then review, memory, and backlog update through the standard runtime loop."
            ),
            lead_agent_id="build-lead",
            implementer_agent_id="fake-codex",
            reviewer_agent_id="reviewer",
            memory_agent_id="memory",
            default_backend_name="fake-codex",
            planner_name="deterministic",
            skill_refs=["codex-handoff", "review-diff", "feishu-write-plan"],
            resource_policy="local_project_resources",
        )
    ]


def is_assignment_lease_expired(assignment: TicketAssignment, now: datetime | None = None) -> bool:
    if assignment.lease_expires_at is None:
        return assignment.status in {AssignmentStatus.CLAIMED, AssignmentStatus.RUNNING}
    try:
        expires_at = datetime.fromisoformat(assignment.lease_expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return (now or datetime.now(UTC)) >= expires_at


def _github_operation_order(operation: str) -> int:
    return {"link": 0, "sync": 1}.get(operation, 2)
