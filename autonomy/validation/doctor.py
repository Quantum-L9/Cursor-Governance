from __future__ import annotations

import argparse
import json
from pathlib import Path

from autonomy.adapters.conformance import AdapterConformance
from autonomy.adapters.protocol import AdapterConfig
from autonomy.io import load_json


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run IDE adapter conformance checks."
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--adapter", required=True)
    parser.add_argument(
        "--requirements",
        default="autonomy/policies/adapter-requirements.json",
    )
    args = parser.parse_args()
    root = Path(args.root)
    config = AdapterConfig.from_dict(load_json(args.adapter))
    requirements_path = (
        root / args.requirements
        if not Path(args.requirements).is_absolute()
        else Path(args.requirements)
    )
    requirements = load_json(requirements_path)
    report = AdapterConformance(
        requirements,
        repository_root=root,
    ).run(config)
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status.value == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
