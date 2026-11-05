<!-- L9_META
schema: 1
parent: l9-pr-integration-testing
layer: reference
role: domain-authority-and-audit
version: 0.1.0
status: active
-->

# Authority, scope and independent source review

Load when freezing PRs, selecting integration order, evaluating semantic ownership or applying the source-review gate. `scripts/bind_github.py` does not grant merge or publication. Invoking the skill publishes one new integration PR of the retested combined tree. It does not update source PR branches, merge, or grant production access.

## Binding and source trust

1. Resolve target repository via its current authority; use `scripts/bind_github.py` only for GitHub PR metadata. Bind target branch HEAD at the freeze time separately from the historical PR base SHA. Record head owner, branch, source repo, state and fetch ref. If a branch moves after binding, fail the run rather than silently change what is tested.
2. For stacked PRs, validate parent-child commit ancestry and actual target branches. `VERIFIED_DEPENDENCY` is a permissible order basis only with verified ancestry. For independent PRs, compare both merge orders where relevant; a reversed merge that fails or creates a materially different tree is a risk, not a reason to assume an arbitrary ordering is valid.
3. Read the authoritative owner of the changed behavior. Test assertions and PR description provide evidence of intent but cannot override active repository contracts. Record an explicit `UNKNOWN` where authority is unavailable. Refrain from running commands or making readiness claims that require that authority.
4. Preserve the split between PR source head, target baseline, and synthetic combined revision. Neither a GitHub green check nor local merge result is the synthetic integrated revision by default.

## Adversarial review checklist

Perform a separate code inspection of the combined behavior and directly coupled consumers, not just changed lines. Treat these as conditional lenses, not generic high-severity findings:

- **Duplicate ownership:** Two PRs independently define the same state/algorithm/contract, register competing handlers, or shadow validation with incompatible semantics.
- **Cross-boundary mismatch:** Producer emits one schema, authorization behavior, identity, relationship or exception while consumer expects another. Check reachable callers and actual registration, not just method existence.
- **Data/compatibility:** Schema and ORM constraints, historical data, migrations, rollback, uninstall/reinstall and existing clients must survive changed contracts.
- **Concurrency and failure:** Duplicate events, write races, transaction boundaries, retries, lost acknowledgement, persistence errors and absent rollback can bypass green-path unit tests.
- **Security:** Privilege escalation, ACL/record-rule drift, trust-boundary crossing, injection and secret leakage; verify actual role and negative-case witnesses.
- **Test discrimination:** Inspect weak/tautological assertions, skipped or xfailed tests, wrong expected values, mock-only boundaries and new behavior not reached by tests. Run targeted negative probes that encode an authority-backed incorrect result. A passing test on a deliberately wrong result proves a false-green only for the target obligation and fault used.
- **Architectural obligations:** Track every material affected consumer, feature flag, activation path, dependency, generated source, migration and necessary regression test. Distinguish a known owner-approved nonchange from omitted work.

## Review receipt

A substantive review must cite the exact synthetic integrated SHA or tree SHA plus source coordinates and governing contracts. Record coverage, review method, confirmed issues, gaps and corrective obligations. A generic `passed` flag, file count or purely deterministic grep signal cannot close source correctness. Because source inspection by an agent is judgment-based, retain the distinguishing evidence. If the model cannot inspect enough of the combined source, classify `INCOMPLETE_EVIDENCE`.

An active `l9-pr-audit` can provide a detailed read-only independent audit, but it does not remove the obligation to check the actual combined candidate. An external `l9-pr-audit` verdict applies to its source heads, not automatically to the synthetic integrated tree.

## Repair and continuation

Correct the highest authoritative owner whose behavior is wrong; do not patch a downstream symptom to manufacture green. Each confirmed issue has exact source path/revision, expected/actual behavior, reproduction command, root cause or UNKNOWN, correction owner, regression witness and preservation obligation. Invocation of this skill publishes one new integration PR of the retested combined tree. Repairs are committed only on the exported checkout. Source PR branches are not updated, and this skill does not merge. After the source PRs move, throw away the prior verdict and rebind.
