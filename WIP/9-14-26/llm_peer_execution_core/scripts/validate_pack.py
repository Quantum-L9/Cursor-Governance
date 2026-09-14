#!/usr/bin/env python3
"""Validate PR-pack integrity and static architecture invariants."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

BASE_SHA = "0fbd477e507d33ee52f2a87c2d9eb77c15b6a492"
EXPECTED_PACK_VERSION = "3.0.0"
EXPECTED_ADAPTERS = {
    "cursor-foreground",
    "cursor-background",
    "claude-code-direct",
    "chatgpt-manual-handoff",
    "ci-generic-shell",
    "ci-github-actions",
    "github-remote-actions",
    "github-checks",
    "github-deployments",
    "target-deployment-factory",
    "codex-cloud",
    "gemini-review",
    "manus-cloud",
}


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"YAML root must be object: {path}")
    return value


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    overlay = root / "repo_overlay"
    pe = overlay / "environment/program-execution"
    errors: list[str] = []
    checks = 0

    def require(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    baseline = _load_yaml(root / "BASELINE.yaml")
    require(baseline.get("base_sha") == BASE_SHA, "baseline SHA mismatch")
    authority = root / "architecture_authority"
    repo_contracts = overlay / "environment/contracts/execution"
    require(
        (authority / "PEER_EXECUTION_THIN_ADAPTER_LAW.yaml").read_bytes()
        == (repo_contracts / "PEER_EXECUTION_THIN_ADAPTER_LAW.yaml").read_bytes(),
        "law copy differs from repository overlay",
    )
    for adr in sorted(authority.glob("ADR-*.md")):
        require(
            adr.read_bytes() == (repo_contracts / "adr" / adr.name).read_bytes(),
            f"ADR copy differs from repository overlay: {adr.name}",
        )
    require(
        baseline.get("repository") == "Quantum-L9/Cursor-Governance",
        "repository binding mismatch",
    )

    def _skip_inventory(path: Path) -> bool:
        if not path.is_file():
            return True
        if path.name == ".DS_Store" or path.name.startswith("._"):
            return True
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            return True
        return False

    for path in root.rglob("*"):
        if _skip_inventory(path):
            continue
        require("__pycache__" not in path.parts, f"pycache artifact: {path}")
        require(path.suffix != ".pyc", f"bytecode artifact: {path}")
        if path.suffix == ".py":
            try:
                source = path.read_text(encoding="utf-8")
            except Exception as exc:
                errors.append(f"python read: {path}: {exc}")
                continue
            try:
                ast.parse(source, filename=str(path))
            except Exception as exc:
                errors.append(f"python syntax: {path}: {exc}")
            for line_number, line in enumerate(source.splitlines(), 1):
                if len(line) > 100 and "# noqa: E501" not in line:
                    errors.append(
                        f"python line >100: {path}:{line_number}:{len(line)}"
                    )
        elif path.suffix == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"json parse: {path}: {exc}")
        elif path.suffix in {".yaml", ".yml"}:
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(f"yaml parse: {path}: {exc}")

    registry = _load_yaml(pe / "registry/EXECUTION_ADAPTER_REGISTRY.yaml")
    observed = {str(item["adapter_id"]) for item in registry.get("adapters") or []}
    require(observed == EXPECTED_ADAPTERS, f"adapter registry mismatch: {observed}")
    require(
        "claude-code-bounded-autonomy" not in observed,
        "bounded execution remains modeled as provider",
    )

    profile_schema = _load_json(pe / "conformance/schemas/execution-profile.schema.json")
    profiles = _load_yaml(pe / "registry/EXECUTION_PROFILE_REGISTRY.yaml")
    require(
        not list(Draft202012Validator(profile_schema).iter_errors(profiles)),
        "execution profile schema validation failed",
    )
    binding_schema = _load_json(
        overlay / "environment/agents/schemas/peer-runtime-bindings.schema.json"
    )
    bindings = _load_yaml(overlay / "environment/agents/PEER_RUNTIME_BINDINGS.yaml")
    require(
        not list(Draft202012Validator(binding_schema).iter_errors(bindings)),
        "peer runtime bindings schema validation failed",
    )
    adapter_schema = _load_json(
        pe / "conformance/schemas/execution-adapter-spec.schema.json"
    )
    validator = Draft202012Validator(adapter_schema)
    for entry in registry.get("adapters") or []:
        descriptor = pe / str(entry["descriptor"])
        if not descriptor.is_file():
            continue
        value = _load_yaml(descriptor)
        require(
            not list(validator.iter_errors(value)),
            f"descriptor schema failed: {entry['adapter_id']}",
        )
        identity = value.get("identity") or {}
        if identity.get("binding") == "peer_runtime_binding":
            require(
                "agent_ref" not in identity,
                f"provider owns agent_ref: {entry['adapter_id']}",
            )

    for provider in (pe / "adapters").rglob("provider.py"):
        text = provider.read_text(encoding="utf-8")
        if "PROVIDER_CLASS" not in text:
            continue
        require(
            "BaseExecutionAdapter" not in text
            and "PeerExecutionAdapter" not in text
            and "DriverExecutionAdapter" not in text,
            f"thin execution module owns lifecycle class: {provider}",
        )

    require(
        (pe / "peer_execution/autonomy").is_dir(),
        "shared bounded execution runtime missing",
    )
    require(
        not (pe / "adapters/claude-code-bounded-autonomy").exists(),
        "legacy bounded provider overlay remains",
    )
    require(
        (pe / "scripts/run_peer_task_pipeline.py").is_file(),
        "provider-neutral task pipeline missing",
    )
    require(
        (pe / "peer_execution/runner.py").is_file(),
        "shared timeout/poll runner missing",
    )
    contracts_text = (pe / "peer_execution/contracts.py").read_text(encoding="utf-8")
    require(
        "program-execution-controller.rendered-contract.v2" in contracts_text,
        "canonical Controller rendered-contract bridge missing",
    )
    execution_text = (pe / "peer_execution/execution.py").read_text(encoding="utf-8")
    require(
        "resolve_permission_profile" in execution_text,
        "shared core does not enforce permission profile",
    )
    require(
        'record["status"] = "DISPATCHING"' in execution_text,
        "dispatch intent is not persisted before provider invocation",
    )
    require(
        '"type": "provider_invoke_exception"' in execution_text
        and 'record["status"] = "BLOCKED"' in execution_text,
        "provider invocation exceptions are not persisted fail-closed",
    )
    permission_text = (pe / "peer_execution/permissions.py").read_text(encoding="utf-8")
    for action in (
        "push",
        "pull_request",
        "merge",
        "publish_or_release",
        "deploy_or_migrate",
        "destructive_change",
        "external_message",
    ):
        require(
            permission_text.count(f'"{action}"') >= 2,
            f"worker permission profiles do not both deny {action}",
        )
    context_text = (pe / "peer_execution/context.py").read_text(encoding="utf-8")
    require(
        "tempfile.NamedTemporaryFile" in context_text and "os.fsync" in context_text,
        "context manifest writes are not durable and atomic",
    )
    require(
        "refusing symlinked context directory" in context_text,
        "context directory symlink rejection missing",
    )
    loader_text = (pe / "scripts/provider_loader.py").read_text(encoding="utf-8")
    require(
        "_load_thin_component(adapter_id, runtime_root, module)" in loader_text,
        "thin execution component instantiation reloads provider module",
    )
    require(
        "_load_legacy_adapter_class" not in loader_text,
        "legacy thick-adapter loader fallback remains",
    )
    require(
        (pe / "peer_execution/driver_execution.py").is_file()
        and (pe / "peer_execution/terminal_receipts.py").is_file(),
        "shared execution-kind driver core is missing",
    )

    apply_text = (root / "scripts/apply_pr_pack.py").read_text(encoding="utf-8")
    forbidden_remote = ["git push", "gh pr", "gh api", "create_pull_request"]
    for marker in forbidden_remote:
        require(marker not in apply_text, f"remote mutation marker in apply script: {marker}")
    require(
        'repo.rglob("*")' not in apply_text,
        "apply script performs unbounded repository-wide text migration",
    )
    require(
        "def require_landing_base" in apply_text
        and "5707ea8cefd15cfd5b80a9c1503e3f03119f6adc" in apply_text
        and "feat/kernel-pack-new-branch-default" in apply_text,
        "governed porter is not retargeted to the landing-branch HEAD",
    )
    require(
        "_rollback_clean_base" not in apply_text
        and "0fbd477" not in apply_text
        and '"worktree", "add", "--detach"' not in apply_text,
        "stock hard-reset / exact-0fbd477 porter remnants remain",
    )
    require(
        "def patch_makefile_additive" in apply_text
        and "def patch_conftest_additive" in apply_text
        and "conftest.py" in apply_text
        and "OVERLAY_SKIP" in apply_text,
        "additive-only root / overlay-conftest skip is missing",
    )
    require(
        "attempt receipt target escapes Controller attempts root" in execution_text
        and "conflicting evidence" in execution_text
        and "_write_attempt_receipt(target, result)" in execution_text,
        "durable Controller-bounded Attempt Receipt handoff is missing",
    )
    pipeline_text = (pe / "scripts/run_peer_task_pipeline.py").read_text(encoding="utf-8")
    require(
        '"abort-execution"' in pipeline_text
        and "attempt_handoff_or_verification_failure" in pipeline_text,
        "pipeline does not request Controller abort on post-admission failure",
    )
    blocker_test = subprocess.run(
        [sys.executable, "-B", str(root / "scripts/test_blocker_repairs.py")],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    require(
        blocker_test.returncode == 0,
        "blocker repair regression suite failed: "
        + (blocker_test.stdout + blocker_test.stderr)[-4000:],
    )

    applied_validation = (root / "scripts/validate_applied_repo.py").read_text(
        encoding="utf-8"
    )
    require(
        '"status": "SKIPPED"' in applied_validation,
        "unavailable optional static checker is still release-blocking",
    )

    manifest_path = root / "MANIFEST.yaml"
    if manifest_path.is_file():
        manifest = _load_yaml(manifest_path)
        require(
            manifest.get("pack_version") == EXPECTED_PACK_VERSION,
            "manifest pack_version mismatch",
        )
        require(
            manifest.get("manifest_self_excluded") is True,
            "manifest must explicitly exclude its own recursive digest",
        )
        items = manifest.get("files") or []
        require(isinstance(items, list), "manifest files must be a list")
        if isinstance(items, list):
            manifest_paths = [str(item.get("path")) for item in items if isinstance(item, dict)]
            require(
                len(manifest_paths) == len(items),
                "manifest files must contain only object records",
            )
            require(
                len(manifest_paths) == len(set(manifest_paths)),
                "manifest contains duplicate file paths",
            )
            actual_paths = sorted(
                path.relative_to(root).as_posix()
                for path in root.rglob("*")
                if path.is_file()
                and path != manifest_path
                and path.name != ".DS_Store"
                and not path.name.startswith("._")
                and "__pycache__" not in path.parts
                and path.suffix != ".pyc"
            )
            require(
                sorted(manifest_paths) == actual_paths,
                "manifest inventory does not exactly match delivered files",
            )
            require(
                manifest.get("file_count") == len(items),
                "manifest file_count does not match files list",
            )
            for item in items:
                if not isinstance(item, dict):
                    continue
                path = root / str(item.get("path"))
                require(path.is_file(), f"manifest file missing: {item.get('path')}")
                if path.is_file():
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    require(
                        digest == item.get("sha256"),
                        f"manifest digest mismatch: {item.get('path')}",
                    )
                    require(
                        item.get("bytes") == path.stat().st_size,
                        f"manifest byte count mismatch: {item.get('path')}",
                    )

    report = {
        "schema": "l9.peer-execution.pr-pack-self-validation.v1",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": errors,
        "bound_repository": "Quantum-L9/Cursor-Governance",
        "bound_base_sha": BASE_SHA,
        "remote_mutation": "NONE",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
