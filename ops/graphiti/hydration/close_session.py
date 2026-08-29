"""sessionEnd close: Phase A heuristic PICKUP (≤8s) + Phase B LLM distill (≤18s)."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")

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
from ops.graphiti.hydration.resume_signal_scorer import (  # noqa: E402
    should_persist_derived_episode,
    signals_from_close,
)
from ops.graphiti.hydration.transcript import load_transcript_excerpt  # noqa: E402

PHASE_A_BUDGET = 8.0
PHASE_B_BUDGET = 18.0
TOTAL_BUDGET = 30.0


def re_safe(session_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)[:120]


def _closes_dir(project_dir: Path) -> str:
    """Real path to project_dir/.l9/memory/closes (must stay under project root)."""
    root_r = os.path.realpath(str(Path(project_dir).expanduser()))
    closes_r = os.path.realpath(os.path.join(root_r, ".l9", "memory", "closes"))
    if os.path.commonpath([root_r, closes_r]) != root_r:
        raise ValueError("closes directory escapes project root")
    return closes_r


def _receipt_path(project_dir: Path, session_id: str) -> str:
    """Build a receipt filesystem path under project_dir/.l9/memory/closes."""
    safe = re_safe(session_id)
    if not _SAFE_NAME.match(safe):
        raise ValueError("invalid session_id for receipt path")
    closes_r = _closes_dir(project_dir)
    path_r = os.path.realpath(os.path.join(closes_r, f"{safe}.json"))
    if os.path.commonpath([closes_r, path_r]) != closes_r:
        raise ValueError("receipt path escapes closes directory")
    return path_r


def _load_rules() -> dict[str, Any]:
    path = Path(__file__).resolve().parent / "promotion_rules.yaml"
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return {}


def already_closed(project_dir: Path, session_id: str, head_hash: str) -> bool:
    try:
        path_r = _receipt_path(project_dir, session_id)
    except ValueError:
        return False
    if not os.path.isfile(path_r):
        return False
    try:
        # path_r is commonpath-bounded under project_dir/.l9/memory/closes
        with open(path_r, encoding="utf-8") as handle:  # NOSONAR python:S2083
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("head_hash") == head_hash or data.get("status") == "closed"


def write_receipt(project_dir: Path, session_id: str, payload: dict[str, Any]) -> None:
    """Persist a close receipt with taint-safe scalars only."""
    path_r = _receipt_path(project_dir, session_id)
    os.makedirs(os.path.dirname(path_r), exist_ok=True)
    # Use the function-arg session_id (not payload) and head_hash digest only.
    # Omit reason/agent/group/enqueue error text so CodeQL password taint from
    # Phase B key handling cannot reach this storage sink.
    status = payload.get("status")
    status_out = status if status in {"closed", "closed_enqueue_failed"} else "other"
    enqueue_ok = payload.get("enqueue_ok")
    safe = {
        "status": status_out,
        "session_id": str(session_id),
        "head_hash": str(payload.get("head_hash") or ""),
        "phase_a": bool(payload.get("phase_a") is True),
        "phase_b": bool(payload.get("phase_b") is True),
        "enqueue_ok": True if enqueue_ok is True else (False if enqueue_ok is False else None),
        "enqueue_error_present": bool(payload.get("enqueue_error")),
        "write_count": int(payload.get("write_count") or 0),
        "closed_at": str(payload.get("closed_at") or "")[:64],
    }
    # path_r is commonpath-bounded under project_dir/.l9/memory/closes
    with open(path_r, "w", encoding="utf-8") as handle:  # NOSONAR python:S2083
        handle.write(json.dumps(safe, indent=2, ensure_ascii=False) + "\n")


def _git_signal(project_dir: Path) -> str:
    """Project basename only — no git filesystem reads (avoids path-injection sinks)."""
    name = Path(project_dir).name
    if not _SAFE_NAME.match(name):
        name = "project"
    return f"project={name}"


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


def _phase_b_enabled() -> bool:
    return os.environ.get("MEMORY_PHASE_B", "1").strip() not in ("0", "false", "False")


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    cleaned = text.strip("`")
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].strip()
    return cleaned


def _distill_signal_packet(
    *,
    session_id: str,
    transcript: str,
    pickup: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any] | None, str]:
    """Return (packet, skip_reason). skip_reason empty on success.

    Uses the Sonar-reviewed fixed-host OpenAI helper
    (``ops.graphiti.hydration.openai_fixed_host``) — never builds a URL from
    caller input. Key: env or ephemeral SM resolve (opaque skip codes only).
    """
    if not _phase_b_enabled():
        return None, "MEMORY_PHASE_B=0"

    from ops.graphiti.hydration.openai_fixed_host import (
        OpenAIFixedHostError,
        chat_completions,
        message_content,
    )
    from ops.graphiti.hydration.openai_key import resolve_openai_api_key

    key, key_reason = resolve_openai_api_key()
    if not key:
        return None, key_reason or "openai_key_absent"

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
    try:
        resp = chat_completions(
            api_key=key,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=budget_tokens,
            timeout=max(1.0, timeout),
        )
        data = json.loads(_strip_code_fence(message_content(resp)))
        if not isinstance(data, dict):
            return None, "distill_non_object_json"
        packet_id = hashlib.sha256(f"{session_id}:{time.time()}".encode()).hexdigest()[:16]
        return {
            "packet_id": packet_id,
            "session_id": session_id,
            "promotion_decisions": data.get("promotion_decisions") or [],
            "pickup": data.get("pickup") or pickup,
            "do_not_promote": data.get("do_not_promote") or rules.get("do_not_promote") or [],
        }, ""
    except OpenAIFixedHostError as exc:
        # Opaque codes only — never interpolate exception text (may be secret-adjacent).
        code = exc.args[0] if exc.args else "phase_b_transport"
        if code in {"openai_http_401", "openai_http_403", "openai_timeout"}:
            return None, f"phase_b_{code}"
        return None, "phase_b_transport"
    except (KeyError, json.JSONDecodeError, IndexError, OSError, TypeError) as exc:
        return None, f"phase_b_{type(exc).__name__}"


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
        "enqueue_ok": None,
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
    if not _phase_b_enabled():
        skip_b = True
        report["warnings"].append("Phase B skipped: MEMORY_PHASE_B=0")
    elif phase_b_budget < 3.0:
        skip_b = True
        report["warnings"].append("Phase B skipped: insufficient time budget")
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
            session_signals = signals_from_close(
                transcript=transcript,
                reason=reason,
                promotion_decisions=signal.get("promotion_decisions") or [],
            )
            persist_derived = should_persist_derived_episode(session_signals, rules)
            if not persist_derived:
                report["warnings"].append("derived resume episode dropped: low resume signal")
            if rich.get("next_action") and rich.get("active_objective") and persist_derived:
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
                            "context_slice": rich.get("context_slice") or pickup["context_slice"],
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

            promoted = 0
            if persist_derived:
                promote_min = float(rules.get("promote_min_score", 0.65))
                max_promo = int(rules.get("max_promotions_per_close", 5))
                promotable = set(rules.get("promotable_kinds") or ["lesson", "insight", "decision"])
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

    # --- S3 distill enqueue (redacted excerpt; fail-loud when enabled+configured) ---
    enqueue_result: dict[str, Any] | None = None
    try:
        from ops.graphiti.distill_queue.enqueue import (
            bucket_configured,
            enqueue_enabled,
            enqueue_job,
        )

        if not enqueue_enabled():
            if os.environ.get("MEMORY_DISTILL_ENQUEUE", "1").strip() in (
                "0",
                "false",
                "False",
            ):
                report["enqueue_ok"] = None
                report["warnings"].append("distill enqueue skipped: MEMORY_DISTILL_ENQUEUE=0")
            elif not bucket_configured():
                report["enqueue_ok"] = None
                report["warnings"].append("distill enqueue skipped: MEMORY_DISTILL_S3_BUCKET unset")
        elif not (transcript or "").strip():
            report["enqueue_ok"] = None
            report["warnings"].append("distill enqueue skipped: empty transcript excerpt")
        else:
            enqueue_result = enqueue_job(
                session_id=session_id,
                group_id=group_id,
                agent_id=identity["agent_id"],
                transcript_excerpt=transcript,
                heuristic_pickup=pickup,
                reason=reason,
                project_name=project.name,
                dry_run=dry_run,
            )
            report["enqueue_ok"] = True
            report["enqueue"] = {
                "key": enqueue_result.get("key"),
                "content_hash": enqueue_result.get("content_hash"),
                "dry_run": bool(enqueue_result.get("dry_run")),
            }
    except Exception as exc:  # noqa: BLE001
        report["enqueue_ok"] = False
        code = f"enqueue_{type(exc).__name__}"
        report["enqueue_error"] = code
        report["warnings"].append(f"ERROR: distill enqueue failed: {code}")
        print(f"ERROR: distill enqueue failed: {code}", file=sys.stderr)

    receipt = {
        "status": "closed",
        "session_id": session_id,
        "head_hash": head_hash,
        "group_id": group_id,
        "agent_id": identity["agent_id"],
        "phase_a": report["phase_a"],
        "phase_b": report["phase_b"],
        "enqueue_ok": report.get("enqueue_ok"),
        "enqueue": report.get("enqueue"),
        "enqueue_error": report.get("enqueue_error"),
        "write_count": len([w for w in report["writes"] if w.get("written") or w.get("dry_run")]),
        "closed_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "packet_id": report.get("signal_packet_id"),
    }
    if report.get("enqueue_ok") is False:
        receipt["status"] = "closed_enqueue_failed"
    if not dry_run:
        try:
            write_receipt(project, session_id, receipt)
        except (OSError, ValueError) as exc:
            report["warnings"].append(f"receipt write failed: {exc}")
    report["receipt"] = receipt
    report["elapsed_s"] = round(clock() - started, 3)
    report["group_id"] = group_id
    return report
