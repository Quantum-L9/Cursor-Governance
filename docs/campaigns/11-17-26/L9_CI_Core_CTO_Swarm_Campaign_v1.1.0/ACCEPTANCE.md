# Verification matrix and definition of done

| ID | Proof | In-scope expected outcome | Owner |
|---|---|---|---|
| A01 | `l9.repo-execution/v2` and `make-v1` validation | exact four phases, unchanged generated facade | A, CTO |
| A02 | PR Fast test selector has concrete finite census | selected high-risk tests run, nonempty, fail when deliberately broken | A, C, CTO |
| A03 | Core self-CI required check names | exact existing contexts retained, each produced once | B, CTO |
| A04 | SDK/semgrep/Biome/registry and security enforcement | no weakened provider or advisory bypass | C, CTO |
| A05 | Complete deep discoverability | all original discoverable tests run nightly, no silent exclusions | B, C, CTO |
| A06 | Immutable subject identity | nightly pinned to Core main commit, not guessed PR SHA | B, CTO |
| A07 | Scheduled daily workflow and manual dispatch | 07:17 UTC once daily (or documented adjustment), main only | B, CTO |
| A08 | Fail closed for missing suite/runtime, actual failing test | failures nonzero in fast and deep | A, B, C, CTO |
| A09 | Release verification parity | existing full release validation remains | B, CTO |
| A10 | Unique write ownership, Core change-policy companion closure and PR diff audit | zero unauthorized files or read-only writes | CTO |
| A11 | Combined candidate full test and current-head CI | full suite PASS plus required PR statuses PASS | CTO |
| A12 | Publication and merge authority | agents publish only, operator authorizes exact merges, CTO merges stack-safe | CTO |
| A13 | Real post-merge manual deep run on Core main | PASS, run identity, full test counts and logs retained | CTO |
| A14 | First real scheduled run | PASS and identifies Core main SHA; otherwise PENDING_SCHEDULED_PROOF | CTO |
| A15 | Comparative runtime | report ≥3 pre and ≥3 post samples if accessible, else UNKNOWN with evidence; never fabricate an improvement | E, CTO |
| A16 | PR-job overlap census | before and after: the exact test cases per required job; no lost unique critical cases, measured overlap explained | A, B, CTO |
| A17 | Source-bound currentness | frozen Core and CTO-governance SHA, exact PR-base-to-head lineage and current action pins | CTO |
| A18 | Protocol authority | each child mode ACTIVE and own-PR remediation, CTO tests integrated result, exact human grant for each merge | CTO |

## Test classification

Always PR-required: Core contract/admission validation, required status uniqueness, repo registry scoping, SDK contract/provisioning smoke, security/permission boundaries, immutable-pinned workflow shape, build/release guardrails, known regression witnesses for prior false-green defects. CTO classifies actual test modules against these requirements. Do **not** blanket move the entire `tests/workflows` or `tests/repo_execution` directory nightly merely to hit a time target.

Nightly-required: all discoverable existing `unittest` modules, including all PR Fast tests; extended randomized/heavy e2e or scans only when already runnable and owner-supported. Nightly is **full coverage**, not a disjoint leftover subset. Running a PR test a second time at night is intentional; redundant full suites on every PR are not.

Release-required: keep existing exact-tag release validation unchanged. If a release gate currently runs full discovery, prove it still does.

## Repo-native companion gates and historical docs

Core `.l9/core-repo-policy.json` has `repository-execution-evidence`: a changed `Repo.mk` requires a changed `tests/repo_execution/` file **and** both `AGENTS.md` and `docs/repository-execution-runtime.md` changed **inside the same PR**. Lane A owns all four. A changed workflow requires `tests/workflows/` in its PR, owned by B. Do not weaken these rules or try to claim a sibling PR counts. The historic `AGENTS.md` MANIFEST subsection is stale against current `manifest_check_enabled()` (opt-in since 2026-10-20); update that subsection in A only where necessary to prevent false instructions, without making a new manifest.

## Before claiming speed-up

Measure (1) PR workflow wall clock, (2) total billed/runner minutes, (3) count of complete-suite executions per PR, (4) fast selected case count, (5) nightly discovered case count, (6) merge-blocking failures found before vs after. A 2–5 minute PR goal is aspirational; source evidence does not establish it today.

## Fail-safe proof counterexamples

- Remove or mistype selected test path in disposable checkout: PR selector must fail, not run zero tests and pass.
- Introduce a known-failing minimal test fixture in disposable validation: deep and PR selectors that include it must fail.
- Change name of a required workflow job: Core's existing context test must fail.
- Change `required_phases` or make-v1 bytes: Core contract validation must fail.
- Render nightly on a feature branch: main-ref guard must fail loudly or never run as a valid nightly, never attest main.
- Break a known CI security or SDK handoff regression: it remains PR blocking.

No artificial fixtures written to protected Core main; the CTO does adversarial proofs in disposable worktrees.

## Two-stage completion

- **Technical pilot implemented:** all authorized merges landed, required PR checks observed on the live Core runtime, merged main SHA identified, full manually dispatched deep suite passed, all blocking findings disposed. No exact runtime-savings claim without actual samples.
- **Daily scheduler proven:** the first genuinely `schedule`-triggered run on Core main passed; until then preserve `SCHEDULED_PROOF_PENDING`. Cron registration and successful manual dispatch are not this proof.

Parent PRs may be slow while the B conversion is pending. That is expected in the stack and cannot be used to claim that A alone achieved the speed goal.

