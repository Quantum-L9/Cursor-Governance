---
name: l9-update-command
description: minimize slash commands to dag triggers via slash-command-update workflow. use when reducing a command to a thin trigger or auditing dag-trigger commands.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, commands, dag, meta]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
disable-model-invocation: true
---

# Update Command — Minimize Slash Commands

## Purpose

Reduce slash commands to minimal DAG triggers. All execution logic lives in the DAG, not the command file.

## Core Contract

**DAG-ENFORCED.** Execute `slash-command-update-v1` DAG — follow each node's `action` field exactly.

Load [references/update-command-workflow.md](references/update-command-workflow.md).

## Resource Map

- [references/update-command-workflow.md](references/update-command-workflow.md) — DAG invocation and key files.

## Authority Order

1. User target command name.
2. DAG: `.cursor-commands/workflows/dags/slash_command_update_dag.py`
3. Commands registry: `.cursor-commands/commands/*.md`

## Validation

Command file after update MUST be trigger-only (invocation + DAG pointer, no embedded workflow logic).

## Failure Handling

If DAG file missing → STOP and report `Unknown` path.
