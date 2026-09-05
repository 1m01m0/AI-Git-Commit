# AI Git Commit

Generate a commit title and change summary from your staged Git diff using OpenAI, Anthropic, or DeepSeek. Review the suggestion in your terminal, then confirm whether to create the commit.

The current source package is version 0.1.0. It exposes `git-ai-commit` (also accessible as `git ai-commit`) and `ai-commit`. Installation from this repository is documented below; package-registry availability is not assumed.

## Quick start

Requires **Python 3.10+**, Git on `PATH`, and an API key for a supported provider.

```bash
git clone https://github.com/1m01m0/AI-Git-Commit.git
cd AI-Git-Commit
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
git ai-commit --help
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`. Keep the environment active when working in another repository.

Set `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `DEEPSEEK_API_KEY` securely in your shell environment. Select the corresponding provider, then review and stage the intended files:

```bash
export AI_GIT_COMMIT_PROVIDER="openai"
cd /path/to/your-project
git diff
git add path/to/changed-file
git diff --cached
git ai-commit
```

**The API request happens before the commit confirmation.** The staged diff is sent to the configured provider; secrets in that diff are not redacted. Use only changes that you are authorized to send. The CLI never stages files automatically and does not push commits.

## Configuration

Configuration is read from environment variables and a `.env` discovered by `python-dotenv`. Existing environment values take precedence. See [.env.example](.env.example) for the supported names; keep keys and local `.env` files out of version control.

| Variable | Default / meaning |
| --- | --- |
| `AI_GIT_COMMIT_PROVIDER` | `openai`; also accepts `anthropic` or `deepseek`. |
| `OPENAI_API_KEY` | Key for OpenAI. |
| `ANTHROPIC_API_KEY` | Key for Anthropic. |
| `DEEPSEEK_API_KEY` | Key for DeepSeek. |
| `AI_GIT_COMMIT_FALLBACK_PROVIDER` | Unset; optional second provider, different from the primary. |
| `AI_GIT_COMMIT_MODEL` | Unset; override the model name for **both** primary and fallback providers. |
| `AI_GIT_COMMIT_LANGUAGE` | `en`; values starting with `zh` or `cn` request Chinese, all others request English. |
| `AI_GIT_COMMIT_MAX_DIFF_CHARS` | `20000`; positive character limit for diff truncation. |
| `AI_GIT_COMMIT_TIMEOUT_SECONDS` | `60`; positive provider-request timeout. |

The model defaults in [config.py](src/ai_git_commit/config.py) are `gpt-4o-mini`, `claude-haiku-4-5-20251001`, and `deepseek-v4-flash`, respectively. These are source-code defaults, not a guarantee of current provider availability or account access. Override the model if needed.

A fallback is attempted after a primary configuration, request, or response-validation failure. It needs its own key and may receive the same staged diff. There is no separate fallback-model setting; leave the model override unset when you need provider-specific defaults.

## Commit workflow

1. Discover the current Git repository and read `git diff --cached --no-ext-diff --unified=3`.
2. Truncate a large diff and request a JSON suggestion from the selected provider.
3. Validate the title format, its 100-character limit, and up to six change bullets.
4. Display the suggestion and ask `Confirm commit?`, with **No** as the default.
5. On confirmation, run `git commit -F -` with the title and bullets.

Example suggestion (illustrative):

```text
fix(auth): preserve session expiry during token refresh

- keep the original expiry when refreshing a session
- add coverage for expired sessions
```

Accepted types are `feat`, `fix`, `refactor`, `docs`, `test`, `style`, `perf`, `build`, and `chore`; scope and the breaking-change marker are optional. Format validation does not verify whether the description is factually correct.

## Limits and troubleshooting

| Situation | Action |
| --- | --- |
| `git: 'ai-commit' is not a git command` | Activate the installation environment and check that `git-ai-commit` is on `PATH`. |
| No staged changes | Stage the intended files and inspect `git diff --cached`. |
| Missing provider key | Set the key named in the error in the same process environment. |
| Invalid JSON, unsupported model, or provider failure | Check the model/configuration; an explicitly configured fallback may be attempted. |
| Commit fails after confirmation | Check Git identity, repository state, and hooks; normal Git hooks still run. |

Unstaged-only changes and untracked files are excluded until staged. Diff truncation can omit important changes; binary content is not analyzed as image or binary data. There is no interactive message editor, offline model backend, or automatic test execution. Reject an unsuitable suggestion and commit manually if necessary.

Known configuration, Git, provider, or parsing errors return status 1. Cancelling the confirmation returns successfully without a commit. Avoid changing the staged content while the model request or confirmation is pending: the final Git command commits the index as it exists at that time.

## Development and contributions

```bash
python -m pip install -e '.[dev]'
python -m pytest
```

The [tests](tests) cover configuration, staged-diff handling, prompt parsing, provider adapters, and the confirmation flow using isolated fixtures and mocked providers. [Report issues](https://github.com/1m01m0/AI-Git-Commit/issues) with a sanitized reproduction, Python version, provider name, and error message; never include keys or private diffs.

## License

[MIT](LICENSE). Copyright © 2026 AI Git Commit contributors.
