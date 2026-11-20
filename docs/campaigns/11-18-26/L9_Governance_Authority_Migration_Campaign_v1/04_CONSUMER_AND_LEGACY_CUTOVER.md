# Operating-plane and legacy consumer cutover contract

## Cursor-Governance: local authority remains, global policy authorship ends

Only after the `.github` immutable release is authentic and current:

1. Generate or bind a **read-only** local org-policy mirror compatible with `ORG_INVARIANTS.yaml`'s historical consumers. It must not retain `canonical: true` for global policy, self-named `metadata.canonical_source`, or editable-global-source semantics. Bind exact upstream repository/path/SHA and verified policy/schema/assertion digests; generated provenance must be separate from authoritative payload under the admitted canonicalization contract.
2. A versioned **local consumer binding** should reference the canonical immutable org-policy release and declare the applicable policy operations. Reuse existing Cursor `governance/authority-bindings/` mechanisms; no new global projection profile by default. Existing `l9.projection/cursor-governance-operating-plane@2` continues to supply the eight **global semantic** classes and remains source-verified under its own contract. The two inputs retain separate authorities and independent currentness.
3. Move or demote local copies of `governance/ASSERTION_TYPES.yaml`, `schemas/org-invariants.schema.json`, `releases/POLICY_RELEASE.schema.yaml` and `ops/scripts/validate_org_policy.py` into **consumer verification** roles if they are still required; they cannot be editable second normative owners. Prefer a minimal proxy/verifier to three redundant snapshots. Preserve existing runtime checks until equivalent new checks are operational.
4. Retarget real operating-path policy checks, not every prompt: CTO program approval/dispatch, architect/planner change proposals, bounded coding delegation, L4 work and publish gates, adapter activation, repo creation/publish routing and governance bypass. **Enumerate every active actor-invokable operating-plane entrypoint** by inspecting the actual command/skill/adapter/host/CLI/PE registries and authoritative dispatch code. Classify each entrypoint by side effect, authority-sensitive decision, policy applicability, actual owning gate and tested allowed/denied outcome. For a purely read-only/non-governed action, record an evidence-backed `NOT_APPLICABLE` classification rather than silently omitting it. A category-level sample is not evidence that an unenumerated write action is governed. Track *which action* is controlled by *which policy or global invariant* at *which entry/commit/publication boundary*, and observe at least one denial for each distinct material enforcement mechanism. An instruction in `AGENTS.md` by itself is not a host-enforced gate.
5. Correct `AGENTS.md`, `CANONICAL_LAW.md`, `README`/`INVARIANTS.md`, `governance/POLICY_MODEL.md`, `TRUST_MODEL.md`, `CHANGE_PROCESS.md` and `docs/governance/ORG_INVARIANTS.md` where their current **global** authorship claims are active. Preserve local runtime, skills, L4, symlinks, one `make pr`, adapters, autonomy and program ownership. The title `CANONICAL_LAW` may remain for **local operating law** if context unambiguously scopes it; don't impose a ceremonial rename/refactor.
6. Update the existing Cursor `validate-org-policy` workflow/test ownership so it verifies the immutable upstream release and its applicable local binding, not a forked global author. Preserve changed-file gate and unrelated tests. Keep this lane in its own branch/worktree branched from fetched `origin/main`. #1036 is not that base.

### Local consuming behavior, including failure cases

| Probe | Expected |
| --- | --- |
| Verified release and exact payload | Local org-policy binding accepts, with source and digest visible. |
| Mutable upstream `main` only, no immutable release | Deny a *blocking claim* or stop the policy-sensitive action as required; cannot silently trust `main`. |
| Missing or changed digest | Fail closed at actual governed operation. |
| Unknown critical assertion type/version | Fail closed; do not reinterpret as advisory or success. |
| Human authority missing for governance-sensitive merge | Agent must not impersonate approval; block only that change while other work continues. |
| Globally prohibited repo destination (e.g. personal-account owner) | Actual publish/birth path denies and emits evidence. |
| Valid ordinary autonomous delegated action | Remains functional without extra human questions. |
| CI native/`make pr` normal workflow | Unchanged except legitimate new policy predicate and evidence. |

## L9-Ops-MCP: compatibility lane (not broad migration by guess)

Its current `ORG_INVARIANTS.yaml` is a small *legacy v1-style* org owner block, with `canonical_source` pointed at Cursor-Governance's moving `main`. Its `scripts/validate_org_invariants.py` merely scans content and forbidden owner patterns. It is NOT already a complete or digest-verified 4.0.0 mirror. Blind replacement with a large new YAML shape could break established tooling.

After release B:

- Determine the actual readers and action boundary for `ORG_INVARIANTS.yaml` and script/test. Freeze the tested legacy fields used by the repository's birth/routing behavior.
- Adapt the compatibility surface so it derives/validates the **approved `.github` immutable** policy ID/version/digest, not a changing Cursor branch. A local reduced view is allowed only with a deterministic, declared projection contract whose provenance can be checked against the full canonical payload. Do not claim byte-identical full policy if only a projection exists.
- Preserve `owner: Quantum-L9`, personal-owner denial, fail-closed birth/publish and the existing validator's supported invocation. Tighten source checks without making arbitrary string search a cryptographic verifier. Add positive and tamper/mutable-ref/forbidden-destination negatives.
- If no current consumer code can verify the full signed release safely, report exact missing dependency and leave the legacy control functioning while blocking claims of fully migrated cryptographic policy consumption. Do not route an unsafe write around the guard.

## Cross-repository adapter inventory

Scope is the *Cursor-Governance owning operating plane* and one explicitly observed legacy consumer, **not** a wholesale rewrite of every org repo. Run read-only inventory from the authoritative registry. Classify each discovered direct `Cursor-Governance/ORG_INVARIANTS.yaml`, `CANONICAL_LAW` global-policy claim, `L9-ORG` mirror, and policy digest consumer. Change an additional repository only after separate writable authorization; otherwise report precise remaining evidence and do not count the unknown consumer as successfully cut over.

## Cutover barrier

Consumer PRs may be prepared in independent worktrees against frozen candidate artifacts, but cannot **enable or claim** final consumption until admission A, signed release B, digest verification and native positive/negative tests are complete. Deleting the last legacy canonical pointer is not sufficient: require actual policy-sensitive action denial and valid action allowance. Protect existing operator autonomy from unrelated approval gates.
