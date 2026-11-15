---
name: l9-end-session
description: repair a session close that did not land — canonical repair-write of the continuation record (receipt stamped) plus optional governed lesson writes. use when SessionStart printed CLOSE_GAP or the automatic sessionEnd / SessionEnd close failed. never pushes; not required for a normal session end.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, session, handoff, memory, governance, control-plane, force-retry]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-11-14
---

# End Session (close repair)

## Purpose

**Session close is automatic on both hosts.** Cursor `sessionEnd` runs
`ops/hooks/graphiti-session-end.sh` → `ops/graphiti/hydration/close_session.py`
and parks the conversation's authored paths (`ops/scripts/session_end_preserve.py`).
Claude Code `SessionEnd` runs
`environment/agents/adapters/claude-code/hooks/session_end_close.py`: the same
preserve, then the same close under the `claude-session-end` envelope. A resumed
conversation closes again and supersedes its earlier continuation.

Use this skill only to **repair** a close that did not land: SessionStart printed
`CLOSE_GAP <reason>` with `REPAIR: /end-session`, or the automatic close was
killed or failed. A close-gap is a **lifecycle** condition (ADR-0032).
`DEGRADED` (memory did not answer) and `ENVIRONMENT_FAULT` (runtime unbound) are
repaired with `make memory-readiness`, not here. See ADR-0028 (as amended
2026-09-07), ADR-0030 and ADR-0032; map:
[`docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md).

Slash command entry: [`commands/end-session.md`](../../commands/end-session.md)
— it carries the exact commands; this skill carries the contract.

## Mandatory preload

Load [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md) first:

- Use the governance `.venv` interpreter, never bare `python3`.
- Identity is **derived** from host markers (`ops/memory/agent_identity.py`).
  Never pass `--agent-id` or set `L9_MEMORY_AGENT_ID`: a value that differs from
  the derived identity is refused as identity drift, and a Claude surface can
  never stamp the Cursor identity.
- `repair-write` is a deterministic adapter over the same `MemoryService` the
  hooks use. Model-authored lessons are MCP writes on `l9-graphite-memory`:
  `memory.write_agent` (ordinary, no `phase_lock`) or `memory.phase_lock` →
  `memory.write_governed` (conflict-sensitive), with arguments built by
  `python -m ops.memory.agent_write build` and passed unchanged
  (`l9.agent_memory_write.v1`, ADR-0031, CANONICAL_LAW §8.5).

## Core contract

`CLOSE_GAP → HEALTH → repair-write (continuation + receipt) → optional lesson
writes → handoffs (only after a publication) → report`

- **Target:** the prior session named in `.l9/memory/previous_opened.json`.
- **Primary:** `ops.graphiti.hydration.cli repair-write`. It writes the
  canonical continuation and stamps the close receipt. `ops.memory.cli write`
  stamps nothing and is not a repair; `hydration.cli close` is the hook closer,
  not the repair (ADR-0028 Option C rejected).
- **Idempotent:** a receipt already `closed_canonically` is skipped unless
  `--supersede`.
- **Handoffs:** `session_debt.py handoff` generates both briefs from the debt
  ledger; `python -m ops.reports.publish handoffs` delivers them (PR comment and
  governance friction intake). Nothing is committed onto the PR
  (`ops/memory/HANDOFF_CONTRACT.md`).

## Never

- Stage, commit or push anything. Session end does not push (CANONICAL_LAW
  §5.1); unpublished work is already parked on
  `refs/l9/preserved/session/<sid>`, and publication is `make pr`.
- Run the governance backup script as part of this repair (that is
  `/governance-backup`, an explicit operator action).
- Write `memory-bank/`, PICKUP records or a Redis session context (retired), or
  a provider directly.

## Authority order

1. ADR-0030 — one memory control plane (interactive write contract, items 7–9)
2. ADR-0028 (amended 2026-09-07) — hydrate/close visibility and canonical repair
3. `docs/MEMORY_PIPELINE_MAP.md` — live close path
4. `ops/graphiti/hydration/pickup_write.py` — `repair_close`
5. `ops/graphiti/hydration/close_session.py` — the automatic closer (both hosts)
6. [`l9-graphiti-memory`](../l9-graphiti-memory/SKILL.md) — interpreter, flags, writes

## Failure handling

| Symptom | Action |
|---------|--------|
| No `previous_opened.json` / empty session id | No prior session to repair; report and stop |
| Receipt already `closed_canonically` | Skip unless superseding deliberately |
| `identity drift` / `no memory identity` | Remove any `--agent-id` / `L9_MEMORY_AGENT_ID`; the host must be identifiable |
| `No module named 'yaml'` | Use `$GOV/.venv/bin/python` |
| Memory runtime unbound (`BINDING_FAILED`) | `make -C "$GOV" memory-binding`; report the gap — no memory-bank, no provider write |

When blocked: state the exact gap, label it `Unknown`, give the smallest next action.

Reference walkthrough: [`references/end-session-protocol.md`](references/end-session-protocol.md).
