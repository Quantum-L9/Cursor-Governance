---
name: l9-structured-reasoning-deprecated
description: deprecated block-protocol structured reasoning pack retained for reference only. do not activate. use l9-structured-reasoning instead, which owns adaptive routing, evidence ledgers, and document-corpus modes.
disable-model-invocation: true
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, reasoning, deprecated]
owner: igor_beylin
status: deprecated
version: 1.1.0
updated: 2026-08-06
superseded_by: l9-structured-reasoning
---

# Structured Reasoning (Deprecated)

**Deprecated.** Do not activate this pack.

Canonical replacement: `skills/l9-structured-reasoning/` (formerly the 10x rebuild).

## Why deprecated

- Fixed Blocks 0–11 created ceremonial token drag.
- Overlapping mode taxonomies fought with domain Skills.
- Confidence percentages were uncalibrated.
- Document-corpus modes and adaptive routing now live in the canonical pack.

## Migration

| Need | Use |
|---|---|
| Planning / review / architecture / debug / decisions | `l9-structured-reasoning` |
| Multi-document corpus analysis | `l9-structured-reasoning` → `references/document-corpus-reasoning.md` |
| Implementation planning worksheets | `l9-plan` (preferred) or `l9-structured-reasoning` `implementation_plan` profile |

References under this directory remain for historical comparison only.
