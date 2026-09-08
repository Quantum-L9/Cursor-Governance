# Surface bootstrap contract

Authority: ADR-0029. Maps, not a rung — does not outrank CANONICAL_LAW or AGENTS.md.

## Architecture

```text
                 shared lifecycle brain (ops/)
       detect · hydrate classify · close · receipts · gates
                              │
                              ▼
                    canonical surface_detect
                              │
             ┌────────────────┴────────────────┐
             ▼                                 ▼
        Cursor adapter                    Claude adapter
        Cursor events                     Claude events
        thin wrappers                     thin wrappers
```

Adapters bind host events and wrap. Meaning stays upstream. Adapters never
export policy upstream (CANONICAL_LAW §2.1).

## Locked surface-detect precedence

This table is executable doctrine copied from
`ops/autonomy/surface_detect.py`, `ops/scripts/lib/surface_detect.sh`, and their
tests. Consumers must not maintain private marker lists.

| Precedence | Condition | Result |
|---:|---|---|
| 1 | `CURSOR_AGENT` set and explicit `L9_GOVERNANCE_SURFACE` is `claude-code` or `claude-code-remote` | `cursor` |
| 2 | explicit `L9_GOVERNANCE_SURFACE` is one of `cursor`, `claude-code`, `claude-code-remote`, `codex`, `gemini`, `manus` | explicit id |
| 3 | `CLAUDE_CODE_REMOTE=true` | `claude-code-remote` |
| 4 | `CLAUDECODE` or `CLAUDE_CODE_ENTRYPOINT` or `CLAUDE_CODE_SESSION_ID` | `claude-code` |
| 5 | `CURSOR_AGENT` | `cursor` |
| 6 | nothing matched | `unknown` |

The precedence is intentionally not “explicit always wins.” The projected
Claude triad must not steal a Cursor session.

Existing helpers are the public contract:

- Python: `detect_surface`, `is_claude_gate_surface`, `CLAUDE_GATE_SURFACES`
- Shell: `l9_detect_surface`, `l9_is_claude_gate_surface`

Do not add a second detect API.

## Hook-entry policy

`environment/agents/adapters/claude-code/hooks/l9_hook_exec.sh` is the Claude
adapter choke point.

### Observers

All Claude adapter observers skip when `l9_is_claude_gate_surface` is false.
That includes Cursor, Codex, Gemini, Manus, and `unknown`. Unknown observers
must not inject Claude identity or SessionStart context.

### Gates

The named gate table is narrower and must remain narrow:

| Hook | Known non-Claude surface | `unknown` |
|---|---|---|
| `local_execution_gate_wrap.py` | skip | run |
| `memory_gate.py` | skip | run |
| `merge_gate_wrap.py` | run | run |
| `session_debt_wrap.py` | run | run |

`unknown` therefore fails toward enforcing for gates while failing toward
non-injection for observers.

`L9_SURFACE_GUARD=0` disables this entry guard for diagnostics and preserves the
pre-guard behavior.

## Surface identity versus execution personality

Surface ids and execution personalities are different layers.

1. `surface_detect` decides Claude versus not-Claude.
2. If Claude, `ops/autonomy/execution_profile.py` uses the policy
   `cloud_env` / `cloud_value` discriminator to select `claude_cloud` or
   `claude_local`.
3. Non-Claude ids (`cursor`, `codex`, `gemini`, `manus`, `unknown`) use the
   constrained `cursor` personality.

Thus an explicit surface id `claude-code` with `CLAUDE_CODE_REMOTE=true` remains
`claude_cloud`. Do not map detect ids 1:1 to execution personalities and do not
invent a fourth personality.

## Shared upstream ownership

| Meaning | Owner |
|---|---|
| Surface identity | `ops/autonomy/surface_detect.py` + shell twin |
| Hydrate compile | `ops/graphiti/hydration` |
| Hydrate honesty | `ops/scripts/classify_hydrate_state.py` |
| Close / PICKUP | canonical `close_session` / `hydration.cli close` |
| Local execution / L4 / merge gates | `ops/autonomy/` |
| Memory boundary | `ops/memory/` |
| Tree-kernel latch | `ops/autonomy/kernel_gate.py` |

## Platform event binding

| Meaning | Cursor event | Claude event |
|---|---|---|
| Session hydrate | `sessionStart` | `SessionStart` via prefetch |
| Session close | `sessionEnd` | `Stop` |
| Skill route | `beforeSubmitPrompt` | `UserPromptSubmit` |
| L4 / merge | `beforeShellExecution` | `PreToolUse` Bash/GitHub |
| Tree kernels | skipped | `make pr` latch |

Cursor-only and Claude-only event names stay downstream. Shared lifecycle
semantics stay in `ops/`.

## Hydration honesty

Claude `memory_prefetch.py` runs `compile_and_format`, then classifies the
**emitted `additional_context` markdown** with
`classify_hydrate_state.classify`. Packet booleans are authoritative, so a
healthy JSON fence containing `"degraded": false` is not degraded merely
because the word appears.

Do not copy Cursor banner sections into Claude. Share the classifier, not the
presentation.

## Close

Close is verify-only in this alignment:

- `memory_writeback.py` already imports and calls canonical `close_session`.
- `graphiti-session-end.sh` already uses `hydration.cli close`.
- wrapper budget / `skipped_no_prefetch` remain wrapper policy.

No `session_close.py` and no second close authority.

## Receipt boundaries

Cursor and Claude receipt **files** remain separate. The shared reader remains
`ops/scripts/claude_bootstrap_receipt.py --surface` where applicable. This
contract does not merge receipt stores.
