from __future__ import annotations

from email.message import EmailMessage
from typing import Protocol

import requests


class Notifier(Protocol):
    def notify_success(self, dashboard_nome: str, url: str) -> None: ...
    def notify_failure(self, dashboard_nome: str, error: str) -> None: ...


class EmailNotifier:
    def __init__(self, smtp_client, sender: str, recipients: list[str]) -> None:
        self._smtp_client = smtp_client
        self._sender = sender
        self._recipients = recipients

    def notify_success(self, dashboard_nome: str, url: str) -> None:
        self._send(
            f"Dashboard atualizado: {dashboard_nome}",
            f"Novo dashboard disponível em: {url}",
        )

    def notify_failure(self, dashboard_nome: str, error: str) -> None:
        self._send(
            f"[ERRO] Falha ao gerar dashboard: {dashboard_nome}",
            f"Erro: {error}",
        )

    def _send(self, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._sender
        message["To"] = ", ".join(self._recipients)
        message.set_content(body)
        self._smtp_client.send_message(message)


class WebhookNotifier:
    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def notify_success(self, dashboard_nome: str, url: str) -> None:
        requests.post(self._webhook_url, json={"text": f"Dashboard atualizado: {dashboard_nome}\n{url}"})

    def notify_failure(self, dashboard_nome: str, error: str) -> None:
        requests.post(
            self._webhook_url,
            json={"text": f"[ERRO] Falha ao gerar dashboard: {dashboard_nome}\n{error}"},
        )
