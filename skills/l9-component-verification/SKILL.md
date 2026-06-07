---
name: l9-component-verification
description: component audit, deterministic verify, and runtime probe escalation ladder. use for /audit-component, /verify-component, or /probe wiring checks.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, verification, audit, probe, wiring]
owner: igor_beylin
status: active
version: 2.0.0
updated: 2026-06-06
disable-model-invocation: true
---

# Component Verification

## Purpose

Prove components are correctly defined, imported, wired, and loadable — via audit DAG, read-only verify, or runtime probe.

## Core Contract

| Mode | Mutates | Load |
|------|---------|------|
| audit-component | no | [component-audit.md](references/component-audit.md) |
| verify-component | no (diagnostic only) | [verify-component.md](references/verify-component.md) |
| probe | no (import test) | [probe.md](references/probe.md) |

## Authority Order

1. User-specified component path or package.
2. DAG definitions under `.cursor-commands/workflows/dags/`.
3. Protected file list in verify-component reference — read-only; escalate to GMP for edits.

## Resource Map

- [references/component-audit.md](references/component-audit.md) — export/wiring/API audit DAG.
- [references/verify-component.md](references/verify-component.md) — deterministic read-only verification.
- [references/probe.md](references/probe.md) — safe runtime import probe.

## Validation

Verify and probe modes MUST NOT write code. Protected-file fixes → escalate to l9-gmp-protocol.

## Failure Handling

Missing component path → STOP. Import failure → HARD FAIL with evidence table.
