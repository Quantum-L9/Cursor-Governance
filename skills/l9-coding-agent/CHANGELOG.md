# Changelog

## 1.4.1 - 2026-10-12

Projection boundary correction. `.github` owns the law and profiles, a producer emits projections, an upstream publication mechanism supplies them, and this skill consumes them without running the producer.

- `RUNBOOK.md` no longer tells the executing agent to run `python -m l9_semantic_compiler project`. Intake takes an externally supplied artifact, receipt, and authority revision pin. An absent projection stays `BLOCKED_UPSTREAM_PROJECTION_PRODUCER`, and the skill does not assume a producer or publication pipeline is operational.
- `integrations/L9_RUNTIME_BINDING.yaml` 1.2.0 declares the supply boundary (`supplied_by`, `producer_execution`, `revision_pin`, `pin_rule`), rejects self-produced projections and unpinned runs, and marks receipts unauthenticated.
- F-02 (untrusted local authority revision) is repaired in `scripts/verify_canonical_binding.py`:
  - `--expect-revision` is required in both modes. Previously an unpinned run bound whatever `HEAD` the checkout claimed. An absent pin returns `BLOCKED AUTHORITY_REVISION_PIN_ABSENT`; a malformed one returns `AUTHORITY_REVISION_PIN_MALFORMED`.
  - Law bytes are read from the pinned commit's objects, and every commit, tree, and blob hash is recomputed. Working-tree edits hidden by `--skip-worktree`, replace refs, and rewritten loose objects cannot substitute law. Path traversal out of the authority tree is blocked.
  - A pin that no fetched `refs/remotes/origin/*` ref contains returns `BLOCKED AUTHORITY_REVISION_NOT_ON_ORIGIN_TRACKING_REF`.
  - Binding records state `revision_basis: caller_pinned_not_authenticated`, `content_basis: pinned_commit_objects_hash_verified`, and `producer_authentication: unauthenticated_unkeyed_receipt`.
- Added `tests/test_coding_agent_canonical_binding.py`, with 27 cases against a synthetic authority repository and no producer. Behavior conformance grows from 52 to 57 cases (CA-E53 to CA-E57). Runtime alignment adds an absent-pin negative control that checks the blocking reason.
- `SKILL.md` stays byte-identical, for the registry-pin reason recorded under 1.4.0.

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
- No executable producer for this profile existed at `.github@1f42b33` or `l9-semantic-compiler-engine@a1c4104`. Quantum-L9/l9-semantic-compiler-engine#8 adds one for the `invariants` source class (`python -m l9_semantic_compiler project`). Its real output binds through this verifier unchanged, so the live binding works for that class once #8 merges. The profile's other 8 source groups still have no producer.
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
