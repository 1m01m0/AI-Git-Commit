"""Provider abstraction tests without network calls."""

from types import SimpleNamespace

from ai_git_commit.llm import (
    AnthropicProvider,
    DeepSeekProvider,
    OpenAIProvider,
    create_provider,
)


MESSAGES = [
    {"role": "system", "content": "Return JSON."},
    {"role": "user", "content": "Analyze this diff."},
]
RAW_RESPONSE = '{"commit_message": "fix(cli): handle errors", "changes": ["show errors"]}'


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=RAW_RESPONSE))]
        )


class FakeAnthropicClient:
    def __init__(self) -> None:
        self.messages = SimpleNamespace(create=self.create)
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        block = SimpleNamespace(type="text", text=RAW_RESPONSE)
        return SimpleNamespace(content=[block])


def test_openai_compatible_provider_returns_text() -> None:
    client = FakeOpenAIClient()
    provider = OpenAIProvider("secret", "test-model", client=client)

    assert provider.generate(MESSAGES) == RAW_RESPONSE
    assert client.kwargs["response_format"] == {"type": "json_object"}


def test_deepseek_provider_uses_same_interface() -> None:
    provider = DeepSeekProvider("secret", "test-model", client=FakeOpenAIClient())

    assert provider.generate(MESSAGES) == RAW_RESPONSE


def test_anthropic_provider_separates_system_message() -> None:
    client = FakeAnthropicClient()
    provider = AnthropicProvider("secret", "test-model", client=client)

    assert provider.generate(MESSAGES) == RAW_RESPONSE
    assert client.kwargs["system"] == "Return JSON."
    assert client.kwargs["messages"] == [{"role": "user", "content": "Analyze this diff."}]


def test_provider_factory_supports_all_names() -> None:
    assert create_provider("openai", api_key="x", model="m").name == "openai"
    assert create_provider("anthropic", api_key="x", model="m").name == "anthropic"
    assert create_provider("deepseek", api_key="x", model="m").name == "deepseek"

