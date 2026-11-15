# ADR-0029: Surface-hook divergence (shared brain upstream)

## Status

Accepted

## Date

2026-09-04

## Context

Cursor SessionStart and Claude Code SessionStart already diverge (AGENTS.md
`CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1`). Cursor also loads the projected
`.claude/settings.json` triad in this repository, so Claude adapter observers
and Claude-only gates can be invoked from a Cursor session unless host identity
is resolved before dispatch.

The live bug was not a missing Cursor launcher. It was duplicate surface
identity logic downstream of the canonical detector: `memory_prefetch.py`,
`session_start_claude_governance.sh`, and `execution_profile.classify()` each
carried or implied their own Claude predicate. A projected
`L9_GOVERNANCE_SURFACE=claude-code` could therefore make Cursor look like
Claude even though `CURSOR_AGENT` was present.

CANONICAL_LAW §2.1 requires shared capability in `ops/` with adapters wrapping
outward. Host identity and lifecycle meaning therefore belong upstream; adapter
hooks bind platform events only.

## Decision

### 1. Surface identity has one SSOT

`ops/autonomy/surface_detect.py` and its shell twin
`ops/scripts/lib/surface_detect.sh` are authoritative. Consumers must use the
existing `detect_surface` / `is_claude_gate_surface` (or shell twin) helpers and
must not maintain private marker lists.

Locked precedence, copied from the live detector and tests:

1. `CURSOR_AGENT` set **and** explicit `L9_GOVERNANCE_SURFACE` in
   `{claude-code, claude-code-remote}` → `cursor`. The projected Claude triad
   must not steal a Cursor session.
2. Else an explicit id in
   `{cursor, claude-code, claude-code-remote, codex, gemini, manus}` → that id.
3. Else `CLAUDE_CODE_REMOTE=true` → `claude-code-remote`.
4. Else `CLAUDECODE` or `CLAUDE_CODE_ENTRYPOINT` or
   `CLAUDE_CODE_SESSION_ID` → `claude-code`.
5. Else `CURSOR_AGENT` → `cursor`.
6. Else → `unknown`.

`unknown` gates run, fail-toward-closed. `unknown` Claude observers skip so they
cannot inject `agent_id=claude-code` into an unidentified host.

### 2. Launcher divergence is observer-class plus a named gate table

`l9_hook_exec.sh` is the Claude adapter choke point.

- **Observers:** all Claude adapter observers skip unless
  `l9_is_claude_gate_surface` is true. Cursor, Codex, Gemini, Manus, and unknown
  do not receive Claude observer output.
- **Claude-only gates:** only `local_execution_gate_wrap.py` and
  `memory_gate.py` skip on a known non-Claude surface.
- **Shared gates:** `merge_gate_wrap.py` and `session_debt_wrap.py` remain
  active. They are not added to the Claude-only skip set.
- **Unknown:** gates still evaluate; observers skip.
- `L9_SURFACE_GUARD=0` retains the diagnostic pre-guard behavior.

This is intentionally not the broader rule “all gate-class hooks no-op outside
Claude.” That statement is false for the live launcher.

### 3. Surface identity and execution personality are separate decisions

`detect_surface` answers which host surface is active. It does not map 1:1 to
execution personality.

`execution_profile.classify()` first asks `detect_surface` whether the session
is on a Claude gate surface. Only then does the execution-profile policy use
`cloud_env` / `cloud_value` (`CLAUDE_CODE_REMOTE=true`) to choose
`claude_cloud` versus `claude_local`.

Therefore `L9_GOVERNANCE_SURFACE=claude-code` plus
`CLAUDE_CODE_REMOTE=true` is valid as surface id `claude-code` with personality
`claude_cloud`. No fourth personality is introduced; Codex, Gemini, Manus, and
unknown retain the constrained `cursor` personality.

### 4. Hydration honesty is shared upstream

Claude prefetch classifies the emitted `additional_context` markdown with
`ops/scripts/classify_hydrate_state.py` after `compile_and_format`. Packet
booleans, not substring matches, decide degradation, so a healthy JSON fence
containing `"degraded": false` cannot flip the result to DEGRADED.

### 5. Close remains canonical and unchanged

Session close is already owned upstream: `memory_writeback.py` calls the
canonical `close_session`, and `graphiti-session-end.sh` uses
`hydration.cli close`. Wrapper budget / `skipped_no_prefetch` policy does not
justify a second close implementation. No `session_close.py` is introduced.

## Options Considered

Recorded 2026-11-15 from the alternatives this record's Context and Decision
already name; the decision itself is unchanged.

1. **Keep a Claude predicate in each consumer** (`memory_prefetch.py`,
   `session_start_claude_governance.sh`, `execution_profile.classify()`). The
   status quo, and the defect: a projected `L9_GOVERNANCE_SURFACE=claude-code`
   made Cursor look like Claude in some consumers and not others. Rejected.
2. **No-op every gate-class hook outside Claude.** Simple, but false for the live
   launcher: shared gates such as the merge gate must keep enforcing on every
   surface, and an `unknown` surface must fail toward closed. Rejected (Decision §2).
3. **One upstream detector plus a named Claude-only gate table in the launcher.**
   Identity has one SSOT (`surface_detect`), observers skip off Claude, and only
   the named gates skip on a known non-Claude surface. Chosen.

## Consequences

- Cursor sessions cannot be hijacked by the projected Claude surface id.
- Claude observer context is emitted only on a canonical Claude surface.
- Claude desktop/mobile retain their intended gate enforcement.
- Merge/session-debt authority is not accidentally disabled on Cursor.
- Claude local/cloud personality remains policy-driven after canonical surface
  detection.
- Cursor and Claude hydrate output use the same honesty classifier.
- Surface doctrine follows executable code rather than forcing code to satisfy
  stale “explicit always wins” or “all gates no-op” prose.

## See also

- `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md`
- ADR-0006 (single memory front door)
- ADR-0028 (hydrate/close visibility)

## Amendment (2026-09-07) — the shared brain is ops/memory + MemoryService (ADR-0030)

Decision item 3's "Graphiti client" reads as **`ops/memory` over the bound
`l9-graphite-memory` `MemoryService`**: that boundary, the binding manifest and
the canonical session state are the shared, upstream memory brain. Per-surface
remains hook registration, session receipts and projection engines — and each
surface's *memory front door* is the same door (`ops/memory`), so "memory front
door" in item 3 names where a surface wires it, not a surface-local transport.
The receipt-unification seam in item 4 is unchanged. Nothing in this ADR
authorizes a provider call or a second memory stack.

## Amendment (2026-11-15) — the gate table follows `l9_hook_exec.sh`

Decision item 2's lists drifted from the launcher. As executed:

- **Claude-only gates** (skip on a known non-Claude surface):
  `local_execution_gate_wrap.py`, `memory_gate.py` and
  `coding_agent_binding_gate_wrap.py`.
- **Shared gates:** `merge_gate_wrap.py`, `swarm_role_gate_wrap.py` (registered only on
  `mcp__claude-code-remote__.*`) and `context7_stack_pretool.py`.
  `session_debt_wrap.py` is gate-classified but not registered: `session_debt.py`
  runs on demand, not as a Stop gate (`rules/42-no-abandoned-work`).

`environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md` carries the same table; the
launcher's `l9_required_class` and Claude-only `case` are the authority for both.
