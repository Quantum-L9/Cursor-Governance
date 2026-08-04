---
name: l9-pr-remediation
description: recursive pr improvement loop — read ci failures, code review bot comments, sonarcloud static-analysis findings, and pre-existing ruff/mypy/eslint/typescript/test/build debt on the baseline, apply root-cause fixes, verify every gate locally, push one commit to the pr branch, reply to review threads, wait for re-run, loop until ci is green and no new actionable signals remain. use when a pr has failing ci, a failing sonarcloud quality gate or open sonarcloud issues, unresolved review comments from gemini or coderabbit, pre-existing lint/type debt to pay down (ruff, mypy, eslint, tsc) via an audit-first entry mode, or when the user asks to fix a pr, remediate review feedback or static-analysis findings, or run a pr improvement loop.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, pr, ci, code-review, sonarcloud, static-analysis, ruff, mypy, eslint, typescript, technical-debt, recursive, remediation, github, review-replies]
owner: igor_beylin
status: active
version: 2.3.0
updated: 2026-08-04
disable-model-invocation: true
---

# PR Remediation Loop

## Purpose

Operate a closed-loop remediation cycle on an open pull request: ingest CI gate failures AND code review bot comments (Gemini, CodeRabbit, GitHub reviewers), apply fixes, verify ALL gates locally, push ONE commit, reply to every review thread with canonical responses, wait for CI confirmation, then loop until converged or max cycles reached.

**Bounded autonomy:** when used as a **background PR-poll worker** under
`l9-bounded-autonomy` / `/autonomy`, run inside the campaign authorization
**packet** (declared PR/branch only; ≤3 cycles; never merge). Main continues
other work — do not expect the parent turn to AwaitShell on this loop.

## Core Contract

| Input | Source | Tool |
|-------|--------|------|
| CI failures | GitHub Actions logs | `gh run view --log-failed` |
| Review comments | PR review threads | `gh api /repos/{owner}/{repo}/pulls/{pr}/reviews` + `gh pr view --comments` |
| Inline suggestions | PR diff comments | `gh api /repos/{owner}/{repo}/pulls/{pr}/comments` |
| CI workflow definitions | `.github/workflows/*.yml` | File read (for gate discovery) |
| SonarCloud findings | SonarCloud API (`/issues/search`, `/rules/show`, quality gate) | `scripts/sonar_fetch.py` (stdlib, secret-safe) |
| Pre-existing lint/type/test/build debt | Repository-owned toolchain (Ruff, mypy, ESLint, `tsc`, tests, build) on the `main` baseline | `scripts/debt_audit.py` (stdlib, secret-safe) |

| Output | Condition |
|--------|-----------|
| ONE commit pushed to PR branch | Every cycle that produces actionable changes |
| Canonical replies to ALL review threads | Every cycle, after push |
| Batch summary comment on PR | Every cycle, after replies |
| Deferred issues created | When findings are deferred |
| Convergence report | Final cycle |

## Authority Order

1. User request (PR number, repo, specific instructions).
2. CI failure logs (exact error output from the failing gate).
3. Review bot comments (Gemini, CodeRabbit, human reviewers).
4. Repo ground truth: `.github/workflows/*.yml`, `tsconfig.json`, `package.json`, lint configs, `sonar-project.properties`.
5. Current SonarCloud API evidence (confirmed against source — never the raw finding alone).
6. This skill's references.
7. `Unknown` — do not invent fixes for unclear comments or unconfirmed findings.

## Non-Negotiable Rules

1. **ONE commit, ONE push per cycle.** ALL fixes for a cycle MUST be batched into a single commit with a single push. Multiple pushes per cycle is a protocol violation.
2. **Local verify is a BLOCKING GATE.** MUST run ALL CI gate commands locally and confirm exit 0 before any push. If local verify fails, fix the failure BEFORE pushing — do NOT push and hope CI catches it.
3. **Gate discovery BEFORE fixing.** MUST parse ALL workflow YAML files to enumerate every CI gate command BEFORE applying any fixes. No surprises from unknown gates.
4. **Remote CI is confirmation, not discovery.** After push, CI polling confirms what local verify already proved. If CI finds something local verify missed, that's a protocol failure to document.
5. **Every thread gets a reply.** No silent fixes. Every review comment receives a canonical-format response and is resolved.
6. **Validation gates are mandatory.** Each workflow step produces a required artifact (see validation-gates.md). Cannot advance without the artifact.
7. **MUST NOT loop more than 3 cycles** (configurable via `max_cycles`).
8. **MUST NOT fix comments marked as "discussion" or "question"** without user confirmation.
9. **MUST NOT force-push or rewrite history** on the PR branch.
10. **MUST preserve existing PR description and metadata.**
11. **MUST label deferred items explicitly with reason and linked issue.**
12. **When parallel CI jobs fail independently**, use parallel triage (one fix per job, still batched into one commit).
13. **When review comments conflict with CI requirements**, CI wins (it blocks merge).
14. **SonarCloud findings are retrieved from the API and confirmed against current source** before any fix. Never modify code solely because SonarCloud reported it; fix root causes, not symptoms, and cluster issues that share one defect.
15. **No suppression shortcuts to clear SonarCloud.** MUST NOT use `NOSONAR`, blanket rule suppression, broad exclusions, or lower a quality-gate threshold. A narrow, documented suppression is allowed only for a *proven* false positive where a code fix would be less safe.
16. **Never mutate remote SonarCloud state** (issue status, resolution, or hotspot review) and **never expose the token** — read `SONAR_TOKEN` by environment reference only.
17. **A local fix is not a remote SonarCloud closure.** The quality gate is not green until observed green on the exact analyzed revision; otherwise report `PENDING_REMOTE_ANALYSIS` and claim no closure.
18. **Pre-existing debt is fixed at the root, never suppressed.** MUST NOT clear Ruff/mypy/ESLint/`tsc` by blanket `noqa`/`type: ignore`/`eslint-disable`/`@ts-ignore`, broad tool exclusions, weakening strictness or a quality threshold, deleting or skipping tests, replacing real logic with stubs, or adding `Any`/unsafe casts/non-null assertions to hide a design defect. A narrow, documented suppression is allowed only for a *proven* false positive where a code fix would be less safe.
19. **Separate baseline debt from regressions.** MUST record pre-existing baseline failures (present on the recorded `main` SHA) distinctly from regressions introduced during remediation. Both are resolved before completion, but they are reported separately.
20. **Use the repository-owned toolchain, unmodified.** MUST detect the repository's actual language/config and prefer its Make targets or package scripts; MUST NOT introduce Python or Node tooling into a repository that does not already use it.

## Compact Workflow

**Entry modes.** Two ways in, one convergence loop:
- *PR-attached* (default) — a PR already exists; start at step 1 and react to its signals.
- *Audit-first* — no PR yet, the task is pre-existing Ruff/mypy/ESLint/`tsc`/test/build
  debt on the baseline. Load [references/debt-remediation.md](references/debt-remediation.md):
  fetch `origin/main` and record its SHA, create the isolated branch, run
  `scripts/debt_audit.py` to snapshot the baseline, classify and cluster the debt, fix
  root causes, then rejoin at step 6 (local verify) → push → open PR → converge.

1. **Identify PR** — get PR number, repo, branch from user or context.
2. **Discover CI gates** — read ALL `.github/workflows/*.yml` files. Extract every `run:` command that can fail. Build the local verify command list. → **Produce Gate A artifact.**
3. **Ingest signals** — load [references/signal-ingestion.md](references/signal-ingestion.md).
   - Fetch CI run status and failed logs.
   - Fetch all unresolved review comments and inline suggestions.
   - If SonarCloud is configured (`sonar-project.properties`) or the SonarCloud check is
     failing, load [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md),
     bind project/branch identity, and run `scripts/sonar_fetch.py` to snapshot every issue
     for the exact PR/branch (fail-closed on ambiguous identity or unreconcilable revision).
   - If remediating pre-existing lint/type debt (audit-first mode, or a baseline-level
     Ruff/mypy/ESLint/`tsc`/test/build failure), load
     [references/debt-remediation.md](references/debt-remediation.md) and run
     `scripts/debt_audit.py` to snapshot the toolchain baseline (detected languages, tool
     versions, per-gate exit codes, suppression counts, and false-pass flags).
4. **Classify findings** — load [references/finding-classifier.md](references/finding-classifier.md).
   - Route CI failures by type (lint, type-check, test, build, security).
   - Route review comments by actionability (actionable, discussion, deferred).
   - Confirm each SonarCloud finding against current source; drop stale/false-positive/
     generated-scope findings with evidence; cluster the rest by root cause.
   - Confirm each pre-existing debt finding against current source; separate baseline debt
     from regressions introduced during remediation; apply the hostile-audit rules (empty
     targets, broad excludes, stale suppressions, false passes) before trusting any PASS.
   - → **Produce Gate B artifact.**
5. **Apply ALL fixes** — load [references/fix-engine.md](references/fix-engine.md).
   - Fix ALL blocking items (CI failures).
   - Fix ALL actionable review comments.
   - Fix confirmed SonarCloud root causes with the minimal change (one cluster at a time);
     no suppression shortcuts.
   - Fix confirmed pre-existing lint/type debt at the authoritative owner (one cluster at a
     time); add a regression test for every behavioral fix; no blanket `noqa`/`type: ignore`/
     `eslint-disable`, no strictness or threshold weakening, no deleted or skipped tests.
   - Skip discussion-only and deferred items.
   - Do NOT commit or push yet.
   - → **Produce Gate C artifact** (git diff --stat).
6. **Local verify (BLOCKING GATE)** — run EVERY CI gate command locally.
   - If ANY gate fails → fix it immediately, re-run ALL gates.
   - Repeat until ALL gates pass locally (max 5 iterations).
   - Only proceed to step 7 when local verify is fully green.
   - → **Produce Gate D artifact** (all exit codes = 0).
7. **Commit and push (ONCE)** — single commit with conventional message, single push.
   - → **Produce Gate E artifact** (commit SHA, push count = 1).
8. **Reply to review threads** — load [references/review-replies.md](references/review-replies.md).
   - Reply to every thread using canonical format (Fixed/Deferred/Acknowledged/Disagreed).
   - Create issues for deferred items.
   - Resolve all threads.
   - Post batch summary comment.
   - → **Produce Gate F artifact** (reply count, resolved count).
9. **Wait and confirm** — load [references/convergence-loop.md](references/convergence-loop.md).
   - Wait for CI to complete (poll `gh run list` on the branch).
   - CI should pass (local verify already confirmed). If it fails, investigate the delta.
   - Check for new review comments posted after push.
   - If new actionable signals exist → loop back to step 3.
   - If CI green AND no new actionable comments → converge.
10. **Report** — emit convergence block and deferred items list.

## Resource Map

- [references/signal-ingestion.md](references/signal-ingestion.md) — how to fetch and parse CI logs + review comments + workflow YAML.
- [references/finding-classifier.md](references/finding-classifier.md) — classification rules for routing signals to fix strategies.
- [references/fix-engine.md](references/fix-engine.md) — fix methodology per finding type, local verification protocol, batch discipline.
- [references/review-replies.md](references/review-replies.md) — canonical reply formats, thread resolution, batch summary, downstream leverage.
- [references/convergence-loop.md](references/convergence-loop.md) — wait, poll, re-check, and convergence gate logic.
- [references/validation-gates.md](references/validation-gates.md) — enforcement layer with required artifacts at each step.
- [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md) — SonarCloud signal: fail-closed API retrieval, root-cause clustering, minimal-fix contract, security-hotspot policy, and the local-fix-is-not-remote-closure rule.
- [references/debt-remediation.md](references/debt-remediation.md) — pre-existing Ruff/mypy/ESLint/`tsc`/test/build debt signal: language & toolchain detection, audit-first entry mode, hostile-audit rules, root-cause clustering, the prohibited-shortcut contract, required artifacts, and the final-verdict taxonomy.
- [scripts/sonar_fetch.py](scripts/sonar_fetch.py) — stdlib, secret-safe fetcher: paginates issues + rules + quality gate + measures into a secret-free snapshot; fail-closed on incomplete pagination.
- [scripts/debt_audit.py](scripts/debt_audit.py) — stdlib, secret-safe baseline auditor: detects the owned toolchain, runs each gate with a fixed argv allowlist, and records exit codes, tool versions, suppression counts, and false-pass flags into a secret-free snapshot; fail-closed on an unclassifiable toolchain or out-of-tree output path.

## Validation

Before declaring convergence:
- CI status MUST be `success` on latest commit.
- SonarCloud: confirmed root causes fixed and locally validated. Remote quality-gate closure
  is `PENDING_REMOTE_ANALYSIS` until the candidate revision is analyzed — never claimed from
  local reasoning. No remote issue/hotspot state was mutated.
- Pre-existing debt: every applicable Ruff/mypy/ESLint/`tsc`/test/build gate passes locally
  through the repository-owned invocation, with no new unexplained suppressions and no
  weakened gate; baseline debt and any remediation-introduced regressions are both resolved
  and reported separately; final verdict assigned per debt-remediation.md.
- No new unresolved review comments posted after last push.
- All review threads replied to and resolved.
- All actionable findings from initial ingestion addressed or explicitly deferred.
- All deferred items have linked issues.
- All 6 gate artifacts produced for the final cycle.
- Convergence block emitted with all required fields.

## Failure Handling

- CI logs unavailable → STOP; ask user for run ID or paste logs.
- Review API rate-limited → wait 60s, retry once, then STOP.
- Fix causes new CI failure → revert that fix, mark as deferred, continue.
- Local verify passes but remote CI fails → investigate environment delta, document, defer if unresolvable.
- Thread resolution API fails → log, continue (non-blocking for merge).
- Max cycles reached without convergence → emit `partial` status with remaining items.
- Conflicting review comments → mark as deferred, ask user.
- SonarCloud project/branch identity ambiguous, or analyzed revision cannot be reconciled with
  local source → STOP; report `BLOCKED` (do not fix against a mismatched revision).
- SonarCloud fetch incomplete (retrieved ≠ API total) → STOP; the partial set is `BLOCKED`,
  not a smaller issue set.
- A SonarCloud fix would require weakening a rule/gate or its root cause is `Unknown` → stop
  that cluster; record it, do not suppress.
- No supported toolchain detected (`debt_audit.py` status `BLOCKED`) → STOP; report
  `BLOCKED`. Do not introduce tooling the repository does not already use.
- A required gate's tool is `UNAVAILABLE` / `UNAVAILABLE_NEEDS_INSTALL` → install via the
  repository-owned method and re-run; never treat an unavailable gate as a pass.
- `debt_audit.py` reports a `FALSE_PASS` (gate exit 0 with crash / empty-target output) →
  treat the gate as failing; fix the real cause and re-verify before trusting it.
- A pre-existing debt fix would require weakening Ruff/mypy/ESLint/TypeScript/tests/CI →
  STOP that cluster; record it, do not suppress or weaken the gate.
- Gate artifact cannot be produced → STOP at that gate, report `blocked`.
