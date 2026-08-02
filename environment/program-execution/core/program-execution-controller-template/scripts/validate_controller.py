#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

REQUIRED = [
    "README.md",
    "ARCHITECTURE.md",
    "RUNBOOK.md",
    "INSTANTIATION_GUIDE.md",
    "SECURITY.md",
    "VALIDATION.md",
    "DESIGN_RATIONALE.md",
    "CHANGELOG.md",
    "CONTROLLER.yaml",
    "TEMPLATE_VARIABLES.yaml",
    "policy/authority.yaml",
    "policy/autonomy.yaml",
    "policy/evidence.yaml",
    "policy/parallelism.yaml",
    "policy/remote-actions.yaml",
    "policy/risk-tiers.yaml",
    "policy/stop-conditions.yaml",
    "policy/waivers.yaml",
    "references/BLUEPRINT_MAPPING.md",
    "references/AUTHORITY_AND_RISK.md",
    "references/STATE_MACHINE.md",
    "references/CONTRACTS_AND_SCOPE.md",
    "references/SCHEDULER_AND_LEASES.md",
    "references/WORKER_ADAPTER.md",
    "references/VERIFICATION_AND_RECEIPTS.md",
    "references/RECOVERY.md",
    "references/REMOTE_ACTIONS.md",
    "references/APPROVALS_WAIVERS_AND_HANDOFF.md",
    "references/NEGATIVE_TEST_MATRIX.md",
    "schemas/controller.schema.json",
    "schemas/program-lock.schema.json",
    "schemas/source-contract.schema.json",
    "schemas/task-contract.schema.json",
    "schemas/attempt-receipt.schema.json",
    "schemas/verification-receipt.schema.json",
    "schemas/approval.schema.json",
    "schemas/gate-evaluation.schema.json",
    "schemas/handoff-receipt.schema.json",
    "schemas/event.schema.json",
    "schemas/repository-registration.schema.json",
    "schemas/waiver.schema.json",
    "scripts/pec.py",
    "scripts/instantiate.py",
    "scripts/validate_controller.py",
    "scripts/run_negative_tests.py",
    "scripts/pec/__init__.py",
    "scripts/pec/common.py",
    "scripts/pec/blueprint.py",
    "scripts/pec/contracts.py",
    "scripts/pec/controller.py",
    "scripts/pec/ledger.py",
    "scripts/pec/state.py",
    "scripts/pec/cli.py",
]
PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _is_external_or_fragment_link(target: str) -> bool:
    """True for URL/mailto links and in-page fragments (skip filesystem checks)."""
    if target.startswith("#"):
        return True
    if ":" not in target:
        return False
    scheme = target.split(":", 1)[0].lower()
    return scheme in {"http", "https", "mailto"}


FORBIDDEN = [
    "program-execution-controller.source-contract.v1",
    "program-execution-controller.attempt-receipt.v1",
    "program-execution-controller.program-lock.v1",
    '"status": "LOCAL_PASS"',
]


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate(root: Path, mode: str) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    if errors:
        return errors

    for path in root.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: JSON parse failed: {exc}")
    for path in [*root.rglob("*.yaml"), *root.rglob("*.yml")]:
        try:
            load_yaml(path)
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: YAML parse failed: {exc}")

    try:
        controller = load_yaml(root / "CONTROLLER.yaml")
        schema = json.loads(
            (root / "schemas" / "controller.schema.json").read_text(encoding="utf-8")
        )
        for exc in Draft202012Validator(schema).iter_errors(controller):
            loc = ".".join(str(v) for v in exc.path) or "<root>"
            errors.append(f"CONTROLLER.yaml:{loc}: schema violation: {exc.message}")
        contracts = controller["controller"]["contracts"]
        if contracts != {
            "controller": "program-execution-controller.v2",
            "blueprint": "program-execution-blueprint.v2",
            "pair": "program-execution-system.v2",
        }:
            errors.append("CONTROLLER.yaml contract identifiers are not canonical v2 values")
        if (
            mode == "instantiated"
            and controller["controller"]["definition_status"] != "instantiated"
        ):
            errors.append("instantiated Controller requires definition_status=instantiated")
    except Exception as exc:
        errors.append(f"CONTROLLER.yaml validation failed: {exc}")

    policies = {
        "policy/authority.yaml": "program-execution-controller.authority-policy.v2",
        "policy/autonomy.yaml": "program-execution-controller.autonomy-policy.v2",
        "policy/evidence.yaml": "program-execution-controller.evidence-policy.v2",
        "policy/parallelism.yaml": "program-execution-controller.parallelism-policy.v2",
        "policy/remote-actions.yaml": "program-execution-controller.remote-action-policy.v2",
        "policy/risk-tiers.yaml": "program-execution-controller.risk-policy.v2",
        "policy/stop-conditions.yaml": "program-execution-controller.stop-policy.v2",
        "policy/waivers.yaml": "program-execution-controller.waiver-policy.v2",
    }
    for rel, expected in policies.items():
        value = load_yaml(root / rel)
        if value.get("schema") != expected or value.get("schema_version") != "2.0.0":
            errors.append(f"{rel}: policy contract mismatch")

    task_schema = json.loads(
        (root / "schemas" / "task-contract.schema.json").read_text(encoding="utf-8")
    )
    if task_schema.get("$id") != "program-execution-controller.rendered-contract.v2":
        errors.append("task-contract schema identity mismatch")
    if (
        task_schema.get("properties", {}).get("schema", {}).get("const")
        != "program-execution-controller.rendered-contract.v2"
    ):
        errors.append("task-contract payload schema const mismatch")

    text_files = [
        p
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".py"}
    ]
    for path in text_files:
        content = path.read_text(encoding="utf-8", errors="ignore")
        scan_for_legacy = path.resolve() != Path(__file__).resolve()
        for forbidden in FORBIDDEN if scan_for_legacy else []:
            if forbidden in content:
                errors.append(
                    f"{path.relative_to(root)}: forbidden legacy contract/state found: {forbidden}"
                )
        if mode == "instantiated":
            matches = PLACEHOLDER.findall(content)
            if matches:
                errors.append(
                    f"{path.relative_to(root)}: unresolved template variables {sorted(set(matches))}"  # noqa: E501
                )

    for path in root.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(content):
            if _is_external_or_fragment_link(target):
                continue
            clean = target.split("#", 1)[0]
            if clean and not (path.parent / clean).resolve().exists():
                # Links to the distribution sibling are valid only in paired layout.
                if clean.startswith("../shared/") or clean.startswith(
                    "../program-execution-blueprint-template/"
                ):
                    continue
                errors.append(f"{path.relative_to(root)}: broken link {target}")

    for path in root.rglob("*.py"):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: Python compile failed: {exc}")

    manifest_path = root / "MANIFEST.yaml"
    if not manifest_path.is_file():
        errors.append("missing MANIFEST.yaml")
    else:
        manifest = load_yaml(manifest_path)
        if manifest.get("schema") != "program-execution-controller.manifest.v2":
            errors.append("MANIFEST.yaml schema mismatch")
        expected = {entry["path"]: entry["sha256"] for entry in manifest.get("files") or []}
        actual = {
            p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*")
            if p.is_file()
            and p.name != "MANIFEST.yaml"
            and "__pycache__" not in p.parts
            and p.suffix != ".pyc"
        }
        if set(expected) != set(actual):
            errors.append(
                f"manifest path mismatch: missing={sorted(set(actual) - set(expected))}, stale={sorted(set(expected) - set(actual))}"  # noqa: E501
            )
        for rel in sorted(set(expected) & set(actual)):
            if expected[rel] != actual[rel]:
                errors.append(f"manifest digest mismatch: {rel}")

    if any(p.name == "__pycache__" or p.suffix == ".pyc" for p in root.rglob("*")):
        errors.append("compiled Python debris present")
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--mode", choices=["template", "instantiated"], default="template")
    args = p.parse_args()
    errors = validate(args.root, args.mode)
    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS")
    print(f"mode={args.mode}")
    print(f"root={args.root.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
