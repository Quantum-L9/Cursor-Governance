<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: cross_repo_routing
tags: [issues, cross-repo, owner, ssot]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-11
/L9_META -->

# Cross-Repo Routing

Pick the **obvious owning repo** before mutating. Wrong-owner fixes deepen drift.

## Preference order (highest first)

1. **Declared SSOT** — package publishes from repo X; consumers depend on X
2. **Shared library / template** — `l9-*` package, Gate SDK, router package home
3. **Governance** — only when the defect is governance wiring/law/skills
4. **Issue-filing repo** — last resort when the behavior is truly local

## Evidence required before mutate

Collect at least two of:

- Issue body names the shared artifact and the other repo
- `package.json` / pyproject dependency points at a Quantum-L9 package
- Import paths or lockfile entries show consumer vs publisher
- README / ADR declares ownership

If evidence conflicts → STOP; ask; do not patch both sides.

## Multi-issue comment rule

When fixing CROSS_REPO, comment on **every** issue in the sticky cluster (same
canonical unblock body, per-repo `owner_repo` + PR/commit links).

## Anti-patterns

- Copying the same fix into two consumers instead of fixing the publisher
- “Updating both bots” without a shared version bump
- Closing consumer issues while the SSOT still drifts
