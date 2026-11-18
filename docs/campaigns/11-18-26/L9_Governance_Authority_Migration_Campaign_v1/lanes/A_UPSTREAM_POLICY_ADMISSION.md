```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/.github
  read_only:
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/l9-ci-core
    - https://github.com/Quantum-L9/l9-ci-sdk
  unlisted_repositories: no_access
```

# A: admit org-policy authority at `.github`

**Executor:** the activating CTO session. A pool agent must not clone, branch, or push this repository. **Start:** after S freezes current authority and rules out overlapping `.github` PRs. **One `.github` worktree,** created with `agent_worktree_start.sh` from a dedicated clone. No editing Cursor source; use it as historical predecessor input. Authority comes from live `.github/semantics/authority_model.yaml` and its owner-approved admission process, not from this pack. Publication and the proof that push works are in `09_EXECUTION_BINDING.md`. This launch chat is not the exact-head admission.

## Editable surfaces

Within `.github`, only existing `policies/` owner surfaces or narrowly justified successors, their direct schema/assertion registry, validator, native tests, ADR and release/admission metadata, and affected policy-facing docs. `semantics/authority_model.yaml`, `invariants.yaml`, `projection_profiles.yaml`, `repository_registry.yaml` and external product code are **read-only for this lane**, unless separately authorized after resolving a true inconsistency at their owner. No gratuitous Semantic Foundation version churn.

## Work contract

- Extract predecessor `quantum-l9.org-invariants` policy 4.0.0 with exact 13 `L9-ORG-001..013` and eight `L9-CTRL-001..008` entries. Verify SHA/metadata, cross-references and native schema grammar; preserve all meanings not explicitly corrected.
- Admit one source path under `.github` organization policy owner. Correct `metadata.canonical_source`, `L9-ORG-004` and active policy pointers. Remove competing owner claims from new artifact; historical lineage remains historical.
- Correct contradictory L9-ORG-007 vs CTRL-006/007, preserving one authorized human owner and separate platform check/bypass obligations. Correct stale required control status context, scope inventory vs applicability, and source-relative protected paths; do not broaden denial power through ambiguous defaults.
- Preserve assertion type/version semantics and fail-closed critical behavior; if evaluator meaning changes, version the type and record explicit compatibility. Retain RFC8785 canonicalization/digest profile and signatures/in-toto for blocking rollout. Keep control state observational until proved.
- Reuse existing `.github` validator/testing mechanism where available, adapting predecessor Cursor `validate_org_policy.py` and tests to the owner rather than inventing an unproved CLI. Add minimal positive/negative path fixtures; require schema, IDs, current authority and full reference closure checks.
- Produce the required ADR/decision and exact subject digest, record known predecessor, compatibility and reasoned delta. Seek the current policy owner's human authorization for the exact PR/head/digest and merge using the verified repository ceremony and applicable checks. No auto admission from passing tests. Revalidate changed head against owner decision.

## Done

Native validation passed at exact head; no duplicate global owner; all invariants/controls dispositioned; owner authority and exact-head decision recorded; PR opened through `make pr` and verified merged; upstream merged commit and content digests captured. Release signing is **B**, not claimed here. Any unverified upstream requirement blocks only admission, not read-only downstream preparation.
