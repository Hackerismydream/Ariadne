from __future__ import annotations

import os
from typing import Any, Protocol

from ariadne_ltb.llm import DeepSeekClient, LLMClient, LLMClientError


class KnowledgeLLM(Protocol):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        ...


def has_deepseek_key() -> bool:
    if os.environ.get("PYTEST_CURRENT_TEST") and not os.environ.get("ARIADNE_ALLOW_KNOWLEDGE_LLM_IN_TESTS"):
        return False
    value = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    return value.startswith("sk-") and len(value) > 10


def default_knowledge_llm() -> KnowledgeLLM:
    return DeepSeekClient()


def call_json(llm: LLMClient | KnowledgeLLM, prompt: str, schema_name: str) -> dict[str, Any]:
    try:
        return llm.complete_json(prompt, schema_name)
    except LLMClientError:
        raise
