#!/usr/bin/env python3
"""Fleet plan for l9-pr-remediation: inventory once, then waves, assignments, acceptance.

The remediator's preflight used to be prose: one ``gh pr view --json files``
per open PR, a hand-built overlap matrix, a stack probe re-run at merge time,
and "independent PRs may be remediated in parallel" as an optional sentence.
Its only concrete parallel-launch instruction needed a root-autonomy campaign
admission token that nothing produced for a PR fleet. This module is the
deterministic owner of that gap, and deliberately nothing more:

  plan     one REST pass (parallel per-PR file fetch), stack edges, path-level
           overlap (generated-only overlap does not serialize), oldest-first
           bottom-up merge order, optional board verdicts, a receipt with a
           fingerprint so the fleet is inventoried once until a head moves.
  waves    the largest currently safe concurrent set: read-only recon and watch
           lanes always parallel; mutation lanes admitted only when their
           write claims do not conflict under the canonical claim primitive
           (autonomy.runtime.claims.claim_scopes_conflict), capped by the
           surface execution profile (ops/autonomy/execution_profile.py).
  assign   one bounded assignment packet per (PR, role) in the shape
           environment/agents/cursor-subagents/DELEGATION_CONTRACT.yaml
           requires, plus the Task prompt to launch it with.
  accept   validate one returned result document against its assignment with
           the canonical bridge (result_bridge.validate_result_against_assignment)
           and, when the assignment was recorded, the results gateway.
  model    before/after velocity counters for a fleet (serial v4.6 hot path vs
           the wave plan). A model of the prose, not a timing.

Not a scheduler: no leases, no claims registry, no admission, no capacity
accounting beyond the profile caps it reads. Not a merge authority: it never
merges, pushes, or edits. Not a campaign: identity fields on assignments are
run-scoped correlation keys (``lease_id`` is ``no-root-lease-<assignment>``),
which the results gateway honours because it checks a root lease only when a
runtime database is named. Program Execution is never involved.

Probe: L9_PR_FLEET_PROBE_FILE (tests / offline) or live ``gh api`` REST.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
for _path in (str(_HERE), str(_ROOT / "ops" / "scripts"), str(_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import execution_profile  # noqa: E402
from merge_gate import _gh_json  # noqa: E402
from sync_generated_artifacts import GENERATED_PATH_PREFIXES, is_generated_path  # noqa: E402

PAGE_SIZE = 100
MAX_PAGES = 20
FETCH_WORKERS = 8
RECEIPT_DIR = Path(".l9") / "pr"
FLEET_RECEIPT = "fleet.json"
ASSIGNMENT_DIR = "assignments"

#: Paths the remediator may never patch (edit axis CI_PIPELINE + secret plane).
#: fnmatch grammar of autonomy.runtime.capability_gateway.path_matches: ``*``
#: crosses ``/``, so ``.github/workflows/*`` covers every nesting level.
FORBIDDEN_PATHS = (
    ".github/workflows/*",
    ".github/actions/*",
    ".github/CODEOWNERS",
    "ops/secrets/*",
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
)

ROLE_RECON = "recon"
ROLE_REMEDIATE = "pr_remediation"
ROLE_WATCH = "recon"  # a watcher observes and never mutates: the read-only role
KINDS = {"recon": ROLE_RECON, "remediate": ROLE_REMEDIATE, "watch": ROLE_WATCH}

RESULT_SCHEMA_PATH = (
    "environment/agents/cursor-subagents/schemas/cursor-subagent-result.schema.json"
)


class FleetError(RuntimeError):
    """Telemetry could not be resolved. Callers plan nothing, never guess."""


# ---------------------------------------------------------------------------
# inventory
# ---------------------------------------------------------------------------


def _probe() -> dict[str, Any] | None:
    override = os.environ.get("L9_PR_FLEET_PROBE_FILE", "").strip()
    if not override:
        return None
    try:
        payload = json.loads(Path(override).expanduser().read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise FleetError(f"unreadable L9_PR_FLEET_PROBE_FILE ({exc})") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("prs"), list):
        raise FleetError("L9_PR_FLEET_PROBE_FILE must be an object with a prs list")
    return payload


def _rest_pages(path: str) -> list[Any]:
    out: list[Any] = []
    for page in range(1, MAX_PAGES + 1):
        sep = "&" if "?" in path else "?"
        try:
            body = _gh_json(["api", f"{path}{sep}per_page={PAGE_SIZE}&page={page}"])
        except RuntimeError as exc:
            raise FleetError(f"gh api {path} failed: {exc}") from exc
        if not isinstance(body, list):
            raise FleetError(f"gh api {path} returned a non-list payload")
        out.extend(body)
        if len(body) < PAGE_SIZE:
            return out
    raise FleetError(
        f"gh api {path}: pagination exceeded {MAX_PAGES} pages; refusing a partial set"
    )


def _normalize_pr(item: dict[str, Any]) -> dict[str, Any]:
    head = item.get("head") if isinstance(item.get("head"), dict) else {}
    base = item.get("base") if isinstance(item.get("base"), dict) else {}
    return {
        "number": int(item["number"]),
        "title": str(item.get("title") or ""),
        "createdAt": str(item.get("created_at") or item.get("createdAt") or ""),
        "headRefName": str(head.get("ref") or item.get("headRefName") or ""),
        "headRefOid": str(head.get("sha") or item.get("headRefOid") or ""),
        "baseRefName": str(base.get("ref") or item.get("baseRefName") or ""),
        "isDraft": bool(item.get("draft", item.get("isDraft", False))),
        "files": [str(f) for f in item.get("files") or []],
    }


def _fetch_files(repo: str, number: int) -> list[str]:
    rows = _rest_pages(f"repos/{repo}/pulls/{number}/files")
    return sorted({str(row.get("filename") or "") for row in rows if row.get("filename")})


def inventory(repo: str) -> list[dict[str, Any]]:
    """Open PRs with files, one pass, files fetched concurrently. Raises FleetError."""
    injected = _probe()
    if injected is not None:
        prs = [_normalize_pr(dict(item)) for item in injected["prs"]]
    else:
        rows = _rest_pages(f"repos/{repo}/pulls?state=open")
        prs = [_normalize_pr(row) for row in rows if isinstance(row, dict)]
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
            files = list(pool.map(lambda pr: _fetch_files(repo, pr["number"]), prs))
        for pr, listing in zip(prs, files, strict=True):
            pr["files"] = listing
    for pr in prs:
        if not pr["headRefOid"] or not pr["headRefName"] or not pr["createdAt"]:
            raise FleetError(f"PR #{pr['number']} is missing head SHA, head ref, or createdAt")
    return sorted(prs, key=lambda pr: (pr["createdAt"], pr["number"]))


def fingerprint(prs: list[dict[str, Any]]) -> str:
    seed = sorted((pr["number"], pr["headRefOid"]) for pr in prs)
    return hashlib.sha256(json.dumps(seed, sort_keys=True).encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# topology
# ---------------------------------------------------------------------------


def stack_edges(prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """child -> parent where the child's base is another open PR's head."""
    by_head = {pr["headRefName"]: pr["number"] for pr in prs}
    edges = []
    for pr in prs:
        parent = by_head.get(pr["baseRefName"])
        if parent is not None and parent != pr["number"]:
            edges.append({"child": pr["number"], "parent": parent})
    return edges


def overlap_matrix(prs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for i, left in enumerate(prs):
        for right in prs[i + 1 :]:
            shared = sorted(set(left["files"]) & set(right["files"]))
            if not shared:
                continue
            out.append(
                {
                    "prs": [left["number"], right["number"]],
                    "files": shared,
                    "generated_only": all(is_generated_path(path) for path in shared),
                }
            )
    return out


def merge_order(prs: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[int]:
    """Oldest createdAt first, parents before their stacked children (bottom-up)."""
    parents = {edge["child"]: edge["parent"] for edge in edges}
    ordered: list[int] = []
    placed: set[int] = set()
    remaining = [pr["number"] for pr in prs]  # already createdAt-sorted
    while remaining:
        progressed = False
        for number in list(remaining):
            parent = parents.get(number)
            if parent is None or parent in placed or parent not in remaining:
                ordered.append(number)
                placed.add(number)
                remaining.remove(number)
                progressed = True
        if not progressed:
            # A cycle cannot happen on real GitHub topology; fail closed anyway.
            raise FleetError("stack topology cycle: " + ", ".join(map(str, remaining)))
    return ordered


# ---------------------------------------------------------------------------
# waves
# ---------------------------------------------------------------------------


def write_claims(pr: dict[str, Any]) -> list[dict[str, Any]]:
    """Exclusive write claims one remediation of this PR holds.

    Path-scoped keys use the claim plane's own grammar so overlap resolves the
    way the registry would resolve it; generated paths are omitted because a
    generated-only collision heals after merge (generated-heal.md). The branch
    key is opaque and serializes two mutators of the same head.
    """
    claims = [
        {"key": f"path:{path}", "mode": "write", "exclusive": True}
        for path in pr["files"]
        if not is_generated_path(path)
    ]
    claims.append({"key": f"branch:{pr['headRefName']}", "mode": "write", "exclusive": True})
    return claims


def _claims_conflict(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> bool:
    from autonomy.runtime.claims import claim_scopes_conflict  # noqa: PLC0415

    for claim in left:
        for other in right:
            if claim_scopes_conflict(
                key=claim["key"],
                mode=claim["mode"],
                exclusive=bool(claim["exclusive"]),
                other_key=other["key"],
                other_mode=other["mode"],
                other_exclusive=bool(other["exclusive"]),
            ):
                return True
    return False


def profile_caps(surface: str | None = None) -> dict[str, Any]:
    """Concurrency caps from the canonical execution-profile owner. Never a local number."""
    policy = execution_profile.load_policy(_ROOT)
    resolved = surface or execution_profile.classify(os.environ, policy)
    profile = policy["profiles"][resolved]
    return {
        "surface": resolved,
        "max_parallel": int(profile["max_parallel"]),
        "max_mutation_lanes": int(profile["max_mutation_lanes"]),
        "owner": (
            "ops/autonomy/claude-execution-profiles.json via ops/autonomy/execution_profile.py"
        ),
    }


def waves(
    prs: list[dict[str, Any]],
    *,
    caps: dict[str, Any],
    order: list[int] | None = None,
    boards: dict[int, str] | None = None,
) -> dict[str, Any]:
    """Assign every PR to the earliest wave in which it may safely mutate.

    A PR joins the current mutation wave when its write claims conflict with no
    PR already admitted to that wave and the mutation-lane cap has room.
    Read-only recon for every PR and watchers for ``board=wait`` PRs run in the
    first wave up to the total cap. Nothing here launches anything; it only
    names the largest currently safe wave.
    """
    by_number = {pr["number"]: pr for pr in prs}
    sequence = order or [pr["number"] for pr in prs]
    claims = {number: write_claims(by_number[number]) for number in sequence}
    pending = list(sequence)
    mutation_waves: list[dict[str, Any]] = []
    while pending:
        admitted: list[int] = []
        blocked_claim: list[dict[str, Any]] = []
        blocked_cap: list[int] = []
        for number in pending:
            if len(admitted) >= caps["max_mutation_lanes"]:
                blocked_cap.append(number)
                continue
            clash = [other for other in admitted if _claims_conflict(claims[number], claims[other])]
            if clash:
                blocked_claim.append({"pr": number, "conflicts_with": clash})
                continue
            admitted.append(number)
        if not admitted:  # cap of zero would loop forever; fail closed instead
            raise FleetError("mutation lane cap admits nothing; check the execution profile")
        mutation_waves.append(
            {"remediate": admitted, "blocked_claim": blocked_claim, "blocked_cap": blocked_cap}
        )
        pending = [number for number in pending if number not in admitted]

    first = mutation_waves[0]
    read_budget = max(0, caps["max_parallel"] - len(first["remediate"]))
    watch = [n for n in sequence if (boards or {}).get(n) == "wait"]
    recon = [n for n in sequence if n not in first["remediate"]]
    watch_now = watch[:read_budget]
    recon_now = [n for n in recon if n not in watch_now][: max(0, read_budget - len(watch_now))]
    return {
        "caps": caps,
        "first_wave": {
            "remediate": first["remediate"],
            "recon": recon_now,
            "watch": watch_now,
            "launch_count": len(first["remediate"]) + len(recon_now) + len(watch_now),
            "blocked_claim": first["blocked_claim"],
            "blocked_cap": first["blocked_cap"],
        },
        "mutation_waves": mutation_waves,
        "wave_count": len(mutation_waves),
    }


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def _board_for(repo: str, number: int) -> dict[str, Any]:
    import pr_board  # noqa: PLC0415

    return pr_board.board_for(repo, str(number))


def plan(
    repo: str,
    *,
    with_boards: bool = False,
    surface: str | None = None,
    prior: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prs = inventory(repo)
    edges = stack_edges(prs)
    order = merge_order(prs, edges)
    overlap = overlap_matrix(prs)
    boards: dict[int, str] = {}
    verdicts: dict[str, Any] = {}
    if with_boards and prs:
        with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
            results = list(pool.map(lambda pr: _board_for(repo, pr["number"]), prs))
        for pr, verdict in zip(prs, results, strict=True):
            boards[pr["number"]] = str(verdict.get("board") or "wait")
            verdicts[str(pr["number"])] = verdict
    caps = profile_caps(surface)
    wave_plan = waves(prs, caps=caps, order=order, boards=boards) if prs else None
    stacked = {edge["child"] for edge in edges} | {edge["parent"] for edge in edges}
    conflicting = {n for item in overlap if not item["generated_only"] for n in item["prs"]}
    print_fp = fingerprint(prs)
    return {
        "repo": repo,
        "fingerprint": print_fp,
        "unchanged": bool(prior and prior.get("fingerprint") == print_fp),
        "open_prs": len(prs),
        "prs": [
            {
                **pr,
                "independent": pr["number"] not in stacked and pr["number"] not in conflicting,
                "board": boards.get(pr["number"]),
            }
            for pr in prs
        ],
        "stack_edges": edges,
        "overlap": overlap,
        "merge_order": order,
        "merge_train": [n for n in order if boards.get(n) == "merge"] if with_boards else None,
        "boards": verdicts if with_boards else None,
        "waves": wave_plan,
        "velocity": velocity_model(prs, wave_plan) if wave_plan else None,
    }


def write_receipt(payload: dict[str, Any], root: Path | None = None) -> Path:
    base = root or Path.cwd()
    path = base / RECEIPT_DIR / FLEET_RECEIPT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_receipt(root: Path | None = None) -> dict[str, Any] | None:
    path = (root or Path.cwd()) / RECEIPT_DIR / FLEET_RECEIPT
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# velocity model (a model of the v4.6 prose, not a timing)
# ---------------------------------------------------------------------------


def velocity_model(prs: list[dict[str, Any]], wave_plan: dict[str, Any]) -> dict[str, Any]:
    """Counters for the serial v4.6 hot path versus this wave plan.

    ``serial`` is derived from the prose the pack shipped with: one
    ``gh pr view --json files`` per PR and one ``gh pr view`` per PR for the
    stack probe at preflight, the same stack probe again before each merge,
    every PR remediated one at a time, and a foreground 15 s poll (32 snapshot
    cap) owned by the main agent after each publish. ``waves`` counts what this
    module does. Neither column is wall-clock; both are deterministic counts.
    """
    n = len(prs)
    first = wave_plan["first_wave"]
    pages = max(1, -(-n // PAGE_SIZE))
    fetch_rounds = max(1, -(-n // FETCH_WORKERS)) if n else 0
    return {
        "open_prs": n,
        "serial": {
            "remote_queries_preflight": 1 + 2 * n,
            "duplicate_stack_probes_at_merge": n,
            "first_wave_launched": min(n, 1),
            "first_wave_parallelism": min(n, 1),
            "main_agent_foreground_waits": n,
            "max_foreground_poll_snapshots": 32 * n,
        },
        "waves": {
            "remote_queries_preflight": pages + n,
            "remote_query_rounds_preflight": pages + fetch_rounds,
            "duplicate_stack_probes_at_merge": 0,
            "first_wave_launched": first["launch_count"],
            "first_wave_parallelism": first["launch_count"],
            "first_wave_mutators": len(first["remediate"]),
            "main_agent_foreground_waits": 0,
            "mutation_waves": wave_plan["wave_count"],
            "blocked_claim_first_wave": len(first["blocked_claim"]),
            "blocked_cap_first_wave": len(first["blocked_cap"]),
        },
    }


# ---------------------------------------------------------------------------
# assignments
# ---------------------------------------------------------------------------


def _run_id(explicit: str | None) -> str:
    return explicit or uuid.uuid4().hex[:8]


def _campaign_id(repo: str, run_id: str) -> str:
    return "pr-remediation-" + repo.replace("/", "-") + "-" + run_id


def _objective(kind: str, repo: str, pr: dict[str, Any]) -> str:
    number = pr["number"]
    head = pr["headRefOid"]
    if kind == "recon":
        return (
            f"Read-only diagnosis of {repo}#{number} at head {head}: failed required checks "
            "and their logs, every unresolved review thread (any author), code-review agent "
            "comments, cited files at this head. Record observed / expected / root cause / "
            "Unknown per finding with ownership on the edit axis. Change no files."
        )
    if kind == "watch":
        return (
            f"Observe {repo}#{number} at head {head} until mergeStateStatus is CLEAN or a "
            "required check turns red; report the terminal observation with the exact head. "
            "Never push, merge, edit, or resolve threads."
        )
    return (
        f"Remediate {repo}#{number} on branch {pr['headRefName']} from head {head}: plan every "
        "ingested finding, fix only CODEBASE clusters inside the allowed paths, run "
        "`L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo`, one commit, one `git push` "
        "of this already-open PR branch, reply to every thread with "
        "skills/l9-pr-remediation/scripts/reply_threads.py. Never merge, never force-push, "
        "never edit CI surfaces, never ask the human to unblock."
    )


def build_assignment(
    repo: str,
    pr: dict[str, Any],
    *,
    kind: str,
    run_id: str,
    graph_id: str,
) -> dict[str, Any]:
    if kind not in KINDS:
        raise FleetError(f"unknown assignment kind {kind!r}; expected one of {sorted(KINDS)}")
    role = KINDS[kind]
    number = pr["number"]
    assignment_id = f"{kind}-pr{number}-{run_id}"
    allowed = sorted(set(pr["files"]))
    if kind == "remediate":
        allowed = sorted(set(allowed) | {f"{prefix}*" for prefix in GENERATED_PATH_PREFIXES})
    packet = {
        "schema": "l9.pr-fleet.assignment.v1",
        "assignment_id": assignment_id,
        "kind": kind,
        "repo": repo,
        "pr": number,
        "head_ref": pr["headRefName"],
        "campaign_id": _campaign_id(repo, run_id),
        "graph_id": graph_id,
        "action_id": assignment_id,
        "agent_id": f"{role}-pr{number}-{run_id}",
        "parent_agent_id": "l9-pr-remediation-main",
        # Correlation key only. No root-autonomy lease exists for a fleet task;
        # the results gateway checks a root lease only when a runtime database
        # is named, so this value is never mistaken for one.
        "lease_id": f"no-root-lease-{assignment_id}",
        "base_sha": pr["headRefOid"],
        "role": role,
        "result_role": role,
        "subagent_role": role,
        "objective": _objective(kind, repo, pr),
        "input_artifact_ids": [],
        "allowed_paths": allowed,
        "forbidden_paths": list(FORBIDDEN_PATHS),
        "mutation": kind == "remediate",
        "result_kind": "PRRemediationReport" if role == ROLE_REMEDIATE else "ReconReport",
        "result_schema": RESULT_SCHEMA_PATH,
    }
    packet["cursor"] = _cursor_binding(role)
    return packet


def _cursor_binding(role: str) -> dict[str, Any]:
    """Managed Task type and background policy from their single owners."""
    try:
        from autonomy.adapters.cursor import adapter  # noqa: PLC0415

        return {
            "managed_task_type": adapter._cursor_subagent_type(role),
            "run_in_background": adapter.runs_in_background(role),
            "owner": "environment/agents/cursor-subagents/CURSOR_SUBAGENT_ROLES.yaml",
        }
    except Exception as exc:  # noqa: BLE001 - binding is advisory; report, never invent
        return {"managed_task_type": None, "run_in_background": None, "unavailable": str(exc)}


def render_prompt(packet: dict[str, Any]) -> str:
    lines = [
        "# l9-pr-remediation bounded assignment",
        "",
        f"assignment_id: {packet['assignment_id']}",
        f"repo: {packet['repo']}  pr: #{packet['pr']}  head_ref: {packet['head_ref']}",
        f"base_sha: {packet['base_sha']}",
        f"role: {packet['role']}  kind: {packet['kind']}  "
        f"mutation: {str(packet['mutation']).lower()}",
        f"campaign_id: {packet['campaign_id']}  graph_id: {packet['graph_id']}",
        f"action_id: {packet['action_id']}  agent_id: {packet['agent_id']}",
        f"lease_id: {packet['lease_id']}",
        "",
        "## Objective",
        packet["objective"],
        "",
        "## Allowed paths (exact grant; a document reporting other changed files is rejected)",
        *(f"- {path}" for path in packet["allowed_paths"]),
        "",
        "## Forbidden paths",
        *(f"- {path}" for path in packet["forbidden_paths"]),
        "",
        "## Completion",
        f"Return exactly one document conforming to {packet['result_schema']} with",
        f"result_kind {packet['result_kind']}, identity fields copied verbatim from above,",
        "files_changed truthful, validations reported as PASS/FAIL/BLOCKED/NOT_RUN, and",
        "status completed|partial|blocked|failed. Natural-language completion is invalid.",
        "Stop if the head SHA moves under you; report it as blocked.",
    ]
    return "\n".join(lines)


def write_assignment(packet: dict[str, Any], root: Path | None = None) -> Path:
    base = root or Path.cwd()
    path = base / RECEIPT_DIR / ASSIGNMENT_DIR / f"{packet['assignment_id']}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def record_lifecycle_assignment(packet: dict[str, Any], workspace: Path) -> dict[str, Any]:
    """Durable assignment receipt the results gateway loads at acceptance time."""
    from environment.agents.lifecycle import receipts  # noqa: PLC0415

    fields = {
        key: packet[key]
        for key in (
            "assignment_id",
            "campaign_id",
            "graph_id",
            "action_id",
            "agent_id",
            "parent_agent_id",
            "subagent_role",
            "result_role",
            "objective",
            "input_artifact_ids",
            "allowed_paths",
            "forbidden_paths",
            "lease_id",
            "base_sha",
        )
    }
    fields.update(
        {
            "subject_agent_id": None,
            "workspace": str(workspace),
            "repository": packet["repo"],
            "repository_class": "governed_repository",
            "surface": "cursor-ide",
        }
    )
    if receipts.assignment_path(packet["assignment_id"]).is_file():
        return receipts.load_assignment(packet["assignment_id"]) or fields
    return receipts.write_assignment(fields)


# ---------------------------------------------------------------------------
# acceptance
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise FleetError(f"unreadable {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FleetError(f"{path} is not a JSON object")
    return data


def resolve_assignment(ref: str, root: Path | None = None) -> dict[str, Any]:
    path = Path(ref)
    if not path.is_file():
        path = (root or Path.cwd()) / RECEIPT_DIR / ASSIGNMENT_DIR / f"{ref}.json"
    if not path.is_file():
        raise FleetError(f"assignment not found: {ref}")
    return _load_json(path)


def accept(
    packet: dict[str, Any],
    document: dict[str, Any],
    *,
    host_status: str = "completed",
    use_gateway: bool = True,
) -> dict[str, Any]:
    """Judge one result document against its assignment. Never infers success.

    The canonical bridge decides structural validity, identity correlation,
    role, writable scope, and read-only-role change claims. The results gateway
    then writes the durable acceptance receipt when the assignment was
    recorded. A partial, blocked, or failed document that correlates is
    accepted as evidence with its own status preserved, never as completion.
    """
    from environment.agents.results.adapters import cursor_subagent  # noqa: PLC0415

    bridge = cursor_subagent.result_bridge
    spec = {
        "campaign_id": packet["campaign_id"],
        "graph_id": packet["graph_id"],
        "action_id": packet["action_id"],
        "agent_id": packet["agent_id"],
        "lease_id": packet["lease_id"],
        "base_sha": packet["base_sha"],
        "role": packet["role"],
        "allowed_paths": list(packet["allowed_paths"]),
        "action_allowed_paths": [],
        "forbidden_paths": list(packet["forbidden_paths"]),
    }
    try:
        normalized = bridge.validate_result_against_assignment(document, spec)
    except bridge.ResultValidationError as exc:
        return {
            "status": "REJECTED",
            "reason": str(exc),
            "assignment_id": packet["assignment_id"],
            "document_status": document.get("status") if isinstance(document, dict) else None,
        }
    outcome: dict[str, Any] = {
        "status": "ACCEPTED" if normalized["status"] == "completed" else "ACCEPTED_INCOMPLETE",
        "reason": "ok",
        "assignment_id": packet["assignment_id"],
        "document_status": normalized["status"],
        "files_changed": list(normalized["deliverable"]["files_changed"]),
        "validations": list(normalized["deliverable"]["validations"]),
        "artifact_digest": normalized["provenance"]["artifact_digest"],
        "gateway": None,
    }
    if use_gateway:
        outcome["gateway"] = _gateway_accept(packet, normalized, host_status)
        gateway_status = str(outcome["gateway"].get("status") or "")
        if gateway_status == "REJECTED":
            outcome["status"] = "REJECTED"
            outcome["reason"] = str(outcome["gateway"].get("reason") or "gateway rejected")
    return outcome


def _gateway_accept(
    packet: dict[str, Any], normalized: dict[str, Any], host_status: str
) -> dict[str, Any]:
    from environment.agents.lifecycle import receipts  # noqa: PLC0415
    from environment.agents.results import gateway  # noqa: PLC0415

    if receipts.load_assignment(packet["assignment_id"]) is None:
        return {"status": "SKIPPED", "reason": "assignment not recorded; bridge verdict stands"}
    return_receipt = {
        "assignment_id": packet["assignment_id"],
        "status": "RETURNED",
        "campaign_id": packet["campaign_id"],
        "graph_id": packet["graph_id"],
        "action_id": packet["action_id"],
        "agent_id": packet["agent_id"],
        "lease_id": packet["lease_id"],
        "base_sha": packet["base_sha"],
        "parent_agent_id": packet["parent_agent_id"],
        "surface": "cursor-ide",
        "result_role": packet["result_role"],
        "host_status": host_status,
    }
    receipt = gateway.accept(return_receipt=return_receipt, surface_result=normalized)
    return {
        "status": str(receipt.get("status") or ""),
        "reason": str(receipt.get("reason") or ""),
        "result_id": receipt.get("result_id"),
        "receipt_digest": receipt.get("receipt_digest"),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return
    print(json.dumps(payload, sort_keys=True, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="inventory once, topology, waves, receipt")
    p_plan.add_argument("--repo", required=True, help="owner/name")
    p_plan.add_argument("--board", action="store_true", help="attach pr_board.py verdicts")
    p_plan.add_argument("--surface", choices=["cursor", "claude_local", "claude_cloud"])
    p_plan.add_argument("--json", action="store_true")
    p_plan.add_argument("--no-receipt", action="store_true")

    p_assign = sub.add_parser("assign", help="emit bounded assignments for a wave")
    p_assign.add_argument("--repo", required=True)
    p_assign.add_argument("--pr", type=int, action="append", default=[], help="repeatable")
    p_assign.add_argument("--kind", choices=sorted(KINDS), required=True)
    p_assign.add_argument("--run-id", default=None)
    p_assign.add_argument("--record", action="store_true", help="write lifecycle assignment")
    p_assign.add_argument("--prompt", action="store_true", help="print the Task prompt")
    p_assign.add_argument("--json", action="store_true")

    p_accept = sub.add_parser("accept", help="judge a returned result document")
    p_accept.add_argument("--assignment", required=True, help="assignment id or path")
    p_accept.add_argument("--result", required=True, type=Path)
    p_accept.add_argument("--host-status", default="completed")
    p_accept.add_argument("--no-gateway", action="store_true")
    p_accept.add_argument("--json", action="store_true")

    p_model = sub.add_parser("model", help="before/after velocity counters")
    p_model.add_argument("--repo", required=True)
    p_model.add_argument("--surface", choices=["cursor", "claude_local", "claude_cloud"])
    p_model.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            prior = load_receipt()
            payload = plan(args.repo, with_boards=args.board, surface=args.surface, prior=prior)
            if not args.no_receipt:
                payload["receipt"] = str(write_receipt(payload))
            _print(payload, args.json)
            return 0
        if args.command == "assign":
            fleet = load_receipt()
            if fleet is None or fleet.get("repo") != args.repo:
                fleet = plan(args.repo)
                write_receipt(fleet)
            by_number = {int(pr["number"]): pr for pr in fleet["prs"]}
            numbers = args.pr or [
                int(n)
                for n in (fleet.get("waves") or {})
                .get("first_wave", {})
                .get({"recon": "recon", "remediate": "remediate", "watch": "watch"}[args.kind], [])
            ]
            run_id = _run_id(args.run_id)
            packets = []
            for number in numbers:
                if number not in by_number:
                    raise FleetError(f"PR #{number} is not in the fleet receipt")
                packet = build_assignment(
                    args.repo,
                    by_number[number],
                    kind=args.kind,
                    run_id=run_id,
                    graph_id=str(fleet["fingerprint"]),
                )
                packet["path"] = str(write_assignment(packet))
                if args.record:
                    record_lifecycle_assignment(packet, Path.cwd())
                    packet["lifecycle_recorded"] = True
                if args.prompt:
                    packet["prompt"] = render_prompt(packet)
                packets.append(packet)
            _print({"run_id": run_id, "assignments": packets}, args.json)
            return 0
        if args.command == "accept":
            packet = resolve_assignment(args.assignment)
            document = _load_json(args.result)
            outcome = accept(
                packet, document, host_status=args.host_status, use_gateway=not args.no_gateway
            )
            _print(outcome, args.json)
            return 0 if outcome["status"] != "REJECTED" else 1
        if args.command == "model":
            payload = plan(args.repo, surface=args.surface)
            _print(payload.get("velocity") or {}, args.json)
            return 0
    except FleetError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
