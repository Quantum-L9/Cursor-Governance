---
name: l9-component-verification
description: Audit, deterministically verify, or runtime-probe a named component — exports, imports, wiring, and loadability — as a read-only escalation ladder. Use from /audit-component, or from /analyze, /evaluate, or /analyze_evaluate when the user names a component, module, import, or wiring check. Do not use for DAG authoring or registration, for editing the component, or for generic repo exploration.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, verification, audit, probe, wiring]
  owner: igor_beylin
  status: active
  version: 2.1.0
  updated: 2026-08-28
---

# Component Verification

## Purpose

Prove components are correctly defined, imported, wired, and loadable — via read-only audit, deterministic verify, or runtime probe. `/audit-component` is the live slash for mode `audit-component`. `/analyze`, `/evaluate`, and `/analyze_evaluate` still load this skill when the user names a component. Folded slashes `/probe` and `/verify-component` remain modes on that family.

## Core Contract

| Mode | Mutates | Load |
|------|---------|------|
| audit-component | no | [component-audit.md](references/component-audit.md) |
| verify-component | no (diagnostic only) | [verify-component.md](references/verify-component.md) |
| probe | no (import test) | [probe.md](references/probe.md) |

## Authority Order

1. User-specified component path or package.
2. Verified repo ground truth — the component's actual exports, imports, and consumers.
3. The mode reference for the selected mode (audit / verify / probe).
4. Protected file list in verify-component reference — read-only; escalate to GMP for edits.
5. `Unknown` — STOP rather than assert unproven wiring.

## Ownership Boundary

Owns exactly three read-only modes: **AUDIT COMPONENT**, **VERIFY COMPONENT**,
**RUNTIME PROBE**.

Does not own DAG mechanics. This skill teaches no DAG construction,
registration, or discovery conventions; if a mode is ever backed by a DAG, it
references that DAG's canonical path under `workflows/dags/` and nothing more.
Authoring, updating, validating, or registering a DAG is `l9-dag-authoring`.

A DAG is an implementation detail of a mode here, never this skill's identity.

## Resource Map

- [references/component-audit.md](references/component-audit.md) — export/wiring/API audit levels.
- [references/verify-component.md](references/verify-component.md) — deterministic read-only verification.
- [references/probe.md](references/probe.md) — safe runtime import probe.

## Validation

Verify and probe modes MUST NOT write code. Protected-file fixes → escalate to l9-gmp-protocol.

## Failure Handling

Missing component path → STOP. Import failure → HARD FAIL with evidence table.
