# Doctrine → Cursor mechanism map

Maps Claude Code autonomy law onto Cursor SOP behavior. Do not weaken these mappings.

## Authority sources

| Source | Path | Role |
|---|---|---|
| ADR-0001 | `docs/decisions/ADR-0001-claude-code-bounded-concurrent-autonomy.md` | Autonomy ON, ordinary merge ON after remediation, force/admin OFF |
| Settings | `environment/agents/adapters/claude-code/settings.template.json` | Allow scoped push/PR create; omit merge; deny force/admin |
| Runtime | `autonomy/` | provider-neutral authorization, leases, scheduling, capability mediation, and receipts |
| Claude adapter | `autonomy/adapters/claude_code/` | thin Claude Code binding to root autonomy |
| Hooks | `environment/agents/adapters/claude-code/hooks/*` | Thin fail-open adapters over `ops/skill_routing/` (SessionStart, route hint, usage log) |
| Routing | `ops/skill_routing/` + `ops/generated/skill-registry.json`; rule `rules/23-l9-skill-routing.mdc` (+ generated `environment/generated/llm-rules/l9-skill-routing.md`) | Recommendation ≠ authority; `hint_allowed` may surface Read (`explicit_hint`); mutate only with packet |

## Settings posture (summary)

- **Allow:** scoped local git commits; non-force push + PR create/update **only after L4 release_authorized**.
- **Deny:** mid-execution push/PR (`ops/autonomy/local_execution_gate.py`), `.env` / `.mcp.json` reads, `rm -rf`, force-push, `reset --hard`, `clean -fd`, `gh pr merge --admin`.
- **Allow ordinary merge:** `Bash(gh pr merge:*)` after `/l9-pr-remediation` (green + mergeable + threads resolved). `merge_gate.py` authorizes merge only from the scoped, expiring receipt `/l9-pr-remediation` writes (or a human `L9_MERGE_AUTHORIZED=<reason>`); no environment boolean is consulted.
- **Env:** `L9_AUTONOMY_ENABLED=true`, `L9_AUTONOMY_MAX_PARALLEL` / `L9_AUTONOMY_MAX_MUTATION_LANES` (Cursor and Claude: `480` / `128` — saturation, bounded by claims), `L9_AUTONOMY_REMEDIATION_SKILL=l9-pr-remediation`, `L9_L4_LOCAL_AUTONOMY=1` (default). There is no autonomous-merge env boolean.

## L4 local autonomy (standing)

| Step | Mechanism |
|---|---|
| Stacked local execution | Feature branch commits only; no mid-exec remote |
| Release receipt | `python3 ops/autonomy/l4_local.py authorize-release` |
| Scoped PR | `make pr` / `PULL_REQUEST_TEMPLATE.md` |
| Gate | Claude PreToolUse + Cursor `beforeShellExecution` → `local_execution_gate.py` |

## Hooks posture

SessionStart / skill-router hooks are **fail-open** (context/telemetry).
**Fail-closed** remote gates (do not weaken): `ops/autonomy/merge_gate.py` and
`ops/autonomy/local_execution_gate.py` (L4 no mid-execution push).

## Parallelism flags → Cursor

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

- **Claude Code surface:** use the root `autonomy/` runtime through
  `autonomy/adapters/claude_code/`. Provider-specific code does not own a scheduler.
  Claude multi-lane scheduling is unavailable from this skill.
- **Cursor surface:** this skill + `/autonomy` + agent-requested rule — Task/background poll SOP only; no second Python scheduler.
