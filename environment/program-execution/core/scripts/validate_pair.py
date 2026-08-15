#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT_REQUIRED = [
    "README.md",
    "ARCHITECTURE.md",
    "CANONICAL_VOCABULARY.yaml",
    "COMPATIBILITY.yaml",
    "ALIGNMENT_REPORT.md",
    "IMPROVEMENT_REPORT.md",
    "DELTA_REPORT.md",
    "CONVERGENCE_REPORT.yaml",
    "VALIDATION.md",
    "CHANGELOG.md",
    "RELEASE_NOTES.md",
    "validation/validation_report.yaml",
    "validation/validation_checks.jsonl",
    "validation/validation_findings.jsonl",
    "validation/execution_trace.jsonl",
    "shared/INTERFACE_CONTRACT.md",
    "shared/OWNERSHIP_MATRIX.yaml",
    "shared/STATE_MODEL.yaml",
    "shared/AUTHORIZATION_MODEL.yaml",
    "shared/EVIDENCE_MODEL.yaml",
    "shared/ERROR_TAXONOMY.yaml",
    "shared/HANDOFF_PROTOCOL.yaml",
    "program-execution-blueprint-template/PROGRAM.yaml",
    "program-execution-controller-template/CONTROLLER.yaml",
    "MANIFEST.yaml",
]
LEGACY = [
    r"\bepic\b",
    r"program-execution-blueprint\.v1",
    r"program-execution-controller\.v1",
    r"program-execution-system\.v1",
]


def _is_external_or_fragment_link(target: str) -> bool:
    """True for URL/mailto links and in-page fragments (skip filesystem checks)."""
    if target.startswith("#"):
        return True
    if ":" not in target:
        return False
    scheme = target.split(":", 1)[0].lower()
    return scheme in {"http", "https", "mailto"}


def load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def child(command: list[str]) -> list[str]:
    if not command or not all(isinstance(part, str) and part for part in command):
        raise ValueError("command must be a non-empty list of non-empty strings")
    if command[0] != sys.executable:
        raise ValueError("child commands must invoke sys.executable")
    pack_root = Path(__file__).resolve().parents[1]
    script = Path(command[1]).resolve()
    try:
        script.relative_to(pack_root)
    except ValueError as exc:
        raise ValueError(f"script escapes pack root: {script}") from exc
    argv = [sys.executable, str(script), *command[2:]]
    r = subprocess.run(argv, text=True, capture_output=True, check=False, timeout=120)
    return (
        []
        if r.returncode == 0
        else [line for line in (r.stdout + "\n" + r.stderr).splitlines() if line.strip()]
    )


def validate(root: Path, mode: str) -> list[str]:
    root = root.resolve()
    errors = []
    for rel in ROOT_REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    if errors:
        return errors
    compat = load(root / "COMPATIBILITY.yaml")
    program = load(root / "program-execution-blueprint-template/PROGRAM.yaml")["program"]
    controller = load(root / "program-execution-controller-template/CONTROLLER.yaml")["controller"]
    if compat.get("pair_contract") != "program-execution-system.v2":
        errors.append("pair contract mismatch")
    shared_schemas = {
        "shared/OWNERSHIP_MATRIX.yaml": "program-execution-system.ownership-matrix.v2",
        "shared/STATE_MODEL.yaml": "program-execution-system.state-model.v2",
        "shared/AUTHORIZATION_MODEL.yaml": "program-execution-system.authorization-model.v2",
        "shared/EVIDENCE_MODEL.yaml": "program-execution-system.evidence-model.v2",
        "shared/ERROR_TAXONOMY.yaml": "program-execution-system.error-taxonomy.v2",
        "shared/HANDOFF_PROTOCOL.yaml": "program-execution-system.handoff-protocol.v2",
    }
    for rel, expected_schema in shared_schemas.items():
        value = load(root / rel)
        if value.get("schema") != expected_schema or value.get("schema_version") != "2.0.0":
            errors.append(f"{rel}: shared contract mismatch")
    expected = {
        "blueprint": compat.get("blueprint_contract"),
        "controller": compat.get("controller_contract"),
        "pair": compat.get("pair_contract"),
    }
    if (
        program.get("contracts", {}).get("blueprint") != expected["blueprint"]
        or program.get("contracts", {}).get("pair") != expected["pair"]
    ):
        errors.append("Blueprint compatibility mismatch")
    if controller.get("contracts") != {
        "controller": expected["controller"],
        "blueprint": expected["blueprint"],
        "pair": expected["pair"],
    }:
        errors.append("Controller compatibility mismatch")
    errors += [
        "Blueprint validator: " + x
        for x in child(
            [
                sys.executable,
                str(root / "program-execution-blueprint-template/scripts/validate_blueprint.py"),
                str(root / "program-execution-blueprint-template"),
                "--mode",
                mode,
            ]
        )
    ]
    errors += [
        "Controller validator: " + x
        for x in child(
            [
                sys.executable,
                str(root / "program-execution-controller-template/scripts/validate_controller.py"),
                str(root / "program-execution-controller-template"),
                "--mode",
                mode,
            ]
        )
    ]
    index = load(root / "program-execution-blueprint-template/EXECUTION_INDEX.yaml")
    owners = index.get("canonical_owners", {})
    required_owners = {
        "task_dependencies": "DEPENDENCY_GRAPH.yaml",
        "gate_definitions": "CONVERGENCE_GATES.yaml",
        "runtime_gate_results": "Program Execution Controller",
        "task_runtime_state": "Program Execution Controller",
        "final_program_verdict": "program_owner_acceptance",
    }
    for key, value in required_owners.items():
        if owners.get(key) != value:
            errors.append(f"canonical owner mismatch: {key}")
    tasks = load(root / "program-execution-blueprint-template/TASK_CARDS.yaml").get("tasks", [])
    for task in tasks:
        if "depends_on" in task or "runtime_state" in task or "status" in task:
            errors.append(f"{task.get('id')}: task contains non-canonical dependency/runtime field")
    gates = load(root / "program-execution-blueprint-template/CONVERGENCE_GATES.yaml").get(
        "gates", []
    )
    for gate in gates:
        if "status" in gate or "result" in gate:
            errors.append(f"{gate.get('id')}: Blueprint gate contains runtime result")
    action_keys = {
        "inspect",
        "local_write",
        "commit",
        "push",
        "pull_request",
        "merge",
        "publish_or_release",
        "deploy_or_migrate",
        "destructive_change",
        "external_message",
    }
    for task in tasks:
        if set(task.get("authorization_ceiling", {})) != action_keys:
            errors.append(f"{task.get('id')}: authorization ceiling action set mismatch")
    for path in root.rglob("*"):
        if "__pycache__" in path.parts:
            continue
        if path.name == "__pycache__" or path.suffix == ".pyc":
            errors.append(f"compiled debris: {path.relative_to(root)}")
    for path in [
        *root.rglob("*.md"),
        *root.rglob("*.yaml"),
        *root.rglob("*.yml"),
        *root.rglob("*.json"),
        *root.rglob("*.py"),
    ]:
        if path.resolve() == Path(__file__).resolve() or path.name == "CANONICAL_VOCABULARY.yaml":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in LEGACY:
            if re.search(pattern, text, re.I):
                errors.append(f"{path.relative_to(root)}: forbidden legacy vocabulary {pattern}")
    link_pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    for path in root.glob("*.md"):
        for target in link_pattern.findall(path.read_text(encoding="utf-8")):
            if _is_external_or_fragment_link(target):
                continue
            clean = target.split("#", 1)[0]
            if clean and not (path.parent / clean).resolve().exists():
                errors.append(f"{path.relative_to(root)}: broken link {target}")
    for path in root.rglob("*.py"):
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            errors.append(f"{path.relative_to(root)}: Python compile failed: {exc}")
    controller_handoff = json.loads(
        (
            root / "program-execution-controller-template/schemas/handoff-receipt.schema.json"
        ).read_text()
    )
    shared_handoff = json.loads((root / "shared/schemas/handoff-receipt.schema.json").read_text())
    if controller_handoff.get("$id") != shared_handoff.get("$id"):
        errors.append("shared and Controller handoff schema identity mismatch")
    manifest = load(root / "MANIFEST.yaml")
    if manifest.get("schema") != "program-execution-system.manifest.v2":
        errors.append("root manifest schema mismatch")
    expected_paths = {x["path"]: x["sha256"] for x in manifest.get("files", [])}
    actual = {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
        and p.name != "MANIFEST.yaml"
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    }
    if set(expected_paths) != set(actual):
        errors.append(
            f"root manifest path mismatch: missing={sorted(set(actual) - set(expected_paths))}, stale={sorted(set(expected_paths) - set(actual))}"  # noqa: E501
        )
    for rel in set(expected_paths) & set(actual):
        if expected_paths[rel] != actual[rel]:
            errors.append(f"root manifest digest mismatch: {rel}")
    return errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("--mode", choices=["template", "instantiated"], default="template")
    a = p.parse_args()
    e = validate(a.root, a.mode)
    print(
        json.dumps({"status": "PASS" if not e else "FAIL", "mode": a.mode, "errors": e}, indent=2)
    )
    return 0 if not e else 1


if __name__ == "__main__":
    raise SystemExit(main())
