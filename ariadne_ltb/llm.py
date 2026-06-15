from __future__ import annotations

import json
import os
import urllib.request
from typing import Protocol


class LLMClient(Protocol):
    def complete_json(self, prompt: str, schema_name: str) -> dict:
        ...


class DeterministicLLM:
    def complete_json(self, prompt: str, schema_name: str) -> dict:
        return {"schema_name": schema_name, "summary": prompt[:200], "source": "deterministic"}


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = (base_url or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
        self.model = model or os.environ.get("DEEPSEEK_MODEL") or "deepseek-v4-pro"

    def complete_json(self, prompt: str, schema_name: str) -> dict:
        if not self.api_key:
            msg = "DEEPSEEK_API_KEY is required for DeepSeekClient"
            raise RuntimeError(msg)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"Return JSON for schema {schema_name}."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)


def default_llm() -> LLMClient:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekClient()
    return DeterministicLLM()
