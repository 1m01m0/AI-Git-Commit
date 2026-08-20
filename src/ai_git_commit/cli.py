"""Command-line entry point for AI Git Commit."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .config import ConfigError, Settings
from .git import GitError, GitRepository, NoStagedChangesError
from .llm import ChatMessage, LLMError, create_provider
from .prompt import (
    CommitSuggestion,
    PromptError,
    build_messages,
    format_commit_message,
    parse_response,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Generate a commit message from staged Git changes with AI.",
)
console = Console()


@app.callback(invoke_without_command=True)
def cli() -> None:
    """Generate and confirm an AI-assisted Git commit."""
    try:
        run()
    except typer.Exit:
        raise
    except (ConfigError, GitError, LLMError, PromptError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1) from exc


def _generate_suggestion(
    settings: Settings,
    messages: list[ChatMessage],
) -> tuple[CommitSuggestion, str]:
    provider_names = [settings.provider]
    if settings.fallback_provider:
        provider_names.append(settings.fallback_provider)

    errors: list[str] = []
    for provider_name in provider_names:
        try:
            provider = create_provider(
                provider_name,
                api_key=settings.api_key_for(provider_name),
                model=settings.model_for(provider_name),
                timeout_seconds=settings.timeout_seconds,
            )
            suggestion = parse_response(provider.generate(messages))
        except (ConfigError, LLMError, PromptError) as exc:
            errors.append(f"{provider_name}: {exc}")
            continue

        if provider_name != settings.provider:
            console.print(
                "[yellow]Primary provider failed; using fallback provider "
                f"{provider_name}.[/yellow]"
            )
        return suggestion, provider_name

    details = "\n".join(f"- {error}" for error in errors)
    raise LLMError(f"All configured LLM providers failed.\n{details}")


def _display_suggestion(suggestion: CommitSuggestion) -> None:
    lines = [suggestion.title]
    if suggestion.changes:
        lines.extend(["", "Changes:", "", *[f"- {change}" for change in suggestion.changes]])
    console.print(
        Panel(
            Text("\n".join(lines)),
            title="Generated commit message",
            border_style="green",
        )
    )


def run() -> None:
    """Run the repository-to-commit workflow."""
    settings = Settings.load()
    repository = GitRepository.discover()

    try:
        diff = repository.get_staged_diff(settings.max_diff_chars)
    except NoStagedChangesError:
        if repository.status():
            console.print(
                "[yellow]No staged changes found. Run `git add` before using "
                "git ai-commit.[/yellow]"
            )
        else:
            console.print("[yellow]Working tree is clean; there is nothing to commit.[/yellow]")
        raise typer.Exit(code=1)

    if diff.truncated:
        console.print(
            f"[yellow]The staged diff is {diff.original_length} characters; "
            f"only the first {settings.max_diff_chars} characters will be analyzed.[/yellow]"
        )

    console.print("[dim]Analyzing staged changes...[/dim]")
    messages = build_messages(diff.text, settings.language)
    suggestion, _provider_name = _generate_suggestion(settings, messages)
    _display_suggestion(suggestion)

    if not typer.confirm("Confirm commit?", default=False):
        console.print("[yellow]Commit cancelled. No commit was created.[/yellow]")
        return

    output = repository.commit(format_commit_message(suggestion))
    console.print("[green]Commit created successfully.[/green]")
    if output:
        console.print(Text(output))


def main() -> None:
    """Run the Typer application."""
    app()
