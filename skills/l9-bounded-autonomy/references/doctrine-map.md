# Doctrine → Cursor mechanism map

Maps Claude Code autonomy law onto Cursor SOP behavior. Do not weaken these mappings.

## Authority sources

| Source | Path | Role |
|---|---|---|
| ADR-0001 | `docs/decisions/ADR-0001-claude-code-bounded-concurrent-autonomy.md` | Autonomy ON, merge OFF, remediation ON |
| Settings | `environment/claude-code/settings.template.json` | Allow scoped push/PR create; omit merge; deny force/admin |
| Profile | `environment/claude-code/autonomy/profiles/pr-convergence.json` | Lanes 4/2, waiting_external, merge_gate |
| Runtime | `environment/claude-code/autonomy/*.py` | Claude-only machine scheduler (do not rewrite for Cursor) |
| Hooks | `environment/claude-code/hooks/*` | Fail-open only (SessionStart context, skill route hint, usage log) |
| Routing | `environment/claude-code/rules/l9-skill-routing.md` | Recommendation ≠ authority; explicit_only never auto-invoked |

## Settings posture (summary)

- **Allow:** scoped git (incl. non-force push), `gh pr/run` inspect+rerun, GitHub MCP read + `subscribe_pr_activity` + PR create/update.
- **Deny:** `.env` / `.mcp.json` reads, `rm -rf`, force-push, `reset --hard`, `clean -fd`, `gh pr merge --admin`.
- **Omitted:** `merge_pull_request` → human merge.
- **Env:** `L9_AUTONOMY_ENABLED=true`, `L9_AUTONOMY_AUTONOMOUS_MERGE=false`, `L9_AUTONOMY_MAX_PARALLEL=4`, `L9_AUTONOMY_MAX_MUTATION_LANES=2`, `L9_AUTONOMY_REMEDIATION_SKILL=l9-pr-remediation`.

## Hooks posture

All Claude Code autonomy-related hooks are **fail-open**. They inject context or telemetry; they do not deny tools. Cursor must not invent fail-closed PreToolUse merge enforcement in this skill ship.

## Profile parallelism flags → Cursor

| Profile flag | Cursor SOP mechanism |
|---|---|
| `require_dependency_ready` | Phase-0 `depends_on[]` — never guess |
| `require_declared_resource_locks` | Every mutation declares `lock_keys[]` |
| `require_isolated_mutation_lane` | `isolation_key` / `best-of-n-runner` for mutation |
| `waiting_external_releases_compute_lane` | `kind:poll` → `Task(run_in_background: true)`; main continues |
| `waiting_external_preserves_declared_locks` | Poll owns `pr:<n>` until join/hand-back |
| `require_join_barrier` | All Tasks terminal + evidence before merge-ready claim |
| `autonomous_merge: false` | Report merge gate only; human merges |
| `concurrency_budget` 4 / 2 | Max 4 Tasks; max 2 `mutation: true` |

## Dual-surface rule

- **Claude Code surface:** use `environment/claude-code/autonomy/cli.py` + profile — see `claude-code-bridge.md`.
- **Cursor surface:** this skill + `/autonomy` + agent-requested rule — Task/background poll SOP only; no second Python scheduler.
