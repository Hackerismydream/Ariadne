from __future__ import annotations

from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ariadne_ltb.knowledge.models import (
    BlockerLearning,
    ContradictionRecord,
    OutcomesLog,
    ProjectPurpose,
    SourceInsight,
    SynthesisTheme,
)
from ariadne_ltb.models import utc_now
from ariadne_ltb.storage import AriadneStore

T = TypeVar("T", bound=BaseModel)


class ProjectKnowledgeStore:
    def __init__(self, store: AriadneStore, project_id: str) -> None:
        self.store = store
        self.project_id = project_id
        self.root = store.base / "knowledge" / project_id
        self.source_insights_dir = self.root / "source_insights"
        self.synthesis_themes_dir = self.root / "synthesis_themes"
        self.contradictions_dir = self.root / "contradictions"
        self.blocker_learnings_dir = self.root / "blocker_learnings"
        self.outcomes_log_path = self.root / "outcomes_log.json"
        self.project_purpose_path = self.root / "project_purpose.json"
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        for directory in [
            self.root,
            self.source_insights_dir,
            self.synthesis_themes_dir,
            self.contradictions_dir,
            self.blocker_learnings_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    def _write(self, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_dump_json(indent=2, exclude_none=False) + "\n", encoding="utf-8")

    def _read(self, path: Path, model_type: type[T]) -> T:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    def _list(self, directory: Path, model_type: type[T]) -> list[T]:
        return [
            self._read(path, model_type)
            for path in sorted(directory.glob("*.json"))
            if path.is_file()
        ]

    def save_project_purpose(self, purpose: ProjectPurpose) -> ProjectPurpose:
        updated = purpose.model_copy(update={"updated_at": utc_now()})
        self._write(self.project_purpose_path, updated)
        return updated

    def load_project_purpose(self) -> ProjectPurpose:
        return self._read(self.project_purpose_path, ProjectPurpose)

    def save_source_insight(self, insight: SourceInsight) -> SourceInsight:
        self._write(self.source_insights_dir / f"{insight.id}.json", insight)
        return insight

    def list_source_insights(self) -> list[SourceInsight]:
        return self._list(self.source_insights_dir, SourceInsight)

    def source_insight_by_source_id(self) -> dict[str, SourceInsight]:
        return {insight.source_document_id: insight for insight in self.list_source_insights()}

    def save_synthesis_theme(self, theme: SynthesisTheme) -> SynthesisTheme:
        self._write(self.synthesis_themes_dir / f"{theme.id}.json", theme)
        return theme

    def list_synthesis_themes(self) -> list[SynthesisTheme]:
        return self._list(self.synthesis_themes_dir, SynthesisTheme)

    def save_contradiction(self, contradiction: ContradictionRecord) -> ContradictionRecord:
        self._write(self.contradictions_dir / f"{contradiction.id}.json", contradiction)
        return contradiction

    def list_contradictions(self) -> list[ContradictionRecord]:
        return self._list(self.contradictions_dir, ContradictionRecord)

    def list_unresolved_contradictions(self) -> list[ContradictionRecord]:
        return [item for item in self.list_contradictions() if item.status == "open"]

    def save_blocker_learning(self, learning: BlockerLearning) -> BlockerLearning:
        self._write(self.blocker_learnings_dir / f"{learning.id}.json", learning)
        return learning

    def list_blocker_learnings(self) -> list[BlockerLearning]:
        return self._list(self.blocker_learnings_dir, BlockerLearning)

    def load_outcomes_log(self) -> OutcomesLog:
        if not self.outcomes_log_path.exists():
            return OutcomesLog(project_id=self.project_id)
        return self._read(self.outcomes_log_path, OutcomesLog)

    def save_outcomes_log(self, log: OutcomesLog, max_entries: int = 20) -> OutcomesLog:
        trimmed = log.model_copy(update={"entries": log.entries[-max_entries:]})
        self._write(self.outcomes_log_path, trimmed)
        return trimmed

