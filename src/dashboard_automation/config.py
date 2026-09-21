from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

VALID_DESTINOS = {"azure-blob", "databricks-native"}


@dataclasses.dataclass(frozen=True)
class QueryConfig:
    sql: str
    warehouse: str


@dataclasses.dataclass(frozen=True)
class ScheduleConfig:
    cron: str | None = None
    enabled: bool = False


@dataclasses.dataclass(frozen=True)
class PromptConfig:
    template: str
    instrucoes_extra: str | None = None


@dataclasses.dataclass(frozen=True)
class PublicacaoConfig:
    destino: str
    slug: str


@dataclasses.dataclass(frozen=True)
class NotificacaoConfig:
    email: list[str] = dataclasses.field(default_factory=list)
    slack_webhook: str | None = None
    teams_webhook: str | None = None


@dataclasses.dataclass(frozen=True)
class DashboardConfig:
    id: str
    nome: str
    query: QueryConfig
    prompt: PromptConfig
    publicacao: PublicacaoConfig
    notificacao: NotificacaoConfig
    schedule: ScheduleConfig = dataclasses.field(default_factory=ScheduleConfig)


def load_config(path: Path | str) -> DashboardConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    publicacao_raw = raw["publicacao"]
    if publicacao_raw["destino"] not in VALID_DESTINOS:
        raise ValueError(
            f"destino inválido: {publicacao_raw['destino']!r} "
            f"(esperado um de {sorted(VALID_DESTINOS)})"
        )

    return DashboardConfig(
        id=raw["id"],
        nome=raw["nome"],
        query=QueryConfig(**raw["query"]),
        schedule=ScheduleConfig(**raw.get("schedule", {})),
        prompt=PromptConfig(**raw["prompt"]),
        publicacao=PublicacaoConfig(**publicacao_raw),
        notificacao=NotificacaoConfig(**raw.get("notificacao", {})),
    )
