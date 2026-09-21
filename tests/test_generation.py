import pandas as pd

from dashboard_automation.config import PromptConfig
from dashboard_automation.generation import AnthropicGenerator, build_prompt


def test_build_prompt_includes_template_instrucoes_and_data(tmp_path):
    template_path = tmp_path / "template.md"
    template_path.write_text("Gere um dashboard HTML com os dados abaixo.", encoding="utf-8")
    data = pd.DataFrame({"mes": ["2026-01"], "total": [1000]})

    prompt = build_prompt(
        PromptConfig(template=str(template_path), instrucoes_extra="Destaque quedas > 10%"),
        data,
    )

    assert "Gere um dashboard HTML" in prompt
    assert "Destaque quedas > 10%" in prompt
    assert "mes,total" in prompt
    assert "2026-01,1000" in prompt


def test_build_prompt_without_instrucoes_extra_omits_section(tmp_path):
    template_path = tmp_path / "template.md"
    template_path.write_text("Template base.", encoding="utf-8")
    data = pd.DataFrame({"a": [1]})

    prompt = build_prompt(PromptConfig(template=str(template_path)), data)

    assert "Template base." in prompt
    assert "Instruções adicionais" not in prompt


class _FakeContentBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeMessage:
    def __init__(self, text: str) -> None:
        self.content = [_FakeContentBlock(text)]


class _FakeMessagesClient:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeMessage(self._response_text)


class _FakeAnthropicClient:
    def __init__(self, response_text: str) -> None:
        self.messages = _FakeMessagesClient(response_text)


def test_anthropic_generator_returns_model_text_and_uses_configured_model(tmp_path):
    template_path = tmp_path / "template.md"
    template_path.write_text("Template.", encoding="utf-8")
    data = pd.DataFrame({"a": [1]})
    fake_client = _FakeAnthropicClient(response_text="<html>ok</html>")

    generator = AnthropicGenerator(client=fake_client, model="claude-sonnet-5")
    result = generator.generate(PromptConfig(template=str(template_path)), data)

    assert result == "<html>ok</html>"
    assert fake_client.messages.calls[0]["model"] == "claude-sonnet-5"
    assert "Template." in fake_client.messages.calls[0]["messages"][0]["content"]
