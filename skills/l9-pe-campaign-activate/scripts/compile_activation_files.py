#!/usr/bin/env python3
"""Compile only the files required to activate a PE campaign.

Purpose: emit CAMPAIGN_SOURCE.yaml + source-integrity-receipt.json and patch
the four host registration files. Never write README, handoff, INTENT.yaml,
or other extras.

Metadata:
  parent: l9-pe-campaign-activate
  layer: script
  role: activation_compiler
  version: 1.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

CAMPAIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
FORBIDDEN_CAMPAIGN_FILES = {
    "README.md",
    "INTENT.yaml",
    "CONTRACT_SOURCE.md",
    "PROGRAM_SOURCE.md",
    "AUTH-001-SUPERSESSION.yaml",
    "PE_COMPILER_MODULE_ALIGNMENT.yaml",
    "CAMPAIGN_EXECUTION_BINDING.yaml",
    "CURRENT_STATE.yaml",
    "VALIDATION_EVIDENCE.md",
    "AGENT_FEED.md",
}
ALLOWED_CAMPAIGN_FILES = {"CAMPAIGN_SOURCE.yaml", "source-integrity-receipt.json"}


class CompileError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_yaml(path: Path) -> Any:
    if yaml is None:
        raise CompileError("PyYAML required")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def dump_yaml(path: Path, value: Any) -> None:
    if yaml is None:
        raise CompileError("PyYAML required")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(value, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )


def require_intent(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise CompileError("intent must be a mapping")
    campaign_id = str(raw.get("campaign_id") or "").strip()
    title = str(raw.get("title") or "").strip()
    objective = str(raw.get("objective") or "").strip()
    tasks = raw.get("tasks")
    if not CAMPAIGN_ID_RE.match(campaign_id):
        raise CompileError("campaign_id must match ^[a-z0-9][a-z0-9-]{2,62}$")
    if not title:
        raise CompileError("title is required")
    if not objective:
        raise CompileError("objective is required")
    if not isinstance(tasks, list) or not tasks:
        raise CompileError("tasks must be a non-empty list")
    return raw


def _task_id(index: int) -> str:
    return f"TASK-{index:03d}"


def _gate_id(index: int) -> str:
    return f"GATE-{index:03d}"


def build_source(intent: dict[str, Any], *, stamp: str) -> dict[str, Any]:
    campaign_id = str(intent["campaign_id"]).strip()
    title = str(intent["title"]).strip()
    objective = str(intent["objective"]).strip()
    owner = str(intent.get("owner") or "Igor Beylin").strip()
    target = intent.get("target") if isinstance(intent.get("target"), dict) else {}
    repository_id = str(target.get("repository_id") or "Quantum-L9/Cursor-Governance").strip()
    source_of_truth = str(target.get("source_of_truth") or "environment/program-execution").strip()
    adapter = str(target.get("adapter") or "git").strip()
    raw_tasks = list(intent["tasks"])

    tasks: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    task_ids: list[str] = []
    for index, item in enumerate(raw_tasks, start=1):
        if not isinstance(item, dict):
            raise CompileError(f"task {index} must be a mapping")
        task_title = str(item.get("title") or "").strip()
        task_objective = str(item.get("objective") or task_title).strip()
        if not task_title:
            raise CompileError(f"task {index} title is required")
        task_id = str(item.get("id") or _task_id(index))
        gate_id = _gate_id(index)
        paths = [str(path) for path in (item.get("paths") or []) if path]
        actions = list(item.get("actions") or [])
        if not actions:
            actions = [f"implement_{task_id.lower().replace('-', '_')}"]
            if paths:
                actions.append("edit_only_declared_paths")
        task_ids.append(task_id)
        tasks.append(
            {
                "id": task_id,
                "title": task_title,
                "definition_status": "ready" if index == 1 else "blocked",
                "workstream_id": "WS-01",
                "wave_id": "W0" if index == 1 else "W1",
                "target_id": "TARGET-001",
                "execution_kind": "repo_local",
                "objective": task_objective,
                "authority_basis_ids": ["AUTH-001"],
                "required_decision_ids": [],
                "blocking_unknown_ids": [],
                "input_evidence_ids": [],
                "actions": actions,
                "acceptance": [
                    {
                        "id": f"AC-{index:03d}",
                        "statement": (f"{task_title} is complete and locally verified."),
                    }
                ],
                "negative_cases": ["scope_expansion", "remote_mutation_before_release"],
                "rollback": {
                    "strategy": "discard_uncommitted_or_revert_local_commit",
                    "trigger": "validation_failure",
                    "validation": "worktree_matches_prior_head",
                },
                "risk": {
                    "tier": "T0",
                    "reversibility": "fully_reversible",
                    "blast_radius": "declared_paths",
                },
                "authorization_ceiling": {
                    "inspect": True,
                    "local_write": True,
                    "commit": True,
                    "push": True,
                    "pull_request": True,
                    "merge": False,
                    "publish_or_release": False,
                    "deploy_or_migrate": False,
                    "destructive_change": False,
                    "external_message": False,
                },
                "completion_gate_ids": [gate_id],
            }
        )
        gates.append(
            {
                "id": gate_id,
                "name": f"{task_id.lower()}_complete",
                "gate_type": "entry" if index == 1 else "completion",
                "blocking": True,
                "owner_authority_id": "AUTH-001",
                "task_ids": [task_id],
                "required_evidence_ids": [],
                "pass_criteria": [f"{task_title} acceptance is met."],
                "failure_effect": "block_successor_tasks",
            }
        )

    later_ids = task_ids[1:]
    waves = [
        {
            "id": "W0",
            "name": "admission_and_first_ready_task",
            "task_ids": [task_ids[0]],
            "predecessor_wave_ids": [],
            "exit_gate_ids": [gates[0]["id"]],
        }
    ]
    if later_ids:
        waves.append(
            {
                "id": "W1",
                "name": "remaining_tasks",
                "task_ids": later_ids,
                "predecessor_wave_ids": ["W0"],
                "exit_gate_ids": [gate["id"] for gate in gates[1:]],
            }
        )

    edges = []
    for index in range(len(task_ids) - 1):
        edges.append({"from": task_ids[index], "to": task_ids[index + 1]})

    return {
        "schema": "l9.program-execution.campaign-source.v2",
        "schema_version": "2.0.0",
        "metadata": {
            "campaign_id": campaign_id,
            "title": title,
            "version": "1.0.0",
            "created_at": stamp,
            "status": "operator_intake",
            "owner": owner,
            "intended_host": repository_id,
            "intended_drop_path": (
                f"environment/program-execution/campaigns/{campaign_id}/CAMPAIGN_SOURCE.yaml"
            ),
            "runtime_root": f"$HOME/.l9/programs/{campaign_id}",
            "worktree_root": f"$HOME/.l9/program-worktrees/{campaign_id}",
            "source_is_immutable": True,
            "remote_mutation_during_admission": False,
        },
        "integrity": {
            "digest_algorithm": "sha256",
            "canonical_encoding": "utf-8",
            "canonical_line_endings": "lf",
            "digest_record_location": "source-integrity-receipt.json",
            "generated_counts_or_digests_may_be_hand_edited": False,
        },
        "pipeline_contract": {
            "pair": "program-execution-system.v2",
            "blueprint": "program-execution-blueprint.v2",
            "controller": "program-execution-controller.v2",
        },
        "operator_directive": {
            "objective": objective,
            "mode": "controlled_autonomous_until_material_boundary",
            "policy_profile": "quantum-l9.safe-autonomy.v1",
            "prohibited_actions": [
                "force_push",
                "admin_merge",
                "deploy",
                "weaken_validators",
                "delete_tests_for_pass",
            ],
        },
        "program": {
            "id": campaign_id,
            "name": title,
            "version": "1.0.0",
            "owner": owner,
            "definition_status": "draft",
            "snapshot_at": stamp[:10],
            "objective": objective,
            "problem_statement": str(intent.get("problem_statement") or objective).strip(),
            "target_state": str(intent.get("target_state") or objective).strip(),
            "scope": {
                "include": [source_of_truth],
                "exclude": [
                    "new repositories",
                    "force_push",
                    "admin_merge",
                    "deploy",
                    "production migration",
                ],
            },
            "contracts": {
                "pair": "program-execution-system.v2",
                "blueprint": "program-execution-blueprint.v2",
                "controller_minimum": "program-execution-controller.v2",
            },
            "authority_order": [
                "applicable_safety_legal_security_requirements",
                "cursor_governance_canonical_law",
                "program_execution_interface_contract",
                "latest_explicit_operator_instruction",
                "accepted_program_definition",
                "implementation",
                "UNKNOWN",
            ],
            "operating_rules": [
                "one_authority_per_responsibility",
                "mutable_runtime_state_remains_outside_git",
                "no_silent_scope_expansion",
                "worker_claim_is_not_verification",
            ],
            "terminal_verdicts": [
                "CONVERGED",
                "CONVERGED_WITH_NON_BLOCKING_RISKS",
                "NOT_CONVERGED",
                "INCONCLUSIVE",
            ],
        },
        "targets": [
            {
                "id": "TARGET-001",
                "name": repository_id,
                "kind": "git_repository",
                "authority_owner": repository_id,
                "execution_mode": "repo_local",
                "repository_id": repository_id,
                "source_of_truth": source_of_truth,
                "environments": ["local", "ci"],
                "mutability": "reversible",
                "expected_revision": "UNKNOWN",
                "adapter": adapter,
            }
        ],
        "authorities": [
            {
                "id": "AUTH-001",
                "responsibility": "campaign_owner",
                "owner": owner,
            }
        ],
        "workstreams": [
            {
                "id": "WS-01",
                "name": title,
                "owner": "AUTH-001",
                "objective": objective,
            }
        ],
        "dependency_edges": edges,
        "waves": waves,
        "tasks": tasks,
        "gates": gates,
        "evidence_requirements": [
            {
                "id": "EVID-001",
                "claim": "exact_target_origin_main_revision_and_worktree_state_are_known",
                "source_type": "repository_inspection",
                "source_location": repository_id,
                "collection_method": "read_only_inspection",
                "freshness": "collect_at_admission",
                "producer": "controller",
                "supports": ["TASK-001"],
                "contradicts": [],
            }
        ],
    }


def write_receipt(source_path: Path, campaign_id: str, *, stamp: str) -> dict[str, Any]:
    data = source_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    receipt = {
        "schema": "source-integrity-receipt.v1",
        "campaign_id": campaign_id,
        "source_file": "CAMPAIGN_SOURCE.yaml",
        "digest_algorithm": "sha256",
        "digest": digest,
        "bytes": len(data),
        "pack_recorded_digest": digest,
        "pack_recorded_bytes": len(data),
        "digest_matches_pack": True,
        "collected_at": stamp,
        "collection_method": "l9-pe-campaign-activate-compile",
        "producer": "l9-pe-campaign-activate",
    }
    receipt_path = source_path.with_name("source-integrity-receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def patch_allowlist(path: Path, campaign_id: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if re.search(rf"^\s*-\s+{re.escape(campaign_id)}\s*$", text, re.M):
        return False
    if "campaign_ids:" not in text:
        raise CompileError(f"{path} missing campaign_ids")
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + f"  - {campaign_id}\n", encoding="utf-8")
    return True


def patch_execution_policy(path: Path, campaign_id: str) -> bool:
    raw = load_yaml(path)
    campaigns = list((raw or {}).get("campaigns") or [])
    if any(str(item.get("id")) == campaign_id for item in campaigns if isinstance(item, dict)):
        return False
    orders = [int(item.get("execute_order") or 0) for item in campaigns if isinstance(item, dict)]
    execute_order = (max(orders) + 1) if orders else 1
    block = (
        f"  - id: {campaign_id}\n"
        f"    integration_branch: campaign/{campaign_id}\n"
        f"    pr_base: campaign/{campaign_id}\n"
        f"    execute_order: {execute_order}\n"
        f"    lane: compiled\n"
    )
    text = path.read_text(encoding="utf-8")
    marker = "\nowner:\n"
    if marker in text:
        text = text.replace(marker, "\n" + block + marker, 1)
    else:
        if not text.endswith("\n"):
            text += "\n"
        text += block
    path.write_text(text, encoding="utf-8")
    return True


def patch_surface_profile(path: Path, campaign_id: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if re.search(
        rf"^\s+{re.escape(campaign_id)}:\n\s+integration_branch:",
        text,
        re.M,
    ):
        return False
    block = f"    {campaign_id}:\n      integration_branch: campaign/{campaign_id}\n"
    marker = "\nauthority_order:\n"
    if marker not in text:
        raise CompileError(f"{path} missing authority_order marker")
    path.write_text(text.replace(marker, block + marker, 1), encoding="utf-8")
    return True


def patch_status_ledger(path: Path, campaign_id: str) -> bool:
    raw = load_yaml(path) if path.is_file() else {}
    campaigns = list((raw or {}).get("campaigns") or [])
    if any(str(item.get("id")) == campaign_id for item in campaigns if isinstance(item, dict)):
        return False
    block = (
        f"  - id: {campaign_id}\n"
        f"    lifecycle: planned\n"
        f"    notes: compiled by l9-pe-campaign-activate\n"
    )
    text = (
        path.read_text(encoding="utf-8")
        if path.is_file()
        else (
            "schema: l9.program-execution.campaign-status-ledger.v1\n"
            f'updated: "{utc_now()}"\n'
            "campaigns:\n"
        )
    )
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + block, encoding="utf-8")
    return True


def assert_no_forbidden(campaign_dir: Path) -> None:
    extras = []
    for path in sorted(campaign_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(campaign_dir).as_posix()
        name = path.name
        if name in FORBIDDEN_CAMPAIGN_FILES or rel.startswith(
            ("handoff/", "deliverables/", "history/")
        ):
            extras.append(rel)
        elif path.parent == campaign_dir and name not in ALLOWED_CAMPAIGN_FILES:
            extras.append(rel)
    if extras:
        raise CompileError("forbidden extra files: " + ", ".join(extras))


def compile_activation(
    intent_path: Path,
    repo_root: Path,
    *,
    stamp: str | None = None,
) -> dict[str, Any]:
    intent = require_intent(load_yaml(intent_path))
    campaign_id = str(intent["campaign_id"]).strip()
    now = stamp or utc_now()
    source = build_source(intent, stamp=now)
    campaign_dir = repo_root / "environment" / "program-execution" / "campaigns" / campaign_id
    campaign_dir.mkdir(parents=True, exist_ok=True)
    source_path = campaign_dir / "CAMPAIGN_SOURCE.yaml"
    dump_yaml(source_path, source)
    write_receipt(source_path, campaign_id, stamp=now)
    assert_no_forbidden(campaign_dir)

    wrote = [
        str(source_path.relative_to(repo_root)),
        str((campaign_dir / "source-integrity-receipt.json").relative_to(repo_root)),
    ]
    patched: list[str] = []
    hosts = (
        (
            repo_root / "environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml",
            patch_allowlist,
        ),
        (
            repo_root / "environment/program-execution/campaigns/CAMPAIGN_EXECUTION_POLICY.yaml",
            patch_execution_policy,
        ),
        (
            repo_root / "ops/autonomy/surface_profile.yaml",
            patch_surface_profile,
        ),
        (
            repo_root / "environment/program-execution/campaigns/CAMPAIGN_STATUS.yaml",
            patch_status_ledger,
        ),
    )
    for path, patcher in hosts:
        if not path.is_file() and path.name != "CAMPAIGN_STATUS.yaml":
            raise CompileError(f"missing host file: {path}")
        if patcher(path, campaign_id):
            patched.append(str(path.relative_to(repo_root)))
    return {
        "campaign_id": campaign_id,
        "wrote": wrote,
        "patched": patched,
        "forbidden": sorted(FORBIDDEN_CAMPAIGN_FILES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--stamp", default="")
    args = parser.parse_args()
    try:
        result = compile_activation(
            args.intent.resolve(),
            args.repo_root.resolve(),
            stamp=args.stamp or None,
        )
    except CompileError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
