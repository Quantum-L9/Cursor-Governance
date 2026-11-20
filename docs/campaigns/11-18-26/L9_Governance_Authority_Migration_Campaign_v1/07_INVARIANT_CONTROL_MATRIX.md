# Policy invariants, existing controls and proof owner

This is a **handoff trace**, not a second canonical invariant registry. Check every statement against source-owner v4 predecessor and the successor admitted in A. Stable `L9-ORG-*` ID refers to the actual source record, not this paraphrase. The named gate is a proposed or observed integration seam to verify, **not** an assertion of deployed enforcement.

| Policy ID | Current required outcome | Minimum owner/gate verification | Mandatory negative or coverage witness |
| --- | --- | --- | --- |
| L9-ORG-001 | Birth happens under Quantum-L9 approved creation path | `.github` provisioner + `l9-repo-template` read-only birth integration | Other org/personal owner refused at birth or blocked as an unavailable platform-enforcement claim. |
| L9-ORG-002 | Governed repo remains Quantum-L9-owned | Registry completeness plus organization inventory and platform/transfer authority | Unknown/changed owner not classified PASS; out-of-org transfer prevention only if platform actually blocks it. |
| L9-ORG-003 | Published code/artifacts target approved org repo | Cursor publish-authority and repo-routing gates, authorized destinations | A personal owner target denied in an actual routed operation. |
| L9-ORG-004 | Unique canonical org-policy source | `.github/policies/` admission and Cursor consumer binding | Cursor-as-authoritative source or unapproved alternate source rejected. |
| L9-ORG-005 | Mirrors correspond to immutable approved release | Signed B provenance + Cursor/L9-Ops consumer verifier | Changed digest / mutable branch ref rejected, not merely text linted. |
| L9-ORG-006 | Consumer cannot weaken governing policy | Core source-immutable check, local operation gates | PR-controlled waiver, local policy or substituted payload cannot disable critical policy. |
| L9-ORG-007 | Exact human owner authorization for sensitive changes | Actual admission/merge authority and independent required CI | Agent self-approval or stale owner decision rejected, one legitimate owner remains permitted. |
| L9-ORG-008 | Governance executable refs immutable | Core action/reusable refs + existing `.github` SHA audit | Mutable action/workflow reference rejected under applicable policy. |
| L9-ORG-009 | Enforcement claims backed by reproducible evidence | Signed release, live ruleset and good/bad merge test | Green unit suite without live required-job denial not recorded as blocking assurance. |
| L9-ORG-010 | Preventive and detective coverage per critical invariant | Control census with one actual prevention and detection path | Missing control cannot be counted just because declared; report inability to prove. |
| L9-ORG-011 | Every in-scope repo classified and governed | `.github` registry + real ruleset coverage, separate applicability | Unknown class, unlisted hosted repo, excluded seed path not automatically exempt. |
| L9-ORG-012 | Exemption scoped, approved, temporary | Policy owner exception ledger and current enforcement gate | Expired, overbroad or unauthorized exemption rejected. |
| L9-ORG-013 | Bypass authorized, timed, auditable | Live ruleset bypass actor audit + approved break-glass record | Privileged bypass lacking proper trail cannot be called verified or safe. |

## Existing 8 control records: disposition requirements

- `L9-CTRL-001` approved provisioner: confirm read-only birth mechanism in `l9-repo-template` and actually authorized owner-only creation, or leave unverified. Not equivalent to the entire birth pipeline merely existing.
- `L9-CTRL-002` organization repository inventory: use `.github/ops/registry-completeness.js`, classify incomplete pagination and stale state.
- `L9-CTRL-003` canonical policy validator: migrate existing Cursor validation to `.github` and prove strict type/source/reference closure.
- `L9-CTRL-004` deterministic mirror renderer: find the actual existing renderer and digest profile. If none exists, record `BLOCKED` and the smallest existing owner path. Do not create a new release product.
- `L9-CTRL-005` consumer required check: reconcile named required check with existing live `Analyze (central Core)` and prove actual failure propagates.
- `L9-CTRL-006` organization ruleset: reconcile `strict`, bypass actors and applicability with real platform state, not desired JSON only; remove second-human contradiction with L9-ORG-007 without weakening branch protection.
- `L9-CTRL-007` governance authorizer: preserve explicit exact human owner authorization, not a fabricated separate codeowner mandate.
- `L9-CTRL-008` break-glass audit: actual event/expiry/incident trace required; missing platform permission means UNKNOWN.

Each control must cite its current authoritative owner, real entrypoint, verified test/evaluation and independent live proof before status changes. A failed, unimplemented or unobservable control is a reported campaign deficit, not a reason to remove its invariant.

## High-value minimum action coverage for Cursor-Governance

| Operating action | Expected governing input | Appropriate owner/gate to verify | Failure probe |
| --- | --- | --- | --- |
| CTO program delegation | Global authority/grant + org-policy constraints | CTO program execution authority check | Agent requests org-policy-author change without owner grant. |
| Architect/Planner recommendations that cause state change | Global scoped authority, local decision binding | Existing mode/handoff and write authorization | Recommendation treated as automatic authority or plan mutation. |
| Coding-agent worktree edits and branch creation | Actual local repo authorization, isolation, one-writer rule | Cursor executor/worktree launcher and L4 | Unlisted repo write attempt blocked. |
| Normal publish and PR creation | Current ownership/routing policy, approval, L4 | Actual Cursor `make pr` preflight+gate+publisher | Disallowed org target or missing L4 denied; valid PR works. |
| Repo birth and registration | Owner and registry-class policy | Existing repo-template `.github` birth integration | Birth without authorized Quantum-L9 identity denied. |
| Adapter/host session activation | Verified current global semantic projection and release | Existing adapter/bootstrap consumption seam | Stale or changed upstream release cannot grant enlarged authority. |
| Governance-sensitive merge | Human owner exact-head authorization and required checks | GitHub actual branch ruleset + CTO ceremony | No legitimate owner authorization blocked, agent-as-human rejected. |
| Emergency bypass | Approved scoped break-glass record | Actual ruleset and audit owner | Expired/uncounted bypass cannot satisfy lawful authorization. |

The above is the **minimum representative action set**, not the complete D16 registry. CTO must enumerate *all active callable entrypoints* from existing mode, commands, skills, hooks, adapters, L4, planner/architect and program-execution registries, trace each side-effecting entrypoint to an owner authorization/policy gate and record exact valid/denied evidence at each distinct gate. Derive the inventory from live source rather than a manually guessed static list. For every row record `COVERED`, `NOT_APPLICABLE` with evidence, `UNKNOWN`, or `GAP`; do not assert the host enforces a skill instruction without an observed host boundary. Unenumerated side-effecting entrypoints prevent a full PASS. Keep the matrix as a consumer assurance output for D07-D12 and D16, not as new organization policy.
