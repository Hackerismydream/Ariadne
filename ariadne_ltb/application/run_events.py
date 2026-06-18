from __future__ import annotations

from ariadne_ltb.application.dtos import AssignmentEventDTO, AssignmentEventsDTO
from ariadne_ltb.application.mappers import assignment_dto
from ariadne_ltb.storage import AriadneStore


class RunEventService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store

    def messages(self, run_id: str, since: int = 0) -> list[dict]:
        self.store.load_run(run_id)
        return [
            message.model_dump(mode="json", exclude_none=False)
            for message in self.store.list_run_messages(run_id, since=since)
        ]

    def assignment_events(self, assignment_id: str, since: str | None = None) -> AssignmentEventsDTO:
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
            if runtime_event.assignment_id not in {None, assignment.id}:
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
            if comment.thread_id not in {None, assignment.id} and comment.payload_ref != assignment.id:
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
        ordered = sorted(events, key=lambda item: (item.timestamp, item.cursor))
        if since:
            ordered = [event for event in ordered if event.cursor > since]
        return AssignmentEventsDTO(assignment=assignment_dto(assignment), events=ordered)
