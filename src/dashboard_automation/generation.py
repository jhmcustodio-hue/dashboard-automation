from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pandas as pd

from .config import PromptConfig


class Generator(Protocol):
    def generate(self, prompt: PromptConfig, data: pd.DataFrame) -> str: ...


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
            max_tokens=8192,
            messages=[{"role": "user", "content": build_prompt(prompt, data)}],
        )
        return message.content[0].text
