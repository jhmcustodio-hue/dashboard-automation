#!/usr/bin/env python3
from pathlib import Path

import yaml

from dashboard_automation.bundle_gen import generate_jobs_yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DASHBOARDS_DIR = PROJECT_ROOT / "dashboards"
OUTPUT_PATH = PROJECT_ROOT / "resources" / "dashboards.generated.yml"


def main() -> None:
    jobs_yaml = generate_jobs_yaml(DASHBOARDS_DIR)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        yaml.dump(jobs_yaml, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    print(f"Escrito {len(jobs_yaml['resources']['jobs'])} job(s) em {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
