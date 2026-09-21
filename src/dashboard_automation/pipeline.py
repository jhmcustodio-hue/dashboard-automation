from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .config import DashboardConfig
from .extraction import QueryExecutor
from .generation import Generator
from .notification import Notifier
from .publishing import Publisher


class PipelineError(Exception):
    pass


@dataclass
class PipelineResult:
    dashboard_id: str
    url: str


def run_dashboard(
    config: DashboardConfig,
    executor: QueryExecutor,
    generator: Generator,
    publisher: Publisher,
    notifiers: list[Notifier],
    max_attempts: int = 2,
    now: dt.datetime | None = None,
) -> PipelineResult:
    timestamp = now or dt.datetime.utcnow()
    last_error: Exception | None = None

    for _ in range(max_attempts):
        try:
            data = executor.execute(config.query)
            html = generator.generate(config.prompt, data)
            publisher.publish_archive(html, config.publicacao, timestamp)
            url = publisher.publish_latest(html, config.publicacao)
        except Exception as exc:  # noqa: BLE001 - qualquer falha de etapa deve disparar retry/alerta, não travar o pipeline
            last_error = exc
            continue
        _notify_all(notifiers, "notify_success", config.nome, url)
        return PipelineResult(dashboard_id=config.id, url=url)

    _notify_all(notifiers, "notify_failure", config.nome, str(last_error))
    raise PipelineError(
        f"Falha ao gerar dashboard {config.id!r} após {max_attempts} tentativas: {last_error}"
    ) from last_error


def _notify_all(notifiers: list[Notifier], method_name: str, *args: object) -> None:
    for notifier in notifiers:
        try:
            getattr(notifier, method_name)(*args)
        except Exception:  # noqa: BLE001 - uma falha de notificação não deve mascarar o resultado real do pipeline nem impedir as demais notificações
            pass
