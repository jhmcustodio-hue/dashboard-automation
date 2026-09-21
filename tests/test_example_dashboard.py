from pathlib import Path

from dashboard_automation.config import load_config

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "dashboards" / "example-dashboard.yaml"


def test_example_dashboard_config_is_valid():
    config = load_config(EXAMPLE_PATH)

    assert config.id == "exemplo-vendas-mensal"
    assert config.publicacao.destino == "azure-blob"
    assert config.schedule.cron == "0 0 7 1 * ?"
    assert config.schedule.enabled is False


def test_example_dashboard_prompt_template_file_exists_and_is_readable():
    config = load_config(EXAMPLE_PATH)
    template_path = Path(__file__).resolve().parent.parent / config.prompt.template

    assert template_path.exists()
    assert "dashboard HTML" in template_path.read_text(encoding="utf-8")
