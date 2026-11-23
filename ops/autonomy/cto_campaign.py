#!/usr/bin/env python3
"""CTO campaign state, check-in tick and operator-decision ledger.

A CTO session coordinating a swarm used to keep campaign state in scratchpad
prose and re-send all of it in every check-in prompt; superseded prompts kept
firing, every check-in rediscovered PR heads and CI from scratch, operator
questions were lost to worker restarts, and operator decisions lived in a
markdown file copied into child briefs by hand. This tool moves that state into
files and reduces each check-in to one command that prints only what changed.

Files (under <workspace>/.l9/cto-mode/, gitignored local state):

  campaign.json      l9.cto-campaign/v1   governance/cto-mode/schemas/campaign.schema.json
  decisions.json     l9.cto-decisions/v1  governance/cto-mode/schemas/decisions.schema.json
  tick-snapshot.json last observed PR state, the baseline the next tick diffs against

Commands:

  init                      create campaign.json
  pool set | pool show      record / show the agent pool
  lane set                  update one lane's state and PRs
  tick [--json]             observe every campaign PR over REST and print the delta
  tick --checkin-text       print the fixed check-in prompt (no network)
  decide ask|answer|pending|brief|show

Everything here is advisory. It never merges, pushes or publishes, holds no
lock (rules/96 E7/E8/E10), and every JSON output carries
"grants_permission": false. Merge readiness is pr_board.py's verdict, merge is
stack_safe_merge.py --run, and git plus the PR gates remain the enforcement.
Telemetry that cannot be read stays explicit as UNKNOWN; it is never coerced
into a state.

Exit codes: 0 success, 1 state or telemetry error, 2 usage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

CAMPAIGN_SCHEMA = "l9.cto-campaign/v1"
DECISIONS_SCHEMA = "l9.cto-decisions/v1"
TICK_SCHEMA = "l9.cto-campaign-tick/v1"
SNAPSHOT_SCHEMA = "l9.cto-campaign-snapshot/v1"
TRAIN_SCHEMA = "l9.cto-train/v1"

STATE_REL = Path(".l9") / "cto-mode"
SCHEMA_DIR = _ROOT / "governance" / "cto-mode" / "schemas"
SCHEMA_FILES = {
    CAMPAIGN_SCHEMA: SCHEMA_DIR / "campaign.schema.json",
    DECISIONS_SCHEMA: SCHEMA_DIR / "decisions.schema.json",
}

# Lane B's classifier. Absent until that lane merges; tick degrades explicitly.
TRIAGE_TOOL = _HERE / "ci_triage.py"
TRIAGE_TIMEOUT_S = 120

DEFAULT_CADENCE_MIN = 10
POOL_STATES = (
    "unassigned",
    "assigned",
    "working",
    "question",
    "blocked",
    "ready-to-merge",
    "idle",
    "stood-down",
    "unknown",
)

POOL_REMINDER = (
    "pool: session status is MCP-only -- merge list_sessions(children: true) output "
    "with `cto_campaign.py pool show` before acting"
)


class CampaignError(RuntimeError):
    """State is missing, invalid or contradictory. Exit 1, never a guess."""


# --------------------------------------------------------------------------
# files


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def state_dir(workspace: Path) -> Path:
    return workspace / STATE_REL


def campaign_path(workspace: Path) -> Path:
    return state_dir(workspace) / "campaign.json"


def decisions_path(workspace: Path) -> Path:
    return state_dir(workspace) / "decisions.json"


def snapshot_path(workspace: Path) -> Path:
    return state_dir(workspace) / "tick-snapshot.json"


def default_train_path(workspace: Path) -> Path:
    return state_dir(workspace) / "train.json"


def _validator(schema_id: str) -> Any:
    from jsonschema import Draft202012Validator

    path = SCHEMA_FILES[schema_id]
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError(f"schema {path} unreadable: {exc}") from exc
    return Draft202012Validator(schema)


def validate(document: Any, schema_id: str) -> None:
    """Raise CampaignError naming every violation; nothing invalid is written or used."""
    errors = sorted(_validator(schema_id).iter_errors(document), key=lambda e: list(e.path))
    if errors:
        detail = "; ".join(
            f"{'/'.join(str(p) for p in err.path) or '<root>'}: {err.message}" for err in errors
        )
        raise CampaignError(f"{schema_id} invalid: {detail}")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError(f"{path} unreadable: {exc}") from exc


def _write_json(path: Path, document: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_campaign(workspace: Path) -> dict[str, Any]:
    path = campaign_path(workspace)
    try:
        document = _read_json(path)
    except FileNotFoundError as exc:
        raise CampaignError(f"no campaign at {path}; run `cto_campaign.py init`") from exc
    validate(document, CAMPAIGN_SCHEMA)
    return document


def save_campaign(workspace: Path, document: dict[str, Any]) -> None:
    document["updated_at"] = now_iso()
    validate(document, CAMPAIGN_SCHEMA)
    _write_json(campaign_path(workspace), document)


def load_decisions(workspace: Path) -> dict[str, Any]:
    path = decisions_path(workspace)
    try:
        document = _read_json(path)
    except FileNotFoundError:
        return {"schema": DECISIONS_SCHEMA, "grants_permission": False, "decisions": []}
    validate(document, DECISIONS_SCHEMA)
    return document


def save_decisions(workspace: Path, document: dict[str, Any]) -> None:
    validate(document, DECISIONS_SCHEMA)
    _write_json(decisions_path(workspace), document)


# --------------------------------------------------------------------------
# campaign + pool


def init_campaign(
    workspace: Path,
    *,
    campaign: str,
    cto_session: str,
    repos: Sequence[str],
    train: str | None,
    cadence_min: int,
    force: bool,
) -> dict[str, Any]:
    path = campaign_path(workspace)
    if path.exists() and not force:
        raise CampaignError(f"{path} exists; pass --force to replace it")
    document: dict[str, Any] = {
        "schema": CAMPAIGN_SCHEMA,
        "grants_permission": False,
        "campaign": campaign,
        "cto_session": cto_session,
        "repos": list(dict.fromkeys(repos)),
        "pool": [],
        "train": train,
        "checkin": {"cadence_min": cadence_min, "last_tick_at": None, "last_digest": None},
        "updated_at": now_iso(),
    }
    save_campaign(workspace, document)
    return document


def pool_set(
    workspace: Path,
    *,
    agent: str,
    session: str | None,
    lane: str | None,
    state: str | None,
    prs: Sequence[int] | None,
    repo: str | None,
) -> dict[str, Any]:
    """Upsert one pool entry by agent; fields not given keep their value."""
    document = load_campaign(workspace)
    entry = next((e for e in document["pool"] if e["agent"] == agent), None)
    if entry is None:
        if not session:
            raise CampaignError(f"new pool agent {agent!r} needs --session")
        entry = {"agent": agent, "session": session, "lane": None, "state": "unassigned", "prs": []}
        document["pool"].append(entry)
    if session:
        entry["session"] = session
    if lane is not None:
        entry["lane"] = lane or None
    if state is not None:
        entry["state"] = state
    if prs is not None:
        entry["prs"] = list(dict.fromkeys(prs))
    if repo is not None:
        entry["repo"] = repo
    save_campaign(workspace, document)
    return entry


def lane_set(
    workspace: Path,
    *,
    lane: str,
    state: str | None,
    prs: Sequence[int] | None,
    add_prs: Sequence[int],
) -> dict[str, Any]:
    document = load_campaign(workspace)
    matches = [e for e in document["pool"] if e["lane"] == lane]
    if not matches:
        raise CampaignError(f"no pool agent holds lane {lane!r}; assign it with `pool set`")
    if len(matches) > 1:
        agents = ", ".join(e["agent"] for e in matches)
        raise CampaignError(f"lane {lane!r} is held by several agents ({agents}); use `pool set`")
    entry = matches[0]
    if state is not None:
        entry["state"] = state
    if prs is not None:
        entry["prs"] = list(dict.fromkeys(prs))
    if add_prs:
        entry["prs"] = list(dict.fromkeys([*entry["prs"], *add_prs]))
    save_campaign(workspace, document)
    return entry


def render_pool(document: dict[str, Any]) -> str:
    lines = [f"campaign {document['campaign']} (cto {document['cto_session']})"]
    if not document["pool"]:
        lines.append("pool: empty")
    for entry in document["pool"]:
        prs = ",".join(f"#{n}" for n in entry["prs"]) or "-"
        lines.append(
            f"  {entry['agent']}  lane={entry['lane'] or '-'}  state={entry['state']}  "
            f"prs={prs}  session={entry['session']}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# tick


def load_train(workspace: Path, campaign: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    """The lane A train manifest when present. A named-but-unreadable train is an error."""
    named = campaign.get("train")
    path = Path(named).expanduser() if named else default_train_path(workspace)
    if named and not path.is_absolute():
        path = workspace / path
    if not path.exists():
        if named:
            raise CampaignError(f"campaign names train {path}, which does not exist")
        return None, ""
    document = _read_json(path)
    if not isinstance(document, dict) or document.get("schema") != TRAIN_SCHEMA:
        raise CampaignError(f"{path} is not a {TRAIN_SCHEMA} document")
    return document, str(path)


def campaign_prs(campaign: dict[str, Any], train: dict[str, Any] | None) -> list[tuple[str, int]]:
    """Every (repo, pr) the campaign tracks, in stable order. Ambiguity is an error."""
    targets: list[tuple[str, int]] = []
    single = campaign["repos"][0] if len(campaign["repos"]) == 1 else None
    for entry in campaign["pool"]:
        repo = entry.get("repo") or single
        if entry["prs"] and not repo:
            raise CampaignError(
                f"pool agent {entry['agent']!r} lists PRs but the campaign spans several "
                "repositories; set the entry's repo with `pool set --repo`"
            )
        targets.extend((str(repo), int(n)) for n in entry["prs"])
    if train is not None:
        repo = str(train.get("repo") or single or "")
        numbers = [p.get("number") for p in train.get("prs") or [] if isinstance(p, dict)]
        if numbers and not repo:
            raise CampaignError("train lists PRs but names no repo")
        targets.extend((repo, int(n)) for n in numbers if isinstance(n, int))
    return sorted(dict.fromkeys(targets))


def _gh_api(path: str) -> Any:
    proc = subprocess.run(
        ["gh", "api", "--method", "GET", path],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0:
        raise CampaignError(f"gh api {path} failed: {(proc.stderr or proc.stdout).strip()[:300]}")
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError as exc:
        raise CampaignError(f"gh api {path} emitted non-JSON: {exc}") from exc


def fetch_pull(repo: str, pr: int) -> dict[str, Any]:
    """REST pull facts: state, merged, head sha, mergeable_state."""
    payload = _gh_api(f"repos/{repo}/pulls/{pr}")
    if not isinstance(payload, dict):
        raise CampaignError(f"REST pull {repo}#{pr} emitted no object")
    head = str(((payload.get("head") or {}).get("sha")) or "")
    if not head:
        raise CampaignError(f"REST pull {repo}#{pr} reported no head sha")
    merged = bool(payload.get("merged")) or bool(payload.get("merged_at"))
    state = "merged" if merged else str(payload.get("state") or "unknown")
    return {
        "state": state,
        "head": head,
        "mergeable_state": str(payload.get("mergeable_state") or "unknown"),
        "draft": bool(payload.get("draft")),
        "merge_commit": str(payload.get("merge_commit_sha") or "") if merged else "",
    }


def board_verdict(repo: str, pr: int) -> dict[str, Any]:
    """pr_board.py's verdict, reused rather than re-derived. Unknown degrades to wait."""
    import pr_board

    return pr_board.board_for(repo, str(pr))


def triage_available() -> bool:
    return TRIAGE_TOOL.is_file()


def triage(repo: str, pr: int, head: str) -> dict[str, dict[str, str]]:
    """Lane B's ci_triage classify, by its frozen CLI. Failure stays explicit."""
    argv = [
        sys.executable,
        str(TRIAGE_TOOL),
        "classify",
        "--repo",
        repo,
        "--pr",
        str(pr),
        "--sha",
        head,
        "--json",
    ]
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, check=False, timeout=TRIAGE_TIMEOUT_S
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CampaignError(f"ci_triage failed: {exc}") from exc
    if proc.returncode != 0:
        raise CampaignError(f"ci_triage exited {proc.returncode}: {proc.stderr.strip()[:300]}")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CampaignError(f"ci_triage emitted non-JSON: {exc}") from exc
    result: dict[str, dict[str, str]] = {}
    for check in payload.get("checks") or [] if isinstance(payload, dict) else []:
        if isinstance(check, dict) and check.get("name"):
            result[str(check["name"])] = {
                "verdict": str(check.get("verdict") or "unknown"),
                "owner_hint": str(check.get("owner_hint") or ""),
                "evidence": str(check.get("evidence") or "")[:200],
            }
    return result


def observe(repo: str, pr: int) -> dict[str, Any]:
    """One PR's state. Every unreadable fact is recorded as UNKNOWN, never guessed."""
    key = f"{repo}#{pr}"
    try:
        pull = fetch_pull(repo, pr)
    except CampaignError as exc:
        return {"key": key, "state": "unknown", "error": str(exc)}
    obs: dict[str, Any] = {"key": key, **pull, "board": None, "failing": [], "pending": []}
    if pull["state"] != "open":
        return obs
    verdict = board_verdict(repo, pr)
    obs["board"] = str(verdict.get("board") or "wait")
    obs["board_reason"] = str(verdict.get("reason") or "")
    obs["failing"] = sorted(str(n) for n in verdict.get("failing_required") or [])
    obs["pending"] = sorted(str(n) for n in verdict.get("pending_required") or [])
    if obs["failing"]:
        if not triage_available():
            obs["triage"] = {"available": False}
        else:
            try:
                classified = triage(repo, pr, pull["head"])
            except CampaignError as exc:
                obs["triage"] = {"available": True, "error": str(exc)}
            else:
                missing = {"verdict": "unknown", "owner_hint": "", "evidence": "not classified"}
                obs["triage"] = {
                    "available": True,
                    "checks": {name: classified.get(name, missing) for name in obs["failing"]},
                }
    return obs


def digest(observations: dict[str, dict[str, Any]]) -> str:
    """Digest of the decision-relevant state; prose reasons are excluded on purpose."""
    relevant = {
        key: {k: v for k, v in obs.items() if k not in {"board_reason"}}
        for key, obs in observations.items()
    }
    blob = json.dumps(relevant, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _short(sha: str) -> str:
    return sha[:7] if sha else "?"


def _triage_text(obs: dict[str, Any], name: str) -> str:
    tri = obs.get("triage") or {}
    if not tri.get("available", False):
        return "triage=UNAVAILABLE (ci_triage.py absent)"
    if tri.get("error"):
        return f"triage=UNKNOWN ({tri['error']})"
    check = (tri.get("checks") or {}).get(name) or {}
    text = f"triage={check.get('verdict', 'unknown')}"
    if check.get("owner_hint"):
        text += f" owner={check['owner_hint']}"
    return text


def delta(prev: dict[str, dict[str, Any]], cur: dict[str, dict[str, Any]]) -> list[str]:
    """One line per change between two snapshots. Identical snapshots give []."""
    lines: list[str] = []
    for key in sorted(set(prev) | set(cur)):
        old, new = prev.get(key), cur.get(key)
        if new is None:
            lines.append(f"DROPPED {key} no longer tracked by the campaign")
            continue
        if new.get("state") == "unknown":
            if old is None or old.get("error") != new.get("error"):
                lines.append(f"UNKNOWN {key} {new.get('error', 'telemetry unavailable')}")
            continue
        if old is None or old.get("state") == "unknown":
            lines.append(
                f"NEW {key} {new['state']} head {_short(new['head'])} "
                f"board={new.get('board') or '-'} mergeable={new['mergeable_state']}"
            )
            lines.extend(
                f"RED {key} '{name}' at {_short(new['head'])} {_triage_text(new, name)}"
                for name in new.get("failing") or []
            )
            continue
        if old["state"] != new["state"]:
            if new["state"] == "merged":
                lines.append(
                    f"MERGED {key} head {_short(new['head'])} "
                    f"merge {_short(new.get('merge_commit', ''))}"
                )
            else:
                lines.append(f"STATE {key} {old['state']} -> {new['state']}")
        if old["head"] != new["head"]:
            lines.append(f"HEAD {key} {_short(old['head'])} -> {_short(new['head'])}")
        if new["state"] != "open":
            continue
        if old.get("board") != new.get("board"):
            reason = new.get("board_reason") or ""
            lines.append(
                f"BOARD {key} {old.get('board') or '-'} -> {new.get('board')}"
                + (f" ({reason})" if reason else "")
            )
        if old.get("mergeable_state") != new.get("mergeable_state"):
            lines.append(f"MERGEABLE {key} {old['mergeable_state']} -> {new['mergeable_state']}")
        old_red = set(old.get("failing") or []) if old["head"] == new["head"] else set()
        for name in new.get("failing") or []:
            if name not in old_red:
                head = _short(new["head"])
                lines.append(f"RED {key} '{name}' at {head} {_triage_text(new, name)}")
        if old["head"] == new["head"]:
            for name in sorted(old_red - set(new.get("failing") or [])):
                lines.append(f"CLEARED {key} '{name}'")
    return lines


def load_snapshot(workspace: Path, expected_digest: str | None) -> dict[str, dict[str, Any]]:
    """The previous tick's observations, only when they match the recorded digest."""
    if not expected_digest:
        return {}
    try:
        document = _read_json(snapshot_path(workspace))
    except (FileNotFoundError, CampaignError):
        return {}
    if not isinstance(document, dict) or document.get("digest") != expected_digest:
        return {}
    observations = document.get("observations")
    return observations if isinstance(observations, dict) else {}


def checkin_text(workspace: Path) -> str:
    py = "$HOME/.cursor-governance/.venv/bin/python"
    script = "$HOME/.cursor-governance/ops/autonomy/cto_campaign.py"
    return f'CTO check-in: run "{py}" "{script}" tick --workspace {workspace} and act on its delta.'


def tick(
    workspace: Path,
    *,
    observer: Callable[[str, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    campaign = load_campaign(workspace)
    train, train_path = load_train(workspace, campaign)
    targets = campaign_prs(campaign, train)
    observe_fn = observer or observe
    observations = {f"{repo}#{pr}": observe_fn(repo, pr) for repo, pr in targets}
    previous_digest = campaign["checkin"]["last_digest"]
    current = digest(observations)
    baseline = load_snapshot(workspace, previous_digest)
    lines = [] if current == previous_digest else delta(baseline, observations)
    if current != previous_digest and not lines and previous_digest is not None:
        # The digest moved but the recorded baseline was lost or tampered with.
        lines = [f"BASELINE {len(observations)} PR(s) re-observed; previous snapshot unavailable"]

    campaign["checkin"]["last_tick_at"] = now_iso()
    campaign["checkin"]["last_digest"] = current
    save_campaign(workspace, campaign)
    _write_json(
        snapshot_path(workspace),
        {"schema": SNAPSHOT_SCHEMA, "digest": current, "observations": observations},
    )
    return {
        "schema": TICK_SCHEMA,
        "grants_permission": False,
        "campaign": campaign["campaign"],
        "train": train_path or None,
        "changed": bool(lines),
        "digest": current,
        "previous_digest": previous_digest,
        "lines": lines,
        "observations": observations,
        "triage_available": triage_available(),
        "reminder": POOL_REMINDER,
        "checkin_text": checkin_text(workspace),
        "ticked_at": campaign["checkin"]["last_tick_at"],
    }


# --------------------------------------------------------------------------
# decisions


def _find(document: dict[str, Any], decision_id: str) -> dict[str, Any] | None:
    return next((d for d in document["decisions"] if d["id"] == decision_id), None)


def parse_option(raw: str) -> dict[str, str]:
    key, sep, text = raw.partition(":")
    if not sep or not key.strip() or not text.strip():
        raise CampaignError(f"--option must be KEY:text, got {raw!r}")
    return {"key": key.strip(), "text": text.strip()}


def render_question(decision: dict[str, Any]) -> str:
    lines = [f"{decision['id']} — {decision['question']}"]
    for index, option in enumerate(decision["options"], start=1):
        mark = " (recommended)" if option["key"] == decision.get("recommended") else ""
        lines.append(f"  {index}. {option['key']}: {option['text']}{mark}")
    example = decision.get("recommended") or decision["options"][0]["key"]
    lines.append(f'Reply with the option key, e.g. "{decision["id"]}: {example}".')
    return "\n".join(lines)


def decide_ask(
    workspace: Path,
    *,
    decision_id: str,
    question: str,
    options: Sequence[str],
    recommended: str | None,
    supersedes: str | None,
) -> dict[str, Any]:
    document = load_decisions(workspace)
    if _find(document, decision_id) is not None:
        raise CampaignError(f"decision {decision_id} already exists")
    parsed = [parse_option(raw) for raw in options]
    keys = [o["key"] for o in parsed]
    if not parsed:
        raise CampaignError("a decision needs at least one --option")
    if len(set(keys)) != len(keys):
        raise CampaignError(f"duplicate option keys: {keys}")
    if recommended is not None and recommended not in keys:
        raise CampaignError(f"--recommended {recommended!r} is not an option key {keys}")
    if supersedes is not None:
        prior = _find(document, supersedes)
        if prior is None:
            raise CampaignError(f"--supersedes {supersedes} names no decision")
        if prior["state"] == "superseded":
            raise CampaignError(f"{supersedes} is already superseded")
        if prior["state"] == "pending":
            # The old question is withdrawn; its replacement is asked instead.
            prior["state"] = "superseded"
            prior["superseded_by"] = decision_id
    decision = {
        "id": decision_id,
        "asked_at": now_iso(),
        "question": question,
        "options": parsed,
        "recommended": recommended,
        "state": "pending",
        "answer": None,
        "answered_at": None,
        "supersedes": supersedes,
    }
    document["decisions"].append(decision)
    save_decisions(workspace, document)
    return decision


def decide_answer(
    workspace: Path,
    *,
    decision_id: str,
    answer: str,
    note: str | None,
    free: bool,
) -> dict[str, Any]:
    document = load_decisions(workspace)
    decision = _find(document, decision_id)
    if decision is None:
        raise CampaignError(f"no decision {decision_id}")
    if decision["state"] != "pending":
        raise CampaignError(f"{decision_id} is {decision['state']}, not pending")
    keys = [o["key"] for o in decision["options"]]
    if answer not in keys and not free:
        raise CampaignError(
            f"answer {answer!r} is not an option key {keys}; pass --free to record free text"
        )
    decision["state"] = "answered"
    decision["answer"] = answer
    decision["answered_at"] = now_iso()
    if note:
        decision["note"] = note
    if decision.get("supersedes"):
        prior = _find(document, decision["supersedes"])
        if prior is not None and prior["state"] == "answered":
            prior["state"] = "superseded"
            prior["superseded_by"] = decision_id
    save_decisions(workspace, document)
    return decision


def pending(workspace: Path) -> list[dict[str, Any]]:
    return [d for d in load_decisions(workspace)["decisions"] if d["state"] == "pending"]


def _answer_text(decision: dict[str, Any]) -> str:
    option = next((o for o in decision["options"] if o["key"] == decision["answer"]), None)
    return f"{option['key']} — {option['text']}" if option else str(decision["answer"])


def brief_block(workspace: Path) -> str:
    """Answered, in-force decisions as one verbatim block for child briefs."""
    answered = [d for d in load_decisions(workspace)["decisions"] if d["state"] == "answered"]
    lines = [
        "OPERATOR DECISIONS (verbatim from decisions.json; binding on this lane; "
        "a superseded decision is omitted):"
    ]
    if not answered:
        lines.append("(none recorded)")
    for decision in answered:
        lines.append(f"{decision['id']} [{decision['answered_at']}] {decision['question']}")
        lines.append(f"  Answer: {_answer_text(decision)}")
        if decision.get("note"):
            lines.append(f"  Note: {decision['note']}")
        if decision.get("supersedes"):
            lines.append(f"  Supersedes: {decision['supersedes']}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# CLI


def _emit(payload: dict[str, Any]) -> None:
    print(json.dumps({**payload, "grants_permission": False}, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cto_campaign.py", description=(__doc__ or "").split("\n", 1)[0]
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="create campaign.json")
    p_init.add_argument("--campaign", required=True)
    p_init.add_argument("--cto-session", required=True)
    p_init.add_argument("--repo", action="append", required=True, help="owner/name (repeatable)")
    p_init.add_argument("--train", default=None, help="path to train.json (l9.cto-train/v1)")
    p_init.add_argument("--cadence-min", type=int, default=DEFAULT_CADENCE_MIN)
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--json", action="store_true")

    p_pool = sub.add_parser("pool", help="agent pool")
    pool_sub = p_pool.add_subparsers(dest="pool_command", required=True)
    p_pset = pool_sub.add_parser("set", help="upsert one pool agent")
    p_pset.add_argument("--agent", required=True)
    p_pset.add_argument("--session")
    p_pset.add_argument("--lane")
    p_pset.add_argument("--state", choices=POOL_STATES)
    p_pset.add_argument("--pr", type=int, action="append", dest="prs")
    p_pset.add_argument("--repo")
    p_pset.add_argument("--json", action="store_true")
    p_pshow = pool_sub.add_parser("show", help="print the pool")
    p_pshow.add_argument("--json", action="store_true")

    p_lane = sub.add_parser("lane", help="lane state")
    lane_sub = p_lane.add_subparsers(dest="lane_command", required=True)
    p_lset = lane_sub.add_parser("set", help="update one lane")
    p_lset.add_argument("--lane", required=True)
    p_lset.add_argument("--state", choices=POOL_STATES)
    p_lset.add_argument("--pr", type=int, action="append", dest="prs", help="replace PR list")
    p_lset.add_argument("--add-pr", type=int, action="append", default=[], dest="add_prs")
    p_lset.add_argument("--json", action="store_true")

    p_tick = sub.add_parser("tick", help="observe campaign PRs and print only the delta")
    p_tick.add_argument("--json", action="store_true")
    p_tick.add_argument(
        "--checkin-text", action="store_true", help="print the fixed check-in prompt and exit"
    )

    p_dec = sub.add_parser("decide", help="operator decision ledger")
    dec_sub = p_dec.add_subparsers(dest="decide_command", required=True)
    p_ask = dec_sub.add_parser("ask", help="record a question; prints the text to send")
    p_ask.add_argument("--id", required=True, dest="decision_id")
    p_ask.add_argument("--question", required=True)
    p_ask.add_argument("--option", action="append", required=True, dest="options")
    p_ask.add_argument("--recommended")
    p_ask.add_argument("--supersedes")
    p_ask.add_argument("--json", action="store_true")
    p_ans = dec_sub.add_parser("answer", help="record the operator's answer")
    p_ans.add_argument("--id", required=True, dest="decision_id")
    p_ans.add_argument("--answer", required=True)
    p_ans.add_argument("--note")
    p_ans.add_argument("--free", action="store_true", help="accept an answer outside the options")
    p_ans.add_argument("--json", action="store_true")
    p_pend = dec_sub.add_parser("pending", help="re-print every unanswered question")
    p_pend.add_argument("--json", action="store_true")
    p_brief = dec_sub.add_parser("brief", help="answered decisions as a child-brief block")
    p_brief.add_argument("--json", action="store_true")
    p_show = dec_sub.add_parser("show", help="print the whole ledger as JSON")
    p_show.add_argument("--json", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
    workspace = args.workspace.expanduser().resolve()
    json_out = bool(getattr(args, "json", False))
    if args.command == "init":
        document = init_campaign(
            workspace,
            campaign=args.campaign,
            cto_session=args.cto_session,
            repos=args.repo,
            train=args.train,
            cadence_min=args.cadence_min,
            force=args.force,
        )
        if json_out:
            _emit({"campaign": document, "path": str(campaign_path(workspace))})
        else:
            print(f"initialized {campaign_path(workspace)}")
        return 0
    if args.command == "pool":
        if args.pool_command == "set":
            entry = pool_set(
                workspace,
                agent=args.agent,
                session=args.session,
                lane=args.lane,
                state=args.state,
                prs=args.prs,
                repo=args.repo,
            )
            if json_out:
                _emit({"pool_entry": entry})
            else:
                print(json.dumps(entry, sort_keys=True))
            return 0
        document = load_campaign(workspace)
        if json_out:
            _emit({"campaign": document["campaign"], "pool": document["pool"]})
        else:
            print(render_pool(document))
        return 0
    if args.command == "lane":
        entry = lane_set(
            workspace, lane=args.lane, state=args.state, prs=args.prs, add_prs=args.add_prs
        )
        if json_out:
            _emit({"pool_entry": entry})
        else:
            print(json.dumps(entry, sort_keys=True))
        return 0
    if args.command == "tick":
        if args.checkin_text:
            text = checkin_text(workspace)
            if json_out:
                _emit({"checkin_text": text})
            else:
                print(text)
            return 0
        result = tick(workspace)
        if json_out:
            _emit(result)
        elif result["lines"]:
            print("\n".join(result["lines"]))
            print(result["reminder"])
        return 0
    if args.command == "decide":
        command = args.decide_command
        if command == "ask":
            decision = decide_ask(
                workspace,
                decision_id=args.decision_id,
                question=args.question,
                options=args.options,
                recommended=args.recommended,
                supersedes=args.supersedes,
            )
            text = render_question(decision)
            if json_out:
                _emit({"decision": decision, "text": text})
            else:
                print(text)
            return 0
        if command == "answer":
            decision = decide_answer(
                workspace,
                decision_id=args.decision_id,
                answer=args.answer,
                note=args.note,
                free=args.free,
            )
            if json_out:
                _emit({"decision": decision})
            else:
                print(f"{decision['id']} answered: {_answer_text(decision)}")
            return 0
        if command == "pending":
            open_items = pending(workspace)
            if json_out:
                _emit({"pending": open_items, "text": [render_question(d) for d in open_items]})
            elif open_items:
                print("\n\n".join(render_question(d) for d in open_items))
            return 0
        if command == "brief":
            block = brief_block(workspace)
            if json_out:
                _emit({"brief": block})
            else:
                print(block)
            return 0
        _emit(load_decisions(workspace))
        return 0
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except CampaignError as exc:
        print(f"cto_campaign: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
