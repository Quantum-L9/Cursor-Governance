---
name: l9-dag-authoring
description: Author, update, validate, register, discover, and optionally bind thin command triggers to L9 DAGs through the canonical SessionDAG architecture while preventing DAG-related Skill sprawl and preserving domain workflow ownership. Use when creating or changing an L9 DAG, repairing SessionDAG registration/discovery, or making a command a thin DAG trigger. Do not use for domain workflow semantics, Skill wiring, Skill compilation, GMP execution, or generic component audits.
paths: "workflows/**, **/*dag*.py, **/*dag*.yaml"
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: dag_lifecycle_owner
  tags: [l9, dag, workflow, authoring, registry, command-binding]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-08-28
  absorbs: [l9-update-command]
---

# DAG Authoring — DAG lifecycle owner

## Core contract

`BIND → CLASSIFY → RECONSTRUCT → DESIGN/RECONCILE → VALIDATE → REGISTER/DISCOVER → OPTIONAL COMMAND BIND → VERIFY → RECEIPT`

Own the **DAG lifecycle mechanism** only. The most-specific domain Skill continues
to own workflow semantics.

## Authority order

1. Explicit user scope and the domain Skill that owns the workflow semantics.
2. `workflows/session/interface.py` — `SessionDAG`, `SessionNode`, `SessionEdge`, node/gate types.
3. `workflows/session/registry.py` — `register_session_dag()` and `get_session_dag()`.
4. `workflows/dags/__init__.py` — the discovery boundary.
5. The existing canonical DAG under `workflows/dags/` when updating.
6. [`references/dag-authoring-protocol.md`](references/dag-authoring-protocol.md).
7. `UNKNOWN` when a material ownership or runtime fact cannot be verified.

## Invariants

- A DAG does not justify a separate Skill. Skills represent capabilities; DAGs
  represent execution graphs.
- Keep domain semantics with the domain owner. Do not become a generic workflow
  god-skill.
- Author canonical DAGs under `workflows/dags/` unless current repository ground
  truth proves another canonical location.
- Register `SessionDAG` objects only through `register_session_dag()`. Never invent
  `ACTIVE_DAGS`, dict-only registries, or a parallel registration layer.
- Validate before registration. Never claim registration or reachability without a
  successful probe.
- Require unique node IDs, resolvable edge endpoints, a resolvable entry node, and
  explicit branch outcomes where gates exist.
- Duplicate DAG IDs fail closed unless the task is an explicit update/migration of
  that same owner.
- Discovery through `workflows/dags/__init__.py` is a separate proof obligation from
  constructing the DAG object.
- Command binding is optional. A command file is a thin trigger, never a second
  workflow implementation.
- Do not own Skill discovery/autonomy wiring. Hand that to `l9-wire-skill-into-repo`
  only when Skill wiring is requested.
- Do not claim commands, imports, registration, tests, or runtime behavior that were
  not actually checked.

## Operation routing

Classify the request as exactly one primary operation:

- `CREATE` — create a new canonical DAG for semantics already owned by a domain capability.
- `UPDATE` — modify an existing canonical DAG without forking ownership.
- `VALIDATE` — prove DAG structure/importability without changing semantics.
- `REGISTER` — repair canonical registration/discovery for an existing DAG.
- `COMMAND_BIND` — create or reduce a command to a thin trigger for an existing DAG.

If the request is actually "design the domain workflow", route to the domain owner
first. This Skill may then encode the resulting workflow as a DAG.

## Command binding rules

A bound command is trigger-only:

- references the canonical DAG id and its `workflows/dags/*.py` path;
- carries no stale `.cursor-commands/workflows/dags` path;
- carries no detailed phase logic and does not restate workflow phases;
- stays short — roughly 80 lines is the ceiling.

A command-binding failure does not invalidate an otherwise valid DAG unless the
command was the required deliverable.

## Consolidation rule

This Skill absorbs the former `l9-update-command` capability for **thin
command-to-DAG binding** (`COMMAND_BIND`, reachable as `/dag-authoring
--bind-command`). It does not absorb the domain behavior of GMP, skill
compilation, maintenance, verification, harvesting, or other workflows that merely
happen to use DAGs.

## Failure behavior

Fail closed before downstream success claims when structural validation, canonical
registration, or discovery fails. Report the smallest repair seam. Do not widen
scope to domain semantics, Skill wiring, or unrelated repo surgery.

Terminal state is `PASS`, `PARTIAL`, `BLOCKED`, or `FAIL`.
