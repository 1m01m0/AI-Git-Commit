"""LLM provider abstraction and supported provider implementations."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from typing import Protocol

from anthropic import Anthropic
from openai import OpenAI


ChatMessage = dict[str, str]


class LLMError(RuntimeError):
    """Raised when a provider cannot return usable model text."""


class LLMProvider(Protocol):
    """Common interface implemented by every supported LLM provider."""

    name: str

    def generate(self, messages: Sequence[ChatMessage]) -> str:
        """Generate raw model text from a chat-style prompt."""
        ...


def _safe_error(error: Exception, api_key: str) -> str:
    """Keep provider errors useful without echoing an API key."""
    detail = str(error).strip() or error.__class__.__name__
    if api_key:
        detail = detail.replace(api_key, "[REDACTED_SECRET]")
    return detail[:300]


def _extract_openai_text(response: Any) -> str:
    choices = getattr(response, "choices", None) or []
    if not choices:
        raise LLMError("The provider returned no choices.")
    content = getattr(getattr(choices[0], "message", None), "content", None)
    if not isinstance(content, str) or not content.strip():
        raise LLMError("The provider returned an empty response.")
    return content.strip()


def _generate_openai_compatible(
    *,
    client: Any,
    provider_name: str,
    api_key: str,
    model: str,
    timeout_seconds: float,
    messages: Sequence[ChatMessage],
) -> str:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=list(messages),
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"},
            timeout=timeout_seconds,
        )
        return _extract_openai_text(response)
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"{provider_name} request failed: {_safe_error(exc, api_key)}") from exc


@dataclass
class OpenAIProvider:
    """OpenAI Chat Completions provider."""

    api_key: str
    model: str
    timeout_seconds: float = 60.0
    client: Any | None = None
    name: str = field(default="openai", init=False)

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)

    def generate(self, messages: Sequence[ChatMessage]) -> str:
        return _generate_openai_compatible(
            client=self.client,
            provider_name=self.name,
            api_key=self.api_key,
            model=self.model,
            timeout_seconds=self.timeout_seconds,
            messages=messages,
        )


@dataclass
class DeepSeekProvider:
    """DeepSeek provider through its OpenAI-compatible endpoint."""

    api_key: str
    model: str
    timeout_seconds: float = 60.0
    client: Any | None = None
    name: str = field(default="deepseek", init=False)

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com",
                timeout=self.timeout_seconds,
            )

    def generate(self, messages: Sequence[ChatMessage]) -> str:
        return _generate_openai_compatible(
            client=self.client,
            provider_name=self.name,
            api_key=self.api_key,
            model=self.model,
            timeout_seconds=self.timeout_seconds,
            messages=messages,
        )


@dataclass
class AnthropicProvider:
    """Anthropic Messages API provider."""

    api_key: str
    model: str
    timeout_seconds: float = 60.0
    client: Any | None = None
    name: str = field(default="anthropic", init=False)

    def __post_init__(self) -> None:
        if self.client is None:
            self.client = Anthropic(api_key=self.api_key, timeout=self.timeout_seconds)

    def generate(self, messages: Sequence[ChatMessage]) -> str:
        system_parts = [
            message["content"]
            for message in messages
            if message.get("role") == "system"
        ]
        conversation = [
            {"role": message["role"], "content": message["content"]}
            for message in messages
            if message.get("role") in {"user", "assistant"}
        ]
        if not conversation:
            raise LLMError("Anthropic requires at least one user or assistant message.")

        request: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 300,
            "temperature": 0.2,
            "messages": conversation,
            "timeout": self.timeout_seconds,
        }
        if system_parts:
            request["system"] = "\n\n".join(system_parts)

        try:
            response = self.client.messages.create(**request)
            blocks = getattr(response, "content", None) or []
            text_parts = [
                block.text
                for block in blocks
                if getattr(block, "type", None) == "text"
                and isinstance(getattr(block, "text", None), str)
            ]
            if not text_parts or not "".join(text_parts).strip():
                raise LLMError("The provider returned an empty response.")
            return "\n".join(text_parts).strip()
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(
                f"{self.name} request failed: {_safe_error(exc, self.api_key)}"
            ) from exc


def create_provider(
    provider: str,
    *,
    api_key: str,
    model: str,
    timeout_seconds: float = 60.0,
) -> LLMProvider:
    """Create one of the supported providers by name."""
    normalized_provider = provider.strip().lower()
    if normalized_provider == "openai":
        return OpenAIProvider(api_key, model, timeout_seconds)
    if normalized_provider == "anthropic":
        return AnthropicProvider(api_key, model, timeout_seconds)
    if normalized_provider == "deepseek":
        return DeepSeekProvider(api_key, model, timeout_seconds)
    raise ValueError(f"Unsupported provider: {provider}")
