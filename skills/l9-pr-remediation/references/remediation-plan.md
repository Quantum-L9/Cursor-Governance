<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: remediation_plan
tags: [pr, plan, preflight, tracking, one-commit, makefile]
owner: igor_beylin
status: active
version: 2.2.0
updated: 2026-08-18
/L9_META -->

# Remediation Plan (this PR → one commit)

## Purpose

After `RUN_CONTRACT` ([run-contract.md](run-contract.md)), write a **structured plan for the PR about to be edited**, then execute the codebase batch and publish **one** commit. Remote CI is confirmation, not a discovery loop.

This is an inline working ledger (cycle proof), not a packaged report.

## Hard order

```text
RUN_CONTRACT (once) → THIS PR'S FINDINGS → PLAN → FIX BATCH + COMPANIONS →
MAKEFILE + CITED-PATH VERIFY → ONE COMMIT → SANCTIONED PUBLISH → REPLY
```

- **No fleet-wide census** after `RUN_CONTRACT` exists. Ingest the PR you are editing.
- **No file edits** until that PR's plan has a disposition for every ingested finding (or a locked plan is being executed).
- **No commit** until the Makefile primary gate is green and cited/planned paths were checked.
- **No second commit** to "see what CI says."
- **No merge** because this PR is now green. Merge waits for FIRST_MERGE_GATE.

A locked `Remediation-Cycle` / plan whose files still match is executed, not rewritten.

## 1. This PR's findings (not a second fleet census)

Ingest open surfaces on **this** head. Skip Sonar/CodeQL/debt unless that check is failing or configured-and-blocking.

| Surface | How | Track as |
|---------|-----|----------|
| Required + failed checks | `gh pr checks`, `gh run view --log-failed`, annotations | `ci` |
| Human reviews + inline + issue comments | REST + GraphQL threads | `review` |
| Code-review agents | `github-code-quality[bot]`, Copilot — [code-review-agents.md](code-review-agents.md) | `code_review_agent` |
| Other bots | CodeRabbit, Gemini, `github-advanced-security` | `bot` |
| Sonar / CodeQL / debt | fetch scripts only when failing or blocking; output under `$PWD` | `scanner` / `debt` |

Completeness for **this PR**: every unresolved thread, every failed check, every Code Quality / Copilot comment. Do not block the plan on a green-check scanner fetch.

## 2. Plan schema (working ledger)

```yaml
remediation_plan:
  pr: "{owner}/{repo}#{n}"
  head_sha: "{40-char}"
  locked_plan_reused: false
  one_and_done: true

  findings:
    - id: "cq-1"
      source: github-code-quality | copilot | human | bot | ci | sonar | codeql | debt
      author: "{login}"
      file: "path"          # null if none
      line: 12              # null if none
      message: "{one line}"
      ownership: CODEBASE | CI_PIPELINE | ENVIRONMENT | HUMAN | FALSE_POSITIVE
      disposition: fix | reply_ack | reply_disagree | defer | already_fixed | note_pipeline | note_environment
      cluster: "{root-cause id}"
      root_cause: "{verified cause or Unknown}"
      confidence: high | medium | low | Unknown
      status: pending | done
      evidence: "{observed command or file:line that justifies this disposition}"

  clusters:
    - id: "{root-cause}"
      finding_ids: ["cq-1", "ci-2"]
      files: ["path"]
      companions: []        # generator outputs required in the same commit
      action: "{one-line fix}"

  verify:
    makefile_targets: ["precommit-repo"]
    cited_paths: ["path"]
    extra_local_commands: []
    all_green: false

  commit_policy:
    commits: 1
    publish: "git push"   # already-open PR branch
    no_verify: false
```

**Plan gate (blocks edits):**

- [ ] `RUN_CONTRACT` exists for the run
- [ ] Every ingested finding on **this** PR has `ownership` + `disposition` + `evidence` + `root_cause` (or `Unknown`)
- [ ] Every `disposition: fix` has `confidence` of `high` or `medium` and a cited-file read at the current head
- [ ] Every `fix` item is in a cluster with files + action
- [ ] Companion list is complete when touching `pec/*`, `skills/*`, or `rules/*`
- [ ] `verify.makefile_targets` lists the discovered make gate when a Makefile exists
- [ ] `verify.cited_paths` lists every finding path (even if the default toolchain excludes it)
- [ ] `commit_policy.commits == 1`

Companion miss is a plan-gate failure. Cursor-Governance: skill edits → `sync_generated_artifacts.py` → both `skill-registry.json` copies.

## 3. Local verify (blocks commit)

Discover, then run. Local verify **is** `make precommit-repo`. Do not run `make pr-check`. Do not require `pre-commit --all-files`. Do not invoke INTERNAL `precommit` / `pr-preflight` / `pr-full`.

### Discover

```bash
ls Makefile Makefile.am 2>/dev/null
# remediator verbs: precommit-repo (verify), git push (publish)
```

Prefer: `precommit-repo` (verify), then `git push` (publish). `improve` is optional kernels, not verify. Do not run `make pr` or `make pr-check`.

### Run (blocking)

```bash
PR_BASE=origin/main make precommit-repo
```

Rules:

1. Local verify **is** `make precommit-repo`.
2. Cited/planned paths get a real check even when `pyproject` / ruff excludes them (WIP/CQ case).
3. Re-run after any verify-fix. Do not commit on a partial green.
4. **Never** `git commit --no-verify` / `--no-gpg-sign`.
5. Native-ext import fail is `ENVIRONMENT`, not a lock-pin or source edit. Do not use `uv python find --system`.
6. Local verify iterations ≤ 5. Still one commit at the end.
7. Do not replay every workflow `run:`. Do not run ceremony `make pr-check`.

### No Makefile

Fall back to the workflow `run:` list in [fix-engine.md](fix-engine.md). Record that fallback on the plan.

## 4. One commit, one remediator publish

After `verify.all_green: true` and every `fix` cluster is `done`:

```text
git add <planned files only>
git commit -m "fix(pr-remediation): resolve {count} findings"
# remediator sanctioned publish — already-open PR branch:
git push
```

- Exactly one new commit on the branch for this remediation.
- Exactly one remediator publish (`git push` of the already-open PR branch).
- Do not run `make pr` or `make pr-check`. Campaign / feature work that is not this skill still must not treat raw `git push` as its publish path when `make pr` exists.
- Never `git add -u` / `-A`.
- Commit message lists finding ids; trailer `Remediation-Cycle: {repo}#{pr}/cycle-1`.
- **Forbidden:** commit-per-finding, publish-to-probe-CI, "wip" then fixup.

If a hook auto-modifies files on commit, amend only when the user-rule amend conditions are met; that amendment is still the same single commit.

## 5. Tracking during the batch

- [ ] Every `disposition: fix` is `done` or reverted + `defer` with reason
- [ ] Every non-fix disposition already has the reply text ready
- [ ] `verify.all_green: true`
- [ ] Staged names ⊆ planned files + companions (+ hook autofix tolerance)
- [ ] FIRST_MERGE_GATE still closed for this PR

## 6. When a second cycle is allowed

Only if, **after** the single publish, a **new** signal appears:

- a new review / Code Quality / Copilot / advanced-security comment with `created_at` after the publish
- a remote CI failure whose cause is an environment delta not reproducible locally

Not allowed as cycle 2: a finding that was on the PR at plan time and was skipped; an unrun local gate; splitting the batch because it looked large.

Cycle 2: re-ingest the **new** signals only, one plan, one commit. Never start cycle 4. Still no merge until FIRST_MERGE_GATE.
