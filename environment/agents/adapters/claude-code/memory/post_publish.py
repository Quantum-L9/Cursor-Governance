"""Post-publish Stop-hook state shared by the two handoff hooks.

Two Stop hooks run IN PARALLEL after a publication (Claude Code runs every
matching hook concurrently):

* ``memory_writeback.py`` — the repository handoff, closed into the in-scope
  repository's continuation; it alone may block the Stop to request both
  handoffs (concurrent ``decision: block`` outputs have no documented merge).
* ``governance_handoff_writeback.py`` — the governance handoff, written to the
  ``cursor-governance`` namespace only; it never blocks.

Both must agree on WHICH publication is this session's and on each one's
once-only ledger, so that logic lives here and nowhere else. Each hook keeps
its own ledger directory: they run concurrently, so neither may read the
other's ledger as a signal.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

import memory_state as st

#: The publish receipt written by ``make pr`` (ops/scripts/write_pr_summary.py).
PR_SUMMARY_REL = Path(".l9") / "pr" / "pr-summary.json"


def safe(key: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in key)[:180]


def ledger(root: Path, rel: Path, key: str) -> dict:
    try:
        return json.loads((root / rel / f"{safe(key)}.json").read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_ledger(root: Path, rel: Path, key: str, fields: dict, *, who: str) -> None:
    path = root / rel / f"{safe(key)}.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {**ledger(root, rel, key), **fields, "publication": key, "updated_at": time.time()}
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", "utf-8")
    except OSError as exc:
        print(f"{who}: ledger not written ({type(exc).__name__})", file=sys.stderr)


def prefetch_receipt(contract: dict, receipt_id: str) -> dict:
    try:
        data = json.loads(st.receipt_path(contract, receipt_id).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def prefetch_started_at(contract: dict, receipt_id: str) -> float:
    try:
        return float(prefetch_receipt(contract, receipt_id).get("created_at") or 0)
    except (TypeError, ValueError):
        return 0.0


def publication(root: Path, started_at: float) -> dict[str, Any] | None:
    """This session's newest publication in ``root``, or None.

    The publish receipt must post-date this session's prefetch — a container can
    outlive a session, and an earlier session's publication is not this one's
    to hand off.
    """
    path = root / PR_SUMMARY_REL
    try:
        if path.stat().st_mtime < started_at:
            return None
        summary = json.loads(path.read_text(encoding="utf-8"))
        number = int(summary["number"])
        repo = str(summary["repo"])
        head_sha = str(summary.get("head_sha") or "")
        head = str(summary.get("head") or "")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
    return {
        "key": f"{repo}#{number}@{head_sha[:12]}",
        "repo": repo,
        "number": number,
        "url": str(summary.get("url") or ""),
        "label": f"{repo}#{number}",
        # The PR head branch and commit: where the handoff reports are pushed
        # (ops/reports/publish.py refuses any other checked-out branch).
        "head": head,
        "head_sha": head_sha,
    }


def publish_report(
    publisher: str, root: Path, pub: dict, lines: list[str], *, brief: Any = None, **meta: str
) -> str:
    """Deliver one end-session handoff and return its announcement line.

    ``publisher`` names the ``ops.reports.publish`` function
    (``publish_session_handoff`` / ``publish_governance_handoff``); the import
    happens here, after the hook made the governance tree importable. A
    governance ``brief`` is turned into friction-intake items here. Nothing is
    committed or pushed: the session handoff becomes the PR's handoff comment
    and governance friction goes to the Cursor-Governance intake.

    Fail-open: a Stop hook must never die on a report. The returned line is
    appended to the hook's announcement so the outcome is never silent.
    """
    try:
        from ops.reports import handoff_delivery
        from ops.reports import publish as reports

        extra: dict[str, Any] = dict(meta)
        if brief is not None:
            extra["friction"] = handoff_delivery.friction_items(brief)
        path, result = getattr(reports, publisher)(root, pub, lines, **extra)
        return "• " + result.line([path], root)
    except Exception as exc:  # noqa: BLE001 - reported in the announcement, never silent
        return f"• report NOT published ({type(exc).__name__}: {str(exc)[:200]})"


def is_subagent(event: dict) -> bool:
    """A subagent / background run never closes or hands off the parent session."""
    if event.get("is_background_agent") or event.get("isBackgroundAgent"):
        return True
    return str(event.get("agent_type") or event.get("agentType") or "").lower() == "subagent"


def session_roots(contract: dict, receipt_id: str, fallback: Any, workspace: Path) -> list[Path]:
    """Repositories this session put in scope, else ``fallback(workspace)``.

    ``roots`` records the roots SessionStart selected (``hydrated_roots`` on a
    receipt written before SessionStart became health-only), so reusing it
    keeps the post-publish end symmetric with SessionStart. An absent or
    malformed session receipt is an ordinary state, not an error.
    """
    receipt = prefetch_receipt(contract, receipt_id)
    roots = [Path(r) for r in (receipt.get("roots") or receipt.get("hydrated_roots") or [])]
    roots = [r for r in roots if str(r) and r.is_dir()]
    return roots or list(fallback(workspace))


def emit(message: str) -> None:
    """Stop-hook output: a user-visible message that does not continue the turn."""
    print(json.dumps({"systemMessage": message}, ensure_ascii=False))
