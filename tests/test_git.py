"""Git integration tests using isolated temporary repositories."""

from pathlib import Path
import subprocess

import pytest

from ai_git_commit.git import (
    GitRepository,
    NoStagedChangesError,
    NotGitRepositoryError,
)


def _run_git(directory: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=directory, check=True, capture_output=True, text=True)


def _make_repository(directory: Path) -> GitRepository:
    _run_git(directory, "init", "--quiet")
    _run_git(directory, "config", "user.email", "test@example.com")
    _run_git(directory, "config", "user.name", "Test User")
    return GitRepository.discover(directory)


def test_discover_rejects_non_repository(tmp_path: Path) -> None:
    with pytest.raises(NotGitRepositoryError):
        GitRepository.discover(tmp_path)


def test_get_staged_diff_returns_staged_content(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    source_file = tmp_path / "example.py"
    source_file.write_text("print('hello')\n", encoding="utf-8")
    _run_git(tmp_path, "add", "example.py")

    diff = repository.get_staged_diff()

    assert "example.py" in diff.text
    assert "print('hello')" in diff.text
    assert diff.truncated is False


def test_get_staged_diff_can_be_truncated(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    source_file = tmp_path / "large.txt"
    source_file.write_text("line\n" * 500, encoding="utf-8")
    _run_git(tmp_path, "add", "large.txt")

    diff = repository.get_staged_diff(max_chars=500)

    assert diff.truncated is True
    assert diff.original_length > 500
    assert "Diff truncated" in diff.text


def test_commit_uses_generated_message(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)
    source_file = tmp_path / "example.py"
    source_file.write_text("print('hello')\n", encoding="utf-8")
    _run_git(tmp_path, "add", "example.py")

    repository.commit("feat(cli): add initial command\n\n- add command entrypoint")
    message = subprocess.run(
        ["git", "log", "-1", "--format=%B"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout

    assert "feat(cli): add initial command" in message
    assert "- add command entrypoint" in message


def test_empty_staged_diff_is_rejected(tmp_path: Path) -> None:
    repository = _make_repository(tmp_path)

    with pytest.raises(NoStagedChangesError):
        repository.get_staged_diff()

