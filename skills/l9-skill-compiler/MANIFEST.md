<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: release
role: manifest
version: 3.8.0
status: active
-->

# Manifest

## Release

- Name: `l9-skill-compiler`
- Version: `3.8.0`
- Tier: `exemplary`
- Canonical baseline: v3.3.0
- Release date: 2026-08-13

## Source archives

- `l9-skill-compiler-v3.2(8).zip` SHA-256 `90a657d47520170746b88ca9d7eda6b7f63e3b6116a1d7f7ef3fc42f1463e1fa`
- `l9-skill-compiler-v3.3.zip` SHA-256 `b1253722d6b9c9bfce2da8c6b835b4d655f77dd7c70239f697c818902fe1f164`
- `l9-skill-compiler-v3.4.0.zip` SHA-256 `af336f8d7deb0ee14e3f022216ce1724e74cd2dad675166902428064af79ac27`
- `l9-skill-compiler-v3.5.0.zip` SHA-256 `ac0f8b71cf15f7ed79c6d5b313a07f0296a9bc8dab178b6fc0cf0153abcd4579`

## Convergence decisions

- Retain the complete v3.3 standalone contracts, intelligence framework, and validators.
- Adopt v3.4 scope locking, gate schemas, anti-drift controls, and execution-cost controls.
- Adopt v3.5 validation evidence, recursive improvement, convergence analysis, and stronger build-quality logic.
- Remove duplicate alias contracts and unsupported custom frontmatter keys.
- Replace global personal-profile rules with scoped user instructions.
- Isolate L9 repository doctrine in `adapters/l9-platform.md`.
- Make repository wiring conditional rather than a universal completion gate.
- Package runtime distributions as exact `skill.zip` with `SKILL.md` at archive root and no wrapper directory.
- Keep source regression tests out of runtime ZIPs by default.
- Keep `validate_*.py` scripts only when the runtime control plane explicitly references them.

## Runtime distribution inventory

The runtime ZIP contains the files below except source-only development files listed afterward.


- `CHANGELOG.md`
- `MANIFEST.md`
- `README.md`
- `RUNBOOK.md`
- `SKILL.md`
- `VALIDATION.md`
- `adapters/claude-code.md`
- `adapters/cursor.md`
- `adapters/l9-platform.md`
- `adapters/manus.md`
- `expertise_model.yaml`
- `references/binding-runtime-directives.md`
- `references/build_execution_contract.md`
- `references/canonical-smart-exemplary-spec.yaml`
- `references/enforcement-gates.md`
- `references/expertise_extraction_framework.md`
- `references/file-contract.md`
- `references/kernel-agent-state.md`
- `references/kernel-anti-drift.md`
- `references/kernel-build-quality.md`
- `references/kernel-compounding-leverage.md`
- `references/kernel-convergence-architect.md`
- `references/kernel-execution-cost.md`
- `references/kernel-first-order-thinking.md`
- `references/kernel-reasoning-think-strategy.md`
- `references/kernel-recursive-improvement.md`
- `references/kernel-skill-doctrine.md`
- `references/kernel-validation-evidence.md`
- `references/kernel-zero-stub-build.md`
- `references/meta-standard.md`
- `references/output-modes.md`
- `references/platform-portability.md`
- `references/skill-pack-contract.md`
- `references/smart-exemplary-skill-contract.md`
- `schemas/gate-a-source-parse.schema.yaml`
- `schemas/gate-b-expertise-model.schema.yaml`
- `schemas/gate-c-file-tree.schema.yaml`
- `schemas/gate-d-build-manifest.schema.yaml`
- `schemas/gate-e-validation-report.schema.yaml`
- `schemas/gate-f-wiring-report.schema.yaml`
- `schemas/gate-g-package-record.schema.yaml`
- `scripts/package_skill.py`
- `scripts/validate_exemplary_skill.py`
- `scripts/validate_skill_pack.py`
- `scripts/validate_smart_exemplary_spec.py`
- `skill_intelligence_report.yaml`

## Source-only development files

- `tests/test_validators.py`
