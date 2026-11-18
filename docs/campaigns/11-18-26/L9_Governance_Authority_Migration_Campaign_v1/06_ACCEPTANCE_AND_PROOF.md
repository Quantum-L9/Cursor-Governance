# Definition of Done and campaign closure receipt

A campaign PR, green unit test or complete ZIP is not an organization enforcement verdict. CTO must reconcile every required evidence row below against the **exact final repository commits and actual live controls**, mark `PASS`, `BLOCKED` or `NOT_PROVEN`, and cite the observation. No row disappears by omission. All mandatory rows must be PASS before declaring the *entire campaign* complete.

| ID | Mandatory acceptance | Required evidence, exact subject | Owner |
| --- | --- | --- | --- |
| D01 | Canonical owner unique | `.github` exact policy path, admission record/digest, Cursor `canonical:false`, no active competing source | A,C |
| D02 | 13 invariants, 8 controls, versioned assertion semantics preserved | ID census/diff v4 predecessor vs admitted successor, explicitly dispositioned changes | A |
| D03 | L9-ORG-007 contradiction eliminated | Human-authorized owner merge, current check/ruleset requirements, CTRL-006/007 consistency tests | A |
| D04 | Inventory vs applicability unambiguous | Archived/fork-inclusive register, explicit class, exclusions and per-control applicability | A,F |
| D05 | Release immutable and authentic | Actual merged SHA, payload/schema/registry digests, verified signed release and required in-toto attestation | B |
| D06 | Operating-plane consumer binds source | Current org-policy binding and existing semantic @2 independently verified at immutable coordinates | C |
| D07 | Local operational behavior preserved | Behavioral probes of changed CTO/planner/architect/coding/L4/adapter/publication paths, without a new human bottleneck. This is not an `OPEN_PR=0 make pr` rehearsal | C |
| D08 | Invalid governed operating action denied | Real owner mismatch, unknown critical assertion and digest tamper at an owning action boundary; traceable receipt | C,M,E |
| D09 | Legacy L9-Ops-MCP compatibility works | Original owner rule remains, new immutable provenance, valid + negative tests | M |
| D10 | Core policy gate non-skippably contributes to required result | Pinned release, failed policy causes `Analyze (central Core)` failure on exact test head; valid case passes | E |
| D11 | Live GitHub ruleset blocks a negative PR | Actual PR/check/merge-block observation (not JSON, not unit fixture); P0/P1/P2 coverage and verified self-governed applicability | F |
| D12 | Bypass/exception controls have honest state | Current live bypass actors, authorization/expiry/audit mechanism or explicitly BLOCKED, no fake control assurance | F |
| D13 | No duplicate ownership or uncontrolled repo writes | Changed-file scope/PR URLs; exactly one writer per worktree; no SDK/template edits; no global semantic invariant duplication | CTO |
| D14 | Publication and merging governed | Each PR created via verified `make pr` SSOT; owner-only admission/merge decision on exact subject; native checks and relevant required checks | CTO |
| D15 | Every scope finding dispositioned | Evidence matrix, blocked items with owner, final status and smallest next action; no hidden `PARTIAL` claimed `PASS` | CTO |
| D16 | Every active operating-plane action classified and governed as applicable | Versioned inventory from actual active commands/modes/skills/hooks/adapters/PE/CLI dispatch, each action effect/authority class, real owner gate, applicable global invariant/org-policy binding, valid and denied witness or justified non-applicability; no unclassified side-effecting action | C,CTO |

## Required live challenge set

For each material platform control, collect **one known-good and one known-bad** exact immutable subject under the same policy release, current target, required workflow and live ruleset. Show the bad case actually fails a required job and cannot merge without bypass, not merely that a standalone script exits nonzero. Do not write harmful test changes into production branches: use disposable branches/PRs in authorized writable repos with normal reviewable publication and no bypass. The test PR itself requires a permitted writing scope, so do not invent one in unlisted repositories. If no safe negative PR exists inside scope, mark live denial unproven and state the blocker.

## Evidence record, use one per receipt/finding

```
ID: DXX
status: PASS | BLOCKED | NOT_PROVEN
requirement: ...
governing_policy: path + exact SHA + policy ID/version
subject: repository + exact SHA/PR head + target branch
source_observed: URL/path/blob SHA or tool evidence
validator: real owner tool/job and version, no guessed command
execution: actual run URL/date/outcome, or NOT_RUN
positive_witness: ...
negative_witness: ...
platform_control: ruleset ID / check context / live source / applicable scope
owner_authorization: exact source and actor where required; UNKNOWN is not consent
residual: ...
next_action: minimal named owner action if blocked
```

Do not call this a canonical `l9.*` receipt or claim it passed an external producer validator. This is a local operator-facing evidence ledger. Apply current formal L9 receipt/authority contracts **if the verified owner demands them**; don't synthesize them from prose.

## Final report template

```
CAMPAIGN: L9-ORG-AUTHORITY-CUTOVER-2026-11-18-v1
BASELINES: <all four fresh initial SHAs>
FINAL_REVISIONS: <all final SHAs with source URLs>
ADMISSION: <exact .github approved subject, decision and merger>
RELEASE: <immutable policy SHA, signed digest and attestation verification>
PRs: <list of exact reviewable PR URLs, status and merge SHAs>
CONTROL_MATRIX: <D01..D16, PASS/BLOCKED/NOT_PROVEN, evidence link>
ORG_CENSUS: <registered, in-scope, exempt, not-applicable, unverifiable counts and reasons>
CORE_ENFORCEMENT: <exact required context, good/bad PR observations>
AGENTIC_OPERATION: <real positive/negative path receipts and unchanged authorized behavior>
PLATFORM_BYPASS: <live actor IDs/modes plus auditability and treatment>
UNKNOWN: <specific remaining gaps and responsible owner>
DECISION: PASS | PARTIAL | BLOCKED
MINIMUM_SAFE_NEXT_ACTION: <single highest blocker owner/action, or no action if PASS>
```

**PASS** means every D01-D16 is independently evidenced PASS, mandatory negative paths actually block and no unresolved critical authority/enforcement gap remains. **PARTIAL** means some accepted work completed but other mandatory rows are not evidenced. **BLOCKED** means the next required owner/permission/signing/external-control action prevents the relevant completion path. Do not convert missing observation into unsupported PASS.

## No indefinite mission expansion

After the last material mandatory criterion is proven, close. Optional org CI optimization, a new world-model graph, distributed skill mass refactor, new SDK architecture, unapproved repository additions and policy refinements unrelated to this migration are Phase 2. If a true frozen-architecture contradiction appears, stop only the affected lane and request an authorized successor decision; do not rewrite the boundary while executing.
