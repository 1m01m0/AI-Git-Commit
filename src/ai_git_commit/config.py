"""Configuration loading for AI Git Commit."""

from dataclasses import dataclass
from os import environ
from pathlib import Path
from typing import Mapping

from dotenv import load_dotenv

SUPPORTED_PROVIDERS = frozenset({"openai", "anthropic", "deepseek"})
API_KEY_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}
DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",
    "deepseek": "deepseek-v4-flash",
}


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid or incomplete."""


def _clean(value: str | None) -> str:
    return value.strip() if value else ""


def _parse_positive_int(values: Mapping[str, str], key: str, default: int) -> int:
    raw_value = _clean(values.get(key))
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a positive integer.") from exc
    if value <= 0:
        raise ConfigError(f"{key} must be a positive integer.")
    return value


def _parse_positive_float(values: Mapping[str, str], key: str, default: float) -> float:
    raw_value = _clean(values.get(key))
    if not raw_value:
        return default
    try:
        value = float(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{key} must be a positive number.") from exc
    if value <= 0:
        raise ConfigError(f"{key} must be a positive number.")
    return value


def _normalize_provider(value: str, key: str) -> str:
    provider = _clean(value).lower()
    if provider not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise ConfigError(f"{key} must be one of: {supported}.")
    return provider


@dataclass(frozen=True)
class Settings:
    """Resolved application settings."""

    provider: str
    fallback_provider: str | None
    model: str | None
    language: str
    max_diff_chars: int
    timeout_seconds: float
    api_keys: Mapping[str, str]

    @classmethod
    def load(cls, env_file: str | Path | None = None) -> "Settings":
        """Load settings from an optional .env file and process environment."""
        load_dotenv(dotenv_path=env_file)
        return cls.from_mapping(environ)

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "Settings":
        """Build settings from a mapping, which keeps unit tests isolated."""
        provider = _normalize_provider(
            values.get("AI_GIT_COMMIT_PROVIDER", "openai"),
            "AI_GIT_COMMIT_PROVIDER",
        )

        fallback_value = _clean(values.get("AI_GIT_COMMIT_FALLBACK_PROVIDER"))
        fallback_provider = None
        if fallback_value:
            fallback_provider = _normalize_provider(
                fallback_value,
                "AI_GIT_COMMIT_FALLBACK_PROVIDER",
            )
            if fallback_provider == provider:
                raise ConfigError("The fallback provider must differ from the primary provider.")

        api_keys = {
            name: _clean(values.get(environment_variable))
            for name, environment_variable in API_KEY_ENV_VARS.items()
        }

        return cls(
            provider=provider,
            fallback_provider=fallback_provider,
            model=_clean(values.get("AI_GIT_COMMIT_MODEL")) or None,
            language=_clean(values.get("AI_GIT_COMMIT_LANGUAGE")) or "en",
            max_diff_chars=_parse_positive_int(
                values,
                "AI_GIT_COMMIT_MAX_DIFF_CHARS",
                default=20_000,
            ),
            timeout_seconds=_parse_positive_float(
                values,
                "AI_GIT_COMMIT_TIMEOUT_SECONDS",
                default=60.0,
            ),
            api_keys=api_keys,
        )

    def api_key_for(self, provider: str) -> str:
        """Return a provider key or raise a safe, actionable configuration error."""
        normalized_provider = _normalize_provider(provider, "provider")
        api_key = self.api_keys.get(normalized_provider, "")
        if not api_key:
            environment_variable = API_KEY_ENV_VARS[normalized_provider]
            raise ConfigError(
                f"Missing {environment_variable}. Set it in the environment or .env file."
            )
        return api_key

    def model_for(self, provider: str) -> str:
        """Return the configured model or a provider-specific default."""
        normalized_provider = _normalize_provider(provider, "provider")
        return self.model or DEFAULT_MODELS[normalized_provider]
