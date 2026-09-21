from __future__ import annotations

import dataclasses
from pathlib import Path

import yaml

VALID_DESTINOS = {"azure-blob", "databricks-native"}
VALID_GERACAO_BACKENDS = {"anthropic", "databricks-model-serving"}


@dataclasses.dataclass(frozen=True)
class QueryConfig:
    sql: str
    warehouse: str


@dataclasses.dataclass(frozen=True)
class ScheduleConfig:
    cron: str | None = None
    enabled: bool = False


@dataclasses.dataclass(frozen=True)
class GeracaoConfig:
    # "modelo" só se aplica ao backend "anthropic" (nome do modelo na API da Anthropic).
    # "endpoint" só se aplica ao backend "databricks-model-serving" (nome do serving endpoint
    # no workspace, ex.: "databricks-claude-sonnet-4-5") — mantém o dado dentro do perímetro
    # do Databricks em vez de chamar a API da Anthropic diretamente (ver "Gate de compliance").
    backend: str = "anthropic"
    modelo: str = "claude-sonnet-5"
    endpoint: str | None = None


@dataclasses.dataclass(frozen=True)
class PromptConfig:
    # Depois de passar por `load_config`, `template` é sempre um caminho absoluto
    # (resolvido contra a raiz do projeto, não contra o CWD do processo).
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
    geracao: GeracaoConfig = dataclasses.field(default_factory=GeracaoConfig)


def load_config(path: Path | str) -> DashboardConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    publicacao_raw = raw["publicacao"]
    if publicacao_raw["destino"] not in VALID_DESTINOS:
        raise ValueError(
            f"destino inválido: {publicacao_raw['destino']!r} "
            f"(esperado um de {sorted(VALID_DESTINOS)})"
        )

    geracao = GeracaoConfig(**raw.get("geracao", {}))
    if geracao.backend not in VALID_GERACAO_BACKENDS:
        raise ValueError(
            f"backend de geração inválido: {geracao.backend!r} "
            f"(esperado um de {sorted(VALID_GERACAO_BACKENDS)})"
        )
    if geracao.backend == "databricks-model-serving" and not geracao.endpoint:
        raise ValueError(
            "geracao.endpoint é obrigatório quando geracao.backend é "
            "'databricks-model-serving' (nome do serving endpoint no workspace)"
        )

    # Todo config real mora em <project_root>/dashboards/<id>.yaml, e os templates em
    # <project_root>/templates/... — logo a raiz do projeto é o avô do arquivo de config.
    # Resolver aqui (e não em generation.py) torna o caminho independente do CWD do processo.
    project_root = Path(path).resolve().parent.parent
    prompt_raw = dict(raw["prompt"])
    prompt_raw["template"] = str((project_root / prompt_raw["template"]).resolve())

    return DashboardConfig(
        id=raw["id"],
        nome=raw["nome"],
        query=QueryConfig(**raw["query"]),
        schedule=ScheduleConfig(**raw.get("schedule", {})),
        geracao=geracao,
        prompt=PromptConfig(**prompt_raw),
        publicacao=PublicacaoConfig(**publicacao_raw),
        notificacao=NotificacaoConfig(**raw.get("notificacao", {})),
    )
