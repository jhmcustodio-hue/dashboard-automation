from datetime import datetime
from unittest.mock import MagicMock

from dashboard_automation.config import PublicacaoConfig
from dashboard_automation.publishing import AzureBlobPublisher, DatabricksNativePublisher


def test_azure_blob_publisher_publish_latest_uploads_to_slug_index():
    container_client = MagicMock()
    publisher = AzureBlobPublisher(container_client=container_client)
    publicacao = PublicacaoConfig(destino="azure-blob", slug="comissoes-mensal")

    path = publisher.publish_latest("<html></html>", publicacao)

    assert path == "comissoes-mensal/index.html"
    _, kwargs = container_client.upload_blob.call_args
    assert kwargs["name"] == "comissoes-mensal/index.html"
    assert kwargs["data"] == "<html></html>"
    assert kwargs["overwrite"] is True
    assert kwargs["content_settings"].content_type == "text/html"


def test_azure_blob_publisher_publish_archive_uses_timestamped_path():
    container_client = MagicMock()
    publisher = AzureBlobPublisher(container_client=container_client)
    publicacao = PublicacaoConfig(destino="azure-blob", slug="comissoes-mensal")
    timestamp = datetime(2026, 9, 21, 7, 0)

    path = publisher.publish_archive("<html></html>", publicacao, timestamp)

    assert path == "archive/comissoes-mensal/2026-09-21T07-00.html"


def test_databricks_native_publisher_publish_latest_uploads_to_workspace_path():
    workspace_client = MagicMock()
    publisher = DatabricksNativePublisher(
        workspace_client=workspace_client, base_path="/Workspace/dashboards"
    )
    publicacao = PublicacaoConfig(destino="databricks-native", slug="comissoes-mensal")

    path = publisher.publish_latest("<html></html>", publicacao)

    assert path == "/Workspace/dashboards/comissoes-mensal/index.html"
    _, kwargs = workspace_client.workspace.upload.call_args
    assert kwargs["path"] == "/Workspace/dashboards/comissoes-mensal/index.html"
    assert kwargs["content"] == b"<html></html>"
    assert kwargs["overwrite"] is True


def test_databricks_native_publisher_publish_archive_uses_timestamped_path():
    workspace_client = MagicMock()
    publisher = DatabricksNativePublisher(
        workspace_client=workspace_client, base_path="/Workspace/dashboards"
    )
    publicacao = PublicacaoConfig(destino="databricks-native", slug="comissoes-mensal")
    timestamp = datetime(2026, 9, 21, 7, 0)

    path = publisher.publish_archive("<html></html>", publicacao, timestamp)

    assert path == "/Workspace/dashboards/archive/comissoes-mensal/2026-09-21T07-00.html"
