# Cursor SessionStart banner — what it promises

The banner is emitted by [`ops/hooks/session_start_bootstrap.sh`](../../../../ops/hooks/session_start_bootstrap.sh)
as `additional_context`. This spec is the contract a reader (human or agent)
may rely on. It does not define a second activation path (`AGENTS.md` §2, §20)
— it documents the one that exists.

## Sections, in order

| Section | Producer | Promise |
|---|---|---|
| `### Governance` | bootstrap hook | tip sha, activation action, wiring PASS/FAIL, backup arming |
| `### Runtime` | [`ops/scripts/session_start_runtime_report.py`](../../../../ops/scripts/session_start_runtime_report.py) | one line per component: `name: class — summary`; class is `ok`, `n/a`, `degraded`, or `failed` |
| `### Degraded` | same reporter | **only** this-session, this-surface, actionable faults; `- none` on a healthy day |
| `### Graphiti hydrate` | `compile_session_packet.py` via the memory orchestrator | packet id, objective, `next=`, stats, packet JSON fence |
| `### Code-graph` | orchestrator | indexed or skipped |
| `### Plan audit` | `skills/l9-pipeline-audit` | pending counts + NEXT 1–3, display-only |

## Degraded-section semantics (the honesty rules)

1. **Hydrate is classified from the packet booleans**, by
   [`ops/scripts/classify_hydrate_state.py`](../../../../ops/scripts/classify_hydrate_state.py):
   `degraded: true` (packet or `hydrate_stats`) and
   `hydrate_stats.close_gap: true` are the only packet positives. The healthy
   fence's literal `"degraded": false` text MUST never flip the flag — no
   substring or shell-glob classification.
2. **Receipts carry surface identity.** A bootstrap receipt whose `workspace`
   is not this session's git root (or is `$HOME`) renders as
   `stale_other_surface` under `### Runtime` with class `n/a`, and never
   enters `### Degraded`.
3. **Cursor never scores Claude.** Under `L9_GOVERNANCE_SURFACE=cursor` the
   `claude-adapter` row is `n/a` (CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1), and
   Claude observer hooks (`memory_prefetch.py`) no-op without a Claude
   runtime marker — a Cursor session contains zero `agent_id=claude-code`
   hydrate blocks.
4. **`n/a` is never a fault.** Missing optional wiring (no cursor receipt,
   no skill-usage log, no local Neo4j) is `n/a` with the reason named.
5. **Silence is never health.** A probe that produced no verdict is `failed`
   with "probe unread", not omitted.

## The bar

A healthy boot prints `### Degraded` followed by `- none`. Every line above
it is true, evidenced, and about this session on this surface.
