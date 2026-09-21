from pathlib import Path

import pandas as pd

from dashboard_automation.config import load_config
from dashboard_automation.generation import build_prompt

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "dashboards" / "example-dashboard.yaml"


def test_example_dashboard_config_is_valid():
    config = load_config(EXAMPLE_PATH)

    assert config.id == "exemplo-vendas-mensal"
    assert config.publicacao.destino == "azure-blob"
    assert config.schedule.cron == "0 0 7 1 * ?"
    assert config.schedule.enabled is False


def test_example_dashboard_prompt_template_file_exists_and_is_readable():
    config = load_config(EXAMPLE_PATH)
    template_path = Path(config.prompt.template)

    assert template_path.is_absolute()
    assert template_path.exists()
    assert "dashboard HTML" in template_path.read_text(encoding="utf-8")


def test_example_dashboard_prompt_template_resolves_regardless_of_cwd(tmp_path, monkeypatch):
    config = load_config(EXAMPLE_PATH)
    monkeypatch.chdir(tmp_path)
    prompt_text = build_prompt(config.prompt, pd.DataFrame({"a": [1]}))

    assert "dashboard HTML" in prompt_text
