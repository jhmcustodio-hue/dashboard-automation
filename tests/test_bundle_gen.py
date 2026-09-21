from pathlib import Path

from dashboard_automation.bundle_gen import generate_jobs_yaml


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_generate_jobs_yaml_skips_dashboards_without_cron(tmp_path):
    _write(
        tmp_path / "sem-schedule.yaml",
        """
id: sem-schedule
nome: "Sem Schedule"
query:
  sql: "SELECT 1"
  warehouse: "w"
prompt:
  template: "t.md"
publicacao:
  destino: "azure-blob"
  slug: "sem-schedule"
""",
    )

    result = generate_jobs_yaml(tmp_path)

    assert result == {"resources": {"jobs": {}}}


def test_generate_jobs_yaml_includes_scheduled_dashboard_paused_by_default(tmp_path):
    _write(
        tmp_path / "com-schedule.yaml",
        """
id: comissoes-mensal
nome: "Comissões — Fechamento Mensal"
query:
  sql: "SELECT 1"
  warehouse: "w"
schedule:
  cron: "0 0 7 1 * ?"
prompt:
  template: "t.md"
publicacao:
  destino: "azure-blob"
  slug: "comissoes-mensal"
""",
    )

    result = generate_jobs_yaml(tmp_path)

    job = result["resources"]["jobs"]["dashboard_comissoes_mensal"]
    assert job["schedule"]["quartz_cron_expression"] == "0 0 7 1 * ?"
    assert job["schedule"]["pause_status"] == "PAUSED"
    task = job["tasks"][0]
    parameters = task["python_wheel_task"]["parameters"]
    assert parameters[0] == "${workspace.file_path}/dashboards/com-schedule.yaml"
    assert parameters[1] == "--trigger=schedule"
    assert task["environment_key"] == "default"
    assert job["environments"] == [
        {
            "environment_key": "default",
            "spec": {"environment_version": "4", "dependencies": ["../dist/*.whl"]},
        }
    ]


def test_generate_jobs_yaml_unpauses_when_schedule_enabled(tmp_path):
    _write(
        tmp_path / "ativo.yaml",
        """
id: ativo
nome: "Ativo"
query:
  sql: "SELECT 1"
  warehouse: "w"
schedule:
  cron: "0 0 7 1 * ?"
  enabled: true
prompt:
  template: "t.md"
publicacao:
  destino: "azure-blob"
  slug: "ativo"
""",
    )

    result = generate_jobs_yaml(tmp_path)

    assert result["resources"]["jobs"]["dashboard_ativo"]["schedule"]["pause_status"] == "UNPAUSED"
