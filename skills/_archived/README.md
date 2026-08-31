# Archived skills

Retired skill packs live here — **not** under the live `skills/` discovery root.

## Law

Deprecated skills **must not** remain as top-level `skills/<name>/` directories.
They must be:

1. Moved here via `git mv skills/<name> skills/_archived/<name>`
2. Removed from `AUTONOMY_MANIFEST.yaml` tiers (never auto- or explicit-invoke)
3. Dropped from adapter reconcile / skill-registry generation
4. Referenced only as historical comparison under `skills/_archived/`

Live discovery surfaces (`skills/*/SKILL.md`, Cursor plugin skills root, Claude
adapter symlinks) must never see archived packs.

**Operating skill:** `l9-wire-into-repo` owns unwire/deprecate/deregister
(`references/validation-unwire.md`). Do not invent a parallel retirement path.
Skill archival is one specialization of unwire — other artifact classes retire
under their own lifecycle contract.

## Contents

| Pack | Superseded by |
|---|---|
| `l9-governance-wiring/` | `skills/l9-wire-into-repo/` (generic wiring); `skills/l9-governance-symlinks/` (workspace binding) |
| `l9-harvest-pipeline/` | Skill wrapper retired — `workflows/dags/harvest_deploy_dag.py` + `workflows/use_harvest_executor.py` via `/harvest`, `/use-harvest` |
| `l9-inspect/` | Skill wrapper retired — `workflows/dags/inspect_dag.py` via `/inspect` |
| `l9-plan-audit/` | `skills/l9-pipeline-audit/` |
| `l9-pr-analysis/` | `skills/l9-pr-remediation/` |
| `l9-pr-remediation-deprecated/` | `skills/l9-pr-remediation/` |
| `l9-structured-reasoning-deprecated/` | `skills/l9-structured-reasoning/` |
| `l9-update-command/` | `skills/l9-dag-authoring/` (COMMAND_BIND operation) |

Every directory under `skills/_archived/` must appear in this table. Rows are
sourced from `AUTONOMY_MANIFEST.yaml` `do_not_migrate_to_skills`.
