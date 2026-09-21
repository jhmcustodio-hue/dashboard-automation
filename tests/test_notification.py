from unittest.mock import MagicMock, patch

import pytest
import requests

from dashboard_automation.notification import EmailNotifier, WebhookNotifier


def test_email_notifier_notify_success_sends_message_with_link():
    smtp_client = MagicMock()
    notifier = EmailNotifier(
        smtp_client=smtp_client, sender="bot@empresa.com", recipients=["time@empresa.com"]
    )

    notifier.notify_success(
        "Comissões — Fechamento Mensal", "https://dashboards.empresa.com/comissoes-mensal"
    )

    smtp_client.send_message.assert_called_once()
    sent_message = smtp_client.send_message.call_args[0][0]
    assert sent_message["To"] == "time@empresa.com"
    assert "Comissões" in sent_message["Subject"]
    assert "https://dashboards.empresa.com/comissoes-mensal" in sent_message.get_content()


def test_email_notifier_notify_failure_marks_subject_as_erro():
    smtp_client = MagicMock()
    notifier = EmailNotifier(
        smtp_client=smtp_client, sender="bot@empresa.com", recipients=["time@empresa.com"]
    )

    notifier.notify_failure("Comissões — Fechamento Mensal", "warehouse indisponível")

    sent_message = smtp_client.send_message.call_args[0][0]
    assert "[ERRO]" in sent_message["Subject"]
    assert "warehouse indisponível" in sent_message.get_content()


def test_webhook_notifier_notify_success_posts_json_with_link():
    with patch("dashboard_automation.notification.requests.post") as mock_post:
        notifier = WebhookNotifier(webhook_url="https://hooks.slack.com/services/xyz")
        notifier.notify_success(
            "Comissões — Fechamento Mensal", "https://dashboards.empresa.com/comissoes-mensal"
        )

    args, kwargs = mock_post.call_args
    assert args[0] == "https://hooks.slack.com/services/xyz"
    assert "Comissões" in kwargs["json"]["text"]
    assert "https://dashboards.empresa.com/comissoes-mensal" in kwargs["json"]["text"]


def test_webhook_notifier_notify_failure_posts_error_text():
    with patch("dashboard_automation.notification.requests.post") as mock_post:
        notifier = WebhookNotifier(webhook_url="https://hooks.slack.com/services/xyz")
        notifier.notify_failure("Comissões — Fechamento Mensal", "warehouse indisponível")

    _, kwargs = mock_post.call_args
    assert "[ERRO]" in kwargs["json"]["text"]
    assert "warehouse indisponível" in kwargs["json"]["text"]


def test_webhook_notifier_notify_success_raises_on_non_2xx_response():
    with patch("dashboard_automation.notification.requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        notifier = WebhookNotifier(webhook_url="https://hooks.slack.com/services/xyz")

        with pytest.raises(requests.HTTPError):
            notifier.notify_success(
                "Comissões — Fechamento Mensal", "https://dashboards.empresa.com/comissoes-mensal"
            )
