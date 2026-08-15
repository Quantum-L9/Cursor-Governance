#!/usr/bin/env python3
"""Contract-first Cursor rules compiler front door."""
from __future__ import annotations
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any
import yaml
ROOT = Path(__file__).resolve().parents[2]
ADAPTERS = Path(__file__).resolve().parent / "adapters"
SCRIPTS = ROOT / "ops" / "scripts"
for directory in (ADAPTERS, SCRIPTS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
from cursor_rules import (  # noqa: E402
    activations_may_overlap,
    discover_rule_bindings,
)
from generate_rules_manifest import (  # noqa: E402
    build_manifest,
    render_markdown,
    serialize_manifest,
)
from render_cursor_rule import (  # noqa: E402
    enforce_context_budget,
    render_cursor_rule,
)
from resolve_rule_contracts import (  # noqa: E402
    directives_conflict,
    load_contract_index,
    resolve_binding,
)
from validate_rule_binding import validate_all_bindings  # noqa: E402
GLOBAL_ALWAYS_BUDGET = int(
    os.environ.get("RULES_ALWAYS_BUDGET", "181203")
)
def resolve_all(
    root: Path,
    registry_path: Path | None = None,
) -> list[dict[str, Any]]:
    findings = validate_all_bindings(root, registry_path)
    if findings:
        raise ValueError(
            "invalid rule bindings: "
            + "; ".join(str(finding) for finding in findings)
        )
    index = load_contract_index(root, registry_path)
    bindings = discover_rule_bindings(root)
    resolved: list[dict[str, Any]] = []
    for binding in bindings:
        if binding.migration_state not in {"contract_bound", "generated"}:
            continue
        resolution = resolve_binding(binding, index)
        resolution["_binding"] = binding
        resolved.append(resolution)
    return resolved
def _global_conflicts(
    resolutions: list[dict[str, Any]],
) -> list[str]:
    failures: list[str] = []
    for index, left in enumerate(resolutions):
        left_binding = left["_binding"]
        for right in resolutions[index + 1 :]:
            right_binding = right["_binding"]
            if not activations_may_overlap(left_binding, right_binding):
                continue
            for left_directive in left["directives"]:
                for right_directive in right["directives"]:
                    if not directives_conflict(
                        left_directive,
                        right_directive,
                    ):
                        continue
                    failures.append(
                        f"{left_binding.binding_id} and "
                        f"{right_binding.binding_id} overlap and conflict: "
                        f"{left_directive['contract_id']}:"
                        f"{left_directive['clause_id']} <> "
                        f"{right_directive['contract_id']}:"
                        f"{right_directive['clause_id']}"
                    )
    return failures
def build_projection_index(
    root: Path,
    registry_path: Path | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    resolutions = resolve_all(root, registry_path)
    conflicts = _global_conflicts(resolutions)
    if conflicts:
        raise ValueError(
            "cross-rule semantic conflicts: " + "; ".join(conflicts)
        )
    projection_index: dict[str, dict[str, Any]] = {}
    rendered_outputs: dict[str, str] = {}
    always_total = 0
    for resolution in resolutions:
        binding = resolution.pop("_binding")
        rendered = render_cursor_rule(resolution)
        metrics = enforce_context_budget(resolution, rendered)
        activation_mode = str(resolution["activation"].get("mode") or "")
        if activation_mode == "always":
            always_total += metrics["measured_bytes"]
        projection_index[resolution["output_path"]] = {
            "migration_state": resolution["migration_state"],
            "binding": {
                "id": resolution["binding_id"],
                "path": binding.relative_path,
                "digest": f"sha256:{resolution['binding_digest']}",
            },
            "contracts": [
                {
                    "contract_id": item["contract_id"],
                    "version": item["version"],
                    "digest": f"sha256:{item['digest']}",
                    "clauses": item["clauses"],
                }
                for item in resolution["resolved_contracts"]
            ],
            "projection": {
                "renderer": "cursor_mdc_v1",
                "content_digest": (
                    "sha256:"
                    + __import__("hashlib").sha256(
                        rendered.encode("utf-8")
                    ).hexdigest()
                ),
                "contract_bundle_digest": (
                    f"sha256:{resolution['bundle_digest']}"
                ),
                "drift": False,
            },
            "context": {
                **metrics,
                "budget_status": "within_budget",
            },
            "semantic_authority": {
                "owner": "contracts",
                "rule_may_redefine": False,
            },
        }
        if resolution["migration_state"] == "generated":
            rendered_outputs[resolution["output_path"]] = rendered
    if always_total > GLOBAL_ALWAYS_BUDGET:
        raise ValueError(
            f"generated always-on rules total {always_total} bytes, "
            f"exceeding global budget {GLOBAL_ALWAYS_BUDGET}"
        )
    return projection_index, rendered_outputs
def _manifest_outputs(
    root: Path,
    projection_index: dict[str, dict[str, Any]],
) -> dict[str, str]:
    manifest = build_manifest(
        root,
        projection_index=projection_index,
    )
    serialized = serialize_manifest(manifest)
    return {
        "rules/RULES-MANIFEST.json": serialized["json"],
        "rules/RULES-MANIFEST.yaml": serialized["yaml"],
        "rules/RULES-MANIFEST.md": render_markdown(manifest),
    }
def expected_outputs(
    root: Path,
    registry_path: Path | None = None,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    projection_index, generated_rules = build_projection_index(
        root,
        registry_path,
    )
    outputs = {
        **generated_rules,
        **_manifest_outputs(root, projection_index),
    }
    return outputs, projection_index
def _atomic_write_set(root: Path, outputs: dict[str, str]) -> None:
    staged: list[tuple[Path, Path]] = []
    try:
        for relative, content in sorted(outputs.items()):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{destination.name}.",
                suffix=".tmp",
                dir=destination.parent,
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            staged.append((Path(temp_name), destination))
        for temporary, destination in staged:
            temporary.replace(destination)
    finally:
        for temporary, _ in staged:
            if temporary.exists():
                temporary.unlink()
def check(
    root: Path,
    registry_path: Path | None = None,
) -> list[str]:
    outputs, _ = expected_outputs(root, registry_path)
    failures: list[str] = []
    for relative, expected in sorted(outputs.items()):
        path = root / relative
        if not path.is_file():
            failures.append(f"missing generated output: {relative}")
            continue
        actual = path.read_text(encoding="utf-8")
        if relative.endswith("RULES-MANIFEST.json"):
            try:
                actual_obj = json.loads(actual)
                expected_obj = json.loads(expected)
            except json.JSONDecodeError:
                failures.append(f"invalid JSON output: {relative}")
                continue
            actual_obj.pop("generated_utc", None)
            expected_obj.pop("generated_utc", None)
            if actual_obj != expected_obj:
                failures.append(f"generated drift: {relative}")
        elif relative.endswith("RULES-MANIFEST.yaml"):
            actual_obj = yaml.safe_load(actual)
            expected_obj = yaml.safe_load(expected)
            if isinstance(actual_obj, dict):
                actual_obj.pop("generated_utc", None)
            if isinstance(expected_obj, dict):
                expected_obj.pop("generated_utc", None)
            if actual_obj != expected_obj:
                failures.append(f"generated drift: {relative}")
        elif actual != expected:
            failures.append(f"generated drift: {relative}")
    return failures
def explain(
    root: Path,
    selector: str,
    registry_path: Path | None,
) -> dict[str, Any]:
    resolutions = resolve_all(root, registry_path)
    for resolution in resolutions:
        binding = resolution["_binding"]
        identity = resolution["rule_identity"]
        if selector in {
            binding.binding_id,
            binding.output_path,
            str(identity.get("rule_id") or ""),
            Path(binding.output_path).stem,
        }:
            return {
                key: value
                for key, value in resolution.items()
                if key != "_binding"
            }
    raise ValueError(f"no contract-bound rule matches {selector!r}")
def impact(
    root: Path,
    contract_id: str,
    registry_path: Path | None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for resolution in resolve_all(root, registry_path):
        matching = [
            item
            for item in resolution["resolved_contracts"]
            if item["contract_id"] == contract_id
        ]
        if matching:
            binding = resolution["_binding"]
            results.append(
                {
                    "binding_id": binding.binding_id,
                    "output_path": binding.output_path,
                    "migration_state": binding.migration_state,
                    "clauses": sorted(
                        {
                            clause
                            for item in matching
                            for clause in item["clauses"]
                        }
                    ),
                }
            )
    return results
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("build", "check", "explain", "impact", "census"),
    )
    parser.add_argument("selector", nargs="?")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--registry", type=Path)
    args = parser.parse_args()
    try:
        root = args.root.resolve()
        if args.command == "build":
            outputs, _ = expected_outputs(root, args.registry)
            _atomic_write_set(root, outputs)
            print(f"GENERATED: {len(outputs)} rule/compiler outputs")
            return 0
        if args.command == "check":
            failures = check(root, args.registry)
            if failures:
                print(f"FAIL ({len(failures)})")
                for failure in failures:
                    print(f"  - {failure}")
                return 1
            print("PASS: rules compiler outputs current")
            return 0
        if args.command == "explain":
            if not args.selector:
                raise ValueError("explain requires a rule/binding selector")
            print(
                json.dumps(
                    explain(root, args.selector, args.registry),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "impact":
            if not args.selector:
                raise ValueError("impact requires a contract ID")
            print(
                json.dumps(
                    impact(root, args.selector, args.registry),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if args.command == "census":
            from build_rule_doctrine_census import build_rule_census
            print(
                yaml.safe_dump(
                    build_rule_census(root, args.registry),
                    sort_keys=False,
                    allow_unicode=True,
                    width=1000,
                )
            )
            return 0
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"RULE_BUILD_ERROR: {exc}", file=sys.stderr)
        return 2
    return 2
if __name__ == "__main__":
    raise SystemExit(main())
