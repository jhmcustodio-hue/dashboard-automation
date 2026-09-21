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
    def __init__(self, container_client) -> None:
        self._container_client = container_client

    def publish_archive(
        self, html: str, publicacao: PublicacaoConfig, timestamp: dt.datetime
    ) -> str:
        path = _archive_name(publicacao.slug, timestamp)
        self._upload(path, html)
        return path

    def publish_latest(self, html: str, publicacao: PublicacaoConfig) -> str:
        path = f"{publicacao.slug}/index.html"
        self._upload(path, html)
        return path

    def _upload(self, path: str, html: str) -> None:
        self._container_client.upload_blob(
            name=path,
            data=html,
            overwrite=True,
            content_settings=ContentSettings(content_type="text/html"),
        )


class DatabricksNativePublisher:
    def __init__(self, workspace_client, base_path: str = "/Workspace/dashboards") -> None:
        self._workspace_client = workspace_client
        self._base_path = base_path.rstrip("/")

    def publish_archive(
        self, html: str, publicacao: PublicacaoConfig, timestamp: dt.datetime
    ) -> str:
        path = f"{self._base_path}/{_archive_name(publicacao.slug, timestamp)}"
        self._upload(path, html)
        return path

    def publish_latest(self, html: str, publicacao: PublicacaoConfig) -> str:
        path = f"{self._base_path}/{publicacao.slug}/index.html"
        self._upload(path, html)
        return path

    def _upload(self, path: str, html: str) -> None:
        self._workspace_client.workspace.upload(
            path=path,
            content=html.encode("utf-8"),
            format=ImportFormat.AUTO,
            overwrite=True,
        )
