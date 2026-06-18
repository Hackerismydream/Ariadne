from __future__ import annotations

from ariadne_ltb.application.dtos import CommentDTO, CreateCommentInput, TimelineDTO
from ariadne_ltb.application.idempotency import IdempotencyStore
from ariadne_ltb.application.mappers import comment_dto, ticket_summary
from ariadne_ltb.models import CommentAuthorType, CommentKind
from ariadne_ltb.storage import AriadneStore


class CommentService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store
        self.idempotency = IdempotencyStore(store)

    def add_human_comment(self, ticket_id_or_key: str, payload: CreateCommentInput) -> CommentDTO:
        replay = self.idempotency.get(payload.idempotency_key)
        if replay:
            return comment_dto(self.store.find_comment(replay["ticket_id"], replay["comment_id"]))
        ticket = self.store.resolve_ticket(ticket_id_or_key)
        comment = self.store.add_comment(
            ticket,
            CommentAuthorType.HUMAN,
            "human",
            CommentKind.COMMENT,
            payload.body,
            payload_ref=payload.assignment_id,
            parent_comment_id=payload.reply_to,
            thread_id=payload.assignment_id,
        )
        self.idempotency.set(
            payload.idempotency_key,
            {"ticket_id": ticket.id, "comment_id": comment.id},
        )
        return comment_dto(comment)

    def timeline(self, ticket_id_or_key: str) -> TimelineDTO:
        ticket = self.store.resolve_ticket(ticket_id_or_key)
        return TimelineDTO(
            ticket=ticket_summary(self.store, ticket),
            comments=[comment_dto(comment) for comment in self.store.list_comments(ticket.id)],
            runtime_events=[
                event.model_dump(mode="json", exclude_none=False)
                for event in self.store.list_runtime_events_for_ticket(ticket.id)
            ],
            artifacts=[
                artifact.model_dump(mode="json", exclude_none=False)
                for artifact in self.store.list_artifacts_for_ticket(ticket.id)
            ],
        )
