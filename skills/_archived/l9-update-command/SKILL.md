---
name: l9-update-command
description: deprecated — do not activate. superseded by l9-dag-authoring, which owns thin command-to-DAG binding as its COMMAND_BIND operation. archived out of live skills discovery.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, commands, dag, deprecated]
  owner: igor_beylin
  status: deprecated
  version: 9.0.0
  updated: 2026-08-28
  superseded_by: l9-dag-authoring
---

# l9-update-command (Deprecated)

**Deprecated. Do not activate this pack.**

Canonical replacement: `skills/l9-dag-authoring/` — thin command-to-DAG binding is
the `COMMAND_BIND` operation there, reachable as `/dag-authoring --bind-command`.

The runtime DAG `workflows/dags/slash_command_update_dag.py` is retained for now.
A Skill is not required to keep a DAG alive: Skills represent capabilities, DAGs
represent execution graphs. Archive that DAG separately once a reference search
proves zero callers.

Archived under `skills/_archived/l9-update-command/` for history only. The body below is the
retired pack, retained verbatim for comparison.

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
