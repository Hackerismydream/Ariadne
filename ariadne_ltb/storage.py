from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ariadne_ltb.models import (
    AgentRun,
    Artifact,
    ArtifactType,
    BuildPacket,
    BuildTicket,
    FeishuWritePlan,
    ProjectSpace,
    ReviewReport,
    stable_id,
)

T = TypeVar("T", bound=BaseModel)


class AriadneStore:
    def __init__(self, root: str | Path = ".") -> None:
        self.root = Path(root).resolve()
        self.base = self.root / ".ariadne"
        self.project_space_path = self.base / "project_space.json"
        self.tickets_dir = self.base / "tickets"
        self.runs_dir = self.base / "runs"
        self.build_packets_dir = self.base / "build_packets"
        self.reviews_dir = self.base / "reviews"
        self.feishu_plans_dir = self.base / "feishu_plans"
        self.artifacts_dir = self.base / "artifacts"
        self.artifact_index_dir = self.base / "artifact_index"
        self.board_dir = self.base / "board"
        self._ensure_layout()

    def _ensure_layout(self) -> None:
        for directory in [
            self.base,
            self.tickets_dir,
            self.runs_dir,
            self.build_packets_dir,
            self.reviews_dir,
            self.feishu_plans_dir,
            self.artifacts_dir,
            self.artifact_index_dir,
            self.board_dir,
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

    def save_ticket(self, ticket: BuildTicket) -> None:
        self._write_model(self.tickets_dir / f"{ticket.id}.json", ticket)

    def load_ticket(self, ticket_id: str) -> BuildTicket:
        return self._read_model(self.tickets_dir / f"{ticket_id}.json", BuildTicket)

    def list_tickets(self) -> list[BuildTicket]:
        tickets = [
            self._read_model(path, BuildTicket)
            for path in sorted(self.tickets_dir.glob("*.json"))
        ]
        return sorted(tickets, key=lambda ticket: ticket.key)

    def save_run(self, run: AgentRun) -> None:
        self._write_model(self.runs_dir / f"{run.id}.json", run)

    def load_run(self, run_id: str) -> AgentRun:
        return self._read_model(self.runs_dir / f"{run_id}.json", AgentRun)

    def save_build_packet(self, packet: BuildPacket) -> None:
        self._write_model(self.build_packets_dir / f"{packet.id}.json", packet)

    def load_build_packet(self, packet_id: str) -> BuildPacket:
        return self._read_model(self.build_packets_dir / f"{packet_id}.json", BuildPacket)

    def save_review_report(self, review_report: ReviewReport) -> None:
        self._write_model(self.reviews_dir / f"{review_report.id}.json", review_report)

    def load_review_report(self, review_report_id: str) -> ReviewReport:
        return self._read_model(self.reviews_dir / f"{review_report_id}.json", ReviewReport)

    def save_feishu_write_plan(self, write_plan: FeishuWritePlan) -> None:
        self._write_model(self.feishu_plans_dir / f"{write_plan.id}.json", write_plan)

    def load_feishu_write_plan(self, write_plan_id: str) -> FeishuWritePlan:
        return self._read_model(self.feishu_plans_dir / f"{write_plan_id}.json", FeishuWritePlan)

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
