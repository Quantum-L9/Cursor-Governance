<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: operator
role: runbook
version: 3.9.0
status: active
-->

# Runbook

## Create or rebuild a skill

1. Inventory all supplied sources and existing skill files.
2. Select the mode in `SKILL.md`.
3. Produce Gate A. Stop if the source is insufficient or contradictory.
4. For exemplary work, produce `expertise_model.yaml` before the file tree.
5. When the request would create a new pack, run `scripts/scan_skill_topology.py <request.json>` and follow its decision (`references/topology-scan.md`). Only `CREATE_NEW` permits a new pack.
6. Produce Gate C with an explicit file allowlist.
7. Build complete files.
8. Run `scripts/validate_skill_pack.py`, `scripts/validate_exemplary_skill.py`, and any domain-specific tests. Record only checks that ran.
9. Record evidence in Gate E and `skill_intelligence_report.yaml`.
10. Apply only the platform adapters requested.
11. Package the staged runtime file set as root-flat `skill.zip`; verify `SKILL.md` is the first/root entry, no wrapper directory exists, and development-only tests did not leak.

## Diagnose a failed pack

Fix in this order: broken authority or source conflicts, missing structure, broken references, stubs or placeholders, failing scripts, weak activation, portability defects, then cosmetics.

## Release rule

No archive ships when validation is failed, blocked, or unverified. Preserve useful components and classify the pack honestly instead.
