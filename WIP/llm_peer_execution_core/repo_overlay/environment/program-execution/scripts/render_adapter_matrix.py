from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import yaml


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "UNKNOWN"


def render(root: Path) -> dict[str, object]:
    registry = yaml.safe_load(
        (root / "registry/EXECUTION_ADAPTER_REGISTRY.yaml").read_text(encoding="utf-8")
    )
    entries: list[dict[str, object]] = []
    for item in registry.get("adapters") or []:
        descriptor_path = root / str(item["descriptor"])
        descriptor = yaml.safe_load(descriptor_path.read_text(encoding="utf-8"))
        capabilities = descriptor.get("capabilities") or {}
        provider = descriptor.get("provider") or {}
        status = descriptor.get("status") or {}
        entries.append(
            {
                "adapter_id": str(item["adapter_id"]),
                "kind": str(item["adapter_kind"]),
                "status": str(status.get("default") or item.get("status")),
                "provider_type": str(provider.get("type")),
                "actions": list(capabilities.get("actions") or []),
                "cancellation": str(capabilities.get("cancellation")),
                "descriptor_sha256": _sha256(descriptor_path),
            }
        )
    repo_root = root.parents[1]
    return {
        "schema": "l9.peer-execution.adapter-matrix.v2",
        "source_base_sha": _git_head(repo_root),
        "generated_from_worktree": True,
        "adapter_count": len(entries),
        "adapters": entries,
    }


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    output = root / "validation/adapter_matrix.yaml"
    output.write_text(yaml.safe_dump(render(root), sort_keys=False), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
