from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import smtplib
from pathlib import Path

import anthropic
from azure.storage.blob import BlobServiceClient
from databricks.sdk import WorkspaceClient

from .config import DashboardConfig, GeracaoConfig, NotificacaoConfig, load_config
from .extraction import DatabricksSQLExecutor
from .generation import AnthropicGenerator, DatabricksModelServingGenerator, Generator
from .notification import EmailNotifier, Notifier, WebhookNotifier
from .pipeline import run_dashboard
from .publishing import AzureBlobPublisher, DatabricksNativePublisher, Publisher


def build_executor() -> DatabricksSQLExecutor:
    warehouses_json = os.environ.get("DATABRICKS_WAREHOUSES")
    if warehouses_json:
        http_path_by_warehouse = json.loads(warehouses_json)
    else:
        http_path_by_warehouse = {
            os.environ["DATABRICKS_WAREHOUSE_NAME"]: os.environ["DATABRICKS_HTTP_PATH"]
        }
    return DatabricksSQLExecutor(
        server_hostname=os.environ["DATABRICKS_SERVER_HOSTNAME"],
        http_path_by_warehouse=http_path_by_warehouse,
        access_token=os.environ["DATABRICKS_TOKEN"],
    )


def build_generator(geracao: GeracaoConfig) -> Generator:
    if geracao.backend == "anthropic":
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        return AnthropicGenerator(client=client, model=geracao.modelo)
    if geracao.backend == "databricks-model-serving":
        return DatabricksModelServingGenerator(
            workspace_client=WorkspaceClient(), endpoint_name=geracao.endpoint
        )
    raise ValueError(f"backend de geração desconhecido: {geracao.backend!r}")


def build_publisher(destino: str) -> Publisher:
    if destino == "azure-blob":
        service_client = BlobServiceClient.from_connection_string(
            os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        )
        container_client = service_client.get_container_client(
            os.environ["AZURE_STORAGE_CONTAINER"]
        )
        return AzureBlobPublisher(
            container_client=container_client,
            base_url=os.environ.get("AZURE_STORAGE_PUBLIC_BASE_URL"),
        )
    if destino == "databricks-native":
        hostname = os.environ.get("DATABRICKS_SERVER_HOSTNAME")
        return DatabricksNativePublisher(
            workspace_client=WorkspaceClient(),
            workspace_host=f"https://{hostname}" if hostname else None,
        )
    raise ValueError(f"destino de publicação desconhecido: {destino!r}")


def build_notifiers(notificacao: NotificacaoConfig) -> list[Notifier]:
    notifiers: list[Notifier] = []
    if notificacao.email:
        smtp_client = smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")))
        smtp_client.starttls()
        smtp_client.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        notifiers.append(
            EmailNotifier(
                smtp_client=smtp_client,
                sender=os.environ["SMTP_USER"],
                recipients=notificacao.email,
            )
        )
    if notificacao.slack_webhook:
        notifiers.append(WebhookNotifier(webhook_url=notificacao.slack_webhook))
    if notificacao.teams_webhook:
        notifiers.append(WebhookNotifier(webhook_url=notificacao.teams_webhook))
    return notifiers


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    parser = argparse.ArgumentParser(
        description="Roda o pipeline de um dashboard a partir de um config YAML."
    )
    parser.add_argument("config_path", type=Path)
    parser.add_argument("--trigger", choices=["schedule", "manual"], default="manual")
    args = parser.parse_args()

    config: DashboardConfig = load_config(args.config_path)
    result = run_dashboard(
        config=config,
        executor=build_executor(),
        generator=build_generator(config.geracao),
        publisher=build_publisher(config.publicacao.destino),
        notifiers=build_notifiers(config.notificacao),
        now=dt.datetime.utcnow(),
    )
    print(f"Dashboard {result.dashboard_id!r} publicado em: {result.url}")


if __name__ == "__main__":
    main()
