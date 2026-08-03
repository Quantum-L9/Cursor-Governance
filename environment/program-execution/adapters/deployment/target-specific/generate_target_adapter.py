from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_target_adapter import validate

_SAFE_ADAPTER_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$")

MODULE_TEMPLATE = """from __future__ import annotations

from pathlib import Path

from adapters.common.subprocess_runner import run_argv


def run(
    commands: list[list[str]],
    cwd: str | Path,
    timeout_seconds: int = 900,
):
    results = []
    for argv in commands:
        result = run_argv(
            argv,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        results.append(result.to_evidence())
        if result.exit_code != 0:
            break
    return results
"""


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _descriptor(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "program-execution-adapter.spec.v1",
        "adapter_id": spec["adapter_id"],
        "adapter_version": spec["adapter_version"],
        "adapter_kind": "target_deployment",
        "contract_family": "program-execution-system.v2",
        "provider": {"type": "subprocess", "protocol_version": "1.0.0"},
        "capabilities": {
            "target_kinds": [spec["target_kind"]],
            "actions": [
                "preflight",
                "deploy",
                "observe",
                "rollback",
                "collect",
                "cleanup",
            ],
            "async_execution": False,
            "cancellation": "unsupported",
            "structured_output": True,
            "isolated_execution": True,
            "remote_credentials": "conditional",
        },
        "identity": {
            "binding": "controller_contract",
            "memory_write": "forbidden",
        },
        "security": {
            "default_deny": True,
            "may_narrow_authority": True,
            "may_widen_authority": False,
            "autonomous_merge": False,
            "force_push": False,
            "direct_graphiti_write": False,
        },
        "receipts": {
            "lifecycle_schema": ("program-execution-adapter.lifecycle-receipt.v1"),
            "terminal_core_receipt": "deployment",
        },
        "status": {
            "default": "non_routable",
            "blocked_reason": ("Generated adapter requires conformance and registry admission."),
        },
    }


def _write_manifest(target: Path) -> None:
    files = []
    for path in sorted(target.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            files.append(
                {
                    "path": path.relative_to(target).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
    _write_json(
        target / "MANIFEST.json",
        {"schema": "target-adapter.manifest.v1", "files": files},
    )


def generate(spec_path: Path, output_root: Path) -> Path:
    schema = Path(__file__).with_name("target-adapter-spec.schema.json")
    errors = validate(spec_path, schema)
    if errors:
        raise ValueError("; ".join(errors))
    spec: dict[str, Any] = json.loads(spec_path.read_text(encoding="utf-8"))
    adapter_id = str(spec["adapter_id"])
    if not _SAFE_ADAPTER_ID.fullmatch(adapter_id):
        raise ValueError(f"unsafe adapter_id: {adapter_id!r}")
    output_root = output_root.resolve()
    target = (output_root / adapter_id).resolve()
    try:
        target.relative_to(output_root)
    except ValueError as exc:
        raise ValueError(f"adapter path escapes output root: {target}") from exc
    target.mkdir(parents=True, exist_ok=False)

    import yaml

    descriptor_text = yaml.safe_dump(_descriptor(spec), sort_keys=False)
    (target / "ADAPTER.yaml").write_text(descriptor_text, encoding="utf-8")
    _write_json(target / "TARGET_CONTRACT.json", spec)
    for phase in (
        "preflight",
        "deploy",
        "observe",
        "rollback",
        "collect",
        "cleanup",
    ):
        (target / f"{phase}.py").write_text(MODULE_TEMPLATE, encoding="utf-8")
    tests = target / "tests"
    tests.mkdir()
    positive_test = (
        "from pathlib import Path\n\n\n"
        "def test_descriptor_present():\n"
        "    descriptor = Path(__file__).parents[1] / 'ADAPTER.yaml'\n"
        "    assert descriptor.is_file()\n"
    )
    negative_test = (
        "import yaml\n"
        "from pathlib import Path\n\n\n"
        "def test_generated_adapter_is_not_routable():\n"
        "    path = Path(__file__).parents[1] / 'ADAPTER.yaml'\n"
        "    value = yaml.safe_load(path.read_text())\n"
        "    assert value['status']['default'] == 'non_routable'\n"
    )
    hostile_test = (
        "from pathlib import Path\n\n\n"
        "def test_no_autonomous_merge_surface():\n"
        "    root = Path(__file__).parents[1]\n"
        "    text = '\\n'.join(\n"
        "        path.read_text() for path in root.glob('*.py')\n"
        "    )\n"
        "    assert 'merge_pull_request' not in text\n"
        "    assert 'enable_auto_merge' not in text\n"
    )
    for name, content in {
        "test_positive.py": positive_test,
        "test_negative.py": negative_test,
        "test_hostile.py": hostile_test,
    }.items():
        (tests / name).write_text(content, encoding="utf-8")
    _write_json(
        target / "COMPATIBILITY.json",
        {
            "core": "program-execution-system.v2",
            "adapter": "program-execution-adapter.v1",
            "routable": False,
        },
    )
    _write_manifest(target)
    return target


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if len(args) != 2:
        print(
            "usage: generate_target_adapter.py SPEC.json OUTPUT_ROOT",
            file=sys.stderr,
        )
        return 2
    target = generate(Path(args[0]).resolve(), Path(args[1]).resolve())
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
