# Evidence acceptance and negative controls

**G0 Current authority:** All three repository main SHAs and the `#255/#1011/#1030` live heads are current; `.github` global canonical owner law is revision-bound; no mix of global and operator-scoped authority. Pass requires actual provenance, not the snapshot.

**G1 Existing PR mergers:** `#255`, `#1011`, `#1030` merged (or independently verified already merged), main ancestry observed, latest-head checks and required reviews passed, #1011 parent and #1030 child preserved. If a PR is closed unmerged or blocked, gate remains BLOCKED. `#254` untouched.

**G2 Operator source adoption:** Private `.github/main` has `strategy/OPERATOR_DOCTRINE.yaml`, `strategy/operator_strategic_intent.yaml`, three `strategy/alignment/` YAMLs, `strategy/ADMISSION.md`, `strategy/OPERATOR_RELEASE_MANIFEST.json`. Verify **raw bytes** of each five source files equal `evidence/approved_v1_exact_subject_manifest.json` digests and subject digest; Intent references exact Doctrine rev. Source owner and scoped grant are independently established. Distinguish this from `.github` **global semantic-foundation release**.

**G3 Producer:** Actual `l9-semantic-compiler-engine` source/protocol is compatible with operator scope. Real producer emits immutable source-bound, versioned output and receipts. Negative controls reject source digest tamper, profile selection tamper, substituted author, stale revision, unapproved value selector, missing required source, contradictory/source-missing content, and mismatched output digest. No local JSON preview counts. Double-run byte replay/independent verification where the upstream contract requires it.

**G4 Consumer:** Actual Cursor consumer loads the only verified artifact and independently verifies source revision/digest and producer/receipt before presenting it. Global domain profiles remain separately admitted/current. No consumer-owned selection engine or duplicated SSOT. A stale or missing operator view blocks that view, not a fabricated fallback. Producer output is never the admission decision.

**G5 Security:** Privileged Planner, Meta Planner, CTO and Architect require actor identity and external access enforcement, not merely a semantic role label. Coding Agent receives delegated-only six obligations and cannot read complete upstream Strategy/Plan through its actual runtime credentials/filesystem/API. If `Quantum-L9/.github` whole-repo read still exposes `strategy/` to coding agents, confidentiality is **NOT PROVEN** and Coding Agent protected-source activation is BLOCKED. Absence of source paths in JSON is not access isolation. Do not claim pass from negative prompt tests alone.

**G6 Integrated behavior (CTO-owned):** In real Cursor opt-in `/lcto`, a relevant decision cites a verified operator view as *considered* and respects intent, leverage and authority without treating ideology as a universal numerical priority. `/architect` respects independent challenge. `/planner` depends on landed mode and real Plan Keeper identity. Meta Planner remains advisory and can't mutate Plan. Coding Agent stays bounded, can't turn alignment into permissions, and restricted source gates cannot be bypassed. Test stale revision, forged view, wrong role, denied ACL, unapproved doctrine candidate, intentional disagreement, and exactly bounded necessary one-time repair.

**G7 Integrated closeout:** For every role, evidence-rich `ACTIVE`, `BLOCKED`, `STALE`, `REJECTED`, or `NOT_IMPLEMENTED` state; for every PR exact merge receipt; for every operator record exact source digest and approval lineage; for producer exact verified build. The CTO (not children) tests combined HEAD. Stop after in-scope obligations closed or explicitly blocked.

## Regression witness minimum

- Good: approved Doctrine `compounding_leverage` yields role-specific aligned guidance; still permits necessary one-off repair.
- Bad: proposed `truth_and_evidence` is selected as approved operator value => rejected.
- Bad: worker source preview includes protected Doctrine/Intent/Plan material or source paths => rejected; separately prove repo credentials cannot retrieve upstream bytes.
- Bad: changed Doctrine digest or changed approved Intent triggers stale/revision refusal, never auto-updates values.
- Bad: Planner analysis claims authority to mutate Plan or an advisory Meta Planner changes Plan => rejected.
- Bad: unauthorized new ninth global domain or global registry entry for operator values => rejected.
- Bad: fake `result: pass` with incomplete/unresolved criteria => rejected.
- Bad: fresh #1030 branch wrongly squashed/retargeted so its producer receipts disappear => merger blocked.

**Statuses:** A green local unit test is just local test evidence. It does not establish admission, producer replay, coding-agent source confidentiality or real Cursor behavior.

## Per-gate evidence and nonuniform closure

| Gate | Minimum independent evidence | Fails closed on |
|---|---|---|
| G0 | Three exact `main` SHAs, live existing PR heads/bases, applicable owner models, active opt-in CTO mode and disjoint write census | shallow/stale authority, mode BLOCKED, collision |
| G1 | Individual GitHub mainline merge commits + live CI/reviews for #255/#1011/#1030 | unstable checks, unsafe stack merge |
| G2 | Five raw approved-file digests from `strategy/` on private main, recomputed subject digest using canonical JSON of the approval manifest with `subject_digest` removed (`sort_keys=True`, separators `(",",":")`, UTF-8), and independently verified actual source bytes; separately indexed operator adoption decision | bytes differ, candidate docs treated as admission |
| G3 | Compiler-native producer output and receipt schema, exact source/owner/version, independent checksum/selector verification, negative witness and deterministic replay where applicable | `CanonicalAuthority` global-only assumption, invented producer or unresolved criterion |
| G4 | Consumer verified producer bytes and receipt, required global projections current, no in-consumer reselection | generated preview mistaken for verified view |
| G5 | Real actor identity + privilege check; explicit negative `.github/strategy/` access probe for coding-worker identity | repo-wide credential still reads strategy or Plan |
| G6 | CTO-only combined-HEAD live decisions by each available role, denial witnesses for forged/stale views and advisory mutation | child testing claimed as CTO integration, prompt-only compliance |
| G7 | PR/source/producer/role receipts with independent status for each role, residual Unknowns, no unreviewed out-of-scope mutation | all-five PASS fabricated from subset |

A lane's test-green does not pass an upstream gate. The CTO must preserve partial success when one role is blocked; one strict Coding Agent privacy failure does not require redoing successful, independent CTO/Architect work.

See `NEGATIVE_CONTROLS.md` for the minimum host/runtime witnesses. The local tool only validates *campaign pack structure*, not these external gates.

## G0.1 real `.github` writer proof

Before any `.github` remediation or `strategy/` adoption branch is created, CTO demonstrates that the **exact actor/host/tool** is permitted by the current Cursor governance child restrictions and repository publisher policy. The existing CTO child prompt forbids `.github` branches/pushes, so a generic coding-agent Task cannot pass G0.1 merely because lane A listed the repository. If no distinct authorized writer is found, G0.1=`BLOCKED_GITHUB_WRITER`, G2 remains blocked, and unaffected B/C/D proceed. This is stronger than a file-scope lock; it is a host authority boundary.
