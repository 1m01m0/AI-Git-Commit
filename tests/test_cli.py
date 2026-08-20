"""CLI workflow tests with fake repository and provider boundaries."""

from dataclasses import dataclass, field

from typer.testing import CliRunner

from ai_git_commit import cli
from ai_git_commit.config import Settings
from ai_git_commit.git import DiffResult, NoStagedChangesError
from ai_git_commit.llm import LLMError


runner = CliRunner()
VALID_RESPONSE = '{"commit_message": "feat(cli): add commit flow", "changes": ["add confirmation"]}'


@dataclass
class FakeRepository:
    diff: DiffResult | None = DiffResult("diff --git a/file b/file\n", False, 28)
    status_output: str = ""
    commits: list[str] = field(default_factory=list)

    def get_staged_diff(self, max_chars: int) -> DiffResult:
        if self.diff is None:
            raise NoStagedChangesError("No staged changes found.")
        return self.diff

    def status(self) -> str:
        return self.status_output

    def commit(self, message: str) -> str:
        self.commits.append(message)
        return "[main abc1234] feat(cli): add commit flow"


class FakeProvider:
    def __init__(self, response: str = VALID_RESPONSE, error: Exception | None = None) -> None:
        self.response = response
        self.error = error

    def generate(self, messages):
        if self.error:
            raise self.error
        return self.response


def _settings(**values: str) -> Settings:
    return Settings.from_mapping(
        {
            "OPENAI_API_KEY": "openai-secret",
            "ANTHROPIC_API_KEY": "anthropic-secret",
            **values,
        }
    )


def test_rejecting_confirmation_does_not_commit(monkeypatch) -> None:
    repository = FakeRepository()
    monkeypatch.setattr(cli.Settings, "load", lambda: _settings())
    monkeypatch.setattr(cli.GitRepository, "discover", lambda: repository)
    monkeypatch.setattr(cli, "create_provider", lambda *args, **kwargs: FakeProvider())

    result = runner.invoke(cli.app, [], input="n\n")

    assert result.exit_code == 0
    assert repository.commits == []
    assert "Commit cancelled" in result.stdout


def test_confirming_creates_commit(monkeypatch) -> None:
    repository = FakeRepository()
    monkeypatch.setattr(cli.Settings, "load", lambda: _settings())
    monkeypatch.setattr(cli.GitRepository, "discover", lambda: repository)
    monkeypatch.setattr(cli, "create_provider", lambda *args, **kwargs: FakeProvider())

    result = runner.invoke(cli.app, [], input="y\n")

    assert result.exit_code == 0
    assert repository.commits == [
        "feat(cli): add commit flow\n\n- add confirmation"
    ]
    assert "Commit created successfully" in result.stdout


def test_primary_provider_failure_uses_configured_fallback(monkeypatch) -> None:
    repository = FakeRepository()
    provider_calls: list[str] = []

    def fake_create_provider(provider_name, **kwargs):
        provider_calls.append(provider_name)
        if provider_name == "openai":
            return FakeProvider(error=LLMError("temporary outage"))
        return FakeProvider()

    monkeypatch.setattr(
        cli.Settings,
        "load",
        lambda: _settings(
            AI_GIT_COMMIT_PROVIDER="openai",
            AI_GIT_COMMIT_FALLBACK_PROVIDER="anthropic",
        ),
    )
    monkeypatch.setattr(cli.GitRepository, "discover", lambda: repository)
    monkeypatch.setattr(cli, "create_provider", fake_create_provider)

    result = runner.invoke(cli.app, [], input="n\n")

    assert result.exit_code == 0
    assert provider_calls == ["openai", "anthropic"]
    assert "fallback provider anthropic" in result.stdout


def test_no_staged_changes_does_not_call_provider(monkeypatch) -> None:
    repository = FakeRepository(diff=None, status_output=" M file.py")
    provider_called = False

    def unexpected_provider(*args, **kwargs):
        nonlocal provider_called
        provider_called = True
        return FakeProvider()

    monkeypatch.setattr(cli.Settings, "load", lambda: _settings())
    monkeypatch.setattr(cli.GitRepository, "discover", lambda: repository)
    monkeypatch.setattr(cli, "create_provider", unexpected_provider)

    result = runner.invoke(cli.app, [])

    assert result.exit_code == 1
    assert provider_called is False
    assert "git add" in result.stdout

