---
name: l9-pr-remediation-deprecated
description: deprecated packaging-heavy pr remediation pack retained for reference only. do not activate. use l9-pr-remediation instead — the unified single-path pack with concurrent clusters, short polls, sonar/codeql/debt depth, and no run-report or tar deliverables.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pr, remediation, deprecated]
  owner: igor_beylin
  status: deprecated
  version: 3.5.0
  updated: 2026-08-06
  superseded_by: l9-pr-remediation
---

# PR Remediation (Deprecated)

**Deprecated.** Do not activate this pack.

Canonical replacement: `skills/l9-pr-remediation/` (v3.0.0 unified).

## Why deprecated

- Multiple operating modes (mutating / dry-run / CI-signal) slowed the hot path.
- Run-report schemas, validators, issue-file bundles, and tar.gz packaging added ceremony without faster convergence.
- Dropped SonarCloud / CodeQL / debt operational depth relative to the unified pack.
- Longer poll defaults (45s) vs unified 15s short-poll.

## Migration

| Need | Use |
|---|---|
| Converge a failing PR | `l9-pr-remediation` |
| CI vs codebase ownership | `l9-pr-remediation` → `references/ownership-boundary.md` |
| Sonar / CodeQL / debt depth | `l9-pr-remediation` + its fetch scripts |

References under this directory remain for historical comparison only.
