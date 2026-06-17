from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field

from ariadne_ltb.llm import DeepSeekClient, LLMClientError, LLMUsage, load_local_env, redact_secrets
from ariadne_ltb.models import AriadneModel


class LLMAgentRole(str, Enum):
    BUILD_LEAD = "build_lead"
    RESEARCH = "research"
    KNOWLEDGE = "knowledge"
    PROJECT_CONTEXT = "project_context"
    PLANNER = "planner"
    REVIEWER = "reviewer"
    MEMORY = "memory"
    FEISHU_PLANNER = "feishu_planner"
    GITHUB_PLANNER = "github_planner"


class LLMAgentResult(AriadneModel):
    role: LLMAgentRole
    schema_name: str
    succeeded: bool
    output_json: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    provider: str = "deepseek"
    model: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)


class JSONLLMAgent:
    def __init__(
        self,
        role: LLMAgentRole,
        client: DeepSeekClient | None = None,
        root: str | Path = ".",
    ) -> None:
        self.role = role
        self.client = client
        self.root = Path(root)

    def run(self, prompt: str, schema_name: str) -> LLMAgentResult:
        load_local_env(self.root)
        client = self.client or DeepSeekClient()
        try:
            response = client.complete_json_response(prompt, schema_name)
        except LLMClientError as exc:
            return LLMAgentResult(
                role=self.role,
                schema_name=schema_name,
                succeeded=False,
                error=redact_secrets(exc.error.message),
            )
        return LLMAgentResult(
            role=self.role,
            schema_name=schema_name,
            succeeded=True,
            output_json=response.content_json,
            model=response.model,
            usage=response.usage,
        )
