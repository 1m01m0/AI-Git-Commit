# AI Git Commit

> Generate perfect git commits with AI.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: MVP](https://img.shields.io/badge/status-MVP-orange.svg)](https://github.com/)

AI Git Commit is a lightweight CLI that analyzes staged Git changes and
generates a clear, conventional commit message with OpenAI, Anthropic, or
DeepSeek.

> The project is currently in MVP development. The first public release will
> follow final packaging, documentation, and GitHub verification.

## Demo

A short terminal demo will be added at `docs/demo.gif` before the first
release.

## Features

- Run with `git ai-commit`.
- Analyze staged Git changes without automatically staging files.
- Support OpenAI, Anthropic, and DeepSeek through one provider interface.
- Validate model output as a Conventional Commit title.
- Preview the generated message before committing.
- Require explicit user confirmation.
- Retry with an explicitly configured fallback provider after API or parsing failures.
- Never automatically stage files or commit without confirmation.

## Installation

```bash
pip install ai-git-commit-cli
```

The PyPI distribution is named `ai-git-commit-cli` because the shorter
`ai-git-commit` name is already used by another project. The installed product
and Git command remain **AI Git Commit** and `git ai-commit`.

For local development:

```bash
git clone <repository-url>
cd ai-git-commit
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

## Configuration

Set the provider API key before running the command:

```bash
export OPENAI_API_KEY="your-api-key"
```

Supported keys:

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
export DEEPSEEK_API_KEY="your-api-key"
```

Optional settings:

```bash
export AI_GIT_COMMIT_PROVIDER="openai"
export AI_GIT_COMMIT_FALLBACK_PROVIDER="deepseek"
export AI_GIT_COMMIT_MODEL=""
export AI_GIT_COMMIT_LANGUAGE="en"
export AI_GIT_COMMIT_MAX_DIFF_CHARS="20000"
export AI_GIT_COMMIT_TIMEOUT_SECONDS="60"
```

Set `AI_GIT_COMMIT_PROVIDER` to `anthropic` or `deepseek` when using those
providers. A fallback is attempted only when it is explicitly configured and
has its corresponding API key. The same values can be stored in a local
`.env` file. Do not commit that file.

The default models are `gpt-4o-mini`, `claude-haiku-4-5-20251001`, and
`deepseek-v4-flash`; set `AI_GIT_COMMIT_MODEL` when a different model is needed.

## Usage

AI Git Commit operates on staged changes:

```bash
git add .
git ai-commit
```

The tool displays the generated title and change summary, then asks for
confirmation. Enter `n` to exit without running `git commit`. Unstaged and
untracked files are not sent to the model until they are staged with `git add`.

## Examples

```text
Generated commit message:

feat(auth): implement JWT authentication

Changes:

- add JWT token validation
- update login API
- remove legacy session handling

Confirm commit? (y/n)
```

## Roadmap

- [ ] First stable CLI release
- [ ] Deterministic Conventional Commit type classification
- [ ] More polished Chinese and English language modes
- [ ] Commit history style learning
- [ ] `git ai-pr` for pull request descriptions
- [ ] Demo GIF and release automation

## Privacy and safety

The staged diff is sent to the provider selected in your environment. Review
your provider's data policy before using this tool with proprietary code. API
keys are read from environment variables or `.env` and are never included in
the generated commit message.

## Contributing

Bug reports, feature requests, and pull requests are welcome. Please keep
changes focused, add tests for behavior changes, and run `python -m pytest`
before submitting a pull request.

## License

AI Git Commit is released under the MIT License. See [LICENSE](LICENSE).

If this tool saves you time, consider giving the project a star when the
repository is published.
