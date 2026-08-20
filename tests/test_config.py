"""Configuration behavior tests."""

import pytest

from ai_git_commit.config import ConfigError, Settings


def test_settings_resolve_provider_and_runtime_limits() -> None:
    settings = Settings.from_mapping(
        {
            "AI_GIT_COMMIT_PROVIDER": "deepseek",
            "AI_GIT_COMMIT_FALLBACK_PROVIDER": "openai",
            "AI_GIT_COMMIT_LANGUAGE": "zh-CN",
            "AI_GIT_COMMIT_MAX_DIFF_CHARS": "5000",
            "AI_GIT_COMMIT_TIMEOUT_SECONDS": "12.5",
            "DEEPSEEK_API_KEY": "deepseek-secret",
        }
    )

    assert settings.provider == "deepseek"
    assert settings.fallback_provider == "openai"
    assert settings.language == "zh-CN"
    assert settings.max_diff_chars == 5000
    assert settings.timeout_seconds == 12.5
    assert settings.model_for("deepseek") == "deepseek-v4-flash"


def test_missing_api_key_is_actionable() -> None:
    settings = Settings.from_mapping({})

    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        settings.api_key_for("openai")


def test_primary_and_fallback_must_differ() -> None:
    with pytest.raises(ConfigError, match="must differ"):
        Settings.from_mapping(
            {
                "AI_GIT_COMMIT_PROVIDER": "openai",
                "AI_GIT_COMMIT_FALLBACK_PROVIDER": "openai",
            }
        )

