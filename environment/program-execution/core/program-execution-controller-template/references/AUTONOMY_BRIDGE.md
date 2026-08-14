# Autonomy Bridge — Program Execution System ↔ Cursor/Claude autonomy

PES Program Lock is authoritative for program state. Cursor/Claude campaign runtimes under `.l9/autonomy/` are orchestration state. Do not collapse the stores; **align fields**.

## Vocabulary

| Prefer | Avoid |
|---|---|
| campaign authorization **packet** | envelope |
| Program Lock + Blueprint ceiling | silent widen |
| Task Card `autonomy_action_id` | unnamed parallel graphs |
| `program_deploy_max_autonomy` | autonomous_merge |

## Field alignment (Phase 0)

`PHASE0_USER_CONFIG.yaml` → `campaign_authorization_packet` must agree with:

- Blueprint `EXECUTION_TARGETS.yaml` repos / targets
- Controller Program Lock digest binding
- Cursor skill packet: `skills/l9-bounded-autonomy/references/campaign-authorization-packet.md`
- ADR-0001 / `environment/agents/adapters/claude-code/autonomy/profiles/pr-convergence.json` (lanes, merge OFF)

Machine `autonomy/schemas/campaign-authorization.schema.json` remains an optional later adapter shape; PES does not reimplement that scheduler.

## Task Card ↔ action / lease

Each mutating Task Card SHOULD set `autonomy_action_id` to a stable ID (e.g. `pes.wave1.task002`) used by:

- Cursor `/autonomy` Task prompts (declared locks, isolation)
- Claude `cli.py` action graph (when on Claude surface)
- Controller lease claims (one writer per repository)

## Dual-surface rule

- **Cursor:** `l9-bounded-autonomy` + `/autonomy` — Task/background poll SOP only; no second Python scheduler.
- **Claude Code:** `environment/agents/adapters/claude-code/autonomy/cli.py` + profile.
- **PES Controller:** admits/schedules/verifies Blueprint tasks; binds exact SHA; evaluates gates.

## Kill switch posture

Phase 0 names `.l9/autonomy/revoke` and operator action `touch_revoke_and_runtime_suspend`. File-watch auto-enforce is **not** assumed in `autonomy/runtime` today; operator must suspend explicitly.

## Rail invariants (unchanged)

Exact SHA, one-writer-per-repo, narrow-never-widen, independent verification, human merge, local `make pr` before push/PR.
