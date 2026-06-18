from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field

from ariadne_ltb.models import AriadneModel


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-pro"
DEFAULT_DEEPSEEK_FAST_MODEL = "deepseek-v4-flash"
DEFAULT_LLM_TIMEOUT_SECONDS = 60

LOCAL_ENV_ALLOWLIST = {
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "ARIADNE_LLM_PROVIDER",
    "ARIADNE_LLM_BASE_URL",
    "ARIADNE_LLM_MODEL",
    "ARIADNE_LLM_FAST_MODEL",
    "ARIADNE_LLM_TIMEOUT_SECONDS",
}


class LLMUsage(AriadneModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMMessage(AriadneModel):
    role: str
    content: str


class LLMRequest(AriadneModel):
    provider: str = "deepseek"
    schema_name: str
    model: str = DEFAULT_DEEPSEEK_MODEL
    messages: list[LLMMessage]
    response_format: dict[str, str] = Field(default_factory=lambda: {"type": "json_object"})
    stream: bool = False
    temperature: float = 0.2
    max_tokens: int = 4096

    def payload(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [message.model_dump(mode="json") for message in self.messages],
            "response_format": self.response_format,
            "stream": self.stream,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


class LLMResponse(AriadneModel):
    provider: str = "deepseek"
    schema_name: str
    model: str
    content_json: dict[str, Any]
    raw_content: str
    usage: LLMUsage = Field(default_factory=LLMUsage)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class LLMError(AriadneModel):
    provider: str = "deepseek"
    error_type: str
    message: str
    status_code: int | None = None
    retryable: bool = False


class LLMClientError(RuntimeError):
    def __init__(self, error: LLMError) -> None:
        self.error = error
        super().__init__(error.message)


class LLMTransport(Protocol):
    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        ...


class UrllibLLMTransport:
    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))


class LLMClient(Protocol):
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        ...


class DeterministicLLM:
    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        return {"schema_name": schema_name, "summary": prompt[:200], "source": "deterministic"}


class DeepSeekClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        transport: LLMTransport | None = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("ARIADNE_LLM_BASE_URL")
            or os.environ.get("DEEPSEEK_BASE_URL")
            or DEFAULT_DEEPSEEK_BASE_URL
        ).rstrip("/")
        self.model = (
            model
            or os.environ.get("ARIADNE_LLM_MODEL")
            or os.environ.get("DEEPSEEK_MODEL")
            or DEFAULT_DEEPSEEK_MODEL
        )
        self.fast_model = os.environ.get("ARIADNE_LLM_FAST_MODEL") or DEFAULT_DEEPSEEK_FAST_MODEL
        self.timeout_seconds = timeout_seconds or _timeout_from_env()
        self.transport = transport or UrllibLLMTransport()

    def complete_json(self, prompt: str, schema_name: str) -> dict[str, Any]:
        return self.complete_json_response(prompt, schema_name).content_json

    def complete_json_response(self, prompt: str, schema_name: str) -> LLMResponse:
        if not self.api_key:
            raise LLMClientError(
                LLMError(
                    error_type="missing_api_key",
                    message="DEEPSEEK_API_KEY is required for DeepSeekClient.",
                    retryable=False,
                )
            )
        request = self.build_request(prompt, schema_name)
        try:
            body = self.transport.post_json(
                f"{self.base_url}/chat/completions",
                request.payload(),
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
                self.timeout_seconds,
            )
        except urllib.error.HTTPError as exc:
            raise self._client_error("http_error", exc, status_code=exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise self._client_error("transport_error", exc, retryable=True) from exc

        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise LLMClientError(
                LLMError(
                    error_type="invalid_response",
                    message=redact_secrets(f"DeepSeek response did not contain valid JSON: {exc}"),
                    retryable=False,
                )
            ) from exc
        usage = _usage_from_raw(body.get("usage") if isinstance(body, dict) else None)
        return LLMResponse(
            schema_name=schema_name,
            model=str(body.get("model") or self.model),
            content_json=parsed,
            raw_content=content,
            usage=usage,
            raw_response=_safe_raw_response(body),
        )

    def build_request(self, prompt: str, schema_name: str) -> LLMRequest:
        return LLMRequest(
            schema_name=schema_name,
            model=self.model,
            messages=[
                LLMMessage(
                    role="system",
                    content=(
                        "You are an Ariadne production agent. Return only valid json. "
                        f"The response must match the requested schema: {schema_name}."
                    ),
                ),
                LLMMessage(role="user", content=prompt),
            ],
        )

    def _client_error(
        self,
        error_type: str,
        exc: BaseException,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> LLMClientError:
        return LLMClientError(
            LLMError(
                error_type=error_type,
                status_code=status_code,
                retryable=retryable,
                message=redact_secrets(f"DeepSeek {error_type}: {exc}", extra_secrets=[self.api_key]),
            )
        )


def default_llm() -> LLMClient:
    if os.environ.get("DEEPSEEK_API_KEY"):
        return DeepSeekClient()
    return DeterministicLLM()


def load_local_env(root: str | Path) -> list[str]:
    env_path = Path(root).resolve() / ".env"
    if not env_path.exists():
        return []
    loaded: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in LOCAL_ENV_ALLOWLIST or key in os.environ:
            continue
        os.environ[key] = _strip_env_quotes(value.strip())
        loaded.append(key)
    return loaded


def llm_doctor_status(root: str | Path) -> list[str]:
    loaded = load_local_env(root)
    provider = os.environ.get("ARIADNE_LLM_PROVIDER") or "deepseek"
    model = os.environ.get("ARIADNE_LLM_MODEL") or os.environ.get("DEEPSEEK_MODEL") or DEFAULT_DEEPSEEK_MODEL
    fast_model = os.environ.get("ARIADNE_LLM_FAST_MODEL") or DEFAULT_DEEPSEEK_FAST_MODEL
    base_url = os.environ.get("ARIADNE_LLM_BASE_URL") or os.environ.get("DEEPSEEK_BASE_URL") or DEFAULT_DEEPSEEK_BASE_URL
    return [
        f"LLM provider: {provider}",
        f"DeepSeek API key: {'set' if os.environ.get('DEEPSEEK_API_KEY') else 'unset'}",
        f"DeepSeek base URL: {base_url}",
        f"DeepSeek default model: {model}",
        f"DeepSeek fast model: {fast_model}",
        f"LLM timeout seconds: {_timeout_from_env()}",
        f"Loaded local env keys: {', '.join(sorted(loaded)) if loaded else 'none'}",
    ]


def redact_secrets(message: str, extra_secrets: list[str | None] | None = None) -> str:
    redacted = message
    for secret in extra_secrets or []:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    redacted = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "sk-[REDACTED]", redacted)
    redacted = re.sub(r"(Bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", redacted)
    return redacted


def _timeout_from_env() -> int:
    raw_value = os.environ.get("ARIADNE_LLM_TIMEOUT_SECONDS")
    if not raw_value:
        return DEFAULT_LLM_TIMEOUT_SECONDS
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_LLM_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_LLM_TIMEOUT_SECONDS


def _strip_env_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _safe_raw_response(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": body.get("id"),
        "model": body.get("model"),
        "created": body.get("created"),
        "usage": body.get("usage"),
        "choices": [
            {
                "finish_reason": choice.get("finish_reason"),
                "index": choice.get("index"),
            }
            for choice in body.get("choices", [])
            if isinstance(choice, dict)
        ],
    }


def _usage_from_raw(raw_usage: object) -> LLMUsage:
    if not isinstance(raw_usage, dict):
        return LLMUsage()
    return LLMUsage(
        prompt_tokens=raw_usage.get("prompt_tokens"),
        completion_tokens=raw_usage.get("completion_tokens"),
        total_tokens=raw_usage.get("total_tokens"),
    )
