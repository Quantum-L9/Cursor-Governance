<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: operator
role: runbook
version: 3.8.0
status: active
-->

# Runbook

## Create or rebuild a skill

1. Inventory all supplied sources and existing skill files.
2. Select the mode in `SKILL.md`.
3. Produce Gate A. Stop if the source is insufficient or contradictory.
4. For exemplary work, produce `expertise_model.yaml` before the file tree.
5. Produce Gate C with an explicit file allowlist.
6. Build complete files.
7. Run both validators and any domain-specific tests.
8. Record evidence in Gate E and `skill_intelligence_report.yaml`.
9. Apply only the platform adapters requested.
10. Package the staged runtime file set as root-flat `skill.zip`; verify `SKILL.md` is the first/root entry, no wrapper directory exists, and development-only tests did not leak.

## Diagnose a failed pack

Fix in this order: broken authority or source conflicts, missing structure, broken references, stubs or placeholders, failing scripts, weak activation, portability defects, then cosmetics.

## Release rule

No archive ships when validation is failed, blocked, or unverified. Preserve useful components and classify the pack honestly instead.
