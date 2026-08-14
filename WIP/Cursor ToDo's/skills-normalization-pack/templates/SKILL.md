---
name: folder-name-exactly
description: what this does in one clause. use when <trigger>, <trigger>, or <trigger>. do not use when <near-miss case>.
paths: optional/glob/**, **/*.ext
disable-model-invocation: false
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, area]
---

# Skill name

## Scope

Which tasks activate this and which explicitly do not.

## Source of truth

Which files, commands, or specs are authoritative for this workflow.

## Procedure

1. Numbered, deterministic steps.
2. Point at scripts for anything that should not be improvised:
   `scripts/do-the-thing.sh`
3. Keep this file lean. Push depth into sibling reference files.

## Outputs

What must exist when this completes - a diff, a report, a passing gate.

## Stop conditions

When to pause and report a blocker instead of improvising. Be explicit; this
is the difference between autonomy and damage.
