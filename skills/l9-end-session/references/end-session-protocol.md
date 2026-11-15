<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-end-session
layer: reference
role: session_close_protocol
tags: [l9, session, handoff, memory, governance]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-11-14
auto_chain: extract-chat
--- /SKILL_META ---
-->

# /end-session — close repair walkthrough

## How a session closes (automatic, both hosts)

| Host | Event | Steps | Budget |
|---|---|---|---|
| Cursor | `sessionEnd` | 1. `graphiti-session-end.sh` → `close_session.py` (`ContinuationCapsuleV2` → governed candidate → `memory.close` → distill). 2. `governance-backup.sh` → `session_end_preserve.py` parks this conversation's authored paths on `refs/l9/preserved/session/<sid>`. | 30 s / 120 s |
| Claude Code | `SessionEnd` | `session_end_close.py`: preserve first (local, fast), then the same close under `claude-session-end`. A post-publish Stop also closes, with the handoff brief. | 60 s (host cap) |

- The authored-path ledger (`~/.cursor/l9/sessions/<sid>/authored.json`) is fed
  by Cursor `postToolUse` / `afterShellExecution` and by Claude `PostToolUse`
  (Write / Edit / MultiEdit / NotebookEdit). Preserve reads only that ledger,
  never porcelain, and never touches the worktree (rules/49 item 8).
- Every close is idempotent per transcript head. A resumed conversation has a
  new head, closes again, and supersedes its earlier continuation.
- Nothing on session end stages, commits or pushes (CANONICAL_LAW §5.1).
- The next SessionStart on either host reads the prior session's close receipt
  locally and prints `CLOSE_GAP <reason>` + `REPAIR: /end-session` when it did
  not land.

Authority: CANONICAL_LAW §5.1, §8.6, §8.9; ADR-0028 (amended 2026-09-07),
ADR-0030, ADR-0031, ADR-0032. Protocol spec: `end-session.yaml`.

---

## The repair

### 1. Repair the continuation (required)

```bash
GOV="$HOME/.cursor-governance"
PY="$GOV/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"
SID="$("$PY" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("session_id") or "")' \
  "$WS/.l9/memory/previous_opened.json" 2>/dev/null)"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli health --workspace "$WS")
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.graphiti.hydration.cli repair-write \
  --project-dir "$WS" --session-id "${SID:?no prior session}" \
  --objective "{TASK}" --next "{NEXT}" --files "{FILES}" --blocker "{BLOCKER}")
```

- No `--agent-id`, no `L9_MEMORY_AGENT_ID`: identity is derived, and a
  differing configured value is refused as identity drift.
- If health fails or the write is refused, report the gap. Do not fall back to
  `memory-bank/` or a provider write.

### 2. Durable lessons (optional)

Model-authored facts take the agent lane (ADR-0033): one `memory.write_agent`
per atomic fact on the `l9-graphite-memory` MCP server, its arguments built by
the contract builder and passed unchanged (`l9.agent_memory_write.v1`):

```bash
NS="$(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.cli resolve --workspace "$WS" \
  | "$PY" -c 'import json,sys; print(json.load(sys.stdin)["namespace"]["write_namespace_hint"])')"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.memory.agent_write build \
  --namespace "$NS" --class insight --content "{one terse fact}" --tag "{topic}")
```

The builder stamps the derived `agent:<id>` tag and a content-derived
`idempotency_key`. `memory.phase_lock` → `memory.write_governed` (add
`--task-signature`) is the optional conflict-sensitive pair; the phase lock
authorizes no file edit, commit or push. A human operator may use the operator
CLI; the model never substitutes it for the agent write.

### 3. Handoffs (only after a publication)

```bash
"$PY" "$GOV/ops/autonomy/session_debt.py" handoff --workspace "$WS" \
  --pr {PR} --objective "{TASK}" --status "{STATUS}" --next "{NEXT}"
(cd "$GOV" && PYTHONPATH="$GOV" "$PY" -m ops.reports.publish handoffs --workspace "$WS")
```

The first generates both briefs from the debt ledger; the second delivers them
(the session handoff as the PR's handoff comment, governance friction to its
intake). Nothing is committed onto the PR.

### 4. Report

```markdown
## Session close repaired
- session: {SID} — receipt {status} (write_count {n})
- lessons written: {count}
- handoffs: {delivered | not applicable — no publication}
```

## Retired — do not do

| Retired step | Why |
|---|---|
| Governance backup push (`git add -A` + `git push` of the SSOT) | Session end does not push (CANONICAL_LAW §5.1); rules/49 forbids `git add -A`; publication is `make pr` |
| Redis `cache_set_session_context` | Not a resume layer; the continuation record is the resume SSOT |
| PICKUP records / `--kind pickup_context` | Retired provider-era format; stamps no close receipt |
| `memory-bank/` writes | Retired 2026-08-11 |
| `--agent-id cursor` | Identity is derived; a configured value is refused as drift |
