from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ariadne_ltb.application.dtos import AssignmentEventDTO, AssignmentEventsDTO, AssignmentEventStreamDTO
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.models import AgentRun
from ariadne_ltb.models import TicketAssignment
from ariadne_ltb.storage import AriadneStore


@dataclass
class AssignmentEventCache:
    signature: tuple[tuple[str, int, int], ...] = field(default_factory=tuple)
    events: list[AssignmentEventDTO] = field(default_factory=list)


class RunEventService:
    def __init__(self, store: AriadneStore, cache: AssignmentEventCache | None = None) -> None:
        self.store = store
        self.cache = cache

    def messages(self, run_id: str, since: int = 0) -> list[dict]:
        self.store.load_run(run_id)
        return [
            message.model_dump(mode="json", exclude_none=False)
            for message in self.store.list_run_messages(run_id, since=since)
        ]

    def assignment_events(self, assignment_id: str, since: str | None = None) -> AssignmentEventsDTO:
        assignment, events = self._assignment_events(assignment_id, since=since)
        return AssignmentEventsDTO(assignment=assignment_dto(assignment), events=events)

    def assignment_event_stream_batch(
        self,
        assignment_id: str,
        since: str | None = None,
    ) -> AssignmentEventStreamDTO:
        assignment, events = self._assignment_events(assignment_id, since=since)
        cursor = events[-1].cursor if events else since
        return AssignmentEventStreamDTO(
            assignment=assignment_dto(assignment),
            events=events,
            cursor=cursor,
            heartbeat=False,
        )

    def heartbeat(self, assignment_id: str, since: str | None = None) -> AssignmentEventStreamDTO:
        assignment = self.store.load_assignment(assignment_id)
        return AssignmentEventStreamDTO(
            assignment=assignment_dto(assignment),
            events=[],
            cursor=since,
            heartbeat=True,
        )

    def _assignment_events(
        self,
        assignment_id: str,
        since: str | None = None,
    ) -> tuple[TicketAssignment, list[AssignmentEventDTO]]:
        assignment = self.store.load_assignment(assignment_id)
        signature = self._event_signature(assignment_id)
        if self.cache is not None and self.cache.signature == signature:
            ordered = self.cache.events
        else:
            ordered = self._load_assignment_events(assignment_id)
            if self.cache is not None:
                self.cache.signature = signature
                self.cache.events = ordered
        if since:
            ordered = [event for event in ordered if event.cursor > since]
        return assignment, ordered

    def _load_assignment_events(self, assignment_id: str) -> list[AssignmentEventDTO]:
        assignment = self.store.load_assignment(assignment_id)
        ticket = self.store.load_ticket(assignment.ticket_id)
        events: list[AssignmentEventDTO] = [
            AssignmentEventDTO(
                id=f"assignment:{assignment.id}",
                source="assignment",
                cursor=f"assignment:{assignment.created_at}:{assignment.id}",
                timestamp=assignment.created_at,
                assignment_id=assignment.id,
                ticket_id=ticket.id,
                ticket_key=ticket.key,
                stage="assignment",
                event_type=assignment.status.value,
                actor=assignment.agent_name,
                summary=f"Assignment {assignment.status.value}: {assignment.agent_name}",
                ref_id=assignment.id,
            )
        ]
        for runtime_event in self.store.list_runtime_events_for_ticket(ticket.id):
            if runtime_event.assignment_id != assignment.id:
                continue
            events.append(
                AssignmentEventDTO(
                    id=runtime_event.id,
                    source="runtime_event",
                    cursor=f"runtime_event:{runtime_event.timestamp}:{runtime_event.id}",
                    timestamp=runtime_event.timestamp,
                    assignment_id=assignment.id,
                    ticket_id=ticket.id,
                    ticket_key=ticket.key,
                    stage=runtime_event.stage,
                    event_type=runtime_event.event_type,
                    actor=runtime_event.actor,
                    summary=f"{runtime_event.stage}: {runtime_event.event_type}",
                    ref_id=runtime_event.payload_ref,
                )
            )
        for comment in self.store.list_comments(ticket.id):
            if comment.thread_id != assignment.id and comment.payload_ref != assignment.id:
                continue
            events.append(
                AssignmentEventDTO(
                    id=comment.id,
                    source="comment",
                    cursor=f"comment:{comment.created_at}:{comment.id}",
                    timestamp=comment.created_at,
                    assignment_id=assignment.id,
                    ticket_id=ticket.id,
                    ticket_key=ticket.key,
                    stage="comment",
                    event_type=comment.kind.value,
                    actor=comment.author,
                    summary=comment.body,
                    ref_id=comment.payload_ref,
                )
            )
        for run_id in ticket.agent_run_ids:
            try:
                run = self.store.load_run(run_id)
            except FileNotFoundError:
                continue
            if run.metadata.get("assignment_id") != assignment.id:
                continue
            for message in self.store.list_run_messages(run.id):
                events.append(
                    AssignmentEventDTO(
                        id=f"{message.run_id}:{message.seq}",
                        source="run_message",
                        cursor=f"run_message:{message.seq}:{message.run_id}",
                        timestamp=message.timestamp,
                        assignment_id=assignment.id,
                        ticket_id=ticket.id,
                        ticket_key=ticket.key,
                        stage=message.stage,
                        event_type=message.message_type.value,
                        actor=run.agent_name,
                        summary=message.content,
                        ref_id=message.artifact_ref or message.result_ref,
                    )
                )
        assignment_runs = self._assignment_runs(ticket.agent_run_ids, assignment.id)
        assignment_run_ids = set(assignment_runs)
        for artifact in self.store.list_artifacts_for_ticket(ticket.id):
            if artifact.agent_run_id not in assignment_run_ids:
                continue
            run = assignment_runs.get(artifact.agent_run_id)
            events.append(
                AssignmentEventDTO(
                    id=f"artifact:{artifact.id}",
                    source="artifact",
                    cursor=f"artifact:{artifact.created_at}:{artifact.id}",
                    timestamp=artifact.created_at,
                    assignment_id=assignment.id,
                    ticket_id=ticket.id,
                    ticket_key=ticket.key,
                    stage=artifact.artifact_type.value,
                    event_type="written",
                    actor=run.agent_name if run else "Ariadne",
                    summary=f"{artifact.artifact_type.value}: {artifact.summary}",
                    ref_id=artifact.id,
                )
            )
        ordered = sorted(events, key=lambda item: (item.timestamp, item.cursor))
        return ordered

    def _assignment_runs(self, run_ids: list[str], assignment_id: str) -> dict[str, AgentRun]:
        runs: dict[str, AgentRun] = {}
        for run_id in run_ids:
            try:
                run = self.store.load_run(run_id)
            except FileNotFoundError:
                continue
            if run.metadata.get("assignment_id") == assignment_id:
                runs[run.id] = run
        return runs

    def _event_signature(self, assignment_id: str) -> tuple[tuple[str, int, int], ...]:
        assignment = self.store.load_assignment(assignment_id)
        ticket = self.store.load_ticket(assignment.ticket_id)
        paths: list[Path] = [
            self.store.assignments_dir / f"{assignment.id}.json",
            self.store.comments_dir / f"{ticket.id}.jsonl",
            self.store.journal_path,
        ]
        for run_id in ticket.agent_run_ids:
            paths.append(self.store.run_messages_path(run_id))
            paths.append(self.store.runs_dir / f"{run_id}.json")
        for artifact in self.store.list_artifacts_for_ticket(ticket.id):
            paths.append(self.store.artifact_index_dir / f"{artifact.id}.json")
            paths.append(Path(artifact.path))
        signature: list[tuple[str, int, int]] = []
        for path in paths:
            try:
                stat = path.stat()
            except FileNotFoundError:
                signature.append((str(path), 0, 0))
                continue
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))
        return tuple(signature)
