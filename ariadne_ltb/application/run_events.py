from __future__ import annotations

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
