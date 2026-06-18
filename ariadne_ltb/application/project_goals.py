from __future__ import annotations

import json
from pathlib import Path

from ariadne_ltb.application.dtos import CreateProjectGoalInput, ProjectGoalDTO
from ariadne_ltb.models import stable_id, utc_now
from ariadne_ltb.storage import AriadneStore


class ProjectGoalService:
    def __init__(self, store: AriadneStore) -> None:
        self.store = store
        self.path = store.project_dir / "goals.json"

    def list(self) -> list[ProjectGoalDTO]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [ProjectGoalDTO.model_validate(item) for item in data.get("goals", [])]

    def create(self, payload: CreateProjectGoalInput) -> ProjectGoalDTO:
        goals = self.list()
        now = utc_now()
        goal = ProjectGoalDTO(
            id=stable_id("goal", payload.title, payload.north_star, now),
            title=payload.title.strip(),
            north_star=payload.north_star.strip(),
            current_state=payload.current_state.strip(),
            target_state=payload.target_state.strip(),
            target_project_id=payload.target_project_id,
            knowledge_inputs=[item.strip() for item in payload.knowledge_inputs if item.strip()],
            feedback_signals=[item.strip() for item in payload.feedback_signals if item.strip()],
            created_at=now,
            updated_at=now,
        )
        self._save([goal, *[item.model_copy(update={"status": "reviewing"}) for item in goals]])
        return goal

    def load(self, goal_id: str) -> ProjectGoalDTO:
        for goal in self.list():
            if goal.id == goal_id:
                return goal
        msg = f"unknown goal: {goal_id}"
        raise FileNotFoundError(msg)

    def _save(self, goals: list[ProjectGoalDTO]) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"goals": [goal.model_dump(mode="json") for goal in goals]}, indent=2) + "\n",
            encoding="utf-8",
        )
        return self.path
