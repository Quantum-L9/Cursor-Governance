# Cursor-Governance: mandatory first real consumer acceptance

> **v1.7.1 (2026-11-20):** the SHAs and pull-request states in this file are the 2026-11-19 snapshot. `09_EXECUTION_BINDING.md` holds the live recheck and outranks any conflicting sentence here.

**Hard gate:** Do not declare upstream CI migration operational or start fleet rollout until the new Core+SDK integrated runtime is actually tested against `https://github.com/Quantum-L9/Cursor-Governance` and the evidence below is verified. This gate is in addition to Core self-CI and SDK fixtures. Cursor-Governance is an actual consumer, not a synthetic unit-test repository.

## Gate 0: prerequisite and permission proof

- Rebind current `Quantum-L9/l9-ci-core`, `Quantum-L9/l9-ci-sdk`, `Quantum-L9/.github` and `Quantum-L9/Cursor-Governance` revisions, open PRs, and effective GitHub required-workflow ruleset. Inspect any stacked branch interactions.
- Upstream implementation must be accepted/promoted through the existing owner and Core SDK compatibility firewall before **production inheritance** is claimed. An unmerged SDK or Core PR is not installed fleet behavior.
- During development, shadow/canary execution on pinned test revisions is permitted where existing workflows allow, with preserved trust boundaries. It is **not** a substitute for a required-workflow evaluation on the promoted source.
- No unauthorized merges, branch-protection changes, unsafe token privileges, unapproved paid account changes, or raw agent pushes. If final live evaluation requires a merge that is not authorized, return `BLOCKED_ON_PROMOTION`, not PASS.

## Gate 1: inspect and preserve the consumer baseline

**Historical native platform baseline:** CodeQL PR #1067 scan
`44657558641` uploaded results but lacked an overlay-base cache; Sonar
`44657558389` ran 8175 tests with coverage and produced a real PASSED gate.
Compare post-Core native behavior against these exact runs, not against
configuration comments. Cursor PR #1062 is open and has no hosted Sonar
apply receipt at its inspected head. Reconcile its transition and verify
actual dispatch and analysis before retiring any current quality signal.
Read `CODEQL_SONAR_LEVERAGE.md` for negative witnesses and account limits.



Capture Cursor default branch/base commit, existing required checks and actual local CI runs. Specifically enumerate and bind:

- `.semgrep/l9-pr.yml` (4 custom rules observed) with rule IDs, file/path restrictions and expected findings.
- `ops/scripts/run_pr_security.sh` local security ceremony, velocity/full profiles, and any applicable Gitleaks/Bandit/pip-audit behavior.
- `.github/workflows/codeql.yml`, `codeql-nightly.yml`, `codeql-reusable.yml`, and CodeQL default versus nightly query-suite behavior; PR #1067 is already merged, so preserve rather than reimplement it.
- Sonar integration and PR #1062 overlap, current toolchain/stamp files, native repo test entrypoints, and mixed-language detected source surface.
- Current scanner coverage and elapsed time, not just green check names. Retain baseline run IDs/URLs and exact `head_sha`.

## Gate 2: real central invocation and configuration inheritance

On an actual governed Cursor PR/merge evaluation at the intended promoted Core/SDK revision, prove that:

1. The effective GitHub ruleset selected Core `org-ci.yml` and its required `Analyze (central Core)` job evaluated **this exact Cursor head**.
2. SDK detected every applicable source language/framework and required provider instance; each ran, produced an explicit valid not-applicable reason, or failed/incomplete as its actual status. A Python+TypeScript condition cannot collapse to one language.
3. Applicable central Semgrep/general scanner config was resolved from Core/SDK without copying it into Cursor. Package/executable revisions and digests are recorded. The consumer must not be asked to repin Core/SDK for an ordinary upstream update.
4. Cursor-owned custom Semgrep rules remain effective in a correctly *scoped* execution. Do not silently force the memory-path restrictions on unrelated code or change the product-owned rule meaning.
5. Other required native or repo-owned checks (actual tests, Sonar/CodeQL in their own trust contexts) still produce correct results and are not falsely described as SDK-executed.

## Gate 3: positive/negative witnesses and failure injection

- Run **known-bad and known-good** fixtures in a disposable controlled test branch/fixture harness, not by merging intentional vulnerabilities into main. At minimum exercise a centrally owned general rule, a Cursor-specific memory/transport boundary rule, and a capability or required-provider failure. Preserve exact matching and negative scope evidence.
- Demonstrate one consumer attempt to override a central required tool version, severity, provider or ignore scope is refused or does not reduce coverage.
- Demonstrate that a missing scanner, broken rulepack or unsupported required language yields FAIL/INCOMPLETE instead of green.
- Demonstrate both CodeQL PR-default and nightly-extended **configuration remains wired as already accepted**. Reuse existing live receipts; do not force an extra overnight schedule run solely for ceremony. A synthetic configuration test cannot be presented as native CodeQL execution.
- Compare before/after findings, required scope, tool runtime, duplicates, provider authorizations, and CI cost. No pruning of unique findings or product-native tests for speed.

## Gate 4: promotion / rollout decision

- Maintain existing consumer checks until **both** central known-bad/known-good parity and actual required Cursor evaluation are demonstrated. If central does not execute a Cursor-specific rule, keep its current local enforcement and return the missing binding to the SDK/Core owner.
- A passing **synthetic fixture** or Core self-test alone does not satisfy this gate; a successful real consumer run without fault-injection tests also does not satisfy it.
- **Fail closed at earliest source owner**: fix an SDK selection/normalization defect in SDK, a Core profile/orchestration defect in Core, a product rule meaning defect only at the Cursor owner. Never insert a local waiver to camouflage a broken Core rollout.
- Publish immutable proof: source SHAs, effective ruleset, actual run URL/job conclusion, detector inventory, required-check ledger, native provider receipts where permitted, four custom-rule dispositions, fixture test logs, and run-time delta.

**Acceptance result:** `CURSOR_CANARY_PASS` only if all required gates have actual evidence; otherwise `CURSOR_CANARY_BLOCKED` with exact failed item, owner and next action. These are **campaign report labels**, not new L9 canonical states. Only `CURSOR_CANARY_PASS` permits broader consumer cleanup and rollout.
