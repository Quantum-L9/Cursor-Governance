# Upstream admission and immutable release contract

## Target, source, and order

The canonical organization policy is to be admitted by the `Quantum-L9/.github` owner into its existing `policies/` concern. `semantics/` remains the authority, invariant, and projection foundation, **not** the repository into which all operational policy bodies are copied. Use the observed Cursor-Governance 4.0.0 artifacts as migration inputs, not as continuing global authority after the admission.

Treat these as two independently provable events:

1. **Source admission A:** merge the exact `.github` canonical policy candidate, its policy grammar, assertion registry, validators and decision record. The owner decision must bind the exact PR head and/or candidate digest through the live admission mechanism. Record source revision, owner authority, decision and immutable content. No “admitted” from a drafted PR or CI pass.
2. **Immutable release B:** open the release pull request stacked on A's open head as soon as that head exists. The release record references that head, then the merged SHA when the operator merges A, by a push to the already-open B pull request. Prove the signing/attestation chain required by the admitted policy (including in-toto when applicable), verify the immutable ref and content, and make the open head available for consumers to pin. Do not invent a release signer or present an unverified signature as proof. Do not wait for the GitHub merge before B, C, M, E, or F publish.

If the existing `.github` admission and distribution protocol can safely combine A and B without using a future unknown SHA, the CTO may combine execution while still retaining two distinct decisions and proof surfaces. Otherwise preserve this dependency, not a forced merge queue for unrelated tasks.

## Inputs that must retain traceable identity

| Current Cursor-Governance source | Successor owner in `.github` | Migration treatment |
| --- | --- | --- |
| `ORG_INVARIANTS.yaml` v4.0.0 | Existing `policies/` organizational policy concern, preferred candidate `policies/ORG_INVARIANTS.yaml` | Keep stable policy ID and 13 `L9-ORG` IDs; amend the authority references and contract contradictions. Explicit versioned successor, not an unversioned silent rewrite. |
| `governance/ASSERTION_TYPES.yaml` | The new policy owner's versioned assertion-registry sibling | Carry registered type/version definitions and unknown behavior. Avoid rewriting evaluator semantics without version bump. |
| `schemas/org-invariants.schema.json` | Policy schema owner | Replace Cursor-only path constants, preserve strict schema validation and non-duplicate definitions. |
| `releases/POLICY_RELEASE.schema.yaml` | Policy release-contract owner | Replace Cursor-only canonical repository/path constants, preserve required digests, approval reference, compatibility record and immutable ref. |
| `governance/POLICY_MODEL.md`, `TRUST_MODEL.md`, `CHANGE_PROCESS.md` | `.github` policy documentation/ADR as required | Retain needed explanations under new owner; never promote Cursor `CANONICAL_LAW.md` to the global constitutional authority. |
| `ops/scripts/validate_org_policy.py`, `tests/org_policy/`, existing workflow | `.github` policy validation implementation | Adapt tests/validator at authoritative owner, preserve duplicate-key rejection, assertion-reference validation, schemas, error behavior. Do not copy untested assumptions. |
| `L9-CTRL-001..008` and embedded assurance fields | Normative control requirements at `.github`; current-state evidence under actual verifier owner | Preserve stable control identifiers and required outcomes; distinguish declared control obligations from evidence of deployment. No copy of stale status as fresh proof. |

File names above for new `.github` successors are suggested addresses. A source-level owner census must prove no existing equivalent before creating extra files. New standalone policy owner files are justified only if an existing `.github` surface cannot carry normative policy plus independently versioned grammar safely.

## Mandatory semantic reconciliations, no optional redesign

**Authority:** `metadata.canonical_source` and `L9-ORG-004.expected` must bind `.github` to one noncompeting canonical path. Every in-policy backreference, protected path, release constant, default and documentation must use that owner. Treat historical `Cursor_Governance_is_canonical` provenance as a past claim, never as present authority.

**L9-ORG-007:** preserve the v4.0.0 owner's explicit-authorized-human rule: one authenticated human holding repository authority may approve even if author; approved operator chat/GitHub record can qualify when attributable, current and exact-head bound. `L9-CTRL-006.require_codeowner_approval` and `L9-CTRL-007.require_independent_human_review` currently conflict. Align to this owner authorization without removing non-human checks or branch protection. Distinguish the *human authority* requirement from any independently imposed GitHub platform review requirement; do not silently override a live platform setting. Align `mirror_contract` human-review wording with the chosen binding.

**Coverage:** global repository inventory includes archived and forked repositories, but operational controls may have narrower applicability. Explicitly enumerate **inventory inclusion**, **policy applicability**, **control attachment** and **reasoned exceptions**. Do not equate a class's disabled governance-caller seed with exemption from org law. Reconcile `repository_scope`, `consumer_policy` and `.github/semantics/repository_registry.yaml` without changing the latter's authority by inference.

**Required check naming:** `L9-CTRL-005` still lists `org-governance/invariants` whereas the real org required check is `Analyze (central Core)`. Prefer embedding policy evaluation under the current Core required context if provably fail-closed and non-skippable. Record the corresponding amendment to normative control capability; **do not** invent a required status and change the org ruleset in advance. If a dedicated status is indispensable, first prove the existing Core check cannot enforce the outcome and obtain an explicit source-owner decision.

**Enforcement/evidence claims:** the source `control_registry` says all eight controls absent/unenforced, despite existence of active CI, validator, repository inventory check and ruleset. Audit by direct source and platform evidence; update assertion status only when corresponding evidence is current. Do not upgrade a control merely because code or a test file exists. Preserve `unknown`, `indeterminate`, `blocked` when evidence lacks proof. Distinguish policy authorship from actual enforcement. Evidence/assurance snapshots should not be frozen inside policy as if timeless; migrate or mark as dated if their role requires.

**Trust and release:** preserve immutable revision, canonical RFC8785 digest profile (UTF-8, NFC, LF) and required signature/attestation chain unless the authorized owner explicitly admits a new versioned policy and its compatibility impact. Digest equality does not establish trusted signer identity or GitHub merge authorization. Preserve unknown critical assertion fail closed. `L9-ORG-012/013` bypass and exception conditions are not waived by this campaign.

**Authority precedence:** any local task instruction, agent prompt, doctrine or control claim that appears to outrank applicable `.github` canonical authority must be resolved against the existing global authority order and explicit user grant. Do not reinterpret a user-authorized task as permission for an agent to admit or bypass global law.

## Admission validation obligations

- One stable normalized payload with one canonical path, documented projection/mirror digest profile, complete schema and assertion registry.
- Exactly 13 distinct migrated `L9-ORG-001..013` IDs and eight `L9-CTRL-001..008` identifiers, plus a reviewed, reasoned delta for any corrected statements. No silent deletion or recategorization.
- Positive fixtures: valid policy passes strict validation; every referenced assertion type/version resolves; old consumers' expected payload where appropriate remains compatible.
- Negative fixtures: duplicate YAML keys, unknown critical assertion, wrong canonical owner, invalid assertion version, altered protected requirement, stale/incorrect digest, unauthorized policy admission, and missing/invalid release metadata must fail or remain unknown per admitted contract.
- Documentation points to the highest authoritative owner, no residual active Cursor-as-global policy claim; changed path references verified against actual repository content.
- Exact owner-approved admission decision at the declared target-class authority and the actual merged SHA. Changes after approval require reauthorization under the source contract.

## Release proof

Release identity must contain at least policy ID/version, exact `.github` source SHA, canonical path, schema digest, assertion-registry digest, payload digest, owner authorization reference, compatibility claim and the signed/attested proof required by the policy. Check actual signature verification and payload source match from a consumer-accessible immutable reference. If a necessary signer, trusted attestor or signing key is unavailable, report **B blocked** rather than publishing a fabricated or unsigned “blocking” release. Other independent lanes may continue in preparatory mode without activating enforcement.

Do not edit, push, merge, or publish during offline pack construction. All above are executor obligations for CTO.
