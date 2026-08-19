# Pre-existing debt remediation (Ruff / mypy / ESLint)

This reference governs the **static-analysis and type-debt** signal: a repository
carries pre-existing Ruff, mypy, ESLint, TypeScript, test, or build failures on its own
`main` baseline, and the task is to remediate the underlying causes and drive a green,
review-clean pull request — not to suppress the tools into silence.

It shares the skill's single hot path (local-verify gate, one-commit-per-cycle,
concurrent clusters, short-poll CI). When no PR exists yet, record a baseline SHA,
classify debt, fix root causes, open a remediation PR, and continue on that PR — same
path, not a separate mode.

## When this signal applies

- The user asks to "fix pre-existing lint/type debt", "get Ruff/mypy/ESLint green", "pay
  down static-analysis debt", or "clean up the toolchain" on a repository.
- CI on `main` is red for lint/type/test/build reasons unrelated to any one feature.
- A PR already open is failing lint/type gates and the failures predate its diff.

If a PR already exists, skip the branch-creation phase and feed the baseline straight
into the normal ingestion/classification/fix loop.

## Authority order (this signal)

1. Current user instruction.
2. Repository-local `AGENTS.md` / governance and accepted ADRs.
3. Repository configuration (`pyproject.toml`, `ruff.toml`, `mypy.ini`, `eslint.config.*`,
   `tsconfig.json`, `package.json`, `Makefile`, `tox.ini`).
4. Repository-native validation commands (Make targets, package scripts, documented
   commands) — **preferred over direct tool invocation**.
5. Current CI workflow definitions and their exact commands + versions.
6. Confirmed source evidence — never a raw tool line alone.
7. `Unknown` — do not invent a fix for an unclassifiable finding.

## Language & toolchain detection

Use the repository's actual language and existing configuration. **Never introduce
Python or Node tooling into a repository that does not already use it.**

| Classification | Marker files |
|---|---|
| `python` | `pyproject.toml`, `setup.cfg`, `setup.py`, `requirements.txt`, `tox.ini`, `noxfile.py` |
| `node` | `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `tsconfig.json`, `eslint.config.*`, `.eslintrc*` |
| `mixed` | both sets present — run both toolchains against their owned source surfaces |
| `unsupported` | neither — STOP, report `BLOCKED` |

Required tools by language: **Python → Ruff + mypy** (plus the repo test runner and any
build/package validation); **Node → ESLint** (plus `tsc`, tests, and build when present).

## Baseline capture — `scripts/debt_audit.py`

Run the deterministic auditor first. It is stdlib-only, secret-safe, runs each gate with a
fixed argv allowlist (never a shell string), redacts token-shaped output, and confines
`--output` to the working tree:

```bash
"${GOV_PY:-$PWD/.venv/bin/python}" scripts/debt_audit.py --output debt-baseline.json
"${GOV_PY:-$PWD/.venv/bin/python}" scripts/debt_audit.py --output debt-baseline.json --language mixed
```

The snapshot records: `head_sha`, detected `languages`, `tool_versions`, the repository
`preferred_invocation` surface (Make targets + package scripts), each gate's
`status`/`exit_code`/truncated `output`, `suppression_counts`, and `failing_gates`. Gate
statuses are `PASS`, `FAIL`, `FALSE_PASS`, `UNAVAILABLE`, `UNAVAILABLE_NEEDS_INSTALL`, or
`ERROR`. A missing tool is `UNAVAILABLE`, **never a silent PASS**.

The auditor captures evidence; it does not fix. When a repository-owned wrapper exists
(`make lint`, `npm run lint`), prefer it for the actual fix-verify cycle — the snapshot's
direct-tool runs exist to give granular per-gate evidence and to expose false passes.

### Hostile audit rules

A green tool is not proof of a clean repository. Before trusting any PASS, check for:

- **False passes** — the auditor flags `FALSE_PASS` when a gate exits 0 while its output
  shows a traceback, "no files checked", or "0 files checked". Investigate every one.
- **Empty or mis-scoped targets** — a tool configured to scan a path that no longer holds
  source, or excluded down to nothing.
- **Broad excludes / per-file ignores** hiding active code.
- **Stale suppressions** — `# noqa`, `# type: ignore`, `// eslint-disable`, `@ts-ignore`.
  High `suppression_counts` are debt to investigate, not a baseline to preserve.
- **Scripts that exit 0 after a tool fails** (e.g. `|| true` in a workflow step).
- **Local/CI drift** — different commands or tool versions between local and CI.
- **Generated code being linted** when the generator is the real owner to fix.

## Issue classification

For every finding record: `finding_id`, `tool`, `rule_or_code`, `path`, `line`,
`baseline_present`, `validity`, `root_cause_cluster`, `severity`, `proposed_fix`,
`regression_risk`, `validation`.

`validity` ∈ `CONFIRMED`, `FALSE_POSITIVE`, `GENERATED_SOURCE`, `CONFIGURATION_DEFECT`,
`STALE_SUPPRESSION`, `EXTERNAL_BLOCKER`, `UNKNOWN`.

Separate **pre-existing baseline debt** (present on the initial `main` snapshot) from
**regressions introduced during remediation**. Both must be resolved before completion,
but they are reported separately.

## Root-cause clustering

Consolidate findings into the smallest set of underlying defects so a minimal fix removes
the maximum debt. Cluster by shared symbol, type contract, utility, import/export,
configuration, generator, repeated unsafe pattern, test fixture, or architectural
violation. Fix priority: install/all-validation blockers → security & correctness →
shared causes closing many findings → type-contract failures → build/test failures →
lint/maintainability → cosmetic.

## Remediation rules

**Required**

- Fix underlying causes at the authoritative implementation owner, not symptoms.
- Preserve public behavior unless the existing behavior is itself defective.
- Preserve architecture and ownership boundaries; keep the diff as small as correctness
  permits; no formatting-only churn in unrelated files.
- Add or update a regression test for every behavioral fix.
- Update generated output only through its canonical generator.
- Remove a stale suppression only **after** the underlying issue is actually corrected.
- Make each commit coherent and independently understandable.

**Prohibited** (these clear the tool without fixing the defect — do not use them)

- `blanket_noqa`, `blanket_type_ignore`, `blanket_eslint_disable`, broad tool exclusions.
- Weakening strictness, lowering a quality threshold, or changing a gate config to pass.
- Deleting or skipping tests; replacing real logic with stubs; swallowing exceptions.
- `Any`/`unknown` types, unsafe casts, or non-null assertions used to hide a design
  defect rather than reflect a proven invariant.
- Unrelated refactors or dependency upgrades not required by a confirmed defect.
- Marking a valid review comment resolved without a fix or evidence-backed rebuttal.

A **narrow, documented** suppression is permitted only for a *proven* false positive where
a code fix would be less safe — the same standard the SonarCloud signal uses.

## Phase flow (maps onto the skill loop)

1. **Bind** — read governance, fetch `origin/main`, record its SHA, create an isolated
   branch/worktree from `origin/main`, inspect worktree status. Do not absorb, stash,
   reset, or reformat unexplained pre-existing local changes.
2. **Baseline** — run `debt_audit.py`; install dependencies via the repository-owned
   method when a gate is `UNAVAILABLE_NEEDS_INSTALL`; classify pre-existing failures.
3. **Audit** — apply the hostile audit rules; verify source coverage and ignore scope;
   map findings to current source; cluster by root cause; rank by impact and fix cost.
4. **Remediate** — fix the highest-leverage cluster first; run targeted validation after
   each cluster; inspect the diff for scope creep; add regression tests; repeat until
   every `CONFIRMED` finding is resolved.
5. **Full local validation** — the skill's blocking local-verify gate: run every
   configured Ruff check, mypy, ESLint, `tsc`, tests, build, and repository-native
   validation; confirm no unintended file changes and no new unexplained suppressions.
6. **Commit / push / PR** — one scoped commit (or a small coherent series), rebased on
   latest `origin/main`; open the PR against `main` with baseline + after evidence;
   subscribe to the PR.
7. **Converge** — hand to the normal CI + review-reply loop until required checks are
   green and no unanswered code-review agent (`github-code-quality[bot]`, Copilot) or other review threads remain.

## Required artifacts

Emit these alongside the usual gate artifacts so the work is auditable:

- `PRE_EXISTING_DEBT_BASELINE.md` — repo + `main` SHA, languages/toolchain, per-tool
  findings, pre-existing vs external failures. (Backed by `debt-baseline.json`.)
- `DEBT_ISSUE_REGISTER` — one row per finding with validity, cluster, disposition,
  validation.
- `DEBT_REMEDIATION_CHANGE_MANIFEST` — file, symbol, change type, cluster, findings
  resolved, behavior impact, validation.
- `PR_REMEDIATION_LEDGER` — one row per convergence iteration (head SHA, checks, review
  threads, fixes, commit SHA, result).

## Final verdict

- `GREEN_CLEAN_REVIEW_RESOLVED` — all in-scope pre-existing errors resolved; applicable
  Ruff/mypy/ESLint/tsc/tests/build green; all required PR checks green; no unresolved
  code-review agent (`github-code-quality[bot]`, Copilot) or blocking review threads; branch clean; PR **not merged**.
- `GREEN_WITH_EXPLICIT_NON_BLOCKING_DEBT` — required checks green and remaining debt is
  out-of-scope or explicitly accepted, with no hidden failures.
- `PARTIALLY_REMEDIATED` — some confirmed debt fixed, required errors/reviews remain.
- `BLOCKED` — auth prevents push/PR, a required toolchain cannot run, unexplained local
  changes overlap required files, or a required-check failure cannot be resolved.
- `INCONCLUSIVE` — repository state or validation evidence is insufficient.

## Fail-closed / stop conditions

- Repository identity or `main` is ambiguous → STOP.
- Adding missing required tool configuration would be an unauthorized architectural
  decision → STOP.
- The only way to pass is to weaken Ruff, mypy, ESLint, TypeScript, tests, or CI → STOP;
  never weaken a gate.
- A required check is `UNKNOWN` → STOP until the failing boundary is understood.
- Do not merge, release, or deploy. Do not resolve a review thread without a fix or an
  evidence-backed rebuttal. Report `BLOCKED` rather than emit a misleading pass.
