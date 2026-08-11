"""sessionEnd close: Phase A heuristic PICKUP (≤8s) + Phase B LLM distill (≤18s)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_GRAPHITI_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _GRAPHITI_DIR.parent.parent
if str(_GRAPHITI_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPHITI_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from episode_contract import redact_pii  # noqa: E402
from group_resolver import resolve_group_id  # noqa: E402

from ops.graphiti.hydration.identity import (  # noqa: E402
    IdentityError,
    envelope_body,
    resolve_write_identity,
    stamp_source_description,
)
from ops.graphiti.hydration.transcript import load_transcript_excerpt  # noqa: E402

PHASE_A_BUDGET = 8.0
PHASE_B_BUDGET = 18.0
TOTAL_BUDGET = 30.0


def _receipt_path(project_dir: Path, session_id: str) -> Path:
    safe = re_safe(session_id)
    return project_dir / ".l9" / "memory" / "closes" / f"{safe}.json"


def re_safe(session_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]


def _load_rules() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "promotion_rules.yaml"
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def already_closed(project_dir: Path, session_id: str, head_hash: str) -> bool:
    path = _receipt_path(project_dir, session_id)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("head_hash") == head_hash or data.get("status") == "closed"


def write_receipt(project_dir: Path, session_id: str, payload: dict[str, Any]) -> None:
    path = _receipt_path(project_dir, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _git_signal(project_dir: Path) -> str:
    import subprocess

    try:
        branch = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        ).stdout.strip()
        head = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        ).stdout.strip()
        status = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        ).stdout.strip()
        dirty = len(status.splitlines()) if status else 0
        return f"branch={branch or '?'} head={head or '?'} dirty_files={dirty}"
    except (OSError, subprocess.SubprocessError):
        return "git=unavailable"


def _heuristic_pickup(
    *,
    project_dir: Path,
    session_id: str,
    transcript: str,
    reason: str,
) -> dict[str, str]:
    git = _git_signal(project_dir)
    # Last user-ish lines from transcript
    last_lines = [ln for ln in transcript.splitlines() if ln.strip()][-8:]
    slice_text = "\n".join(last_lines)[:1500]
    objective = f"Continue work in {project_dir.name}"
    next_action = "Resume from latest Graphiti PICKUP and user request"
    for ln in reversed(last_lines):
        low = ln.lower()
        if low.startswith("user:") or "user_query" in low:
            next_action = ln.split(":", 1)[-1].strip()[:400] or next_action
            break
    return {
        "active_objective": objective,
        "next_action": next_action,
        "context_slice": f"{git}\nreason={reason}\nsession={session_id}\n{slice_text}"[:3500],
        "blockers": [],
    }


def _write_kind(
    body: str,
    *,
    kind: str,
    group_id: str,
    agent_id: str,
    user_id: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    import graphiti_memory_client as gmc
    from episode_contract import EpisodeContract

    now = datetime.now(UTC)
    stamped = envelope_body(body, agent_id=agent_id, user_id=user_id, kind=kind)
    contract = EpisodeContract(
        name=f"{kind}-{group_id}-{int(now.timestamp())}",
        episode_body=stamped,
        source="json" if stamped.strip().startswith("{") else "text",
        source_description=stamp_source_description(agent_id, kind),
        reference_time=now,
        group_id=group_id,
        kind=kind,
        agent_id=agent_id,
        user_id=user_id,
    )
    payload = contract.to_mcp_payload()
    if dry_run:
        return {"written": False, "dry_run": True, "payload": payload}
    result = gmc.call_tool("add_memory", payload)
    return {"written": True, "kind": kind, "result": result}


def _distill_signal_packet(
    *,
    session_id: str,
    transcript: str,
    pickup: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any] | None, str]:
    """Return (packet, skip_reason). skip_reason empty on success."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return None, "OPENAI_API_KEY absent"
    budget_tokens = int(os.environ.get("MEMORY_DISTILL_TOKEN_BUDGET", "300"))
    rules = _load_rules()
    system = (
        "Extract durable session signals. Output ONLY JSON with keys: "
        "promotion_decisions (list of {kind, body, decision, score}), "
        "pickup ({active_objective, next_action, context_slice, blockers}), "
        "do_not_promote (list of strings). "
        "kind in lesson|insight|decision|preference|constraint; "
        "decision in promote|defer|reject. "
        "Promote only durable facts; never dump the transcript. "
        f"Max promote items: {rules.get('max_promotions_per_close', 5)}."
    )
    user = json.dumps(
        {
            "session_id": session_id,
            "heuristic_pickup": pickup,
            "transcript_excerpt": transcript[:8000],
        },
        ensure_ascii=False,
    )
    req_body = json.dumps(
        {
            "model": "gpt-4o-mini",
            "max_tokens": budget_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=req_body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=max(1.0, timeout)) as resp:  # noqa: S310
            body = json.loads(resp.read())
        text = body["choices"][0]["message"]["content"].strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        data = json.loads(text)
        if not isinstance(data, dict):
            return None, "distill returned non-object JSON"
        packet_id = hashlib.sha256(f"{session_id}:{time.time()}".encode()).hexdigest()[:16]
        return {
            "packet_id": packet_id,
            "session_id": session_id,
            "promotion_decisions": data.get("promotion_decisions") or [],
            "pickup": data.get("pickup") or pickup,
            "do_not_promote": data.get("do_not_promote") or rules.get("do_not_promote") or [],
        }, ""
    except urllib.error.HTTPError as exc:
        detail = f"openai_http_{exc.code}"
        if exc.code in (401, 403):
            detail = f"OPENAI_API_KEY rejected ({exc.code}) — Phase B skipped"
        return None, detail
    except TimeoutError:
        return None, "Phase B distill timed out — keeping Phase A"
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, IndexError, OSError) as exc:
        return None, f"Phase B distill failed ({type(exc).__name__}) — keeping Phase A"


def close_session(
    *,
    project_dir: str | Path,
    session_id: str,
    reason: str = "completed",
    transcript_path: str | None = None,
    agent_id: str | None = None,
    is_background_agent: bool = False,
    dry_run: bool = False,
    clock: Any = None,
) -> dict[str, Any]:
    """Run Phase A (+ optional Phase B). Fail-open; never raises to hooks."""
    clock = clock or time.monotonic
    started = clock()
    project = Path(project_dir).expanduser().resolve()
    session_id = session_id or "default"
    report: dict[str, Any] = {
        "status": "skipped",
        "session_id": session_id,
        "reason": reason,
        "phase_a": False,
        "phase_b": False,
        "writes": [],
        "warnings": [],
    }

    try:
        identity = resolve_write_identity(
            explicit_agent_id=agent_id,
            surface="claude-code" if (agent_id or "").startswith("claude") else "cursor",
        )
    except IdentityError as exc:
        report["warnings"].append(str(exc))
        report["status"] = "skipped"
        return report

    transcript, t_source = load_transcript_excerpt(
        transcript_path=transcript_path,
        conversation_id=session_id,
    )
    transcript = redact_pii(transcript)
    head_hash = hashlib.sha256(
        f"{session_id}:{reason}:{transcript[:2000]}:{t_source}".encode()
    ).hexdigest()[:24]

    if already_closed(project, session_id, head_hash) and not dry_run:
        report["status"] = "idempotent_skip"
        return report

    resolved = resolve_group_id(project)
    group_id = str(resolved.get("group_id") or "")
    if not group_id or resolved.get("readonly"):
        msg = str(resolved.get("error") or resolved.get("warning") or "unresolved group")
        report["warnings"].append(f"WARN: write blocked — {msg}")
        report["status"] = "skipped"
        report["skip_reason"] = msg
        return report

    if is_background_agent and not transcript:
        report["warnings"].append("background agent without transcript — Phase A git-only")

    # --- Phase A ---
    phase_a_deadline = started + PHASE_A_BUDGET
    pickup = _heuristic_pickup(
        project_dir=project,
        session_id=session_id,
        transcript=transcript,
        reason=reason,
    )
    import graphiti_memory_client as gmc

    try:
        gmc.load_env()
    except Exception as exc:  # noqa: BLE001
        report["warnings"].append(f"load_env: {exc}")

    # Pipe line first so Graphiti fact extraction indexes objective/next for hydrate.
    search_line = (
        f"PICKUP|objective={pickup['active_objective']}|next={pickup['next_action']}|"
        f"agent={identity['agent_id']}|session={session_id}"
    )
    pickup_body = (
        search_line
        + "\n"
        + json.dumps(
            {
                "type": "PICKUP",
                "active_objective": pickup["active_objective"],
                "next_action": pickup["next_action"],
                "context_slice": pickup["context_slice"],
                "session_id": session_id,
                "reason": reason,
                "agent_id": identity["agent_id"],
                "search_line": search_line,
            },
            ensure_ascii=False,
        )
    )
    summary_body = json.dumps(
        {
            "type": "session_summary",
            "session_id": session_id,
            "reason": reason,
            "transcript_source": t_source,
            "phase": "A",
            "agent_id": identity["agent_id"],
            "git": _git_signal(project),
        },
        ensure_ascii=False,
    )

    try:
        w1 = _write_kind(
            pickup_body,
            kind="pickup_context",
            group_id=group_id,
            agent_id=identity["agent_id"],
            user_id=identity["user_id"],
            dry_run=dry_run,
        )
        report["writes"].append(w1)
        w2 = _write_kind(
            summary_body,
            kind="session_summary",
            group_id=group_id,
            agent_id=identity["agent_id"],
            user_id=identity["user_id"],
            dry_run=dry_run,
        )
        report["writes"].append(w2)
        report["phase_a"] = True
        report["status"] = "phase_a"
        report["pickup"] = pickup
    except Exception as exc:  # noqa: BLE001
        report["warnings"].append(f"Phase A write failed: {exc}")
        report["status"] = "failed"
        return report

    elapsed_a = clock() - started
    if elapsed_a > PHASE_A_BUDGET:
        report["warnings"].append(f"Phase A over budget ({elapsed_a:.1f}s)")

    # --- Phase B ---
    remaining = TOTAL_BUDGET - (clock() - started)
    rules = _load_rules()
    phase_b_budget = min(PHASE_B_BUDGET, max(0.0, remaining - 1.0))
    skip_b = False
    if phase_b_budget < 3.0:
        skip_b = True
        report["warnings"].append("Phase B skipped: insufficient time budget")
    elif not os.environ.get("OPENAI_API_KEY", "").strip():
        skip_b = True
        report["warnings"].append("Phase B skipped: OPENAI_API_KEY absent")
    elif is_background_agent and not transcript:
        skip_b = True
        report["warnings"].append("Phase B skipped: background agent, no transcript")
    elif clock() > phase_a_deadline and remaining < 5:
        # still allow B if overall budget remains
        pass

    signal: dict[str, Any] | None = None
    if not skip_b:
        signal, b_reason = _distill_signal_packet(
            session_id=session_id,
            transcript=transcript or pickup["context_slice"],
            pickup=pickup,
            timeout=phase_b_budget,
        )
        if signal is None:
            report["warnings"].append(
                f"Phase B skipped: {b_reason or 'distill failed'} — keeping Phase A"
            )
        else:
            report["phase_b"] = True
            report["signal_packet_id"] = signal.get("packet_id")
            # Optionally supersede pickup with richer one
            rich = signal.get("pickup") or {}
            if rich.get("next_action") and rich.get("active_objective"):
                rich_line = (
                    f"PICKUP|objective={rich['active_objective']}|next={rich['next_action']}|"
                    f"agent={identity['agent_id']}|session={session_id}"
                )
                rich_body = (
                    rich_line
                    + "\n"
                    + json.dumps(
                        {
                            "type": "PICKUP",
                            "active_objective": rich["active_objective"],
                            "next_action": rich["next_action"],
                            "context_slice": rich.get("context_slice")
                            or pickup["context_slice"],
                            "session_id": session_id,
                            "packet_id": signal.get("packet_id"),
                            "agent_id": identity["agent_id"],
                            "search_line": rich_line,
                        },
                        ensure_ascii=False,
                    )
                )
                try:
                    report["writes"].append(
                        _write_kind(
                            rich_body,
                            kind="pickup_context",
                            group_id=group_id,
                            agent_id=identity["agent_id"],
                            user_id=identity["user_id"],
                            dry_run=dry_run,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    report["warnings"].append(f"Phase B pickup write failed: {exc}")

            promote_min = float(rules.get("promote_min_score", 0.65))
            max_promo = int(rules.get("max_promotions_per_close", 5))
            promotable = set(rules.get("promotable_kinds") or ["lesson", "insight", "decision"])
            promoted = 0
            for item in signal.get("promotion_decisions") or []:
                if promoted >= max_promo:
                    break
                if not isinstance(item, dict):
                    continue
                if item.get("decision") != "promote":
                    continue
                kind = str(item.get("kind") or "lesson")
                if kind not in promotable:
                    continue
                score = float(item.get("score") or 0)
                if score < promote_min:
                    continue
                body = str(item.get("body") or "").strip()
                if not body:
                    continue
                try:
                    report["writes"].append(
                        _write_kind(
                            body,
                            kind=kind,
                            group_id=group_id,
                            agent_id=identity["agent_id"],
                            user_id=identity["user_id"],
                            dry_run=dry_run,
                        )
                    )
                    promoted += 1
                except Exception as exc:  # noqa: BLE001
                    report["warnings"].append(f"promote {kind} failed: {exc}")
            report["status"] = "phase_a_b"
            report["promoted"] = promoted

    receipt = {
        "status": "closed",
        "session_id": session_id,
        "head_hash": head_hash,
        "group_id": group_id,
        "agent_id": identity["agent_id"],
        "phase_a": report["phase_a"],
        "phase_b": report["phase_b"],
        "write_count": len([w for w in report["writes"] if w.get("written") or w.get("dry_run")]),
        "closed_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "packet_id": report.get("signal_packet_id"),
    }
    if not dry_run:
        try:
            write_receipt(project, session_id, receipt)
        except OSError as exc:
            report["warnings"].append(f"receipt write failed: {exc}")
    report["receipt"] = receipt
    report["elapsed_s"] = round(clock() - started, 3)
    report["group_id"] = group_id
    return report
