---
name: l9-governance-wiring
description: deprecated legacy bundle for workspace symlinks, component wiring, confirmation, governance checks, inventory, health, and backup. do not activate; use l9-wire-into-repo for generic repository wiring and the appropriate narrower owner for specialized governance operations.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, governance, wiring, symlinks, backup]
  owner: igor_beylin
  status: deprecated
  version: 2.0.0
  updated: 2026-08-31
---

# Governance Wiring (ARCHIVED)

> **Deprecated and archived.** Generic repository wiring is owned by
> `skills/l9-wire-into-repo/`. Workspace symlink setup/validation is owned by
> `skills/l9-governance-symlinks/`. This pack is retained as history only —
> its references below describe retired machinery and are not repaired.

## Purpose

Wire governance workspace symlinks, run component wire DAG, confirm wiring audits, governance compliance checks, rules inventory, and push GlobalCommands SSOT to GitHub.

## Core Contract

| Mode | Load |
|------|------|
| wire governance | [governance-workspace.md](references/governance-workspace.md) |
| wire component | [wire-executor.md](references/wire-executor.md) |
| confirm-wiring | [confirm-wiring.md](references/confirm-wiring.md) |
| governance check | [governance-check.md](references/governance-check.md) |
| governance-backup | [governance-backup.md](references/governance-backup.md) |
| rules inventory | [rules-inventory.md](references/rules-inventory.md) |

## Resource Map

- [references/governance-workspace.md](references/governance-workspace.md)
- [references/wire-executor.md](references/wire-executor.md)
- [references/confirm-wiring.md](references/confirm-wiring.md)
- [references/governance-check.md](references/governance-check.md)
- [references/governance-backup.md](references/governance-backup.md)
- [references/rules-inventory.md](references/rules-inventory.md)
- [references/operational-health.md](references/operational-health.md) — the two live health checks, baseline reading, no-weakening rule

## Authority Order

1. CANONICAL_LAW.md — GlobalCommands SSOT via `.cursor-commands/`.
2. `ops/scripts/setup_workspace_symlinks.sh`, `check_governance_wiring.sh`, `backup_to_github.sh`.
3. Wire executor for code components.

## Validation

Governance workspace check MUST pass before session proceed (`/start-session` auto-chains).

## Failure Handling

Miswired symlinks → run `wire_governance_workspace.sh`. Protected file wire changes → escalate to GMP.
