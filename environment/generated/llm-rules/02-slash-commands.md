---
description: Slash command recognition and execution - repo-agnostic governance protocols
---

# Slash Command Recognition

When the user types a message starting with `/` followed by a command name, this is a **slash command** that triggers a governance protocol.

## Recognition Pattern

If user message matches: `/commandname` or `/command-name` or `/command_name`

Then:
1. If the slash basename matches a registered skill in `ops/generated/skill-registry.json`, read `skills/<name>/SKILL.md` (Claude Code: native skill slash; Cursor: plugin discovery).
2. Else read the corresponding file from the command locations (see below)
3. Execute the protocol defined in that file or skill
4. Follow all steps, phases, and output formats specified

## Command File Locations (Repo-Agnostic)

Commands and workflows are resolved in this order:

| Location | Purpose | Priority |
|----------|---------|----------|
| `.cursor/commands/{cmd}.md` | Repo-specific commands | 1st (highest) |
| `.cursor-commands/commands/{cmd}.md` | Shared governance commands (symlink → SSOT) | 2nd |
| `~/.cursor/plugins/local/l9-governance/commands/{cmd}.md` | Same SSOT via l9-governance plugin | 2nd (equivalent) |
| `skills/{name}/SKILL.md` | Registered L9 skill when slash basename equals skill name | 1st for skill names |
| L9 skill via router hint | Skill-backed route (see `skills/AUTONOMY_MANIFEST.yaml`) | When no command file |
| `.cursor/workflows-synced/` | Synced workflow executors and DAGs | For DAG execution |
| `.cursor/workflows-synced/dags/` | DAG definitions | For DAG-based commands |

**Registry (machine + human):**

- `commands/COMMANDS_MANIFEST.yaml` — enabled slash → file map (source of truth for what is active)
- `commands/commands-index.md` — human quick reference

> When governance is activated (`sessionStart` bootstrap, `/start-session`, or `make start`),
> the `l9-governance` plugin + `.cursor-commands` symlink expose skills and the
> **non-wrapper** `commands/` library. Skill-named slashes (`/l9-issue-remediation`, …)
> load `skills/<name>/SKILL.md` — there is no duplicate `commands/` file. Remaining
> commands are executors, DAGs, or bootstrap only. See `commands/commands-index.md`.

### Workflow/DAG Resolution

When a command specifies `dag_file:` in its YAML header:
1. First check: `.cursor/workflows-synced/dags/{dag_name}.py`
2. Fallback: `.cursor-commands/workflows/dags/{dag_name}.py`

### Script Resolution

When a command needs generator scripts:
1. First check: `.cursor/workflows-synced/scripts/{script}.py`
2. Fallback: `scripts/{script}.py` (repo root)

## Available Slash Commands (enabled)

Live commands match `commands/COMMANDS_MANIFEST.yaml` (**18** — skill wrappers retired to `commands/_archived/`). For remediators, planners, CI, wiring, and analysis, invoke the **skill** directly (`skills/<name>/SKILL.md`).

| Command | File | Description |
|---------|------|-------------|
| `/start-session` | `commands/start-session.md` | Run L9 sessionStart bootstrap (`make start`) |
| `/gmp` | `commands/gmp.md` | GMP executor + plan Build |
| `/governance-backup` | `commands/governance-backup.md` | Push governance SSOT to GitHub |
| `/clean` | `commands/clean.md` | Workspace cleanup (`make clean`) |
| `/harvest` | `commands/harvest.md` | Harvest deploy DAG |
| `/use-harvest` | `commands/use-harvest.md` | Deploy harvested artifacts |
| `/migrate` | `commands/migrate.md` | Migration executor |
| `/inspect` | `commands/inspect.md` | External code gate (inspect DAG) |
| `/refactor` | `commands/refactor.md` | Refactoring DAG |
| `/refactor-sweep` | `commands/refactor-sweep.md` | Broad refactor sweep |
| `/index` | `commands/index.md` | Export repo indexes |
| `/pr-train` | `commands/pr-train.md` | Stacked PR train DAG |
| `/l9-plan-build` | `commands/l9-plan-build.md` | Plan-simple + kernels + Build DAG |
| `/l9-audit-plans` | `commands/l9-audit-plans.md` | Plans-store shelf (not pipeline audit) |
| `/lcto` | `commands/lcto.md` | L CTO strategic mode |
| `/spec` | `commands/spec.md` | Specification generator |
| `/rules` | `commands/rules.md` | List governance rules |
| `/update-command` | `commands/update-command.md` | Slash minimizer DAG (legacy) |

Skill examples (no `commands/` file): `l9-issue-remediation`, `l9-pr-remediation`, `l9-plan`, `l9-pipeline-audit`, `l9-bounded-autonomy`, `l9-ynp`, `l9-code-analysis`, `l9-ci-ops`, `l9-forge`, `l9-repo-sync`, `l9-end-session`, … — full map in `ops/generated/skill-registry.json`.

Full map: `commands/COMMANDS_MANIFEST.yaml`. Human index: `commands/commands-index.md`.

## Execution Protocol

When a slash command is detected:

1. **Resolve command file** using priority order above
2. **Parse the YAML header** for metadata (auto_chain, dag_file, etc.)
3. **If DAG-based**: Load DAG from `.cursor/workflows-synced/dags/` first, then fallback
4. **Execute the protocol** following all steps in the markdown body
5. **Produce the specified output format** as defined in the command file
6. **Auto-chain** to the next command if `auto_chain` is specified in metadata

## DAG Execution (Repo-Agnostic)

For commands with `dag_file:` in their header:

```python
# Resolution order for DAG files:
# 1. .cursor/workflows-synced/dags/{dag_name}.py
# 2. .cursor-commands/workflows/dags/{dag_name}.py

# Example for a command with dag_file:
dag_path = ".cursor/workflows-synced/dags/readme_pipeline_dag.py"
# Load and execute DAG nodes in sequence
```

## 🔒 LOCKED: Execution Flow (v1.0)

**All significant commands follow this LOCKED execution flow:**

```
PLAN (Phase 0) → EXECUTE (Phase 1-6) → CHAIN (/ynp or next)
```

## Variations

Commands may be typed with variations:
- `/analyze+evaluate` → `commands/analyze_evaluate.md`
- `/analyze-evaluate` → `commands/analyze_evaluate.md`
- `/analyzeEvaluate` → `commands/analyze_evaluate.md`

Normalize to underscore format for file lookup.

## CRITICAL: Always Read the File

**NEVER** execute a slash command from memory. **ALWAYS** read the actual command file to ensure you have the current protocol version.

<!-- generated-from: rules/02-slash-commands.mdc; do-not-edit -->
