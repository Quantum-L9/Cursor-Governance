# CodeQL remediation (code-scanning alerts)

This reference governs the **CodeQL / code-scanning** signal: a repository has active
CodeQL alerts (security or correctness), or a CodeQL configuration gap that hides
vulnerable code, and the task is to remediate the authoritative root causes and drive a
green, review-clean pull request — never to dismiss, exclude, or weaken the analysis into
silence.

It shares the skill's convergence machinery (local-verify gate, one-commit-per-cycle,
review-reply protocol, CI polling). What it adds is a **security-remediation entry mode**:
confirm each alert against current source by tracing dataflow before touching code, fix at
the earliest trust boundary, and prove the fix with a negative test.

## When this signal applies

- The **CodeQL** code-scanning check is failing on a PR, or the repo has open CodeQL
  alerts on `main`.
- The user asks to "fix CodeQL findings", "clear code-scanning alerts", "remediate the
  security debt", or "close the SSRF/path-traversal/injection alert".
- A CodeQL analysis coverage gap is suspected (a language or source root not analyzed).

If a PR already exists, feed the alert baseline into the normal ingestion/classification/
fix loop. Otherwise create the branch first, snapshot the baseline, then remediate.

## Authority order (this signal)

1. Current user instruction.
2. Repository-local `AGENTS.md` / governance, accepted ADRs, `SECURITY.md` / threat model.
3. Public contracts and schemas.
4. Repository tests and runtime behavior.
5. CodeQL query semantics and alert path-flow evidence — never a dashboard count alone.
6. Current CI and review evidence.
7. `Unknown` — do not modify code solely because an alert exists.

## Baseline capture — `scripts/codeql_fetch.py`

Snapshot the alert inventory first. The fetcher is stdlib-only, **read-only** (it never
mutates alert state — dismissal is fail-closed policy, not a fetcher action), reads the
token by environment reference only (`GITHUB_TOKEN`/`GH_TOKEN`, Authorization redacted in
the receipt), pins the API host (SSRF allow-list), confines `--output` to the working
tree, and is **fail-closed on incomplete pagination** (a next page after the cap →
`BLOCKED`, never a smaller-than-real set):

```bash
python3 scripts/codeql_fetch.py --owner OWNER --repo REPO \
  --ref refs/heads/main --output codeql-alerts-before.json
# For a PR head: --ref refs/pull/<number>/head
```

The snapshot records, per alert: `alert_number`/URL, `rule_id`, CWE tags,
`problem_severity`, `security_severity`, `state`, dismissal metadata,
`analyzed_commit_sha`, `path`/lines, the sink `message`, and `tool_version` — plus the
`latest_analysis` (exact analyzed commit + tool) and a `severity_breakdown`. Dismissed
alerts are retrieved separately for review (a dismissal may be stale after code drift).
Code-scanning requires authentication; an unauthenticated/forbidden response is `BLOCKED`,
never an empty pass.

## Configuration audit (before trusting any "0 alerts")

A green CodeQL check is not proof of coverage. Verify:

- **All owned languages are analyzed** — none dropped from the matrix; source roots
  actually extracted; compiled languages reach a real build (autobuild reaching the build,
  monorepo packages built), not an empty database that "succeeds".
- **Query suites are explicit** — `security-extended` / `security-and-quality` present and
  not narrowed; custom query packs pinned, not drifting.
- **Paths/ignores are justified** — no `paths-ignore` hiding vulnerable owned code; no
  vendored/generated code pulled in that should be excluded.
- **Triggers and permissions** — analysis runs on `main` and pull requests; `security-events:
  write` present; SARIF upload success verified (not silently failing).

## Hostile dataflow review

For every path/taint alert, before fixing:

- Trace the flow from **source → transformations → sink**; confirm a sanitizer actually
  **dominates** the sink (not merely present on some path), and that barriers are
  recognized by the active query version.
- Do not assume a helper named `validate`/`sanitize` is effective — read it.
- Check alternate call paths, aliases, wrappers, and indirect entrypoints; check whether
  user-controlled data enters via config, env, files, network, CLI, DB, queue, or webhook.
- Check that authorization occurs **before** the sensitive action, and that errors do not
  leak secrets or structure.
- Check whether **one root cause raises multiple alerts** across call sites, and whether a
  fix closes only the reported line while **equivalent paths remain**.

## Alert classification

Normalize each alert (the fetcher does most of this) and assign `validity` ∈
`CONFIRMED_VULNERABILITY`, `CONFIRMED_BUG`, `VALID_HARDENING_GAP`,
`FALSE_POSITIVE_CANDIDATE`, `STALE_ALERT`, `GENERATED_OR_VENDOR_SCOPE_ERROR`,
`QUERY_OR_CONFIGURATION_DEFECT`, `ACCEPTED_RISK_REQUIRES_REVALIDATION`, `UNKNOWN`.
Reconcile the alert's `analyzed_commit_sha` with current `main`; a fix must target current
source, not a stale revision.

## Root-cause clustering & priority

Consolidate alerts into the smallest set of authoritative causes. Cluster by shared
untrusted source, sensitive sink, missing validation, authorization boundary,
serialization/parsing layer, file/path utility, DB access layer, command-exec wrapper,
HTTP client, template/renderer, configuration defect, or CodeQL workflow gap.

Priority: critical/high exploitable security → auth/authz bypass → RCE/command exec →
injection & path traversal → secret/sensitive-data exposure → unsafe deserialization &
dynamic loading → SSRF & network-boundary → confirmed runtime bugs → shared causes closing
many alerts → CodeQL workflow blind spots → medium/low with high-leverage fixes.

## Remediation rules

**Required**

- Fix the **earliest authoritative cause**; validate untrusted data at the correct trust
  boundary; prefer **allowlists** and **parameterized APIs** over escaping.
- Preserve encoding/canonicalization order (validate after canonicalization).
- Authorize before the sensitive action; minimize privilege and data exposure; make
  resource ownership and cleanup explicit.
- Preserve public API compatibility unless the API is unsafe by design.
- Add a **negative test** reproducing the vulnerable/incorrect path, and a regression test
  proving equivalent paths are covered.
- Keep fixes small and auditable.

**Prohibited** (these hide the alert without removing the risk — do not use them)

- Dismissing valid alerts; bulk or "won't fix" dismissal.
- Blanket CodeQL exclusions; removing `security-extended`; weakening query suites;
  suppressing SARIF upload; `# codeql` / NOSONAR-style inline suppression.
- Marking an alert false-positive without path-flow proof.
- Input blacklists where an allowlist is required; sanitizing **after** the sink;
  validation without canonicalization; escaping where a safe parameterized API exists.
- Authorization after mutation; swallowing exceptions; hardcoded secrets.
- Changing tests to accept insecure behavior; resolving only the reported line while
  equivalent paths remain; broad refactors without a root-cause need.

### Custom query / model policy

Modeling a wrapper as a sanitizer, or adding a barrier, is allowed **only** when runtime
safety is proven first, the modeled source/sink/sanitizer is documented, query tests are
added, query packs are pinned, and no false negative is introduced. Never model unsafe
code as safe, add a barrier only to clear an alert, or suppress an entire rule for one
false positive.

### Dismissal policy

Remote dismissal is **forbidden by default**. Allowed only when the alert is a proven
false positive, the current query+version and runtime invariant are recorded, repository
security policy permits it, the exact reason/comment is documented, and no safer code or
model fix is preferable. `used-in-tests` / `won't-fix` dismissals and bulk dismissals are
prohibited.

## Phase flow (maps onto the skill loop)

1. **Bind** — read governance + security policy, fetch `origin/main`, record its SHA,
   create the isolated branch, inspect worktree status, identify languages & CodeQL setup.
2. **Baseline** — run `codeql_fetch.py`; retrieve all alerts + instances + analysis
   metadata; record repository tests/build state; classify pre-existing alerts.
3. **Configuration audit** — verify coverage, build mode, query suites, paths/ignores,
   triggers, permissions, and SARIF-upload success; detect empty/partial-database passes.
4. **Confirmation** — map each alert to current source, trace dataflow/control-flow,
   classify validity, find unreported equivalent paths, cluster, prioritize.
5. **Remediation** — fix one root-cause cluster at a time; add negative + regression
   tests; run targeted tests; inspect the diff for scope creep; repeat until every
   `CONFIRMED` in-scope finding is resolved.
6. **Full local validation** — the skill's blocking gate: static analysis, type checks,
   tests, build, and a fresh local CodeQL database + configured/custom queries when the
   CodeQL CLI is available; compare before/after SARIF; confirm no new alerts.
7. **Commit / push / PR** — scoped commit(s) referencing alert numbers + root causes;
   rebased on latest `origin/main`; open the PR against `main` with a security summary
   (no exploit secrets), baseline vs after counts, and root-cause evidence; subscribe.
8. **Converge** — hand to the CI + review-reply loop; **requery CodeQL alerts for the
   exact head SHA** each cycle until the CodeQL check is green with no active in-scope
   alerts and no unresolved Copilot/review threads.

## Required artifacts

- `CODEQL_BASELINE_AUDIT.md` — repo + `main` SHA, CodeQL setup, languages analyzed, query
  suites/versions, active alerts by severity/rule, dismissed-alert review, coverage gaps.
  (Backed by `codeql-alerts-before.json`.)
- `CODEQL_ALERT_REGISTER` — one row per alert with source/sink/path-flow, severity,
  analyzed SHA, validity, cluster, disposition, validation.
- `CODEQL_ROOT_CAUSE_PLAN` — one row per cluster (root cause, alert numbers, sinks,
  exploitability, blast radius, minimal fix, required tests, priority).
- `CODEQL_CHANGE_MANIFEST` / `PR_REMEDIATION_LEDGER` — file→cluster→alerts-resolved
  traceability, and per-iteration convergence state (head SHA, CI + CodeQL checks, active
  alerts, review threads, fixes, commit SHA, result).

## Final verdict

- `GREEN_CODEQL_CLEAN_REVIEW_RESOLVED` — all confirmed in-scope alerts resolved; coverage
  gaps fixed; exact PR head SHA analyzed; CodeQL check green; no new in-scope alerts;
  tests + build pass; all required checks green; no unresolved Copilot/review threads;
  branch clean; PR **not merged**.
- `GREEN_WITH_EXPLICIT_ACCEPTED_RISKS` — required checks green and remaining alerts are
  proven false positives or explicitly accepted with authority and evidence; no hidden
  failures.
- `PARTIALLY_REMEDIATED` — some confirmed alerts fixed, required alerts/checks/reviews
  remain.
- `BLOCKED` — auth prevents CodeQL access/push/PR, CodeQL analysis cannot run, or a
  required-check failure cannot be resolved.
- `INCONCLUSIVE` — repository/alert state or analysis revision is insufficient.

## Fail-closed / stop conditions

- Repository, `main`, or CodeQL project identity is ambiguous, or the analyzed revision
  cannot be reconciled → STOP.
- The only way to clear an alert is to weaken CodeQL scope/query suites, or to dismiss
  without proven authority → STOP; never weaken or dismiss.
- A required check or CodeQL result is `UNKNOWN` → STOP until the boundary is understood.
- Do not merge, release, or deploy. Do not resolve a review thread without a fix or an
  evidence-backed rebuttal. Do not disclose exploit detail beyond what remediation needs.
