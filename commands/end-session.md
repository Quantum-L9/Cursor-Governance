---
name: end-session
description: Repair a session close that did not land (SessionStart printed CLOSE_GAP) — canonical repair-write, never a push
---

# /end-session — repair a missed session close

**Normal session ends need nothing.** Both hosts close automatically:

| Host | Event | What runs |
|---|---|---|
| Cursor | `sessionEnd` | `graphiti-session-end.sh` closes the continuation; `governance-backup.sh` → `session_end_preserve.py` parks this conversation's authored paths on `refs/l9/preserved/session/<sid>` |
| Claude Code | `SessionEnd` | `session_end_close.py`: the same preserve, then the same close under `claude-session-end` |

A resumed conversation closes again and **supersedes** its earlier continuation.
Nothing on session end stages, commits or pushes (CANONICAL_LAW §5.1).

This command is the **repair** for a close that did not land. Skill:
[`skills/l9-end-session/SKILL.md`](../skills/l9-end-session/SKILL.md). Map:
[`docs/MEMORY_PIPELINE_MAP.md`](../docs/MEMORY_PIPELINE_MAP.md),
[ADR-0028](../docs/decisions/ADR-0028-session-hydrate-close-visibility.md).

## When to use

- SessionStart printed `CLOSE_GAP <reason>` and `REPAIR: /end-session` (both
  hosts read the prior session's close receipt locally).
- You know the automatic close failed or was killed (Claude Code caps SessionEnd
  at 60 s).

Not for `DEGRADED` (memory did not answer) or `ENVIRONMENT_FAULT` (runtime
unbound): those are `make memory-readiness`, not a close repair (ADR-0032).

## Execution

### 1 — Repair the continuation (required)

```bash
GOV="$HOME/.cursor-governance"
PY="$GOV/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
PRIOR="$WS/.l9/memory/previous_opened.json"
SID="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("session_id") or "")' "$PRIOR" 2>/dev/null)"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli health --workspace "$WS")
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.graphiti.hydration.cli repair-write \
  --project-dir "$WS" --session-id "${SID:?no prior session in previous_opened.json}" \
  --objective "{TASK}" --next "{NEXT}" --files "{FILES}" --blocker "{BLOCKER}")
```

- `repair-write` is the only close-gap repair: it writes the canonical
  continuation **and** stamps the close receipt. `ops.memory.cli write` does
  neither and is not this step.
- Do **not** pass `--agent-id` or set `L9_MEMORY_AGENT_ID`. Identity is derived
  from host markers (`ops/memory/agent_identity.py`); a value that differs from
  the derived one is refused as identity drift.
- A receipt already `closed_canonically` is skipped unless `--supersede`.

### 2 — Durable lessons (optional)

One atomic fact per write, built by the contract builder and passed unchanged to
the `l9-graphite-memory` MCP tool (`l9.agent_memory_write.v1`):

```bash
NS="$(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli resolve --workspace "$WS" \
  | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["namespace"]["write_namespace_hint"])')"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.agent_write build \
  --namespace "$NS" --class insight --content "{one terse fact}" --tag "{topic}")
```

→ `memory.write_agent` with exactly those arguments. Use `memory.phase_lock` →
`memory.write_governed` only for a conflict-sensitive fact.

### 3 — Handoffs (only after a publication)

Generate both briefs from the debt ledger (record friction first with
`session_debt.py friction`), then deliver them:

```bash
"$PY" "$GOV/ops/autonomy/session_debt.py" handoff --workspace "$WS" \
  --pr {PR} --objective "{TASK}" --status "{STATUS}" --next "{NEXT}"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.reports.publish handoffs --workspace "$WS")
```

### 4 — Report

Name the repaired session id, the receipt status after the repair, the lesson
count, and whether handoffs were delivered.

## Never

- `git add -A`, a commit of foreign paths, or any push. Unpublished work is
  already parked by the session-end preserve; publish with `make pr`.
- The governance backup script from this command (that is `/governance-backup`,
  an explicit operator action).
- `memory-bank/`, PICKUP records, Redis session context — all retired.
