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


class _RaisingSuccessNotifier:
    def __init__(self) -> None:
        self.success_calls = 0

    def notify_success(self, dashboard_nome, url):
        self.success_calls += 1
        raise RuntimeError("webhook indisponível")

    def notify_failure(self, dashboard_nome, error):
        raise AssertionError("notify_failure não deveria ser chamado em um pipeline bem-sucedido")


def test_run_dashboard_notify_success_failure_does_not_trigger_retry_or_raise():
    config = _make_config()
    executor = _FakeExecutor()
    publisher = _FakePublisher()
    raising_notifier = _RaisingSuccessNotifier()

    result = run_dashboard(
        config=config,
        executor=executor,
        generator=_FakeGenerator(),
        publisher=publisher,
        notifiers=[raising_notifier],
        max_attempts=2,
        now=dt.datetime(2026, 9, 21, 7, 0),
    )

    assert result == PipelineResult(dashboard_id="comissoes-mensal", url="comissoes-mensal/index.html")
    assert executor.calls == 1
    assert len(publisher.archived) == 1
    assert len(publisher.latest) == 1
    assert raising_notifier.success_calls == 1


class _RaisingFailureNotifier:
    def notify_success(self, dashboard_nome, url):
        raise AssertionError("notify_success não deveria ser chamado em um pipeline com falha total")

    def notify_failure(self, dashboard_nome, error):
        raise RuntimeError("webhook indisponível")


def test_run_dashboard_notify_failure_failure_does_not_block_other_notifiers_or_mask_error():
    config = _make_config()
    executor = _FakeExecutor(fail_times=99)
    publisher = _FakePublisher()
    raising_notifier = _RaisingFailureNotifier()
    other_notifier = _FakeNotifier()

    with pytest.raises(PipelineError):
        run_dashboard(
            config=config,
            executor=executor,
            generator=_FakeGenerator(),
            publisher=publisher,
            notifiers=[raising_notifier, other_notifier],
            max_attempts=2,
            now=dt.datetime(2026, 9, 21, 7, 0),
        )

    assert publisher.latest == []
    assert len(other_notifier.failures) == 1
    assert other_notifier.failures[0][0] == "Comissões — Fechamento Mensal"


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


class _RaisingNotifier:
    def notify_success(self, dashboard_nome, url):
        raise RuntimeError("webhook fora do ar")

    def notify_failure(self, dashboard_nome, error):
        pass


def test_notify_all_logs_when_a_notifier_raises(caplog):
    config = _make_config()
    executor = _FakeExecutor()
    publisher = _FakePublisher()

    with caplog.at_level("ERROR"):
        result = run_dashboard(
            config=config,
            executor=executor,
            generator=_FakeGenerator(),
            publisher=publisher,
            notifiers=[_RaisingNotifier()],
            now=dt.datetime(2026, 9, 21, 7, 0),
        )

    assert result.url == "comissoes-mensal/index.html"
    assert any(
        "notify_success" in record.getMessage() and "_RaisingNotifier" in record.getMessage()
        for record in caplog.records
    )
