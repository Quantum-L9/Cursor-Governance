#!/usr/bin/env python3
"""Render a PLAN_DOCUMENT as a Program Execution campaign-source.v2 for `make campaign`.

`l9-plan` is the Program Execution campaign planner (CANONICAL_LAW
PROGRAM_EXECUTION_PLANNER_V1). Its campaign deliverable is a complete
`l9.program-execution.campaign-source.v2` that `make campaign` takes on its
direct route (campaign_source -> blueprint -> PEC) with nothing synthesized,
inferred or hand-edited: the plan's own dependencies become dependency_edges
and waves, each todo's writable files become the task's scope, and each todo's
own validation commands become the task's terminal verification.

The renderer refuses rather than guesses. A todo that writes files without a
validation command, a dependency on an unknown todo, a cycle, or an unknown the
plan marks `ask`/`block` stops the render. A rendered source is then judged by
Program Execution itself, not by a second validator here:

1. `campaign_input.classify` + `campaign_input.preflight` (what
   `make campaign-check-input` runs);
2. `compile_campaign_source.compile_source` into a throwaway Blueprint;
3. `launchability.check_tasks` with inference OFF, which must report the
   campaign launchable with no synthesized validation.

usage:
  render_campaign_source.py <plan.json> [--out PATH] [--target OWNER/REPO]
                            [--campaign-id ID] [--no-check] [--json]

Exit codes: 0 rendered and admitted; 1 refused (render or PE check); 2 usage.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

SCRIPTS = Path(__file__).resolve().parent
GOV_ROOT = SCRIPTS.parents[2]
PE_SCRIPTS = GOV_ROOT / "environment" / "program-execution" / "scripts"
SOURCE_SCHEMA = "l9.program-execution.campaign-source.v2"
CAMPAIGN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
HASH_PROGRAM_RE = re.compile(r"^pe-[0-9a-f]{8,}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REMOTE_RE = re.compile(r"github\.com[:/]+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$")
#: Plan risk -> campaign risk tier. A writing task is never below T2 in PE.
RISK_TIER = {"low": "T2", "medium": "T2", "high": "T3", "irreversible": "T4"}
BLOCKING_RESOLUTIONS = frozenset({"ask", "block"})
AUTHORITY_ORDER = [
    "applicable_safety_legal_security_requirements",
    "cursor_governance_canonical_law",
    "latest_explicit_operator_instruction",
    "accepted_program_decision",
    "approved_task_card",
    "repository_local_governance",
    "implementation",
    "documentation",
]
OPERATING_RULES = [
    "source_is_immutable_after_intake",
    "targets_array_is_the_single_repository_identity",
    "dependency_edges_are_the_only_task_ordering_authority",
    "writable_paths_are_explicit",
    "validation_commands_are_single_admissible_shell_operations",
    "remote_actions_are_forbidden_in_program_execution",
]
TERMINAL_VERDICTS = [
    "CONVERGED",
    "CONVERGED_WITH_NON_BLOCKING_RISKS",
    "NOT_CONVERGED",
    "INCONCLUSIVE",
]


class RenderError(RuntimeError):
    """The plan cannot become an admissible campaign source; nothing was written."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RenderError([f"cannot load {path}"])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:63].rstrip("-")


def _one_line(text: Any) -> str:
    return " ".join(str(text or "").split())


def resolve_target(plan: Mapping[str, Any], explicit: str | None, repo_root: Path) -> str:
    """The one target repository: --target, then plan.campaign, then the git origin."""
    declared = explicit or (plan.get("campaign") or {}).get("target_repository")
    if declared:
        if not REPO_RE.match(str(declared)):
            raise RenderError([f"target repository {declared!r} is not OWNER/REPO"])
        return str(declared)
    remote = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    match = REMOTE_RE.search(remote.stdout.strip()) if remote.returncode == 0 else None
    if not match:
        raise RenderError(
            [
                "no target repository: pass --target OWNER/REPO, set campaign.target_repository "
                f"in the plan, or run from a checkout whose origin is on GitHub ({repo_root})"
            ]
        )
    return match.group(1)


def resolve_campaign_id(plan: Mapping[str, Any], explicit: str | None) -> str:
    campaign_id = (
        explicit
        or (plan.get("campaign") or {}).get("campaign_id")
        or _slug(str(plan.get("title") or ""))
    )
    if not CAMPAIGN_ID_RE.match(campaign_id) or HASH_PROGRAM_RE.match(campaign_id):
        raise RenderError(
            [
                f"campaign id {campaign_id!r} must match {CAMPAIGN_ID_RE.pattern} and must not "
                "look like a hashed program id; set campaign.campaign_id"
            ]
        )
    return campaign_id


def _waves(order: list[str], deps: Mapping[str, list[str]]) -> dict[str, int]:
    """Topological level of every todo; refuses a cycle or an unknown dependency."""
    level: dict[str, int] = {}
    visiting: set[str] = set()
    errors: list[str] = []

    def walk(node: str) -> int:
        if node in level:
            return level[node]
        if node in visiting:
            errors.append(f"todo dependency cycle through {node!r}")
            return 0
        visiting.add(node)
        prerequisites = deps.get(node, [])
        level[node] = 1 + max((walk(dep) for dep in prerequisites), default=-1)
        visiting.discard(node)
        return level[node]

    for node in order:
        walk(node)
    if errors:
        raise RenderError(sorted(set(errors)))
    return level


def render(
    plan: Mapping[str, Any], *, target: str, campaign_id: str, stamp: str | None = None
) -> dict[str, Any]:
    """The campaign-source.v2 document for *plan*, or RenderError listing every gap."""
    errors: list[str] = []
    todos = [todo for todo in plan.get("todos") or [] if isinstance(todo, dict)]
    if not todos:
        errors.append("plan has no todos")
    todo_ids = [str(todo.get("id")) for todo in todos]
    if len(set(todo_ids)) != len(todo_ids):
        errors.append("todo ids are not unique")
    known = set(todo_ids)
    deps: dict[str, list[str]] = {}
    for todo in todos:
        todo_id = str(todo.get("id"))
        listed = [str(dep) for dep in todo.get("dependencies") or []]
        for dep in listed:
            if dep not in known:
                errors.append(f"todo {todo_id!r} depends on unknown todo {dep!r}")
        deps[todo_id] = [dep for dep in listed if dep in known]
        files = [str(path) for path in todo.get("files") or [] if str(path).strip()]
        commands = [str(cmd).strip() for cmd in todo.get("validation") or [] if str(cmd).strip()]
        blocker = _one_line(todo.get("blocker"))
        if blocker:
            errors.append(
                f"todo {todo_id!r} is blocked ({blocker}); resolve the blocker before rendering "
                "a campaign, or a dependent task would run past missing ground truth"
            )
        if files and not commands:
            errors.append(
                f"todo {todo_id!r} writes {files} but declares no validation command; add "
                "todos[].validation (single admissible commands) so the campaign task has a "
                "terminal verifier"
            )
    for unknown in plan.get("unknowns") or []:
        if isinstance(unknown, dict) and unknown.get("resolution") in BLOCKING_RESOLUTIONS:
            errors.append(
                f"unknown {unknown.get('id')!r} is unresolved ({unknown.get('resolution')}); "
                "resolve it before rendering a campaign"
            )
    if errors:
        raise RenderError(errors)
    level = _waves(todo_ids, deps)
    task_id = {todo_id: f"TASK-{index:03d}" for index, todo_id in enumerate(todo_ids, start=1)}
    title = _one_line(plan.get("title"))
    objective = _one_line(plan.get("objective"))
    owner = _one_line(plan.get("owner")) or "program_owner"
    success = [_one_line(item) for item in plan.get("success_criteria") or [] if item]
    scope = plan.get("scope") or {}
    created = stamp or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    tasks: list[dict[str, Any]] = []
    gates: list[dict[str, Any]] = []
    for index, todo in enumerate(todos, start=1):
        todo_id = str(todo["id"])
        tid = task_id[todo_id]
        gate_id = f"GATE-{index:03d}"
        files = [str(path) for path in todo.get("files") or [] if str(path).strip()]
        commands = [str(cmd).strip() for cmd in todo.get("validation") or [] if str(cmd).strip()]
        writes = bool(files)
        risk = str(todo.get("risk") or "medium")
        text = _one_line(todo.get("task"))
        acceptance = _one_line(todo.get("acceptance")) or (
            f"{text}: every declared validation command passes."
            if commands
            else f"{text}: the inspection is recorded."
        )
        validation = [
            {
                "id": f"VAL-{index:03d}-{number:02d}",
                "method": "command",
                "command_or_inspection": command,
                "environment": "repo_local",
                "expected_result": "PASS",
            }
            for number, command in enumerate(commands, start=1)
        ] or [
            {
                "id": f"VAL-{index:03d}-01",
                "method": "inspection",
                "command_or_inspection": acceptance,
                "environment": "repo_local",
                "expected_result": "PASS",
            }
        ]
        tasks.append(
            {
                "id": tid,
                "title": text[:120] or tid,
                "definition_status": "ready",
                "workstream_id": "WS-01",
                "wave_id": f"W{level[todo_id]}",
                "target_id": "TARGET-001",
                "execution_kind": "repo_local" if writes else "read_only",
                "kernel_profile": "CHANGE" if writes else "AUDIT",
                "objective": text,
                "authority_basis_ids": ["AUTH-001"],
                "required_decision_ids": [],
                "blocking_unknown_ids": [],
                "input_evidence_ids": ["EVID-001"],
                "paths": files,
                "consumers": ["program_execution_controller", "campaign_operator"],
                "entrypoints": ["make campaign"],
                "actions": [f"{str(todo.get('operation') or 'change').lower()}_declared_paths"]
                if writes
                else ["inspect_declared_scope"],
                "acceptance": [
                    {
                        "id": f"AC-{index:03d}",
                        "statement": acceptance,
                        "required_evidence_types": ["test_result"] if commands else ["inspection"],
                    }
                ],
                "validation": validation,
                "negative_cases": ["write_outside_declared_scope", "declared_validation_fails"],
                "rollback": {
                    "strategy": "discard_unaccepted_artifacts_or_revert_local_commit",
                    "trigger": "validation_failure_or_scope_violation",
                    "validation": "git status --short",
                },
                "risk": {
                    "tier": RISK_TIER.get(risk, "T2") if writes else "T0",
                    "reversibility": "irreversible" if risk == "irreversible" else "reversible",
                    "blast_radius": ", ".join(files) if files else "read_only",
                },
                "authorization_ceiling": {
                    "inspect": True,
                    "local_write": writes,
                    "commit": writes,
                    "push": False,
                    "pull_request": False,
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
                "name": f"{tid.lower()}_validated",
                "gate_type": "completion",
                "blocking": True,
                "owner_authority_id": "AUTH-002",
                "task_ids": [tid],
                "required_evidence_ids": ["EVID-001"],
                "pass_criteria": [f"{tid} is complete with its declared validation passing."],
                "failure_effect": "BLOCKED",
            }
        )

    by_wave: dict[int, list[str]] = {}
    for todo_id in todo_ids:
        by_wave.setdefault(level[todo_id], []).append(task_id[todo_id])
    waves = [
        {
            "id": f"W{number}",
            "name": f"wave_{number}",
            "task_ids": by_wave[number],
            "predecessor_wave_ids": [f"W{number - 1}"] if number else [],
            "exit_gate_ids": [
                gate["id"] for gate in gates if gate["task_ids"][0] in by_wave[number]
            ],
        }
        for number in sorted(by_wave)
    ]
    edges = [
        {"from": task_id[dep], "to": task_id[todo_id]}
        for todo_id in todo_ids
        for dep in deps[todo_id]
    ]
    risks = [
        {
            "id": f"RISK-{index:03d}",
            "statement": _one_line(item.get("risk")),
            "owner": owner,
            "mitigations": [_one_line(item.get("mitigation"))],
            "acceptance_status": "accepted",
        }
        for index, item in enumerate(plan.get("risks") or [], start=1)
        if isinstance(item, dict) and item.get("risk")
    ]
    return {
        "schema": SOURCE_SCHEMA,
        "schema_version": "2.0.0",
        "plan_status": "Ready",
        "metadata": {
            "campaign_id": campaign_id,
            "title": title,
            "version": "1.0.0",
            "created_at": created,
            "status": "operator_intake",
            "owner": owner,
            "intended_host": target,
            "source_is_immutable": True,
            "remote_mutation_during_admission": False,
            "rendered_by": "skills/l9-plan/scripts/render_campaign_source.py",
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
        },
        "program": {
            "id": campaign_id,
            "name": title,
            "version": "1.0.0",
            "owner": owner,
            "definition_status": "ready",
            "snapshot_at": created[:10],
            "target_repository_id": target,
            "objective": objective,
            "problem_statement": objective,
            "target_state": "; ".join(success) or objective,
            "scope": {
                "include": [str(item) for item in scope.get("in") or []],
                "exclude": [str(item) for item in scope.get("out") or []],
            },
            "authority_order": list(AUTHORITY_ORDER),
            "operating_rules": list(OPERATING_RULES),
            "terminal_verdicts": list(TERMINAL_VERDICTS),
        },
        "targets": [
            {
                "id": "TARGET-001",
                "name": target,
                "kind": "git_repository",
                "authority_owner": target,
                "execution_mode": "repo_local",
                "adapter": "git",
                "repository_id": target,
                "source_of_truth": str(
                    (plan.get("campaign") or {}).get("source_of_truth") or "repository_origin_main"
                ),
                "environments": ["local"],
                "mutability": "reversible",
                "expected_revision": "UNKNOWN",
            }
        ],
        "authorities": [
            {
                "id": "AUTH-001",
                "responsibility": "program_definition_and_terminal_verdict",
                "owner": owner,
                "scope": ["whole_program", "scope_changes", "terminal_verdict"],
            },
            {
                "id": "AUTH-002",
                "responsibility": "controller_evidence_and_gate_evaluation",
                "owner": "controller",
                "scope": ["evidence_collection", "gate_evaluation"],
            },
        ],
        "decisions": [],
        "unknowns": [],
        "evidence_requirements": [
            {
                "id": "EVID-001",
                "claim": "The target repository identity and pre-execution revision are recorded.",
                "source_type": "repository_inspection",
                "source_location": target,
                "collection_method": "read_only_inspection",
                "freshness": "collect_at_admission",
                "producer": "controller",
                "supports": [gate["id"] for gate in gates],
                "contradicts": [],
            }
        ],
        "workstreams": [
            {
                "id": "WS-01",
                "name": "plan_execution",
                "objective": objective,
                "owner": owner,
                "target_id": "TARGET-001",
            }
        ],
        "dependency_edges": edges,
        "waves": waves,
        "tasks": tasks,
        "gates": gates,
        "risks": risks,
    }


def check_admission(source_path: Path, repo_root: Path) -> dict[str, Any]:
    """Judge the rendered source with Program Execution's own front door and compiler."""
    if str(PE_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(PE_SCRIPTS))
    campaign_input = _load("l9_plan_pe_campaign_input", PE_SCRIPTS / "campaign_input.py")
    try:
        found = campaign_input.classify(source_path)
        if found.kind is not campaign_input.CampaignInputKind.CAMPAIGN_SOURCE_V2:
            raise RenderError([f"rendered source classified as {found.kind.value}, not v2"])
        warnings = campaign_input.preflight(found)
    except campaign_input.CampaignInputRejected as exc:
        raise RenderError([f"PE front door rejected the source: {exc.render()}"]) from exc
    compiler = _load(
        "l9_plan_pe_compile_campaign_source", PE_SCRIPTS / "compile_campaign_source.py"
    )
    launchability = _load("l9_plan_pe_launchability", PE_SCRIPTS / "launchability.py")
    stack = _load("l9_plan_pe_context7_stack_proof", PE_SCRIPTS / "context7_stack_proof.py")
    document = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="l9-plan-campaign-") as raw:
        blueprint = Path(raw) / "blueprint"
        try:
            # The same stack proof make campaign primes for this source: the
            # runner's seed view, proved offline when no external stack is
            # inferred and against the docs otherwise.
            receipt = stack.prove_stack(campaign_input.seed_view(document), primed_dir=Path(raw))
            compiler.compile_source(source_path, blueprint, stack_proof=Path(receipt["path"]))
        except Exception as exc:  # noqa: BLE001 - every compile failure is a refusal
            raise RenderError([f"PE compiler refused the source: {exc}"]) from exc
        report = launchability.check_tasks(
            launchability.blueprint_tasks(blueprint), repo_root, infer=False
        )
    if not report.get("launchable"):
        raise RenderError(
            [
                f"{item.get('task_id')}: {item.get('code')} — {item.get('remedy')}"
                for item in report.get("blockers") or []
            ]
        )
    if report.get("synthesized_validations"):
        raise RenderError(["launchability had to synthesize validations; declare them in the plan"])
    return {
        "front_door": "campaign-source.v2",
        "route": found.route,
        "preflight_warnings": list(warnings),
        "compiled": True,
        "launchable": True,
        "task_count": report.get("task_count"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--target", default=None, help="OWNER/REPO the campaign changes")
    parser.add_argument("--campaign-id", default=None)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--no-check", action="store_true", help="render only (tests)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if str(SCRIPTS) not in sys.path:
        # The validator imports its sibling `paths`; loaded by path from another
        # caller, the skill's scripts directory is not otherwise importable.
        sys.path.insert(0, str(SCRIPTS))
    validator = _load("l9_plan_validate_plan_document", SCRIPTS / "validate_plan_document.py")
    plan_path = args.plan.resolve()
    errors = validator.validate_path(plan_path)
    try:
        if errors:
            raise RenderError([f"PLAN_DOCUMENT invalid: {error}" for error in errors])
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        repo_root = args.repo_root.resolve()
        campaign_id = resolve_campaign_id(plan, args.campaign_id)
        target = resolve_target(plan, args.target, repo_root)
        source = render(plan, target=target, campaign_id=campaign_id)
        out = (
            args.out or repo_root / ".l9" / "plans" / campaign_id / "CAMPAIGN_SOURCE.yaml"
        ).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        # Judge a staged copy; only an admitted source replaces the handoff path,
        # so a refused re-render never destroys a previously admitted one.
        staged = out.with_name(f".{out.stem}.staged-{os.getpid()}{out.suffix or '.yaml'}")
        staged.write_text(
            yaml.safe_dump(source, sort_keys=False, allow_unicode=True, width=100),
            encoding="utf-8",
        )
        try:
            admission = {"skipped": True} if args.no_check else check_admission(staged, repo_root)
        except BaseException:
            staged.unlink(missing_ok=True)
            raise
        os.replace(staged, out)
    except RenderError as exc:
        if args.json:
            print(json.dumps({"status": "REFUSED", "errors": exc.errors}, indent=2))
        else:
            print("REFUSED: the plan is not an admissible campaign-source.v2", file=sys.stderr)
            for error in exc.errors:
                print(f"  - {error}", file=sys.stderr)
        return 1
    result = {
        "status": "ADMITTED" if not args.no_check else "RENDERED",
        "campaign_id": campaign_id,
        "target": target,
        "source": str(out),
        "admission": admission,
        "next": [
            "/coding-agent on   # in the workspace you run make campaign from",
            'L9_PE_OPERATOR_INVOCATION="<your own words asking for this campaign>" '
            f'make -C "$HOME/.cursor-governance" campaign INTENT={out} WS="$PWD"',
        ],
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result['status']}: {out}")
        print(f"  campaign_id: {campaign_id}  target: {target}")
        print("  next (operator only; an agent never sets the invocation):")
        for line in result["next"]:
            print(f"    {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
