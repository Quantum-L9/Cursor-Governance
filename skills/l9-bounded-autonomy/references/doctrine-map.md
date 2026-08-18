# Doctrine → Cursor mechanism map

Maps Claude Code autonomy law onto Cursor SOP behavior. Do not weaken these mappings.

## Authority sources

| Source | Path | Role |
|---|---|---|
| ADR-0001 | `docs/decisions/ADR-0001-claude-code-bounded-concurrent-autonomy.md` | Autonomy ON, ordinary merge ON after remediation, force/admin OFF |
| Settings | `environment/agents/adapters/claude-code/settings.template.json` | Allow scoped push/PR create; omit merge; deny force/admin |
| Profile | `environment/program-execution/peer_execution/autonomy/profiles/pr-convergence.json` | Lanes 4/2, waiting_external, merge_gate |
| Runtime | `environment/program-execution/peer_execution/autonomy/*.py` | Claude-only machine scheduler (do not rewrite for Cursor) |
| Hooks | `environment/agents/adapters/claude-code/hooks/*` | Thin fail-open adapters over `ops/skill_routing/` (SessionStart, route hint, usage log) |
| Routing | `ops/skill_routing/` + `ops/generated/skill-registry.json`; rule `rules/23-l9-skill-routing.mdc` (+ generated `environment/generated/llm-rules/l9-skill-routing.md`) | Recommendation ≠ authority; `hint_allowed` may surface Read (`explicit_hint`); mutate only with packet |

## Settings posture (summary)

- **Allow:** scoped local git commits; non-force push + PR create/update **only after L4 release_authorized**.
- **Deny:** mid-execution push/PR (`ops/autonomy/local_execution_gate.py`), `.env` / `.mcp.json` reads, `rm -rf`, force-push, `reset --hard`, `clean -fd`, `gh pr merge --admin`.
- **Allow ordinary merge:** `Bash(gh pr merge:*)` after `/l9-pr-remediation` (green + mergeable + threads resolved). `merge_gate.py` reads `L9_AUTONOMY_AUTONOMOUS_MERGE=true`.
- **Env:** `L9_AUTONOMY_ENABLED=true`, `L9_AUTONOMY_AUTONOMOUS_MERGE=true`, `L9_AUTONOMY_MAX_PARALLEL=4`, `L9_AUTONOMY_MAX_MUTATION_LANES=2`, `L9_AUTONOMY_REMEDIATION_SKILL=l9-pr-remediation`, `L9_L4_LOCAL_AUTONOMY=1` (default).

## L4 local autonomy (standing)

| Step | Mechanism |
|---|---|
| Stacked local execution | Feature branch commits only; no mid-exec remote |
| Post-finish kernels | `kernels/Recursive Alignment.md` → `kernels/Validate & Repair.md` |
| Release receipt | `python3 ops/autonomy/l4_local.py authorize-release` |
| Scoped PR | `make pr` / `PULL_REQUEST_TEMPLATE.md` |
| Gate | Claude PreToolUse + Cursor `beforeShellExecution` → `local_execution_gate.py` |

## Hooks posture

SessionStart / skill-router hooks are **fail-open** (context/telemetry).
**Fail-closed** remote gates (do not weaken): `ops/autonomy/merge_gate.py` and
`ops/autonomy/local_execution_gate.py` (L4 no mid-execution push).

## Profile parallelism flags → Cursor

| Profile flag | Cursor SOP mechanism |
|---|---|
| `require_dependency_ready` | Phase-0 `depends_on[]` — never guess |
| `require_declared_resource_locks` | Every mutation declares `lock_keys[]` |
| `require_isolated_mutation_lane` | `isolation_key` / `best-of-n-runner` for mutation |
| `waiting_external_releases_compute_lane` | `kind:poll` → `Task(run_in_background: true)`; main continues |
| `waiting_external_preserves_declared_locks` | Poll owns `pr:<n>` until join/hand-back |
| `require_join_barrier` | All Tasks terminal + evidence before merge-ready claim |
| `autonomous_merge: false` | No standing random merges; L4 program/plan Build launch authorizes merge for that stack after green+mergeable (bottom-up) |
| `concurrency_budget` 4 / 2 | Max 4 Tasks; max 2 `mutation: true` |

## Dual-surface rule

- **Claude Code surface:** use `environment/program-execution/peer_execution/autonomy/cli.py` + profile — see `claude-code-bridge.md`.
- **Cursor surface:** this skill + `/autonomy` + agent-requested rule — Task/background poll SOP only; no second Python scheduler.

## Program Execution System (PES) Phase 0

| Source | Path | Role |
|---|---|---|
| Phase 0 dial-in | `WIP/_program-execution-system-v2.0.0/.../PHASE0_USER_CONFIG.yaml` (promoted under `environment/program-execution/core/`) | Autonomy profile, blocking inventory, make pr / lock alignment, packet fields |
| Autonomy bridge | `.../program-execution-controller-template/references/AUTONOMY_BRIDGE.md` | Packet ↔ Program Lock; Task Card `autonomy_action_id`; dual stores |
| Lessons LL-001..004 | `.../LEARNED_LESSONS.md` | CI hygiene, Phase 0 max autonomy, make pr, uv.lock pins |

When a PES program is deploying, Phase 0 selects `program_deploy_max_autonomy` (max within ceiling, `autonomous_merge: false`). Align campaign packet fields with Phase 0; never use “envelope.”
