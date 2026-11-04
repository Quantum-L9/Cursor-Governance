# L9 PR Audit: Quantum-L9/Cursor-Governance

Audit ID: `audit.quantum-l9.cursor-governance.open-prs.2026-10-20`
Generated: `2026-10-20T23:31:37Z`
Baseline: `60aee3be82e97984099678df4a311cf23a0e462a`

## Executive verdict

- Audit: `PARTIALLY_SUCCEEDED`
- Readiness: `NOT_READY`
- Convergence: `PARTIAL`
- Coverage: `PARTIAL`
- Authority resolution: `RESOLVED`
- Combined merge readiness: `NOT_READY`
- Summary: 15 open PRs audited at exact heads. Ready to merge now: #755. Clean of blocking findings but readiness unassertable until the branch is updated from main (behind under the strict ruleset): #737, #738, #739, #741, #746, #752. Not ready: #740, #744, #745, #747, #748, #749, #750, #751. 29 findings, 11 merge-blocking. Convergence is PARTIAL: repository-wide closures and mutation probes remain UNKNOWN.
- Minimum safe next action: Merge the ready PRs in the recorded merge order, and remediate the blocking findings on #744, #745, #747–#751 and #740 at their exact heads.

## Coverage

Domain assessments: INTENT_SCOPE=UNKNOWN, COMMUNICATION_CONTRACTS=UNKNOWN, ROUTING_INTEGRATION=UNKNOWN, OWNERSHIP_AUTHORITY=UNKNOWN, STRUCTURE_SOURCE_OF_TRUTH=UNKNOWN, SCHEMA_CONFIGURATION=UNKNOWN, SECURITY=UNKNOWN, RELIABILITY_OBSERVABILITY=UNKNOWN, TESTING_VALIDATION=UNKNOWN, LEVERAGE_SIMPLICITY=UNKNOWN, CROSS_PR=UNKNOWN, CHANGE_DISCIPLINE=FAIL
Architecture policy adapters: NOT_APPLICABLE
Boundary map: PARTIAL (2 components / 1 boundaries)
Excluded/inaccessible:
- `complete repository file corpus in the deterministic census` | `BLOCKS_CONVERGENCE` | snapshots carry changed files only (repository_files_complete=false)
- `mutation-probe execution` | `BLOCKS_CONVERGENCE` | not executed in this run

## Inspection inventory

Inventoried artifacts: 177
Classes: CONFIGURATION=18, DEPENDENCY_MANIFEST=3, DOCUMENTATION=32, GENERATED=55, OTHER=2, SOURCE=26, TEST=25, WORKFLOW=16

## Recursive audit passes

- Pass 1 `DISCOVERY`: new_information=1 | 0 findings retained; machine rows dispositioned or left UNKNOWN. | next=Re-observe every finding, obligation, claim, probe and closure against the bound heads.
- Pass 2 `VERIFICATION`: new_information=0 | No new material finding discovered; UNKNOWN rows remain residual and block convergence. | next=none

## Deterministic red-team assurance

Changed symbols: 1787
Material claims: 2012
Claim states: SUPPORTED=9, REFUTED=29, NOT_APPLICABLE=0, UNKNOWN=1974
Falsification probes: SURVIVED=9, FALSIFIED=29, INCONCLUSIVE=1974, NOT_APPLICABLE=0

## PR verdicts

- PR #737: `UNKNOWN` | completeness `PASS` | correctness `PASS` | architecture `PASS` | validation `PASS`
- PR #738: `UNKNOWN` | completeness `PASS` | correctness `PASS` | architecture `PASS` | validation `PASS`
- PR #739: `UNKNOWN` | completeness `PASS` | correctness `PASS` | architecture `PASS` | validation `PASS`
- PR #740: `NOT_READY` | completeness `FAIL` | correctness `PASS` | architecture `PASS` | validation `PASS`
- PR #741: `UNKNOWN` | completeness `PASS` | correctness `PASS` | architecture `PASS` | validation `PASS`
- PR #744: `NOT_READY` | completeness `FAIL` | correctness `PASS` | architecture `FAIL` | validation `PASS`
- PR #745: `NOT_READY` | completeness `FAIL` | correctness `FAIL` | architecture `FAIL` | validation `FAIL`
- PR #746: `UNKNOWN` | completeness `PASS` | correctness `PASS` | architecture `PASS` | validation `PASS`
- PR #747: `NOT_READY` | completeness `FAIL` | correctness `FAIL` | architecture `FAIL` | validation `PASS`
- PR #748: `NOT_READY` | completeness `FAIL` | correctness `FAIL` | architecture `FAIL` | validation `FAIL`
- PR #749: `NOT_READY` | completeness `FAIL` | correctness `PASS` | architecture `FAIL` | validation `PASS`
- PR #750: `NOT_READY` | completeness `FAIL` | correctness `PASS` | architecture `FAIL` | validation `PASS`
- PR #751: `NOT_READY` | completeness `PASS` | correctness `FAIL` | architecture `FAIL` | validation `PASS`
- PR #752: `UNKNOWN` | completeness `PASS` | correctness `PASS` | architecture `PASS` | validation `PASS`
- PR #755: `READY_WITH_NON_BLOCKING_NOTES` | completeness `PASS` | correctness `PASS` | architecture `PASS` | validation `PASS`

## Findings

### F-737-F1 - CORRECTNESS - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #737
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Missing, unreadable or malformed required input precludes PASS and must not be defaulted to success. (rules/45-pre-action-verification.mdc)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: Coverage census reports 'complete' when user settings are absent or unparseable, skipping the tier-override check
Observed: When ~/.claude/settings.json is absent or malformed, the census marks the tier-override criterion satisfied and reports status complete.
Expected: When user settings are unreadable, the tier-override criterion is unresolved: status incomplete, or unknown, with a named reason, rather than complete.
Mismatch: _read_user_settings returns None for a missing file or a JSONDecodeError. tier_override_missing is then [] ('if settings is None'), and complete = not missing and not wrong_target and not tier_override_missing becomes true.; The banner printed 'skills projected: 57/57 ... — complete' and rc=0, although no explicit-only skillOverrides existed in any evaluated source.
Root cause: settings is None is treated as 'nothing missing' instead of 'not evaluated'.
Impact: Coverage census reports 'complete' when user settings are absent or unparseable, skipping the tier-override check
Closure: coverage_census with user_settings pointing at a missing or invalid file reports a non-complete status and names the unreadable settings. A test covers both cases.
Evidence IDs: E-F-737-F1-1, E-F-737-F1-2, E-AUTH-737-F1

### F-738-F1 - CROSS_PR - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #738
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Merges run through stack_safe_merge.py, which selects the merge method in code. (rules/48-make-pr-remediation.mdc)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: Sanctioned merge transport would squash #738, contradicting the merge-commit requirement of the .github#188 COMPOSER pin
Observed: #738 is unstacked, so the sanctioned merger would squash it and delete the branch. 1a57fe7 would then be reachable only through refs/pull/738/head, not from main.
Expected: Either the merge uses --merge so that 1a57fe7 stays in main's ancestry, or .github#188 is re-pinned to the squash commit on main before or immediately after merge.
Mismatch: UNSTACKED = 'squash'. select_merge_method picks squash whenever no open PR bases on the head, and merge_argv defaults delete_branch=True.; The vendored .github#188 workflow pins COMPOSER and checkout ref to Cursor-Governance@1a57fe7, a branch-only commit.; 'The pin converges on #738's merge commit once that merge is authorized (MERGE_DEPENDENCY_PENDING)'.
Root cause: This PR adds a cross-repo pin to a pre-merge branch commit, and the repo's merge-method selector does not know about that constraint.
Impact: Sanctioned merge transport would squash #738, contradicting the merge-commit requirement of the .github#188 COMPOSER pin
Closure: After merge, the COMPOSER pin in .github#188 and the vendored fixture name a commit reachable from Cursor-Governance main.
Evidence IDs: E-F-738-F1-1, E-F-738-F1-2, E-F-738-F1-3, E-F-738-F1-4, E-AUTH-738-F1

### F-738-F2 - TEST_QUALITY - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #738
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: New behaviour the plan names must be covered by tests that fail without it. (rules/95-test-fix-policy.mdc / rules/80-gmp-execution.mdc)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: head_sha-only staleness and the real l4_local delegation are not discriminated by any test
Observed: A regression that ignores head_sha, or that breaks or bypasses the l4_local judge, would ship green.
Expected: One test commits an empty or hook-rewrite commit over an unchanged tree and expects STALE. One test writes a real L4 release receipt in a temp repo and expects BOUND, then STALE after a content change.
Mismatch: STALE when the receipt head_sha differs from HEAD over identical bytes.; verify_l4_receipt imports l4_local and calls _allow_from_receipt with current_branch.; Replacing the head_sha check with 'if False' and forcing verify_l4_receipt to return BOUND both leave 73/73 passing. Tests only inject l4_binding values (test file L289-305, L1979-1990).
Root cause: The EvidenceBindingTests stale case changes file content, so the digest catches it before the head_sha check is ever reached. The L4 path has no integration test.
Impact: head_sha-only staleness and the real l4_local delegation are not discriminated by any test
Closure: Both mutations above fail at least one test.
Evidence IDs: E-F-738-F2-1, E-F-738-F2-2, E-F-738-F2-3, E-AUTH-738-F2

### F-738-F3 - CONTRACT - Low - non-blocking

Confidence: `Probable` | root cause: `CONFIRMED`
Affected PRs: #738
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: An empty applicable set is not a PASS unless the scope establishes it; partial coverage is never reported as complete. (rules/45-pre-action-verification.mdc)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: security=pass ticks '`semgrep` clean' and 'No secrets' when the wave scanned nothing
Observed: On a docs- or YAML-only diff, the body claims '`semgrep` clean' although semgrep never ran. On a diff that is entirely excluded, it claims no secrets although gitleaks never ran.
Expected: The receipt records which scanners ran, for example security=pass with a scanned or skipped breakdown. The composer ticks a box only when its scanner ran, or marks it 'not applicable: no source files'.
Mismatch: With no scannable changed files after exclusions, the script SKIPs and exits 0 ('RESULT: PASS — security gate (nothing in scope)') without running gitleaks or semgrep.; Semgrep SKIPs when no .py/.ts/.js file changed.; Any non-advisory passing run writes security=pass, whatever was skipped.
Root cause: The receipt's security field is a single word that does not distinguish a scanner that ran from one that was out of scope.
Impact: security=pass ticks '`semgrep` clean' and 'No secrets' when the wave scanned nothing
Closure: A gate run whose security wave skipped semgrep or skipped everything produces a body with that box unticked and annotated, not ticked.
Evidence IDs: E-F-738-F3-1, E-F-738-F3-2, E-F-738-F3-3, E-F-738-F3-4, E-AUTH-738-F3

### F-738-F4 - RELIABILITY - High - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #738
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: The default publish path on every surface (Cursor, Claude Code desktop, Claude Code Mobile) is PR_REMEDIATE=0 make pr; there is no raw-push fallback. (rules/48-make-pr-remediation.mdc)
Origin: `PRE_EXISTING` | blocking basis: `NON_BLOCKING` - Does not block merge: make pr cannot compose a body on surfaces that cannot reach <owner>/.github; #738 leaves this unchanged
Observed: In a Claude Code cloud session bound to Cursor-Governance only, make pr fails at body composition before push, so no PR can be opened through the sanctioned path. #738's own body was composed elsewhere (stamp .github@d4397e53).
Expected: The canonical template resolves, or fails over to an attested source, on every surface the publish law names. One option is the org-seeded .github/pull_request_template.md that #751 adds, which is byte-identical to #738's fixture, accepted only when it equals a recorded org revision.
Mismatch: resolve_template reads only gh api repos/{owner}/.github{,/commits,/contents}. A consumer or local copy is never read, and any gh failure raises TemplateError.; A composer failure ends make pr with 'FAIL: could not compose the PR body ... nothing was sent'.; HTTP 403: 'GitHub access to this repository is not enabled for this session'.
Root cause: resolve_template treats the org repository as the only source and gh api as the only transport. Session-bound GitHub gateways refuse non-attached repositories.
Impact: make pr cannot compose a body on surfaces that cannot reach <owner>/.github; #738 leaves this unchanged
Closure: OPEN_PR=0 make pr composes a body in a session where repos/Quantum-L9/.github returns 403, without reading an unattested divergent copy.
Evidence IDs: E-F-738-F4-1, E-F-738-F4-2, E-F-738-F4-3, E-AUTH-738-F4

### F-738-F5 - REVIEW - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #738
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Each receipt is marked BOUND, STALE or UNVERIFIED against the head it describes. (PR #738 objective (title/body))
Origin: `PR_EXPOSED` | blocking basis: `NON_BLOCKING` - Does not block merge: The PR's own Evidence region is bound to 19bfbbf, not the current head 3707290, and nothing marks it STALE
Observed: A reviewer reading the live body sees BOUND receipts that describe an earlier head.
Expected: The Evidence region either describes 3707290, after a fresh make pr refresh, or is prefixed STALE.
Mismatch: 'composed at head 19bfbbf5...' and both receipts read 'BOUND ... describes this head', while head_sha is 37072903, a later merge commit.; The caller pins governance-pr.yml@77587b7. Run 39506654823 at 37072903 has only the 'pr / gates' and 'issue' jobs, with no body-refresh job to stamp STALE.
Root cause: The refresh path (.github#188 body job) is not live in this repository's caller pin, and the merge-from-main push was not followed by a local make pr refresh.
Impact: The PR's own Evidence region is bound to 19bfbbf, not the current head 3707290, and nothing marks it STALE
Closure: The live PR body's Evidence names the current head, or is marked STALE.
Evidence IDs: E-F-738-F5-1, E-F-738-F5-2, E-AUTH-738-F5

### F-739-F1 - CORRECTNESS - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #739
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: UNVERIFIED means proof is not available here. BLOCKED is reserved for tamper, forgery, wrong producer or a revision off main. A validator must not coerce unavailable input into a verdict it did not establish. (ops/scripts/coding_projection_status.py)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: Shallow authority clone turns a genuine published pair into BLOCKED ('not on main') instead of UNVERIFIED
Observed: A SessionStart against a sibling Quantum-L9/.github checkout that is shallow (or lacks the asserted revision's objects) reports BLOCKED, a tamper/forgery verdict, for a genuine pair once main has advanced past the pair's revision.
Expected: Missing history or objects yields UNVERIFIED with the reason named (e.g. 'shallow checkout cannot prove ancestry'). BLOCKED is kept for a present revision that is provably not an ancestor, or for content that fails verification.
Mismatch: is_ancestor returns False on any non-zero 'git merge-base --is-ancestor', including when the asserted commit object is absent.; A False ancestry result raises Rejected('published revision ... is not on main'), which classify maps to BLOCKED (status L171-172).; A blob absent at the asserted revision also raises Rejected rather than Unobserved.
Root cause: The verifier does not distinguish 'object absent / history truncated' from 'object present and not an ancestor'. Both git primitives collapse to a boolean or None that is treated as rejection.
Impact: Shallow authority clone turns a genuine published pair into BLOCKED ('not on main') instead of UNVERIFIED
Closure: Before the ancestry check and compute_pins at the asserted revision, verify_published checks that the asserted commit exists ('git cat-file -e <sha>^{commit}') and that the repository is not shallow. If either fails it raises Unobserved, and a test with a shallow clone of a genuine publication expects UNVERIFIED.
Evidence IDs: E-F-739-F1-1, E-F-739-F1-2, E-F-739-F1-3, E-F-739-F1-4, E-AUTH-739-F1

### F-739-F2 - CROSS_PR - Low - non-blocking

Confidence: `Confirmed` | root cause: `INFERENCE`
Affected PRs: #739
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Do not mix unrelated WIP into a governed change's branch; a separate change gets its own branch from origin/main. (AGENTS.md)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: Memory-CI setuptools pin commit is out of scope and byte-identical to open PR #752
Observed: Two open PRs carry the same memory-binding change. Whichever merges second carries a no-op duplicate, and this PR's green 'Exact-head memory lifecycle proof' depends on a change that #752 owns.
Expected: The memory-CI fix lands once, through #752, and this PR's diff is limited to the coding-projection consumer surfaces.
Mismatch: Both commits have patch-id 425e4f837abdc9c8cf86cde6a01f941a175e2179, the same author date (2026-10-20 22:20:16Z) and the same subject 'fix(memory-ci): pin the setuptools that reproduces the official memory wheel'. #752 was opened at 22:20:51Z.; Both files are unrelated to the coding-projection objective. The PR body's Fix section does not mention them; they appear only in the machine-owned Changes-by-intent list.; Clean in both cases (identical hunks), so this is duplicated ownership, not a textual conflict.
Root cause: The memory pin was cherry-picked onto this branch to turn the then-blocking memory proof green, at the same time as it was published separately as #752.
Impact: Memory-CI setuptools pin commit is out of scope and byte-identical to open PR #752
Closure: Either #752 merges first and this PR's copy becomes an empty no-op on refresh, or the duplicate is removed with a new corrective commit (not a revert or force-push), so that one PR owns the change.
Evidence IDs: E-F-739-F2-1, E-F-739-F2-2, E-F-739-F2-3, E-AUTH-739-F2

### F-739-F3 - TEST_QUALITY - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #739
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: ops/hooks/session_start_bootstrap.sh is a high-risk surface requiring extreme care, and every SessionStart sub-operation must decline with a named DEFERRED or TIMED OUT line. (AGENTS.md)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: SessionStart wiring branches (DEFERRED / TIMED OUT / empty / import failure) have no assertions
Observed: The happy path is verified (my sandbox runs). The degraded paths on a high-risk SessionStart surface rely on untested shell branches.
Expected: A test drives emit_coding_projection and the Cursor section through budget-exhausted, timeout and classifier-failure cases and asserts the named lines. The classifier's import failure is either caught or named.
Mismatch: The 125 / 124 / empty-output branches exist, but no test greps for 'coding projection' (repository-wide search finds the string only in the hooks, the workflow and the new files).; The Cursor default and timeout texts are unasserted. The existing stdout-contract test exercises the section only incidentally; my probe confirmed it is present.; 'import yaml' and the verifier import sit outside the 'a report-only line must always print' guard. With the fallback interpreter python3 (Claude hook L571) and no PyYAML, the classifier exits 1 with a traceback and no stdout (observed with python3 -S). The hook then says 'classifier printed nothing
Root cause: The test suite targets the classifier in-process (status.classify) and never executes the hook-level wrappers.
Impact: SessionStart wiring branches (DEFERRED / TIMED OUT / empty / import failure) have no assertions
Closure: Tests assert the 'coding projection:' Claude line and the '### coding projection' Cursor section for normal, DEFERRED/TIMED OUT and classifier-failure cases.
Evidence IDs: E-F-739-F3-1, E-F-739-F3-2, E-F-739-F3-3, E-AUTH-739-F3

### F-740-F1 - CROSS_PR - Medium - BLOCKING

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #740
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: A committed bundle is accepted only after CI reproduces it byte for byte with the pinned compiler (AIB-006), and GAR rejects unresolved required references. (skills/l9-global-architect/integrations/ARCHITECTURE_INTELLIGENCE_BINDING.yaml)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: AIB-006 production attestation is unresolved at this head: the trusted replay workflow lives in PR #741 and its status gates nothing
Observed: If #740 merges as is, the binding points at a workflow that does not exist. The bundle bytes are accepted with integrity and currentness checks only. Even after #741, a FAIL replay status does not block a merge.
Expected: The trusted replay exists on main before the bundle is admitted, and its commit status is a required check for paths under generated/governance/architecture_intelligence/**. Otherwise AIB-006 should be worded as advisory.
Mismatch: Only l9-architecture-intelligence-bundle.yml exists. l9-architecture-intelligence-trusted-replay.yml, named at binding L63 and workflow L37-L39, is absent (commit 43d674d3 moved it to the bootstrap PR).; The replay is a pull_request_target workflow, which runs from the default branch, so it cannot attest #740 unless #741 is on main first.; The required contexts are Analyze (central Core), Lint and Type Check, Test Suite, Root-file append-only gate, governance-self-check and repo-hygiene. l9/architecture-intelligence-trusted-replay is not among them.
Root cause: The trusted replay was split into PR #741 (commit 43d674d3) so that it could run from the default branch, but #740 kept AIB-006 and the trusted_replay reference as if the replay were already in place.
Impact: AIB-006 production attestation is unresolved at this head: the trusted replay workflow lives in PR #741 and its status gates nothing
Closure: #741 is merged to main, and the #740 head carries a PASS l9/architecture-intelligence-trusted-replay status that a required check or ruleset enforces. Alternatively, AIB-006 is downgraded to match the mechanism that actually exists.
Evidence IDs: E-F-740-F1-1, E-F-740-F1-2, E-F-740-F1-3, E-F-740-F1-4, E-AUTH-740-F1

### F-740-F2 - CI - Low - BLOCKING

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #740
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: After any merge touching generated paths, run sync_generated_artifacts.py --force and commit before updating the PR. (AGENTS.md)
Origin: `PR_EXPOSED` | blocking basis: `BLOCKING` - Blocks merge: Merge conflict with main 60aee3b, limited to the two generated skill-registry headers
Observed: GitHub cannot merge the PR (mergeable_state dirty). The repository's keep-ours merge driver for these paths is configured per clone and is not used by GitHub's server-side merge.
Expected: The branch merges current main and regenerates both registries, which then include both skill digests.
Mismatch: Content conflicts appear only in ops/generated/skill-registry.json and environment/agents/adapters/claude-code/generated/skill-registry.json.; The PR changes the GAR skill_sha256 and main changes the l9-pr-remediation skill_sha256 (from #753). Both rewrite the shared generation_id and corpus digest lines, so the hunks overlap. GitHub reports mergeable false, state dirty.
Root cause: Two branches regenerated the same registry headers concurrently. The skill content itself does not conflict.
Impact: Merge conflict with main 60aee3b, limited to the two generated skill-registry headers
Closure: git merge-tree --write-tree origin/main HEAD reports no conflict, and the regenerated registries hold both the GAR 0.8.4 and l9-pr-remediation digests.
Evidence IDs: E-F-740-F2-1, E-F-740-F2-2, E-AUTH-740-F2

### F-740-F3 - PROPORTIONALITY - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #740
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Until Quantum-L9/.github defines an admission decision record, ADMITTED_AND_CURRENT is unreachable and GAR reads architecture intelligence only as a candidate. (skills/l9-global-architect/decisions/ADR-L9-GAR-007.yaml)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: About 924 KB of committed generated bundle that, by construction, can only be read as non-authoritative candidate evidence
Observed: The repository takes on a large generated tree, a new CI workflow and a producer driver whose output cannot inform architectural judgment as admitted law until an upstream record exists. The design is not a duplicate SSOT: it is a projection of the canonical .github owner, following the generated/governance pattern of ADR-0038.
Expected: Defensible as staged infrastructure. Reviewers should accept explicitly that the bundle's present value is candidate-only, or defer committing the payload until the admission record exists. The ADR already escalates that record upstream.
Mismatch: resolve_admission returns only NOT_ADMITTED, STALE or ADMISSION_UNRESOLVED. No code path returns ADMITTED_AND_CURRENT.; CI confirms the committed bundle is not admitted law.; 924 KB in total: composed.json 284,637 bytes, projections/ 274,396 bytes and receipts/ 264,177 bytes. The composed namespaces are required to be byte-equivalent to the per-source projections, so the payload is stored twice.
Root cause: The upstream semantic owner (Quantum-L9/.github authority_model.yaml#admission_rules) has not yet defined an admission decision record.
Impact: About 924 KB of committed generated bundle that, by construction, can only be read as non-authoritative candidate evidence
Closure: An owner decides to keep the candidate-only bundle and records it (for example in the PR body or the ADR's escalation), or the admission record lands upstream and ADMITTED_AND_CURRENT becomes reachable.
Evidence IDs: E-F-740-F3-1, E-F-740-F3-2, E-F-740-F3-3, E-F-740-F3-4, E-AUTH-740-F3

### F-741-F1 - SECURITY - Low - non-blocking

Confidence: `Probable` | root cause: `INFERENCE`
Affected PRs: #741
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: A committed bundle is accepted only after CI reproduces it byte for byte with the pinned compiler, and the status is intended to be requirable by branch protection as that evidence. (.github/workflows/l9-architecture-intelligence-trusted-replay.yml)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: Published replay verdict is an unauthenticated commit status context
Observed: A success status with this context does not by itself prove it was posted by this workflow's replay run.
Expected: Evidence consumed as AIB-006 proof is bound to the trusted workflow run (e.g. a check run / required workflow, or a consumer that verifies the run's attestation artifact and its workflow path), or the limitation is documented where the status is consumed.
Mismatch: The verdict is a plain REST commit status (POST repos/{repo}/statuses/{sha}, context l9/architecture-intelligence-trusted-replay); commit statuses are keyed only by context string, and any token with statuses:write (e.g. a workflow added on a same-repository pull_request branch requesting statuses:
Root cause: GitHub commit statuses are not bound to a workflow identity; the design relies on context name alone.
Impact: Published replay verdict is an unauthenticated commit status context
Closure: Either the attestation is bound to the workflow run (required-workflow or attestation verified by workflow path/run id) or the binding documents that the status is advisory and not standalone production evidence.
Evidence IDs: E-F-741-F1-1, E-AUTH-741-F1

### F-741-F2 - RELIABILITY - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #741
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: The replay runs the trusted driver from the default branch and compares the PR bundle byte for byte. (.github/workflows/l9-architecture-intelligence-trusted-replay.yml)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: Driver-changing PRs cannot obtain a PASS replay before merge
Observed: Such a PR is reported FAIL until the driver lands on main separately, after which the push trigger (L37) replays it.
Expected: A documented two-step procedure (driver first, bundle second) if the status is ever made required.
Mismatch: The driver is always github.sha (main); a PR that changes produce_architecture_intelligence.py output format together with a regenerated bundle is replayed with main's old driver and gets REPLAY_MISMATCH_OR_ERROR; the pull_request_target path filter (L30-31) also does not include the driver path.
Root cause: Intentional trust choice (never execute PR-controlled driver code) with no documented evolution path.
Impact: Driver-changing PRs cannot obtain a PASS replay before merge
Closure: Header comment or binding documents the driver-first sequence; behaviour itself is acceptable.
Evidence IDs: E-F-741-F2-1, E-AUTH-741-F2

### F-744-F1 - CI - High - BLOCKING

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #744
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Whenever a merge touched generated paths, run sync_generated_artifacts.py --force and commit before opening or updating a PR; generated artifacts must reproduce with zero diff. (rules/53-pr-overlap-guardrail.mdc)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: Merge from main left both generated skill registries stale; required governance-self-check red
Observed: Head ships skill registries generated before the main merge; regeneration produces a diff and the routing registry tests fail.
Expected: Both generated registries reproduce byte-for-byte from the head's AUTONOMY_MANIFEST.yaml and SKILL.md corpus.
Mismatch: 'generated artifacts are stale' with ops/generated/skill-registry.json | 18 +++++++++---------; The merge imported skills/AUTONOMY_MANIFEST.yaml, skills/l9-pr-remediation/SKILL.md, skills/l9-bounded-autonomy/SKILL.md edits from main, but ops/generated/skill-registry.json generation_id stayed b7c4ecd6 (7333ddd's) at d6d0d8e9 and b8ed6b2.; generation_id/source_manifest_sha256 do not match the regenerated values c5456177.../db7ee70d...; the claude-code twin is identical and equally stale.
Root cause: Merge d6d0d8e9 resolved the generated registries with the branch side (keep-ours driver behavior) and the regen step was not run afterward.
Impact: Merge from main left both generated skill registries stale; required governance-self-check red
Closure: After merging current main, `python3 ops/scripts/sync_generated_artifacts.py --force` yields no diff in either registry and governance-self-check passes.
Evidence IDs: E-F-744-F1-1, E-F-744-F1-2, E-F-744-F1-3, E-F-744-F1-4, E-AUTH-744-F1

### F-744-F2 - CROSS_PR - Medium - BLOCKING

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #744
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: A branch that conflicts with its freshly fetched base is blocked; generated-path conflicts are resolved by regeneration, not by hand. (rules/53-pr-overlap-guardrail.mdc)
Origin: `PR_EXPOSED` | blocking basis: `BLOCKING` - Blocks merge: Textual conflict with main 60aee3b in the two generated skill registries (mergeable_state dirty)
Observed: GitHub reports mergeable=false / dirty; CI ran on a stale merge ref 6a9226dc against 2406510, not current main.
Expected: Branch merges cleanly with current main.
Mismatch: CONFLICT (content) only in environment/agents/adapters/claude-code/generated/skill-registry.json and ops/generated/skill-registry.json.; Main regenerated the same files after the §6.2.16 kill-switch change (66bfb613), so both sides edited the same lines.
Root cause: Main advanced 4 commits (incl. a registry regeneration) after the branch's last main merge; both files are generated so only regeneration can resolve them, and GitHub does not run the l9-generated merge driver.
Impact: Textual conflict with main 60aee3b in the two generated skill registries (mergeable_state dirty)
Closure: Merge origin/main 60aee3b (or later) into the branch, regenerate both registries (closes F1 too), and GitHub reports mergeable_state clean/unstable-only.
Evidence IDs: E-F-744-F2-1, E-F-744-F2-2, E-AUTH-744-F2

### F-744-F3 - CONTRACT - Medium - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #744
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Campaign and L4 authorize-release publish MUST pass PR_REMEDIATE=0 make pr. (AGENTS.md)
Origin: `PR_EXPOSED` | blocking basis: `NON_BLOCKING` - Does not block merge: /gmp adapter finalize publishes with PR_REMEDIATE=1 after authorize-release; the PR now teaches and tests that
Observed: On adapter surfaces /gmp's L4-release publication emits the remediation handoff (PR_REMEDIATE=1); the sole /gmp teaching surface and a new test now endorse it.
Expected: The L4 authorize-release publication inside finalize passes PR_REMEDIATE=0, matching the Cursor path in the same file.
Mismatch: _publish_pr runs _maybe_l4_release() (authorize-release) then make -C GOV pr with env PR_REMEDIATE=1; the PR rewrote this argv but kept the value.; Replaces the base text 'Finalize is one path on every surface: ... PR_REMEDIATE=0 make pr' with 'Finalize already publishes on claude-code, codex, gemini, and manus. Do not publish again there.'; New test asserts 'PR_REMEDIATE=1 make -C {ROOT} pr WS={repo}' after '--workspace {repo} authorize-release'.
Root cause: The PRE_EXISTING executor value was preserved when resolving review thread RT2; the documentation was aligned to code rather than code to AGENTS.md.
Impact: /gmp adapter finalize publishes with PR_REMEDIATE=1 after authorize-release; the PR now teaches and tests that
Closure: _publish_pr sets PR_REMEDIATE=0 (or the law is amended), and the adapter publish test asserts the compliant value.
Evidence IDs: E-F-744-F3-1, E-F-744-F3-2, E-F-744-F3-3, E-AUTH-744-F3

### F-744-F4 - CONTRACT - Medium - non-blocking

Confidence: `Probable` | root cause: `INFERENCE`
Affected PRs: #744
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: docker-compose.yml, Dockerfile*, .env*, infra/**, deploy/** and the L9 core files are protected in every project and need explicit approval / a dedicated GMP run. (rules/90-protected-core.mdc)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: commands/gmp.md says Cursor-Governance carries no protected paths for consumers, contradicting canonical_global rules 90/93
Observed: The sole /gmp teaching surface tells a consumer run that governance supplies no protected set.
Expected: Run contract item 3 names the work repo's protected paths in addition to the canonical_global protected set (rules/90, rules/93).
Mismatch: 'Protected paths come from the work repo: $WORK/AGENTS.md, $WORK/.cursor/rules/, $WORK/CODEOWNERS. Cursor-Governance carries none for consumers.'; The retired source told the agent to translate the L9 protected set to the target repo each run, not to drop it.
Root cause: Consolidating the skill into the slash rewrote the protected-path clause as repo-local only.
Impact: commands/gmp.md says Cursor-Governance carries no protected paths for consumers, contradicting canonical_global rules 90/93
Closure: Item 3 states the global protected set (rules/90-protected-core.mdc, rules/93-c1-server-protection.mdc) also applies, and test_gmp_slash_contract.py asserts it.
Evidence IDs: E-F-744-F4-1, E-F-744-F4-2, E-AUTH-744-F4

### F-744-F5 - TEST_QUALITY - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #744
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Every exit-2 outcome is one of the named tokens (NO_WORKSPACE, NO_PLAN, NO_SCOPE, OUT_OF_WORKSPACE, NO_TASK), which callers grep on stdout (gmp_executor.py L1320-L1324 comment). (commands/gmp.md)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: State-bound-to-another-clone exit prints no outcome token and is untested
Observed: Exit 2 with no outcome token when loaded state names a different work root.
Expected: A named token is printed (NO_WORKSPACE or a dedicated one documented in gmp.md) and a test covers it.
Mismatch: state_bound_elsewhere prints two diagnostic lines and main exits EXIT_NO_WORKSPACE without printing NO_WORKSPACE.; No test exercises this path.
Root cause: New branch added without the token print used on the other NO_WORKSPACE path (L131).
Impact: State-bound-to-another-clone exit prints no outcome token and is untested
Closure: The path prints a documented token and a test seeds a state file with a foreign work_root and asserts it.
Evidence IDs: E-F-744-F5-1, E-F-744-F5-2, E-AUTH-744-F5

### F-745-F1 - COMPLETENESS - High - BLOCKING

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #745
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: The toolchain comes from pyproject.toml + uv.lock via `uv sync --locked`; requirements.txt + uv.lock are the pin SSOT and the dev extra is kept in lockstep. (AGENTS.md)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: Python pins bumped in pyproject.toml/requirements.txt without regenerating uv.lock
Observed: Every locked environment build fails; no test, lint, type check, license or SBOM evaluation of the new versions occurs.
Expected: uv.lock moves with the manifest pins so `uv sync --locked` succeeds and CI exercises pre-commit 4.7.0, playwright 1.64.0 and claude-agent-sdk 0.2.168.
Mismatch: pre-commit==4.7.0, playwright==1.64.0, claude-agent-sdk==0.2.168.; Lock still carries claude-agent-sdk 0.2.163, playwright 1.63.0, pre-commit 4.6.2; uv.lock is not in the PR diff.; 'error: The lockfile at `uv.lock` needs to be updated, but `--locked` was provided.' -> 'UV: uv sync failed (rc=1)'.
Root cause: Dependabot's `pip` ecosystem (.github/dependabot.yml, package-ecosystem: pip) rewrites pyproject.toml/requirements.txt but not uv.lock; this repo's lock authority is uv.lock (PR #755, opened by the `uv` updater, shows the lockfile-aware path).
Impact: Python pins bumped in pyproject.toml/requirements.txt without regenerating uv.lock
Closure: uv.lock is regenerated for exactly these three packages (uv lock --upgrade-package pre-commit --upgrade-package playwright --upgrade-package claude-agent-sdk) and committed, and Test Suite plus Lint and Type Check pass on the new head.
Evidence IDs: E-F-745-F1-1, E-F-745-F1-2, E-F-745-F1-3, E-F-745-F1-4, E-F-745-F1-5, E-AUTH-745-F1

### F-745-F2 - CI - Low - BLOCKING

Confidence: `Probable` | root cause: `INFERENCE`
Affected PRs: #745
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: A PR touching an additive_only root file must carry the protected-root stamp in its body, evaluated by validate_root_file_protection.py on pull_request. (ops/config/root-file-protection.json)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: Root-file append-only gate result is stale against the edited PR body
Observed: The required check stays red although the PR now satisfies the stamp requirement.
Expected: The gate is re-evaluated against the current body and passes.
Mismatch: 'FAIL PR body: touches additive_only pyproject.toml, requirements.txt but is missing <!-- L9_PROTECTED_ROOT_PR -->' at HEAD_SHA ba20287; both line rewrites were 'JUST'.; The current body starts with '<!-- L9_PROTECTED_ROOT_PR -->'; the validator passes with that body (validation run 4).; Default activity types (opened/synchronize/reopened) exclude `edited`, so the body edit produced no new run.
Root cause: The stamp was added to the body after the synchronize event that ran the gate; the workflow does not listen to `edited`, and a re-run of the same job is expected to replay the original event payload.
Impact: Root-file append-only gate result is stale against the edited PR body
Closure: A new synchronize run of Root-file append-only gate on the post-F1 head reports OK.
Evidence IDs: E-F-745-F2-1, E-F-745-F2-2, E-F-745-F2-3, E-AUTH-745-F2

### F-745-F3 - SOURCE_OF_TRUTH - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #745
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: requirements.txt is a pin SSOT kept in lockstep with pyproject.toml. (AGENTS.md)
Origin: `PRE_EXISTING` | blocking basis: `NON_BLOCKING` - Does not block merge: requirements.txt documents a stale playwright pin
Observed: The SSOT comment names a version three minors behind the real pin.
Expected: The comment names playwright==1.64.0 (or no version).
Mismatch: Comment says pyproject.toml ui-operator declares 'playwright==1.56.0'.; Actual pin is 1.64.0; the comment was already stale at base.
Root cause: Dependabot updates requirement lines, not comments; earlier bumps left it behind.
Impact: requirements.txt documents a stale playwright pin
Closure: requirements.txt L61 matches pyproject.toml's playwright pin.
Evidence IDs: E-F-745-F3-1, E-F-745-F3-2, E-AUTH-745-F3

### F-747-F1 - CONTRACT - Medium - BLOCKING

Confidence: `Confirmed` | root cause: `INFERENCE`
Affected PRs: #747
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Every Core action and the publish-analysis workflow share one pin, because the release's action contracts are designed to be used together; edit each uses: line together (or run ops/sync-v2-starters.sh), and the comment names the current pin. (.github/workflows/l9-analysis.yml)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: Partial bump to publish-analysis@d3fc1b30 disables analysis check publication and splits the one-pin Core contract
Observed: With publish-analysis@d3fc1b30 and the rest of Core at e5cca958, the publish job takes the no-publication branch for mode blocking: no artifact retrieval/validation, no 'L9 semgrep · pr_fast' check, and no SARIF upload, while the run stays green.
Expected: All nine Quantum-L9/l9-ci-core uses: refs (resolve-governance, provision-sdk, invoke-sdk x2, validate-bundle, route-artifacts, build-artifact-manifest, publish-analysis) and the 'Current pin' comment move to the same reviewed SHA in one change, with the caller adapted to any input/contract change in that release.
Mismatch: The workflow's own contract requires one shared Core pin and still names e5cca9582f2d88bdfe0c659d2ece3a9e43e1297b as the current pin after this PR.; After this PR the nine Quantum-L9/l9-ci-core refs are mixed: only publish-analysis.yml (L212) moves to d3fc1b3049e742cefc619db28c695bef1dbe217b, the rest stay at e5cca958.; Inputs show 'publish-check: false'; log: 'No GitHub check publication capability elected for mode blocking'. publish-check job 118918215092 skipped.
Root cause: d3fc1b30's publish-analysis.yml gates publication on a new publish-check input (default false) that this caller, written for e5cca958, does not pass; Dependabot moved only this ref (SHA-only Core updates fall outside the actions-minor-patch group), so the caller was never adapted.
Impact: Partial bump to publish-analysis@d3fc1b30 disables analysis check publication and splits the one-pin Core contract
Closure: One change re-pins every Quantum-L9/l9-ci-core ref in l9-analysis.yml and the L39 'Current pin' comment to a single SHA, adapts caller inputs to that release, and Analyze (semgrep -> SDK) + Publish analysis (Core) show strict normalization with the repo's semgrep-finding-policy.yaml and a created check; #747-#750 are closed as superseded.
Evidence IDs: E-F-747-F1-1, E-F-747-F1-2, E-F-747-F1-3, E-F-747-F1-4, E-F-747-F1-5, E-AUTH-747-F1

### F-748-F1 - INVARIANT - High - BLOCKING

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #748
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: pr_fast runs strict, so an unidentified finding fails the run; sdk_policy semgrep-finding-policy.yaml is resolved under .github/governance; do not disable strict to make findings go away. l9-analysis.yml L33-L39 additionally requires one shared Core pin. (.github/governance/semgrep-identity-map.yaml)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: resolve-governance@d3fc1b30 drops the repo governance-root and disables strict Semgrep normalization
Observed: The resolver at d3fc1b30 rejects governance-root, resolves a different governance set (digest 28431d46 vs 69cdf2dd) with strict=false and policy semgrep-policy.yaml, and the e5cca958 invoke-sdk then normalizes Semgrep without --strict.
Expected: All nine Quantum-L9/l9-ci-core uses: refs (resolve-governance, provision-sdk, invoke-sdk x2, validate-bundle, route-artifacts, build-artifact-manifest, publish-analysis) and the 'Current pin' comment move to the same reviewed SHA in one change, with the caller adapted to any input/contract change in that release.
Mismatch: The workflow's own contract requires one shared Core pin and still names e5cca9582f2d88bdfe0c659d2ece3a9e43e1297b as the current pin after this PR.; After this PR the nine Quantum-L9/l9-ci-core refs are mixed: only resolve-governance (L74) moves to d3fc1b3049e742cefc619db28c695bef1dbe217b, the rest stay at e5cca958.; '##[warning]Unexpected input(s) 'governance-root', valid inputs are ['profile', 'provider', 'event-name', 'repository', 'ref', 'evaluation-date']'; L9_GOVERNANCE_ROOT no longer reaches resolve.py.
Root cause: d3fc1b30's resolve-governance no longer accepts governance-root (its valid inputs are profile/provider/event-name/repository/ref/evaluation-date), so it stops reading the repo's .github/governance pack and supplies its own strict/sdk-policy outputs; the caller and the other Core actions were written for e5cca958 and were not adapted, because Dependabot moved only this ref.
Impact: resolve-governance@d3fc1b30 drops the repo governance-root and disables strict Semgrep normalization
Closure: One change re-pins every Quantum-L9/l9-ci-core ref in l9-analysis.yml and the L39 'Current pin' comment to a single SHA, adapts caller inputs to that release, and Analyze (semgrep -> SDK) + Publish analysis (Core) show strict normalization with the repo's semgrep-finding-policy.yaml and a created check; #747-#750 are closed as superseded.
Evidence IDs: E-F-748-F1-1, E-F-748-F1-2, E-F-748-F1-3, E-F-748-F1-4, E-F-748-F1-5, E-F-748-F1-6, E-F-748-F1-7, E-AUTH-748-F1

### F-749-F1 - CONTRACT - Medium - BLOCKING

Confidence: `Confirmed` | root cause: `INFERENCE`
Affected PRs: #749
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Every Core action and the publish-analysis workflow share one pin, because the release's action contracts are designed to be used together; edit each uses: line together (or run ops/sync-v2-starters.sh), and the comment names the current pin. (.github/workflows/l9-analysis.yml)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: Single-action Core bump splits the one-pin l9-ci-core contract (provision-sdk (L122))
Observed: CI is green with provision-sdk at d3fc1b30 and the other eight Core refs at e5cca958 (job 118917293060: normalize still '--strict --required' with semgrep-finding-policy.yaml); the configuration is one the Core release does not declare supported, and the 'Current pin' comment is now wrong.
Expected: All nine Quantum-L9/l9-ci-core uses: refs (resolve-governance, provision-sdk, invoke-sdk x2, validate-bundle, route-artifacts, build-artifact-manifest, publish-analysis) and the 'Current pin' comment move to the same reviewed SHA in one change, with the caller adapted to any input/contract change in that release.
Mismatch: The workflow's own contract requires one shared Core pin and still names e5cca9582f2d88bdfe0c659d2ece3a9e43e1297b as the current pin after this PR.; After this PR the nine Quantum-L9/l9-ci-core refs are mixed: only provision-sdk (L122) moves to d3fc1b3049e742cefc619db28c695bef1dbe217b, the rest stay at e5cca958.; Runs provision-sdk@d3fc1b30 (adds actions/setup-python 3.12.14 for the SDK runtime) beside resolve-governance/invoke-sdk@e5cca958; outcome success.
Root cause: Dependabot opens one PR per SHA-only action update: the actions-minor-patch group in .github/dependabot.yml only groups semver minor/patch update-types, so l9-ci-core SHA bumps fall out of the group, and open-pull-requests-limit: 5 left validate-bundle, route-artifacts and build-artifact-manifest without any PR. Each PR therefore moves one ref of a release designed to be used together.
Impact: Single-action Core bump splits the one-pin l9-ci-core contract (provision-sdk (L122))
Closure: One change re-pins every Quantum-L9/l9-ci-core ref in l9-analysis.yml and the L39 'Current pin' comment to a single SHA, adapts caller inputs to that release, and Analyze (semgrep -> SDK) + Publish analysis (Core) show strict normalization with the repo's semgrep-finding-policy.yaml and a created check; #747-#750 are closed as superseded.
Evidence IDs: E-F-749-F1-1, E-F-749-F1-2, E-F-749-F1-3, E-AUTH-749-F1

### F-750-F1 - CONTRACT - Medium - BLOCKING

Confidence: `Confirmed` | root cause: `INFERENCE`
Affected PRs: #750
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: Every Core action and the publish-analysis workflow share one pin, because the release's action contracts are designed to be used together; edit each uses: line together (or run ops/sync-v2-starters.sh), and the comment names the current pin. (.github/workflows/l9-analysis.yml)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: Single-action Core bump splits the one-pin l9-ci-core contract (invoke-sdk (L126, L156))
Observed: CI is green with invoke-sdk at d3fc1b30 and the other Core refs at e5cca958 (job 118917306020: normalize '--strict --required', semgrep-finding-policy.yaml); the mixed configuration is undeclared by the Core release and the 'Current pin' comment is now wrong.
Expected: All nine Quantum-L9/l9-ci-core uses: refs (resolve-governance, provision-sdk, invoke-sdk x2, validate-bundle, route-artifacts, build-artifact-manifest, publish-analysis) and the 'Current pin' comment move to the same reviewed SHA in one change, with the caller adapted to any input/contract change in that release.
Mismatch: The workflow's own contract requires one shared Core pin and still names e5cca9582f2d88bdfe0c659d2ece3a9e43e1297b as the current pin after this PR.; After this PR the nine Quantum-L9/l9-ci-core refs are mixed: only invoke-sdk (L126, L156) moves to d3fc1b3049e742cefc619db28c695bef1dbe217b, the rest stay at e5cca958.; invoke-sdk@d3fc1b30 executes semgrep normalize and bundle project-agent-payload beside resolve-governance/provision-sdk/validate-bundle@e5cca958; outcome success.
Root cause: Dependabot opens one PR per SHA-only action update: the actions-minor-patch group in .github/dependabot.yml only groups semver minor/patch update-types, so l9-ci-core SHA bumps fall out of the group, and open-pull-requests-limit: 5 left validate-bundle, route-artifacts and build-artifact-manifest without any PR. Each PR therefore moves one ref of a release designed to be used together.
Impact: Single-action Core bump splits the one-pin l9-ci-core contract (invoke-sdk (L126, L156))
Closure: One change re-pins every Quantum-L9/l9-ci-core ref in l9-analysis.yml and the L39 'Current pin' comment to a single SHA, adapts caller inputs to that release, and Analyze (semgrep -> SDK) + Publish analysis (Core) show strict normalization with the repo's semgrep-finding-policy.yaml and a created check; #747-#750 are closed as superseded.
Evidence IDs: E-F-750-F1-1, E-F-750-F1-2, E-F-750-F1-3, E-AUTH-750-F1

### F-751-F1 - CONTRACT - Medium - BLOCKING

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #751
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: The only PR body is .github/pull_request_template.md, compiled by compose_pr_body.py; the Root-file append-only gate fails CI without <!-- L9_PROTECTED_ROOT_PR --> when an additive_only root file is in the diff. (AGENTS.md)
Origin: `PR_INTRODUCED` | blocking basis: `BLOCKING` - Blocks merge: Seeded release.md is a second PR-body template that law retires and the root-file gate rejects
Observed: GitHub offers a release PR template that the composer never fills and that fails the required Root-file gate for the manifest bump it prescribes.
Expected: This repository exposes exactly one PR body template (.github/pull_request_template.md), or the operator records a superseding decision that admits release.md with the stamp and Protected-root block.
Mismatch: There is no L9_PROTECTED_ROOT_PR stamp, no Protected-root section, no PROTECTED-ROOT-PATHS/CHANGES-BY-INTENT regions and no '## Problem'. L34 asks the author to bump pyproject.toml.; pyproject.toml is additive_only, so a release PR that bumps it requires the stamp.; The gate FAILs a body without the stamp when additive_only files are touched. has_protected_template_stamp(release.md) evaluated to False.
Root cause: The org seeder's 'default' class materializes the pr-templates category for Cursor-Governance, so the repo-local ONE_PR_TEMPLATE rule is not reflected in the seeder class.
Impact: Seeded release.md is a second PR-body template that law retires and the root-file gate rejects
Closure: release.md is removed from this PR (and the seeder class excludes pr-templates for this repo), or a recorded operator decision amends AGENTS.md to admit it and the template carries the stamp and a Protected-root region; the review thread is then resolved.
Evidence IDs: E-F-751-F1-1, E-F-751-F1-2, E-F-751-F1-3, E-F-751-F1-4, E-F-751-F1-5, E-AUTH-751-F1

### F-751-F2 - CROSS_PR - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #751
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: compose_pr_body.py is the one PR-body renderer; one behaviour should have one code path. (ops/scripts/compose_pr_body.py)
Origin: `PR_INTRODUCED` | blocking basis: `NON_BLOCKING` - Does not block merge: Measured-Closes fix duplicates #738's _fill_closes once both land
Observed: Two independent functions implement measured closing keywords once #738 and #751 are both on main.
Expected: One owner of the Closes behaviour in the renderer.
Mismatch: _with_measured_closes wraps _fill_template's output and inserts 'Closes #N' at the end of Problem.; After merge, #738's _fill_closes already writes the same line inside _fill_template. #751's wrapper becomes a guarded no-op (it returns early on 'Closes #\d'), leaving two implementations of one rule.
Root cause: #738 and #751 independently fixed the same org-template change.
Impact: Measured-Closes fix duplicates #738's _fill_closes once both land
Closure: Whichever lands second drops the redundant function, keeping both regression tests green.
Evidence IDs: E-F-751-F2-1, E-F-751-F2-2, E-AUTH-751-F2

### F-752-F1 - SOURCE_OF_TRUTH - Low - non-blocking

Confidence: `Confirmed` | root cause: `CONFIRMED`
Affected PRs: #752
Owner class: `CODEBASE`
Semantic owner: `governance` | execution owner: `l9-pr-remediation`
Mutation guard: `A-GUARD`
Authority: The binding manifest is the record of how artifact_sha256 is reproduced; its narrative must match the command the proof runs. (ops/config/memory-binding.json)
Origin: `PR_EXPOSED` | blocking basis: `NON_BLOCKING` - Does not block merge: Binding narrative still says plain uv build reproduces the official wheel
Observed: Two statements in the same release_evidence object disagree: one says plain uv build reproduces the official wheel, the other says it does not without setuptools==84.0.0.
Expected: The 'build' and description text name the backend pin as part of the reproduction recipe.
Mismatch: The description says 'uv build --wheel under the fixed SOURCE_DATE_EPOCH reproduces those bytes', and 'build' says 'reproduced by uv build --wheel (SOURCE_DATE_EPOCH=1784592000)'. Neither mentions the backend pin that is now required (L75), and build_backend_note (L76) contradicts them.; The proof description ('rebuilds the wheel reproducibly under the recorded SOURCE_DATE_EPOCH') does not mention build_backend_constraint.
Root cause: The PR added new fields beside the existing narrative instead of amending it.
Impact: Binding narrative still says plain uv build reproduces the official wheel
Closure: release_evidence.build and description (and the README proof paragraph) describe reproduction as uv build --wheel --build-constraint <build_backend_constraint> under SOURCE_DATE_EPOCH.
Evidence IDs: E-F-752-F1-1, E-F-752-F1-2, E-AUTH-752-F1

## Preservation obligations

- None recorded.

## Residual UNKNOWNs

- `U-737-1` blocks_readiness=`False` | Hosted fresh-container first start: whether syncClaudeAiSkills:false reaches Claude Code before account sync. This session's anthropic-skills:l9-pr-remediation shadowing happened at first start. | need: A new cloud session started with server-managed settings {syncClaudeAiSkills:false}, or from a rebuilt environment cache, whose init event lists zero anthropic-skills:* entries. The PR declares this HOST_VERIFICATION_BLOCKED and keeps #690 open.
- `U-737-2` blocks_readiness=`False` | Official cloud-session docs say user and project-local settings are 'not read' in cloud sessions, while the PR's live witness shows the container's ~/.claude/settings.json was honoured after restart. | need: /status 'Setting sources' in a hosted session after restart, showing User settings loaded together with syncClaudeAiSkills=false.
- `U-738-1` blocks_readiness=`True` | Branch freshness under the strict status-check policy | need: Main's ruleset sets strict_required_status_checks_policy=true and the PR is mergeable_state=behind (4 commits). The required checks must re-run green after the branch is updated with 60aee3b. The merge is textually clean and local tests pass on the merged tree.
- `U-738-2` blocks_readiness=`False` | Quantum-L9/.github#188 state | need: Whether #188 is merged or re-pinned. It cannot be read from this session (HTTP 403 on Quantum-L9/.github).
- `U-739-1` blocks_readiness=`False` | Fidelity of the verifier to upstream publish-projection.py verify_pair and of the fixture schemas to Quantum-L9/.github@d4397e5 | need: A diff of tests/fixtures/coding_projection/*.schema.yaml against Quantum-L9/.github@d4397e5 semantics/*.schema.yaml, and a run of upstream 'publish-projection.py check' on the same synthetic pairs. The PR body asserts this cross-check, but it was not reproduced here because upstream is outside this repository.
- `U-739-2` blocks_readiness=`False` | Behavior against a real published pair | need: Upstream has no projections branch yet (CI job 118921712977 printed UNVERIFIED 'refs/remotes/origin/projections absent'), so CURRENT/BOUND/BLOCKED have been exercised only on synthetic authorities.
- `U-740-1` blocks_readiness=`True` | Whether the private compiler at 159383e2 reproduces the committed bundle byte for byte | need: A l9/architecture-intelligence-trusted-replay PASS status on the #740 head after #741 is on main. The private compiler is not available to this auditor.
- `U-741-1` blocks_readiness=`False` | Existence and scope of the organization secret GH_TOKEN used at L140 | need: secrets.GH_TOKEN is referenced by no other workflow on main and the secrets API is not reachable through this proxy; if absent or lacking read on Quantum-L9/l9-semantic-compiler-engine, the first real replay (e.g. on #740) fails at checkout and posts FAIL/SUBJECT_UNRESOLVED-class statuses.
- `U-741-2` blocks_readiness=`False` | End-to-end replay behaviour | need: The workflow has never run (only the bundle workflow is registered); a workflow_dispatch with subject_pr=740 after merge is the first live evidence that the compiler installs and reproduces #740's bundle byte for byte.
- `U-744-1` blocks_readiness=`False` | AUDIT-RECORD: reviewer side effect on the real HOME. The command that rewrote ~/.claude/skills/l9-* links and ~/.claude/rules to point into heads/pr-744-regen was: `A=/tmp/claude-0/-home-user-Cursor-Governance/bdbba42e-6ef0-5411-b57c-5b3ef9a74913/scratchpad/audit/heads; mkdir -p "$A/pr-744-regen" && git -C /home/user/Cursor-Governance archive refs/audit/pr-744 | tar -x -C "$A/pr-744-regen" && cd "$A/pr-744-regen" && /home/user/Cursor-Governance/.venv/bin/python ops/scripts/sync_generated_artifacts.py --force --check --json` (run with the real HOME; its output included 'OK: LLM rule adapters reconciled to environment/generated/llm-rules/' and 'OK: LLM skill adapter symlinks reconciled to skills/ SSOT'). Other commands run with the real HOME that may also have touched HOME-scoped state, unve | need: Parent restores ~/.claude/skills and ~/.claude/rules to the SSOT targets and confirms no other HOME paths (e.g. ~/.cursor/l9/routes, ~/.cursor/plans) were written by the listed commands.
- `U-744-2` blocks_readiness=`False` | Whether consumer clones gitignore .l9/ (the executor now writes .l9/gmp/executor-state.json into $WORK) | need: A consumer-repo .gitignore / wiring contract stating .l9/ is ignored, or a run in a consumer showing a clean status after start.
- `U-745-1` blocks_readiness=`True` | Behavioral compatibility of pre-commit 4.7.0 / playwright 1.64.0 / claude-agent-sdk 0.2.168 with the repo | need: A green Test Suite on a head whose uv.lock carries the new versions; no CI evaluated them.
- `U-746-1` blocks_readiness=`False` | CodeQL Action v4.39.0 behavior (breaking: minimum bundle 2.20.7; new checkout_path validation) | need: A run of codeql-reusable.yml at this revision, which happens only when .github/workflows/codeql.yml L43 is re-pinned to a commit containing it.
- `U-747-1` blocks_readiness=`False` | Intended l9-ci-core d3fc1b30 caller contract (how publish-check is meant to be elected) | need: Read access to Quantum-L9/l9-ci-core compare e5cca958...d3fc1b30 (this session gets HTTP 403 on that repo).
- `U-748-1` blocks_readiness=`False` | Whether d3fc1b30 intends org-level governance to supersede repo .github/governance (and its strict default) | need: Quantum-L9/l9-ci-core release notes / compare e5cca958...d3fc1b30 (HTTP 403 from this session).
- `U-751-1` blocks_readiness=`True` | Operator decision on keeping release.md versus excluding pr-templates from the seeder class for this repo | need: Recorded operator instruction or AGENTS.md amendment; review thread PR751-RT1-4326160897 resolution.
- `U-751-2` blocks_readiness=`False` | Byte-exactness of seeded files against Quantum-L9/.github@c52b4f7 | need: GET repos/Quantum-L9/.github/contents/<path>?ref=c52b4f7f7520f31bd3a47f0ced7b6abd1c33d7d3 (403 in this session: repository not enabled).
- `U-751-3` blocks_readiness=`True` | Whether branch protection requires the branch to be up to date (mergeable_state=behind) | need: Branch-protection settings for main. The merge with 60aee3b is textually clean.
- `U-752-1` blocks_readiness=`True` | Whether branch protection requires the branch to be up to date (mergeable_state=behind) | need: Branch-protection settings for main. The merge with 60aee3b is textually clean.
- `U-CORPUS` blocks_readiness=`False` | Deterministic census ran on changed files only (repository_files_complete=false); repository-wide SSOT uniqueness, producer/consumer, bypass and orphan-reachability closures cannot close. | need: Re-run the census with a complete repository file corpus.
- `U-MUTATION` blocks_readiness=`False` | Mutation probes (scripts/execute_mutation_probe.py) were not executed; test discrimination for mutation candidates is unproven. | need: Run execute_mutation_probe.py for each MUTATION_EXECUTION seed on a disposable copy.
- `U-CENSUS-ENUM` blocks_readiness=`False` | l9-pr-audit defect: deterministic_closure.additional_symbol_deltas emits symbol_kind CONSTANT/API_ROUTE/SCHEMA_FIELD/CONFIG_KEY and detection_method PUBLIC_SURFACE_STATIC, which schemas/audit-output.schema.json does not allow, while the builder requires machine symbol rows to equal the census. The canonical bundle cannot pass schema validation until the schema (or generator) is aligned. | need: Align audit-output.schema.json changed_symbol_ledger enums with the census generator vocabulary, then rebuild.
- `U-CENSUS-DUP` blocks_readiness=`False` | l9-pr-audit defect: claim and falsification seed ids hash (pr, kind, subject) only, so one symbol detected by two methods yields duplicate claim seeds (342 here); this audit carries one row per id. | need: Include the machine symbol id in CHANGED_SYMBOL claim/probe seed ids.
- `U-HOME` blocks_readiness=`False` | During review, sync_generated_artifacts.py --force run from the PR #744 head copy re-pointed ~/.claude/skills and ~/.claude/rules at that copy; the session was restored from the SSOT installer. Tests executed by that reviewer after the rewrite ran against a session environment projected from the PR head. | need: Re-run PR #744 validation with an isolated HOME.
- `U-737-READY` blocks_readiness=`True` | Reviewer judged PR #737 READY_WITH_NON_BLOCKING_NOTES; readiness cannot be asserted at this head: GitHub reports mergeable_state=behind; main requires the branch to be up to date before merge. | need: Update the branch from main and observe green required checks on the new head.
- `U-738-READY` blocks_readiness=`True` | Reviewer judged PR #738 READY_AFTER_DEPENDENCY; readiness cannot be asserted at this head: GitHub reports mergeable_state=behind; main requires the branch to be up to date before merge. | need: Update the branch from main and observe green required checks on the new head.
- `U-739-READY` blocks_readiness=`True` | Reviewer judged PR #739 READY_WITH_NON_BLOCKING_NOTES; readiness cannot be asserted at this head: GitHub reports mergeable_state=behind; main requires the branch to be up to date before merge. | need: Update the branch from main and observe green required checks on the new head.
- `U-741-READY` blocks_readiness=`True` | Reviewer judged PR #741 READY_WITH_NON_BLOCKING_NOTES; readiness cannot be asserted at this head: GitHub reports mergeable_state=behind; main requires the branch to be up to date before merge. | need: Update the branch from main and observe green required checks on the new head.
- `U-746-READY` blocks_readiness=`True` | Reviewer judged PR #746 READY_WITH_NON_BLOCKING_NOTES; readiness cannot be asserted at this head: GitHub reports mergeable_state=behind; main requires the branch to be up to date before merge. | need: Update the branch from main and observe green required checks on the new head.
- `U-752-READY` blocks_readiness=`True` | Reviewer judged PR #752 READY_WITH_NON_BLOCKING_NOTES; readiness cannot be asserted at this head: GitHub reports mergeable_state=behind; main requires the branch to be up to date before merge. | need: Update the branch from main and observe green required checks on the new head.

## Evidence

Canonical exact evidence is in `audit.json` under `shared_evidence_index`. This projection intentionally avoids duplicating source excerpts or secret material.
