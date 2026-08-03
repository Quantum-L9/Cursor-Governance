from __future__ import annotations

import sys
from pathlib import Path

import yaml


def render(root: Path) -> dict[str, object]:
    registry = yaml.safe_load(
        (root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
    )
    entries: list[dict[str, object]] = []
    for entry in registry.get("adapters") or []:
        descriptor = yaml.safe_load((root / str(entry["descriptor"])).read_text(encoding="utf-8"))
        capabilities = descriptor.get("capabilities") or {}
        status = descriptor.get("status") or {}
        entries.append(
            {
                "adapter_id": str(entry["adapter_id"]),
                "adapter_kind": str(
                    entry.get("adapter_kind") or descriptor.get("adapter_kind") or "unknown"
                ),
                "target_kinds": list(capabilities.get("target_kinds") or []),
                "actions": list(capabilities.get("actions") or []),
                "default_status": str(
                    status.get("default") or entry.get("status") or "conditional"
                ),
            }
        )
    return {
        "schema": "program-execution-adapter.capability-index.v1",
        "generated_from": "EXECUTION_ADAPTER_REGISTRY.yaml",
        "entries": entries,
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
