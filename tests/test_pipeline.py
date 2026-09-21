import datetime as dt

import pytest

from dashboard_automation.config import (
    DashboardConfig,
    NotificacaoConfig,
    PromptConfig,
    PublicacaoConfig,
    QueryConfig,
    ScheduleConfig,
)
from dashboard_automation.pipeline import PipelineError, PipelineResult, run_dashboard


def _make_config() -> DashboardConfig:
    return DashboardConfig(
        id="comissoes-mensal",
        nome="Comissões — Fechamento Mensal",
        query=QueryConfig(sql="SELECT 1", warehouse="meu-warehouse"),
        prompt=PromptConfig(template="templates/insights-padrao.md"),
        publicacao=PublicacaoConfig(destino="azure-blob", slug="comissoes-mensal"),
        notificacao=NotificacaoConfig(email=["time@empresa.com"]),
        schedule=ScheduleConfig(),
    )


class _FakeExecutor:
    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls = 0

    def execute(self, query):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("warehouse indisponível")
        return "fake-dataframe"


class _FakeGenerator:
    def generate(self, prompt, data):
        return "<html>ok</html>"


class _FakePublisher:
    def __init__(self) -> None:
        self.archived: list[tuple] = []
        self.latest: list[tuple] = []

    def publish_archive(self, html, publicacao, timestamp):
        self.archived.append((html, publicacao.slug, timestamp))
        return f"archive/{publicacao.slug}/{timestamp.isoformat()}.html"

    def publish_latest(self, html, publicacao):
        self.latest.append((html, publicacao.slug))
        return f"{publicacao.slug}/index.html"


class _FakeNotifier:
    def __init__(self) -> None:
        self.successes: list[tuple] = []
        self.failures: list[tuple] = []

    def notify_success(self, dashboard_nome, url):
        self.successes.append((dashboard_nome, url))

    def notify_failure(self, dashboard_nome, error):
        self.failures.append((dashboard_nome, error))


def test_run_dashboard_success_publishes_archive_then_latest_and_notifies():
    config = _make_config()
    executor = _FakeExecutor()
    publisher = _FakePublisher()
    notifier = _FakeNotifier()

    result = run_dashboard(
        config=config,
        executor=executor,
        generator=_FakeGenerator(),
        publisher=publisher,
        notifiers=[notifier],
        now=dt.datetime(2026, 9, 21, 7, 0),
    )

    assert result == PipelineResult(dashboard_id="comissoes-mensal", url="comissoes-mensal/index.html")
    assert len(publisher.archived) == 1
    assert len(publisher.latest) == 1
    assert notifier.successes == [("Comissões — Fechamento Mensal", "comissoes-mensal/index.html")]
    assert notifier.failures == []


def test_run_dashboard_retries_and_succeeds_on_second_attempt():
    config = _make_config()
    executor = _FakeExecutor(fail_times=1)
    publisher = _FakePublisher()

    result = run_dashboard(
        config=config,
        executor=executor,
        generator=_FakeGenerator(),
        publisher=publisher,
        notifiers=[],
        max_attempts=2,
        now=dt.datetime(2026, 9, 21, 7, 0),
    )

    assert executor.calls == 2
    assert len(publisher.latest) == 1
    assert result.url == "comissoes-mensal/index.html"


def test_run_dashboard_all_attempts_fail_notifies_and_raises_without_publishing_latest():
    config = _make_config()
    executor = _FakeExecutor(fail_times=99)
    publisher = _FakePublisher()
    notifier = _FakeNotifier()

    with pytest.raises(PipelineError):
        run_dashboard(
            config=config,
            executor=executor,
            generator=_FakeGenerator(),
            publisher=publisher,
            notifiers=[notifier],
            max_attempts=2,
            now=dt.datetime(2026, 9, 21, 7, 0),
        )

    assert publisher.latest == []
    assert len(notifier.failures) == 1
    assert notifier.failures[0][0] == "Comissões — Fechamento Mensal"
