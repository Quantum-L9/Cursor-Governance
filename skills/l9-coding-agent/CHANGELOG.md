# Changelog

## 1.4.0 - 2026-10-12

- Intake now binds applicable L9 global invariants from `Quantum-L9/.github`, before any mutation and in every mode, through the `l9.projection/cursor-governance-operating-plane@1` profile (`integrations/L9_RUNTIME_BINDING.yaml#canonical_invariant_binding`). The pack references upstream law by identity and digest and holds no copy of it.
- Added `scripts/verify_canonical_binding.py`, a consumer-only verifier. It checks a producer-emitted `l9.projection-artifact/v1` and `l9.compiler-receipt/v1` against an exact, clean `.github` checkout:
  - owner origin, revision, and source registry;
  - profile identity and selector coverage;
  - upstream required fields, read from the upstream schemas;
  - recomputed digests;
  - payload fidelity to the source;
  - receipt binding.

  It never emits a projection.
- The receipt producer must hold the `projection` role that `.github` assigns in `vocabulary.yaml` `organizational_target`. Receipts are unkeyed, so this check narrows producer identity but does not authenticate it.
- Re-checking a prior binding re-verifies its artifact and receipt; the record alone is never trusted. A change to any bound source, profile, invariant or projection digest returns `STALE`.
- Unexpected input shapes return a typed `BLOCKED`/`REJECTED` status instead of crashing.
- Registered the reason code `BLOCKED_UPSTREAM_PROJECTION_PRODUCER` (`catalogs/REASON_CODES.yaml` 1.2.0).
- A non-`BOUND`/`CURRENT` outcome blocks mutation. There is no fallback to local law. Only an explicit current user instruction may let a run proceed with the `Unknown` recorded.
- No executable producer for this profile exists at `.github@1f42b33` or `l9-semantic-compiler-engine@a1c4104`, so a live binding currently ends `BLOCKED_UPSTREAM_PROJECTION_PRODUCER`.
- Enforcement is instructional; no host hook enforces verifier invocation.
- `SKILL.md` is byte-identical to 1.3.0, and its frontmatter `metadata.version` still reads 1.3.0. The intake route lives in `runtime/BOOTSTRAP.yaml`, which `SKILL.md` already names as the first and only read.
  - Reason: `ops/generated/skill-registry.json` and the Claude adapter registry pin `skill_sha256` of `SKILL.md`, and both lie outside this pack.
  - Updating the frontmatter needs an authorized registry regeneration.
- Behavior conformance grows from 40 to 52 cases (CA-E41 to CA-E52). The lazy-bootstrap and runtime-alignment validators now check the intake binding route, its procedure-only keys and the reason code, and run three upstream-free negative controls.

## 1.3.0 repository install - 2026-09-28

- Installed into `Quantum-L9/Cursor-Governance` at `skills/l9-coding-agent/` as the `explicit_only` routing tier, beside its sibling `l9-global-architect`.
- Added `disable-model-invocation: true` to `SKILL.md` frontmatter, which the `explicit_only` tier requires. No other byte of the compiled 1.3.0 pack changed, and no runtime semantics changed.
- Pack version stays 1.3.0: the install adapts invocation, not behavior.

## 1.3.0 - 2026-09-27

- Applied the Validate & Repair v1.0 execution kernel recursively to the complete v1.2.0 pack.
- Added explicit inspection-scope vs modification-scope law.
- Added dependency-aware target graph, evidence-backed finding matrix, root-cause fix mapping, repair priority, and traceability requirements.
- Added whole-target inventory guard, explicit validation result states, final hygiene, and regression requirements.
- Added exact validated-state-to-delivered-state handoff law.
- Added evidence-backed recursive-pass convergence rule; pass count is not readiness evidence.
- Expanded behavior conformance from 28 to 40 cases.
- Preserved GAR/Coding Agent authority split, lazy bootstrap, and implementation-detail sovereignty.

## 1.2.0 - 2026-09-27

- Recompiled under `l9-skill-compiler` v3.8.0 exemplary workflow.
- Added canonical nested frontmatter metadata and exemplary tier provenance.
- Moved `expertise_model.yaml` and `skill_intelligence_report.yaml` to canonical pack-root locations.
- Retired duplicate `metadata/L9_META.yaml`.
- Added README, RUNBOOK, MANIFEST, and VALIDATION operator/release surfaces required for large packs.
- Hardened lazy package routing so exemplary/operator artifacts never enter normal coding intake.
- Added activation/reject conformance cases CA-E21 through CA-E28.
- Preserved the semantic-envelope model, implementation-detail sovereignty, exact-revision evidence, and GAR sibling boundary.
- Changed runtime package format for v3.8.0 packaging: distributable ZIP now places `SKILL.md` at archive root.

## 1.1.0 - 2026-09-27

- Added `runtime/BOOTSTRAP.yaml` as the canonical lazy stage router.
- Replaced eager full-runtime hydration with intake, implementation, validation, convergence, and conditional load groups.
- Added package-wide inventory classification and recursive reachability validation.
- Added `scripts/validate_lazy_bootstrap.py` and integrated it into runtime alignment validation.
- Added loader behavior cases CA-E16 through CA-E20.
- Expanded `SKILL.md` into a context-light routing control plane that references every critical runtime concern without loading it eagerly.
- Kept GAR, L9 runtime, failure catalogs, schemas, evals, and skill-intelligence artifacts conditional.
