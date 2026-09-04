# ADR-0029: Surface-hook divergence (shared brain upstream)

## Status

Accepted

## Date

2026-09-04

## Context

Cursor SessionStart and Claude Code SessionStart already diverge (AGENTS.md
`CURSOR_SESSIONSTART_NO_CLAUDE_CLOUD_V1`). The tree-kernel latch already
skips Cursor (`CURSOR_KERNEL_LATCH_ADAPTER_ONLY_V1`). Claude Code
`PreToolUse` gates (`memory_gate`, `local_execution_gate_wrap`) registered via
`.claude/settings.json` → `l9_hook_exec.sh` still evaluated inside Cursor
sessions because Cursor also loads that settings triad. Symptom: Cursor
editor writes denied for a Claude hydration receipt the Cursor Graphiti
front door never writes.

CANONICAL_LAW §2.1 requires shared capability in `ops/` with adapters wrapping
outward — not Claude-adapter policy imported as Cursor law.

## Decision

1. One surface-detection SSOT in `ops/` (`surface_detect.py` +
   `surface_detect.sh`). Explicit `L9_GOVERNANCE_SURFACE` wins; markers break
   ties toward the adapter; `unknown` fail-toward-enforcing.
2. Divergence point is **hook entry**: `l9_hook_exec.sh` gate-class hooks
   no-op (exit 0) unless the surface is `claude-code` /
   `claude-code-remote`. Kill switch: `L9_SURFACE_GUARD=0`.
3. Shared brain stays upstream: `ops/autonomy/*` gates, Graphiti client,
   kernels, L4. Per-surface: hook registration, memory front door, session
   receipts, projection engines.
4. Hydration-receipt unification across Cursor and Claude is **deferred**
   (known seam). This ADR stops cross-surface gate evaluation first.

## Consequences

- Cursor edits are no longer denied by Claude `memory_gate`.
- Claude desktop/mobile keep full gate enforcement.
- `kernel_gate.py` and `session_start_claude_governance.sh` consume the SSOT
  instead of private marker lists.
- Follow-on: one receipt both bootstraps can write (out of this ADR).

## See also

- `environment/agents/SURFACE_BOOTSTRAP_CONTRACT.md`
- ADR-0006 (single memory front door)
- ADR-0028 (hydrate/close visibility)
