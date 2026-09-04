# Surface bootstrap contract

Authority: ADR-0029. Maps, not a rung — does not outrank CANONICAL_LAW or AGENTS.md.

## Divergence point

```
shared brain (ops/autonomy, ops/graphiti, kernels, L4)
        │
        ▼
 surface_detect  (ops/autonomy/surface_detect.py + ops/scripts/lib/surface_detect.sh)
        │
   ┌────┴────┬─────────────────┐
   ▼         ▼                 ▼
 Cursor   Claude desktop   Claude mobile (remote)
 hooks    PreToolUse       PreToolUse + HTTPS Graphiti
 ~/.cursor  .claude/       CLAUDE_CODE_REMOTE=true
```

Adapters never export policy upstream (CANONICAL_LAW §2.1).

## Shared upstream

| Capability | Owner |
|---|---|
| Local execution / L4 / worktree / verification-bypass gates | `ops/autonomy/` |
| Graphiti client + hydration packet | `ops/graphiti/` |
| Tree kernels (RA + V&R) latch predicate | `ops/autonomy/kernel_gate.py` via `surface_detect` |
| Surface identity | `ops/autonomy/surface_detect.py` |

## Per-surface downstream

| Axis | Cursor | Claude desktop | Claude mobile |
|---|---|---|---|
| Hook registration | `~/.cursor/hooks.json` → `ops/hooks/` | `.claude/settings.json` → `l9_hook_exec.sh` | same adapter; remote markers |
| Memory front door | Cursor Graphiti hydrate / `graphiti-gate-*` | `memory_prefetch` / `memory_gate` | HTTPS `GRAPHITI_MCP_URL` |
| Session receipts | `.l9/memory/`, Cursor session ids | `~/.l9/claude/`, Claude session ids | same Claude plane |
| SessionStart | `session_start_bootstrap.sh` | `session_start_claude_governance.sh` (no-op if not Claude) | cloud refresh path when `CLAUDE_CODE_REMOTE=true` |
| Kernel latch | skipped | fires | fires (`claude-code-remote`) |

## Marker table

| Surface id | How detected |
|---|---|
| `cursor` | `CURSOR_AGENT` set (and no winning explicit / Claude markers) |
| `claude-code` | `CLAUDECODE` / `CLAUDE_CODE_ENTRYPOINT` / `CLAUDE_CODE_SESSION_ID` |
| `claude-code-remote` | `CLAUDE_CODE_REMOTE=true` |
| `codex` / `gemini` / `manus` | explicit `L9_GOVERNANCE_SURFACE` |
| `unknown` | nothing matched — gates must still enforce |

Explicit `L9_GOVERNANCE_SURFACE` always wins when it is a known id.

## Kill switches

- `L9_SURFACE_GUARD=0` — disable the `l9_hook_exec.sh` entry guard (diagnostics).
