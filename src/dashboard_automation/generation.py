from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

from .config import PromptConfig


class GenerationError(Exception):
    pass


class Generator(Protocol):
    def generate(self, prompt: PromptConfig, data: pd.DataFrame) -> str: ...


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    return stripped


def build_prompt(prompt: PromptConfig, data: pd.DataFrame) -> str:
    template_text = Path(prompt.template).read_text(encoding="utf-8")
    parts = [template_text]
    if prompt.instrucoes_extra:
        parts.append(f"\nInstruções adicionais para este dashboard:\n{prompt.instrucoes_extra}")
    parts.append(f"\nDados (CSV):\n{data.to_csv(index=False)}")
    return "\n".join(parts)


class AnthropicGenerator:
    def __init__(self, client, model: str = "claude-sonnet-5") -> None:
        self._client = client
        self._model = model

    def generate(self, prompt: PromptConfig, data: pd.DataFrame) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=16000,
            messages=[{"role": "user", "content": build_prompt(prompt, data)}],
        )
        stop_reason = getattr(message, "stop_reason", None)
        if stop_reason in ("max_tokens", "refusal"):
            raise GenerationError(f"geração interrompida ({stop_reason}) — resposta descartada")

        html = _strip_code_fence(message.content[0].text)
        if "<html" not in html.lower():
            raise GenerationError("resposta do modelo não contém HTML válido")
        return html
