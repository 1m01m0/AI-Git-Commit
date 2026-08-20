"""Git repository and subprocess helpers."""

from dataclasses import dataclass
from pathlib import Path
import subprocess


class GitError(RuntimeError):
    """Raised when a Git operation cannot be completed."""


class NotGitRepositoryError(GitError):
    """Raised when the current directory is outside a Git repository."""


class NoStagedChangesError(GitError):
    """Raised when there is no staged diff to analyze."""


class GitCommandError(GitError):
    """Raised when Git returns a non-zero exit status."""


@dataclass(frozen=True)
class DiffResult:
    """A staged diff and whether it was shortened for the model request."""

    text: str
    truncated: bool
    original_length: int


@dataclass(frozen=True)
class GitRepository:
    """A Git repository rooted at its top-level directory."""

    root: Path

    @classmethod
    def discover(cls, cwd: str | Path | None = None) -> "GitRepository":
        """Find the repository containing ``cwd``."""
        working_directory = Path(cwd or Path.cwd()).resolve()
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=working_directory,
                capture_output=True,
                check=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise GitError("Git is not installed or is not available on PATH.") from exc
        except subprocess.CalledProcessError as exc:
            raise NotGitRepositoryError(
                "Current directory is not inside a Git repository."
            ) from exc

        root_text = result.stdout.strip()
        if not root_text:
            raise GitError("Git did not return a repository root.")
        return cls(root=Path(root_text).resolve())

    def get_staged_diff(self, max_chars: int = 20_000) -> DiffResult:
        """Return the staged diff, optionally limiting its size."""
        if max_chars <= 0:
            raise ValueError("max_chars must be positive.")

        result = self._run(
            [
                "diff",
                "--cached",
                "--no-ext-diff",
                "--unified=3",
                "--",
            ]
        )
        diff_text = result.stdout
        if not diff_text.strip():
            raise NoStagedChangesError("No staged changes found.")

        original_length = len(diff_text)
        if original_length <= max_chars:
            return DiffResult(
                text=diff_text,
                truncated=False,
                original_length=original_length,
            )

        marker = (
            "\n\n[Diff truncated by AI Git Commit after "
            f"{max_chars} characters.]\n"
        )
        available_chars = max(1, max_chars - len(marker))
        return DiffResult(
            text=diff_text[:available_chars] + marker,
            truncated=True,
            original_length=original_length,
        )

    def status(self) -> str:
        """Return short status output for friendly no-change messages."""
        return self._run(["status", "--short", "--untracked-files=all", "--"]).stdout.strip()

    def commit(self, message: str) -> str:
        """Create a commit using stdin, avoiding shell interpolation."""
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Commit message must not be empty.")

        try:
            result = self._run(
                ["commit", "-F", "-"],
                input_text=f"{clean_message}\n",
            )
        except GitCommandError as exc:
            raise GitError(f"Git commit failed: {exc}") from exc

        return "\n".join(
            part for part in (result.stdout.strip(), result.stderr.strip()) if part
        )

    def _run(
        self,
        arguments: list[str],
        *,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                ["git", *arguments],
                cwd=self.root,
                capture_output=True,
                check=True,
                input=input_text,
                text=True,
            )
        except FileNotFoundError as exc:
            raise GitError("Git is not installed or is not available on PATH.") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
            command = "git " + " ".join(arguments)
            message = detail or f"Command failed: {command}"
            raise GitCommandError(message) from exc
        return result
