from __future__ import annotations

from pathlib import Path

from .config import DashboardConfig, load_config


def _job_key(dashboard_id: str) -> str:
    return f"dashboard_{dashboard_id.replace('-', '_')}"


def _job_resource(config: DashboardConfig, config_path: Path) -> dict:
    return {
        "name": f"Dashboard: {config.nome}",
        "schedule": {
            "quartz_cron_expression": config.schedule.cron,
            "timezone_id": "America/Sao_Paulo",
            "pause_status": "UNPAUSED" if config.schedule.enabled else "PAUSED",
        },
        "tasks": [
            {
                "task_key": "run_dashboard",
                "python_wheel_task": {
                    "package_name": "dashboard_automation",
                    "entry_point": "run-dashboard",
                    "parameters": [
                        f"${{workspace.file_path}}/dashboards/{config_path.name}",
                        "--trigger=schedule",
                    ],
                },
            }
        ],
    }


def generate_jobs_yaml(dashboards_dir: Path) -> dict:
    jobs: dict[str, dict] = {}
    for config_path in sorted(dashboards_dir.glob("*.yaml")):
        config = load_config(config_path)
        if config.schedule.cron is None:
            continue
        jobs[_job_key(config.id)] = _job_resource(config, config_path)
    return {"resources": {"jobs": jobs}}
