from __future__ import annotations

import sys
from pathlib import Path

import yaml


def render(root: Path) -> dict[str, object]:
    registry = yaml.safe_load(
        (root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
    )
    index: dict[str, list[str]] = {}
    for entry in registry.get("adapters") or []:
        descriptor = yaml.safe_load((root / str(entry["descriptor"])).read_text(encoding="utf-8"))
        for action in descriptor["capabilities"]["actions"]:
            index.setdefault(str(action), []).append(str(entry["adapter_id"]))
    return {
        "schema": "program-execution-adapter.capability-index.v1",
        "actions": {key: sorted(value) for key, value in sorted(index.items())},
    }


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    output = root / "registry/EXECUTION_CAPABILITY_INDEX.yaml"
    output.write_text(yaml.safe_dump(render(root), sort_keys=False), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
