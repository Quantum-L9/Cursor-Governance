<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: remediation_plan
tags: [pr, plan, census, tracking, one-commit, makefile, pre-commit]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-16
/L9_META -->

# Remediation Plan (census → plan → one commit)

## Purpose

Spend the first pass on a **complete diagnostic census**, write a **structured plan that tracks every finding**, then execute the whole codebase batch and push **one** commit. Remote CI is confirmation, not a discovery loop. Extra commits waste runner minutes.

This is an inline working ledger (cycle proof), not a packaged report.

## Hard order

```text
CENSUS (no edits) → PLAN (disposition every finding) → FIX BATCH →
MAKEFILE + PRE-COMMIT VERIFY → ONE COMMIT → ONE PUSH → REPLY
```

- **No file edits** until the plan has a disposition for every ingested finding.
- **No commit** until Makefile + every `.pre-commit-config.yaml` hook is green.
- **No second commit** to "see what CI says."
- Cycle 2+ is only for signals that **did not exist** at census time (new post-push comments, or a local/remote environment delta). Missing the census is a protocol violation, not a reason to cycle.

## 1. Full census (mandatory, before any patch)

Ingest **all** open surfaces on the current head, in parallel. Do not stop after the first red check.

| Surface | How | Track as |
|---------|-----|----------|
| Required + non-required checks | `gh pr checks`, `gh run view --log-failed`, annotations | `ci` |
| Human reviews + inline + issue comments | REST + GraphQL threads | `review` |
| Code-review agents | `github-code-quality[bot]`, Copilot — [code-review-agents.md](code-review-agents.md) | `code_review_agent` |
| Other bots | CodeRabbit, Gemini, etc. | `bot` |
| Sonar / CodeQL / debt | fetch scripts when configured or failing | `scanner` / `debt` |

Completeness: finding count must cover every unresolved thread, every failed check, every Code Quality / Copilot comment. If a surface was not queried, the census is incomplete — do not plan, do not edit.

## 2. Plan schema (working ledger)

Write this once after classify. Update `status` as work lands. Do not start a second plan mid-batch.

```yaml
remediation_plan:
  pr: "{owner}/{repo}#{n}"
  head_sha: "{40-char}"
  census_complete: true
  one_and_done: true

  findings:
    - id: "cq-1"
      source: github-code-quality | copilot | human | bot | ci | sonar | codeql | debt
      author: "{login}"
      file: "path"          # null if none
      line: 12              # null if none
      message: "{one line}"
      ownership: CODEBASE | CI_PIPELINE | HUMAN | FALSE_POSITIVE
      disposition: fix | reply_ack | reply_disagree | defer | already_fixed | note_pipeline
      cluster: "{root-cause id}"
      status: pending | done
      evidence: "{why this disposition}"

  clusters:
    - id: "{root-cause}"
      finding_ids: ["cq-1", "ci-2"]
      files: ["path"]
      action: "{one-line fix}"

  verify:
    makefile_targets: ["agent-check"]   # discovered; empty if no Makefile
    precommit_config: ".pre-commit-config.yaml"  # null if absent
    precommit_hooks: ["ruff", "ruff-format"]     # every hook id in the file
    extra_local_commands: []            # workflow run: not covered by make/pre-commit
    all_green: false                    # flips true only after verify

  commit_policy:
    commits: 1
    pushes: 1
    no_verify: false
```

**Plan gate (blocks edits):**

- [ ] `census_complete: true`
- [ ] Every ingested finding has `ownership` + `disposition` + `evidence`
- [ ] Every `fix` item is in a cluster with files + action
- [ ] `verify.precommit_hooks` lists **every** hook in `.pre-commit-config.yaml` when that file exists
- [ ] `verify.makefile_targets` lists the discovered make gate(s) when a Makefile exists
- [ ] `commit_policy.commits == 1`

## 3. Local verify — Makefile + pre-commit (blocks commit)

Discover, then run. Prefer one make target that already wraps the rest; still prove every pre-commit hook executed.

### Discover

```bash
# Makefile targets (first existing name wins as the primary gate)
# Prefer: agent-check, pr-check, check, ci, validate, test
ls Makefile Makefile.am 2>/dev/null
make -qp 2>/dev/null | awk -F: '/^[a-zA-Z0-9][^$#\/\t=]*:([^=]|$)/ {print $1}' | sort -u

# Every hook the commit hook would run
test -f .pre-commit-config.yaml && python3 -c "
import yaml,sys
c=yaml.safe_load(open('.pre-commit-config.yaml'))
for r in c.get('repos') or []:
    for h in r.get('hooks') or []:
        print(h.get('id',''))
"
```

If PyYAML is missing, read `.pre-commit-config.yaml` and list every `id:` under `hooks:`.

### Run (blocking)

```bash
# 1) Every pre-commit hook, all files — required when the config exists
pre-commit run --all-files

# 2) Makefile primary gate — required when a Makefile exists
make agent-check    # or the first discovered alias: pr-check | check | ci | validate

# 3) Any workflow run: command not already covered by (1) or (2)
```

Rules:

1. If `.pre-commit-config.yaml` exists, `pre-commit run --all-files` is mandatory. A make target that *should* wrap it does not excuse skipping this unless that target's log shows **each hook id** ran and passed.
2. If a Makefile exists, run the discovered primary target. Do not invent ad-hoc `ruff`/`eslint` one-offs as a substitute when `make` already owns the gate.
3. Re-run **all** of (1)+(2)+(3) after any verify-fix. Do not commit on a partial green.
4. **Never** `git commit --no-verify` / `--no-gpg-sign` / skip hooks. The commit itself must execute the configured hook install (`.pre-commit-config.yaml` / husky / `core.hooksPath`).
5. Local verify iterations ≤ 5. Still one commit at the end.

### No Makefile and no pre-commit

Fall back to the workflow `run:` list in [fix-engine.md](fix-engine.md). Record that fallback on the plan. Do not skip gates that exist.

## 4. One commit, one push

After `verify.all_green: true` and every `fix` cluster is `done`:

```text
git add <planned files only>
git commit -m "fix(pr-remediation): resolve {count} findings"
git push
```

- Exactly one new commit on the branch for this remediation.
- Exactly one push.
- Commit message lists finding ids (or cluster ids) in the body; trailer `Remediation-Cycle: {repo}#{pr}/cycle-1`.
- **Forbidden:** commit-per-finding, push-to-probe-CI, "wip" then fixup, second commit because verify was skipped.

If a hook auto-modifies files on commit, amend only when the user-rule amend conditions are met; that amendment is still the same single commit, not a second remediation commit.

## 5. Tracking during the batch

As each cluster lands, set `status: done` on its findings. Before commit:

- [ ] Every `disposition: fix` is `done` or reverted + `defer` with reason
- [ ] Every non-fix disposition already has the reply text ready (posted after push)
- [ ] `verify.all_green: true`
- [ ] `git diff --cached --name-only` ⊆ planned files (+ hook autofix tolerance)

## 6. When a second cycle is allowed

Only if, **after** the single push, a **new** signal appears that the census could not have seen:

- a new review / Code Quality / Copilot comment with `created_at` after the push
- a remote CI failure whose cause is an environment delta (secrets, runner OS) not reproducible locally

Not allowed as cycle 2:

- a finding that was on the PR at census time and was skipped
- a local gate the agent did not run
- splitting the batch because it "looked large"

Cycle 2 still follows this file: re-census the **new** signals only, one plan, one commit. Never start cycle 4.
