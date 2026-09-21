from unittest.mock import MagicMock, patch

import pytest

from dashboard_automation import cli
from dashboard_automation.config import GeracaoConfig, NotificacaoConfig
from dashboard_automation.generation import DatabricksModelServingGenerator
from dashboard_automation.pipeline import PipelineResult
from dashboard_automation.publishing import AzureBlobPublisher, DatabricksNativePublisher


def test_build_publisher_azure_blob(monkeypatch):
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "fake-conn-string")
    monkeypatch.setenv("AZURE_STORAGE_CONTAINER", "dashboards")
    fake_container_client = object()
    fake_service_client = MagicMock()
    fake_service_client.get_container_client.return_value = fake_container_client

    with patch(
        "dashboard_automation.cli.BlobServiceClient.from_connection_string",
        return_value=fake_service_client,
    ):
        publisher = cli.build_publisher("azure-blob")

    assert isinstance(publisher, AzureBlobPublisher)
    assert publisher._container_client is fake_container_client


def test_build_publisher_databricks_native():
    fake_workspace_client = object()
    with patch("dashboard_automation.cli.WorkspaceClient", return_value=fake_workspace_client):
        publisher = cli.build_publisher("databricks-native")

    assert isinstance(publisher, DatabricksNativePublisher)
    assert publisher._workspace_client is fake_workspace_client


def test_build_executor_uses_single_warehouse_env_vars_by_default(monkeypatch):
    monkeypatch.delenv("DATABRICKS_WAREHOUSES", raising=False)
    monkeypatch.setenv("DATABRICKS_SERVER_HOSTNAME", "adb-123.azuredatabricks.net")
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_NAME", "warehouse-principal")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc123")
    monkeypatch.setenv("DATABRICKS_TOKEN", "fake-token")

    executor = cli.build_executor()

    assert executor._http_path_by_warehouse == {
        "warehouse-principal": "/sql/1.0/warehouses/abc123"
    }


def test_build_executor_uses_databricks_warehouses_json_when_set(monkeypatch):
    monkeypatch.setenv("DATABRICKS_SERVER_HOSTNAME", "adb-123.azuredatabricks.net")
    monkeypatch.setenv("DATABRICKS_TOKEN", "fake-token")
    monkeypatch.setenv(
        "DATABRICKS_WAREHOUSES",
        '{"principal": "/sql/1.0/warehouses/abc123", "vendas": "/sql/1.0/warehouses/def456"}',
    )

    executor = cli.build_executor()

    assert executor._http_path_by_warehouse == {
        "principal": "/sql/1.0/warehouses/abc123",
        "vendas": "/sql/1.0/warehouses/def456",
    }


def test_build_generator_unknown_backend_raises():
    with pytest.raises(ValueError, match="backend de geração desconhecido"):
        cli.build_generator(GeracaoConfig(backend="nao-existe"))


def test_build_generator_databricks_model_serving():
    fake_workspace_client = object()
    with patch("dashboard_automation.cli.WorkspaceClient", return_value=fake_workspace_client):
        generator = cli.build_generator(
            GeracaoConfig(backend="databricks-model-serving", endpoint="databricks-claude-sonnet-4-5")
        )

    assert isinstance(generator, DatabricksModelServingGenerator)
    assert generator._workspace_client is fake_workspace_client
    assert generator._endpoint_name == "databricks-claude-sonnet-4-5"


def test_build_publisher_unknown_destino_raises():
    with pytest.raises(ValueError, match="desconhecido"):
        cli.build_publisher("ftp")


def test_build_notifiers_creates_email_and_slack(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.empresa.com")
    monkeypatch.setenv("SMTP_USER", "bot@empresa.com")
    monkeypatch.setenv("SMTP_PASSWORD", "fake-password")

    with patch("dashboard_automation.cli.smtplib.SMTP") as mock_smtp:
        notificacao = NotificacaoConfig(
            email=["time@empresa.com"], slack_webhook="https://hooks.slack.com/x"
        )
        notifiers = cli.build_notifiers(notificacao)

    assert len(notifiers) == 2
    mock_smtp.assert_called_once()


def test_build_notifiers_returns_empty_list_when_nothing_configured():
    assert cli.build_notifiers(NotificacaoConfig()) == []


def test_main_runs_pipeline_and_prints_url(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "dashboard.yaml"
    config_path.write_text(
        """
id: comissoes-mensal
nome: "Comissões — Fechamento Mensal"
query:
  sql: "SELECT 1"
  warehouse: "meu-warehouse"
prompt:
  template: "templates/insights-padrao.md"
publicacao:
  destino: "azure-blob"
  slug: "comissoes-mensal"
""",
        encoding="utf-8",
    )
    fake_result = PipelineResult(dashboard_id="comissoes-mensal", url="comissoes-mensal/index.html")

    monkeypatch.setattr(cli, "build_executor", lambda: object())
    monkeypatch.setattr(cli, "build_generator", lambda geracao: object())
    monkeypatch.setattr(cli, "build_publisher", lambda destino: object())
    monkeypatch.setattr(cli, "build_notifiers", lambda notificacao: [])
    monkeypatch.setattr(cli, "run_dashboard", lambda **kwargs: fake_result)
    monkeypatch.setattr("sys.argv", ["run-dashboard", str(config_path)])

    cli.main()

    captured = capsys.readouterr()
    assert "comissoes-mensal/index.html" in captured.out
