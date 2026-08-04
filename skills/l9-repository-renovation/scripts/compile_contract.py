#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import load_json, stable_id, utc_now, write_json

CLASS_PHASE = {
    "dependency_authority_drift": "dependency_and_lock_authority",
    "package_boundary_ambiguity": "dependency_and_lock_authority",
    "test_topology_gap": "canonical_test_topology",
    "local_ci_divergence": "canonical_test_topology",
    "dead_wiring": "registry_and_reachability",
    "registry_drift": "registry_and_reachability",
    "documentation_code_drift": "documentation_and_handoff",
    "security_or_permission_drift": "security_and_permissions",
    "repository_integrity_failure": "integrity_repair",
    "syntax_or_parse_failure": "integrity_repair",
    "release_consumer_drift": "release_and_compatibility",
    "validation_theater": "validation_and_ratchet",
}

PHASE_ORDER = [
    "integrity_repair",
    "dependency_and_lock_authority",
    "canonical_test_topology",
    "registry_and_reachability",
    "security_and_permissions",
    "release_and_compatibility",
    "validation_and_ratchet",
    "documentation_and_handoff",
]

DEFAULT_CONTROL_PATHS = {
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
    "requirements-ci.txt",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Makefile",
    "Taskfile.yml",
    "justfile",
    ".pre-commit-config.yaml",
    ".github/workflows/**",
    "scripts/**",
    "ops/scripts/**",
    "ops/config/**",
    "tests/**",
    "docs/**",
    "README.md",
}


def evidence_paths(findings: list[dict[str, Any]]) -> set[str]:
    paths: set[str] = set()
    for item in findings:
        for evidence in item.get("evidence", []):
            candidate = evidence.get("path") or evidence.get("source")
            if isinstance(candidate, str) and candidate not in {"repository", "."}:
                paths.add(candidate)
    return paths


def detect_validation(repo: Path, inventory: dict[str, Any]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = [
        {
            "id": "git-diff-check",
            "command": ["git", "diff", "--check"],
            "timeout_seconds": 60,
            "required": True,
        }
    ]
    manifests = set(inventory.get("manifests", []))
    locks = set(inventory.get("lockfiles", []))
    configs = set(inventory.get("configuration", []))
    makefile = repo / "Makefile"
    make_text = makefile.read_text(encoding="utf-8") if makefile.exists() else ""

    if "pyproject.toml" in manifests:
        if "uv.lock" in locks:
            commands.extend(
                [
                    {
                        "id": "uv-lock",
                        "command": ["uv", "lock", "--check"],
                        "timeout_seconds": 120,
                        "required": True,
                    },
                    {
                        "id": "uv-sync",
                        "command": ["uv", "sync", "--locked"],
                        "timeout_seconds": 600,
                        "required": True,
                    },
                ]
            )
        if "ruff.toml" in configs or ".ruff.toml" in configs or (repo / "pyproject.toml").exists():
            commands.extend(
                [
                    {
                        "id": "ruff-check",
                        "command": ["uv", "run", "--no-build", "ruff", "check", "."],
                        "timeout_seconds": 300,
                        "required": True,
                    },
                    {
                        "id": "ruff-format",
                        "command": ["uv", "run", "--no-build", "ruff", "format", "--check", "."],
                        "timeout_seconds": 300,
                        "required": True,
                    },
                ]
            )
        if re.search(r"(?m)^test\s*:", make_text):
            commands.append(
                {
                    "id": "make-test",
                    "command": ["make", "test"],
                    "timeout_seconds": 1800,
                    "required": True,
                }
            )
        elif inventory.get("tests"):
            commands.append(
                {
                    "id": "pytest",
                    "command": ["uv", "run", "--no-build", "pytest", "-q"],
                    "timeout_seconds": 1800,
                    "required": True,
                }
            )
        if re.search(r"(?m)^pr(?:-check)?\s*:", make_text):
            commands.append(
                {
                    "id": "make-pr",
                    "command": ["make", "pr"],
                    "timeout_seconds": 1800,
                    "required": True,
                }
            )

    if "package.json" in manifests:
        package = inventory.get("node", {})
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        package_manager = package.get("package_manager") or ""
        if str(package_manager).startswith("pnpm") or "pnpm-lock.yaml" in locks:
            runner = "pnpm"
            commands.insert(
                1,
                {
                    "id": "pnpm-install",
                    "command": ["pnpm", "install", "--frozen-lockfile"],
                    "timeout_seconds": 900,
                    "required": True,
                },
            )
        elif str(package_manager).startswith("yarn") or "yarn.lock" in locks:
            runner = "yarn"
            commands.insert(
                1,
                {
                    "id": "yarn-install",
                    "command": ["yarn", "install", "--immutable"],
                    "timeout_seconds": 900,
                    "required": True,
                },
            )
        else:
            runner = "npm"
            commands.insert(
                1,
                {
                    "id": "npm-install",
                    "command": ["npm", "ci"],
                    "timeout_seconds": 900,
                    "required": True,
                },
            )
        for script_name in ("lint", "typecheck", "test", "build"):
            if script_name in scripts:
                if runner == "yarn":
                    command = [runner, script_name]
                else:
                    command = [runner, "run", script_name]
                commands.append(
                    {
                        "id": f"node-{script_name}",
                        "command": command,
                        "timeout_seconds": 1800,
                        "required": True,
                    }
                )

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in commands:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        unique.append(item)
    return unique


def build_plan(contract: dict[str, Any], audit: dict[str, Any]) -> str:
    lines = [
        f"# Repository Renovation Plan: {contract['repository']['name']}",
        "",
        f"Base: `{contract['repository']['base_commit'] or contract['repository']['base_ref']}`",
        f"Contract: `{contract['contract_id']}`",
        "",
        "## Objective",
        "",
        contract["objective"],
        "",
        "## Authority decisions",
        "",
    ]
    for decision in contract["authority_decisions"]:
        lines.append(f"- **{decision['concern']}**: {decision['target_authority']}")
    lines.extend(["", "## Implementation phases", ""])
    for index, phase in enumerate(contract["phases"], start=1):
        lines.append(f"### {index}. {phase['name'].replace('_', ' ').title()}")
        lines.append("")
        lines.append(phase["objective"])
        lines.append("")
        for finding_id in phase["finding_ids"]:
            match = next((item for item in audit["findings"] if item["id"] == finding_id), None)
            if match:
                lines.append(f"- `{finding_id}` {match['summary']}")
        lines.append("")
    lines.extend(["## Validation matrix", ""])
    for command in contract["validation_matrix"]:
        lines.append(f"- `{command['id']}`: `{' '.join(command['command'])}`")
    lines.extend(
        [
            "",
            "## Acceptance criteria",
            "",
            *[f"- {item}" for item in contract["acceptance_criteria"]],
            "",
            "## Pull request boundary",
            "",
            "Create one draft PR after every required validation passes. Do not merge without separate authorization.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compile a repository audit into a bounded renovation contract."
    )
    parser.add_argument("audit", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--branch")
    parser.add_argument("--output", type=Path, default=Path("renovation-contract.json"))
    parser.add_argument("--plan", type=Path, default=Path("RENOVATION_PLAN.md"))
    args = parser.parse_args()

    audit = load_json(args.audit)
    repo = args.repo.resolve()
    findings = audit.get("findings", [])
    grouped: dict[str, list[str]] = defaultdict(list)
    for item in findings:
        grouped[CLASS_PHASE.get(item.get("class"), "validation_and_ratchet")].append(item["id"])

    phases: list[dict[str, Any]] = []
    for phase_name in PHASE_ORDER:
        ids = grouped.get(phase_name, [])
        if not ids:
            continue
        phases.append(
            {
                "name": phase_name,
                "objective": {
                    "integrity_repair": "Restore parseable, conflict-free active sources before changing repository contracts.",
                    "dependency_and_lock_authority": "Align declarations, package boundaries, bootstrap, and lock state with verified imports and consumers.",
                    "canonical_test_topology": "Establish explicit suite ownership and one repository-owned runner consumed by local and CI paths.",
                    "registry_and_reachability": "Reconcile registries and executable wiring so active capabilities are reachable and intentional dormancy is explicit.",
                    "security_and_permissions": "Reduce mutation and credential surfaces while preserving required automation.",
                    "release_and_compatibility": "Preserve or migrate upstream/downstream contracts with versioned evidence.",
                    "validation_and_ratchet": "Replace bypasses and theater with executable drift checks and monotonic quality gates.",
                    "documentation_and_handoff": "Update operator documentation only after executable contracts are proven.",
                }[phase_name],
                "finding_ids": sorted(ids),
                "checkpoint_requires_green": True,
            }
        )

    base_commit = audit.get("repository", {}).get("git_head")
    branch = args.branch or f"renovation/{audit.get('audit_id', 'repository').lower()}"
    allowed = sorted(evidence_paths(findings) | DEFAULT_CONTROL_PATHS)
    contract_id = stable_id(audit.get("audit_id", ""), args.base_ref, branch, prefix="RENOVATION")
    inventory = audit.get("inventory", {})
    authority_decisions = [
        {
            "concern": "dependency_and_environment",
            "target_authority": "one manifest and lock authority per package boundary; CI consumes locked bootstrap",
        },
        {
            "concern": "test_topology",
            "target_authority": "one repository-owned suite registry or explicit discovery contract; CI delegates to it",
        },
        {
            "concern": "automation",
            "target_authority": "local entrypoints own orchestration; CI invokes rather than duplicates",
        },
        {
            "concern": "registries_and_mirrors",
            "target_authority": "one canonical owner with generated or delegated mirrors",
        },
        {
            "concern": "validation",
            "target_authority": "deterministic drift checks plus cold-start evidence",
        },
    ]
    acceptance = [
        "Every high and critical in-scope finding is resolved or converted into an explicit blocking record.",
        "No new high or critical finding is introduced by the renovation.",
        "Dependency installation and test execution use canonical locked entrypoints locally and in CI.",
        "Every active ignored or isolated suite is explicitly registered and executed, or proven non-test content.",
        "No required gate is weakened, bypassed, or made advisory without an explicit ratchet decision.",
        "Changed files remain within contract scope and contain no new placeholders, deferred decisions, or conflict markers.",
        "Before/after audit, validation evidence, rollback, and PR body are complete and reproducible.",
    ]
    contract = {
        "schema_version": "renovation-contract-1.0",
        "contract_id": contract_id,
        "generated_at": utc_now(),
        "source_audit_id": audit.get("audit_id"),
        "objective": "Collapse fragmented repository control-plane authorities into a coherent, reproducible, validated operating model without changing product behavior outside explicit scope.",
        "repository": {
            "name": repo.name,
            "path": str(repo),
            "base_ref": args.base_ref,
            "base_commit": base_commit,
            "target_branch": branch,
        },
        "mode": "RENOVATE_TO_PR",
        "authority_decisions": authority_decisions,
        "scope": {
            "allowed_paths": allowed,
            "forbidden_paths": [
                ".git/**",
                "node_modules/**",
                ".venv/**",
                "dist/**",
                "build/**",
                "coverage/**",
            ],
            "preserved_behavior": [
                "public APIs and data contracts remain compatible unless a migration is explicitly added",
                "runtime feature behavior remains unchanged unless a verified defect requires repair",
                "security, tests, and review gates are not weakened",
            ],
            "forbidden_capabilities": [
                "merge without separate authorization",
                "stage unrelated worktree changes",
                "add a second dependency, test, registry, or CI authority",
                "hide failures through ignores, allow-failure, or floating installs",
                "leave placeholders or deferred implementation choices",
            ],
        },
        "phases": phases,
        "validation_matrix": detect_validation(repo, inventory),
        "acceptance_criteria": acceptance,
        "rollback": {
            "strategy": "revert independently green renovation commits in reverse dependency order",
            "data_migration": "not_authorized_unless_added_to_contract",
        },
        "pr_policy": {
            "draft": True,
            "max_pull_requests": 1,
            "remediate_until_green": True,
            "merge_authorized": False,
            "separate_authorization_required": [
                "stage",
                "commit",
                "push",
                "create_pr",
                "remediation_push",
                "merge",
            ],
        },
        "unknowns": [],
    }
    write_json(args.output, contract)
    args.plan.write_text(build_plan(contract, audit), encoding="utf-8")
    print(
        json.dumps(
            {"contract_id": contract_id, "phases": len(phases), "allowed_paths": len(allowed)},
            indent=2,
        )
    )
    print(f"contract: {args.output}")
    print(f"plan: {args.plan}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
