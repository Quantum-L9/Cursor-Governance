---
name: l9-governance-wiring
description: workspace governance symlinks, component wire executor, confirm-wiring audit, governance checks, rules inventory, and github ssot backup. use for /wire governance, confirm-wiring, or governance-backup.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, governance, wiring, symlinks, backup]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
disable-model-invocation: true
---

# Governance Wiring

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

## Authority Order

1. CANONICAL_LAW.md — GlobalCommands SSOT via `.cursor-commands/`.
2. `ops/scripts/setup_workspace_symlinks.sh`, `check_governance_wiring.sh`, `backup_to_github.sh`.
3. Wire executor for code components.

## Validation

Governance workspace check MUST pass before session proceed (`/start-session` auto-chains).

## Failure Handling

Miswired symlinks → run `wire_governance_workspace.sh`. Protected file wire changes → escalate to GMP.
