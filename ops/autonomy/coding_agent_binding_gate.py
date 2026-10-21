#!/usr/bin/env python3
"""Coding-agent canonical-binding gate (PreToolUse, file mutations).

The ``l9-coding-agent`` skill requires a verified canonical invariant binding
before its first mutation and lets only an explicit user instruction, recorded
verbatim, carry a run past an Unknown (``integrations/L9_RUNTIME_BINDING.yaml``
``unknown_handling``). This gate makes that law mechanical for the file tools
while a coding-agent run is active, so the governance binding can say
``blocks_mutation: true`` truthfully.

The gate trusts no label it can be handed. Every file under the run directory
is agent-writable, so a record that merely *says* ``BOUND`` releases nothing:
the gate re-runs the pack verifier against the record, the committed bundle and
the pinned authority checkout, and allows only on a live ``CURRENT`` verdict.
A reauthorization is likewise not a field in a writable file: it is the
operator-controlled hook environment, which an agent cannot set for the hook
process mid-session.

State contract (written by the skill at intake, removed at convergence):

``<workspace>/.l9/coding-agent/run.json``  ``l9.coding-agent-run/v1``
    {"schema", "started_at", "binding_record": "binding.json",
     "authority_root": "<exact Quantum-L9/.github checkout the binding used>"}
``<workspace>/.l9/coding-agent/binding.json``
    the record ``skills/l9-coding-agent/scripts/verify_canonical_binding.py``
    printed in ``--bundle`` mode (it names the bundle and the pinned revision).

Decision:

* no ``run.json`` above the mutated path: no coding-agent run is active; allow.
* a write inside ``.l9/coding-agent/`` while a run is active: deny (the record
  is the verifier's output and the run state is closed by deleting it, both
  outside the file tools).
* ``L9_CODING_BINDING_REAUTHORIZED=<the user's verbatim instruction>`` in the
  hook environment: allow; the receipt must carry that text.
* the verifier, re-run on the record, the bundle and the pinned authority
  checkout, returns ``CURRENT``: allow.
* anything else, including a malformed event, run or record, an absent
  authority checkout, or a verifier that cannot run: deny, naming the fix.

Operator breakglass (human/ops only, a reason, never a bare flag):
``L9_CODING_BINDING_AUTHORIZED=<reason>``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GOV_ROOT = Path(__file__).resolve().parents[2]
VERIFIER = GOV_ROOT / "skills" / "l9-coding-agent" / "scripts" / "verify_canonical_binding.py"
RUN_DIR = Path(".l9") / "coding-agent"
RUN_FILE = "run.json"
RECORD_FILE = "binding.json"
RUN_SCHEMA = "l9.coding-agent-run/v1"
VERIFIER_PREFIX = "l9-coding-agent/"
BOUND_STATUSES = frozenset({"BOUND", "CURRENT"})
MUTATING_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
BREAKGLASS_ENV = "L9_CODING_BINDING_AUTHORIZED"
REAUTHORIZED_ENV = "L9_CODING_BINDING_REAUTHORIZED"
BARE_FLAGS = frozenset({"1", "true", "yes", "y", "on"})
VERIFIER_TIMEOUT_S = 120
SKILL_LAW = (
    "skills/l9-coding-agent: a verified canonical invariant binding precedes mutation "
    "(RUNBOOK step 4; L9_RUNTIME_BINDING unknown_handling)"
)
REBIND_HINT = (
    "Re-bind: run scripts/verify_canonical_binding.py --bundle <bundle> --authority-root "
    "<.github checkout> --expect-revision <pin>, save its output unchanged as {record}, and "
    "name that checkout as authority_root in {run}. Only the operator may carry the run past an "
    f"Unknown, with {REAUTHORIZED_ENV}=<the user's instruction verbatim> in the hook environment."
)

Reverify = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str
    run: str | None = None


def mutated_path(tool_name: str, tool_input: Any) -> Path | None:
    if not isinstance(tool_input, dict):
        return None
    for key in ("file_path", "notebook_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value.strip():
            return Path(value)
    return None


def locate_run(start: Path) -> Path | None:
    """The nearest ``.l9/coding-agent/run.json`` at or above *start*."""
    current = start.resolve()
    seen: set[Path] = set()
    while current not in seen:
        seen.add(current)
        candidate = current / RUN_DIR / RUN_FILE
        if candidate.is_file():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _meaningful(value: str | None) -> str:
    """A reason or an instruction; a bare yes-flag is neither."""
    text = str(value or "").strip()
    return "" if text.lower() in BARE_FLAGS else text


def reverify(
    *,
    record_path: Path,
    bundle: Path,
    authority_root: Path,
    revision: str,
    verifier: Path = VERIFIER,
) -> dict[str, Any]:
    """Re-run the pack verifier on the prior record; its verdict is the decision.

    The verifier reads law bytes from the pinned commit's objects with recomputed
    hashes, checks the committed bundle bytes and receipts against them, and
    compares the prior record's digests. A fabricated record, a changed bundle,
    or a moved authority cannot come back ``CURRENT``.
    """
    if not verifier.is_file():
        return {"status": "BLOCKED", "reason": "VERIFIER_UNRESOLVED", "verifier": str(verifier)}
    argv = [
        sys.executable,
        str(verifier),
        "--authority-root",
        str(authority_root),
        "--bundle",
        str(bundle),
        "--expect-revision",
        revision,
        "--prior-binding",
        str(record_path),
    ]
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=VERIFIER_TIMEOUT_S,
            check=False,
            env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1"},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"status": "BLOCKED", "reason": "VERIFIER_DID_NOT_RUN", "error": repr(exc)}
    try:
        verdict = json.loads(proc.stdout or "")
    except ValueError:
        return {
            "status": "BLOCKED",
            "reason": "VERIFIER_OUTPUT_UNRESOLVED",
            "exit": proc.returncode,
            "stderr": (proc.stderr or "")[-400:],
        }
    if not isinstance(verdict, dict):
        return {
            "status": "BLOCKED",
            "reason": "VERIFIER_OUTPUT_UNRESOLVED",
            "exit": proc.returncode,
        }
    return verdict


def evaluate(
    tool_name: str,
    tool_input: Any,
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    reverify_fn: Reverify = reverify,
) -> Decision:
    env = os.environ if env is None else env
    if tool_name not in MUTATING_TOOLS:
        return Decision(True, "not a file mutation")
    breakglass = _meaningful(env.get(BREAKGLASS_ENV))
    if breakglass:
        return Decision(True, f"operator breakglass: {breakglass}")

    target = mutated_path(tool_name, tool_input)
    anchor = target if target is not None else cwd
    if not anchor.is_absolute():
        anchor = cwd / anchor
    run_path = locate_run(anchor.parent if target is not None else anchor)
    if run_path is None:
        return Decision(True, "no active coding-agent run")
    run_dir = run_path.parent
    run_hint = REBIND_HINT.format(record=run_dir / RECORD_FILE, run=run_path)

    reauthorized = _meaningful(env.get(REAUTHORIZED_ENV))
    if reauthorized:
        return Decision(
            True,
            "the operator recorded the user's explicit reauthorization of this run with the "
            f"binding Unknown ({REAUTHORIZED_ENV}); the receipt must carry it verbatim",
            run=str(run_path),
        )

    if target is not None:
        try:
            anchor.resolve().relative_to(run_dir.resolve())
            return Decision(
                False,
                f"{run_dir} holds the run state of an active coding-agent run; the binding record "
                "is the verifier's own output and the run is closed by deleting run.json, neither "
                f"through a file tool. {SKILL_LAW}.",
                run=str(run_path),
            )
        except ValueError:
            pass

    try:
        run = _load(run_path)
    except (OSError, ValueError) as exc:
        return Decision(
            False,
            f"{run_path} is unreadable ({exc}); a coding-agent run is active but its state is "
            f"Unknown. {SKILL_LAW}. Rewrite it from intake or remove it if no run is active.",
            run=str(run_path),
        )
    if not isinstance(run, dict) or run.get("schema") != RUN_SCHEMA:
        return Decision(
            False,
            f"{run_path} is not {RUN_SCHEMA}; the active coding-agent run has no valid state. "
            f"{SKILL_LAW}. Rewrite it from intake or remove it if no run is active.",
            run=str(run_path),
        )

    record_rel = run.get("binding_record") or RECORD_FILE
    record_path = (run_dir / str(record_rel)).resolve()
    try:
        record = _load(record_path)
    except (OSError, ValueError) as exc:
        return Decision(
            False,
            f"no verified canonical binding for the active coding-agent run ({record_path}: "
            f"{exc}). {SKILL_LAW}. {run_hint}",
            run=str(run_path),
        )
    if not isinstance(record, dict):
        return Decision(
            False, f"{record_path} is not a binding record. {run_hint}", run=str(run_path)
        )
    status = record.get("status")
    verifier_name = str(record.get("verifier", ""))
    if status not in BOUND_STATUSES or not verifier_name.startswith(VERIFIER_PREFIX):
        reason = record.get("reason")
        return Decision(
            False,
            f"the active coding-agent run's canonical binding is {status or 'absent'}"
            f"{f' ({reason})' if reason else ''}, not BOUND or CURRENT from {VERIFIER_PREFIX}*. "
            f"{SKILL_LAW}. {run_hint}",
            run=str(run_path),
        )

    bundle_field = record.get("bundle")
    authority_field = record.get("authority_root")
    bundle_raw = bundle_field.get("path") if isinstance(bundle_field, dict) else None
    revision = authority_field.get("revision") if isinstance(authority_field, dict) else None
    if not bundle_raw or not isinstance(revision, str) or len(revision) != 40:
        return Decision(
            False,
            f"{record_path} is not a bundle-bound record (no bundle path or pinned revision), so "
            f"it cannot be re-verified. {run_hint}",
            run=str(run_path),
        )
    workspace = run_dir.parent.parent
    bundle = Path(str(bundle_raw))
    if not bundle.is_absolute():
        bundle = workspace / bundle
    authority_raw = run.get("authority_root")
    if not isinstance(authority_raw, str) or not authority_raw.strip():
        return Decision(
            False,
            f"{run_path} names no authority_root, so the binding cannot be re-verified. {run_hint}",
            run=str(run_path),
        )
    authority_root = Path(authority_raw)
    if not authority_root.is_absolute():
        authority_root = workspace / authority_root
    if not authority_root.is_dir():
        return Decision(
            False,
            f"authority_root {authority_root} is not a directory; the binding's authority is not "
            f"observable. {run_hint}",
            run=str(run_path),
        )

    verdict = reverify_fn(
        record_path=record_path,
        bundle=bundle,
        authority_root=authority_root,
        revision=revision,
    )
    live = verdict.get("status")
    if live == "CURRENT":
        return Decision(
            True,
            f"canonical binding CURRENT (re-verified: {verdict.get('reason')})",
            run=str(run_path),
        )
    detail = {k: v for k, v in verdict.items() if k not in {"status", "reason", "verifier"}}
    return Decision(
        False,
        f"the active coding-agent run's canonical binding did not re-verify: {live or 'Unknown'} "
        f"{verdict.get('reason') or ''} {json.dumps(detail, sort_keys=True)[:300]}. "
        f"{SKILL_LAW}. {run_hint}",
        run=str(run_path),
    )


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"coding-agent binding gate: {reason}",
                }
            }
        )
    )


def main(stdin: Any = None) -> int:
    try:
        event = json.load(stdin or sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        _deny(
            f"the PreToolUse event is not JSON ({exc}); a gate that cannot read its event cannot "
            f"evaluate it. Operator override: {BREAKGLASS_ENV}=<reason>."
        )
        return 0
    if not isinstance(event, dict):
        _deny(
            "the PreToolUse event is not an object; a gate that cannot read its event cannot "
            f"evaluate it. Operator override: {BREAKGLASS_ENV}=<reason>."
        )
        return 0
    cwd_raw = str(event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    decision = evaluate(
        str(event.get("tool_name", "")),
        event.get("tool_input") or {},
        cwd=Path(cwd_raw),
    )
    if not decision.allow:
        _deny(decision.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
