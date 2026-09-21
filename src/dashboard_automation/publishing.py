from __future__ import annotations

import datetime as dt
from typing import Protocol

from azure.storage.blob import ContentSettings
from databricks.sdk.service.workspace import ImportFormat

from .config import PublicacaoConfig


class Publisher(Protocol):
    def publish_archive(
        self, html: str, publicacao: PublicacaoConfig, timestamp: dt.datetime
    ) -> str: ...

    def publish_latest(self, html: str, publicacao: PublicacaoConfig) -> str: ...


def _archive_name(slug: str, timestamp: dt.datetime) -> str:
    return f"archive/{slug}/{timestamp.strftime('%Y-%m-%dT%H-%M')}.html"


class AzureBlobPublisher:
    def __init__(self, container_client, base_url: str | None = None) -> None:
        self._container_client = container_client
        self._base_url = base_url.rstrip("/") if base_url else None

    def _resolve_url(self, path: str) -> str:
        return f"{self._base_url}/{path}" if self._base_url else path

    def publish_archive(
        self, html: str, publicacao: PublicacaoConfig, timestamp: dt.datetime
    ) -> str:
        path = _archive_name(publicacao.slug, timestamp)
        self._upload(path, html)
        return self._resolve_url(path)

    def publish_latest(self, html: str, publicacao: PublicacaoConfig) -> str:
        path = f"{publicacao.slug}/index.html"
        self._upload(path, html)
        return self._resolve_url(path)

    def _upload(self, path: str, html: str) -> None:
        self._container_client.upload_blob(
            name=path,
            data=html,
            overwrite=True,
            content_settings=ContentSettings(content_type="text/html"),
        )


class DatabricksNativePublisher:
    def __init__(
        self,
        workspace_client,
        base_path: str = "/Workspace/dashboards",
        workspace_host: str | None = None,
    ) -> None:
        self._workspace_client = workspace_client
        self._base_path = base_path.rstrip("/")
        self._workspace_host = workspace_host.rstrip("/") if workspace_host else None

    def _resolve_url(self, path: str) -> str:
        # NOTA: o formato exato do deep-link para um arquivo do workspace varia conforme a
        # versão da UI do workspace Databricks do operador — este join é a fiação
        # (config -> URL real quando configurada), e o caminho pode precisar de ajuste
        # (ex.: prefixo "#workspace") para o workspace específico.
        if not self._workspace_host:
            return path
        return f"{self._workspace_host}/{path.lstrip('/')}"

    def publish_archive(
        self, html: str, publicacao: PublicacaoConfig, timestamp: dt.datetime
    ) -> str:
        path = f"{self._base_path}/{_archive_name(publicacao.slug, timestamp)}"
        self._upload(path, html)
        return self._resolve_url(path)

    def publish_latest(self, html: str, publicacao: PublicacaoConfig) -> str:
        path = f"{self._base_path}/{publicacao.slug}/index.html"
        self._upload(path, html)
        return self._resolve_url(path)

    def _upload(self, path: str, html: str) -> None:
        self._workspace_client.workspace.upload(
            path=path,
            content=html.encode("utf-8"),
            format=ImportFormat.AUTO,
            overwrite=True,
        )
