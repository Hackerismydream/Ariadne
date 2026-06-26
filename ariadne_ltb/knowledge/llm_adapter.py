from __future__ import annotations

import os
from typing import Any, Protocol

from ariadne_ltb.llm import DEFAULT_DEEPSEEK_FAST_MODEL, DeepSeekClient, LLMClient, LLMClientError


class KnowledgeLLM(Protocol):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        ...


def has_deepseek_key() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("ARIADNE_ALLOW_KNOWLEDGE_LLM_IN_TESTS"):
        return False
    value = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    return value.startswith("sk-") and len(value) > 10


def default_knowledge_llm() -> KnowledgeLLM:
    return DeepSeekClient(
        model=(
            os.environ.get("ARIADNE_KNOWLEDGE_LLM_MODEL")
            or os.environ.get("ARIADNE_LLM_FAST_MODEL")
            or DEFAULT_DEEPSEEK_FAST_MODEL
        )
    )


def call_json(llm: LLMClient | KnowledgeLLM, prompt: str, schema_name: str) -> dict[str, Any]:
    try:
        return llm.complete_json(prompt, schema_name)
    except LLMClientError:
        raise


class KnowledgeNodeError(RuntimeError):
    def __init__(self, node_name: str, schema_name: str, exc: LLMClientError) -> None:
        self.node_name = node_name
        self.schema_name = schema_name
        self.original = exc
        self.node_provenance = node_event(
            node_name,
            status="failed",
            schema_name=schema_name,
            error_type=type(exc).__name__,
            error_message=exc.error.message,
            llm_error_type=exc.error.error_type,
            model=exc.error.model,
            finish_reason=exc.error.finish_reason,
            raw_content_excerpt=exc.error.raw_content_excerpt,
            usage=exc.error.usage.model_dump(mode="json") if exc.error.usage else None,
        )
        super().__init__(f"{node_name}:{exc.error.message}")


def call_node_json(
    llm: LLMClient | KnowledgeLLM,
    prompt: str,
    schema_name: str,
    *,
    node_name: str,
) -> dict[str, Any]:
    try:
        return llm.complete_json(prompt, schema_name)
    except LLMClientError as exc:
        raise KnowledgeNodeError(node_name, schema_name, exc) from exc


def node_event(
    node_name: str,
    *,
    status: str,
    schema_name: str | None = None,
    **metadata: object,
) -> dict[str, object]:
    event: dict[str, object] = {"node": node_name, "status": status}
    if schema_name:
        event["schema_name"] = schema_name
    for key, value in metadata.items():
        if value is not None:
            event[key] = value
    return event
