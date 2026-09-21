from pathlib import Path

import pytest

from dashboard_automation.config import load_config


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "dashboard.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_config_parses_required_fields(tmp_path):
    path = _write(tmp_path, """
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
""")

    config = load_config(path)

    assert config.id == "comissoes-mensal"
    assert config.nome == "Comissões — Fechamento Mensal"
    assert config.query.sql == "SELECT 1"
    assert config.query.warehouse == "meu-warehouse"
    assert config.prompt.template == "templates/insights-padrao.md"
    assert config.prompt.instrucoes_extra is None
    assert config.publicacao.destino == "azure-blob"
    assert config.publicacao.slug == "comissoes-mensal"
    assert config.schedule.cron is None
    assert config.schedule.enabled is False
    assert config.notificacao.email == []
    assert config.notificacao.slack_webhook is None
    assert config.notificacao.teams_webhook is None


def test_load_config_parses_optional_fields_when_present(tmp_path):
    path = _write(tmp_path, """
id: comissoes-mensal
nome: "Comissões — Fechamento Mensal"
query:
  sql: "SELECT 1"
  warehouse: "meu-warehouse"
schedule:
  cron: "0 0 7 1 * ?"
  enabled: true
prompt:
  template: "templates/insights-padrao.md"
  instrucoes_extra: "Destaque quedas > 10%"
publicacao:
  destino: "databricks-native"
  slug: "comissoes-mensal"
notificacao:
  email: ["time@empresa.com"]
  slack_webhook: "https://hooks.slack.com/services/xyz"
""")

    config = load_config(path)

    assert config.schedule.cron == "0 0 7 1 * ?"
    assert config.schedule.enabled is True
    assert config.prompt.instrucoes_extra == "Destaque quedas > 10%"
    assert config.notificacao.email == ["time@empresa.com"]
    assert config.notificacao.slack_webhook == "https://hooks.slack.com/services/xyz"


def test_load_config_rejects_invalid_destino(tmp_path):
    path = _write(tmp_path, """
id: x
nome: "X"
query:
  sql: "SELECT 1"
  warehouse: "w"
prompt:
  template: "t.md"
publicacao:
  destino: "ftp"
  slug: "x"
""")

    with pytest.raises(ValueError, match="destino inválido"):
        load_config(path)
