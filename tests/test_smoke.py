"""Basic package and CLI smoke tests for the project scaffold."""

from typer.testing import CliRunner

from ai_git_commit import __version__
from ai_git_commit.cli import app


def test_package_has_version() -> None:
    assert __version__ == "0.1.0"


def test_cli_help() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Generate a commit message" in result.stdout

