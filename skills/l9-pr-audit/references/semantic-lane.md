<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: semantic-lane
version: 1.0.0
status: active
-->

# Semantic lane contract

A lane is one read-only subagent that judges the PRs of one group from `lanes.plan.json`
(a stack, the dependency-bot PRs, or a single PR). The parent agent launches every lane in
one batch, then reconciles them in `judgment.json`. Lanes never write `audit.json`.

## Brief to hand each lane (fill the brackets)

> You are the `[lane]` semantic lane of an `l9-pr-audit` run over `[owner/repo]`, PRs `[N, ...]`.
> Run directory: `[RUN]`. Read `references/semantic-lane.md` and `schemas/lane-findings.schema.json`
> in the skill, then write exactly one file, `[RUN]/lanes/[lane].json`, valid against that schema.
>
> Inputs: `[RUN]/snapshots/pr-<n>.json` (diff, base/head content, checks, threads, approvals, body),
> `[RUN]/ledgers/pr-<n>-ledger.json` (machine obligations and falsification seeds: your checklist),
> `[RUN]/frozen-pr-set.json` (heads, stacks, ruleset merge gates). PR heads are fetched at
> `refs/remotes/origin/pr/<n>` in `[CLONE]`.
>
> Repository law: discover it (AGENTS.md, CLAUDE.md, ARCHITECTURE/INVARIANTS docs, ADRs, CODEOWNERS,
> contracts, enforcing tests) and cite the file. Use the authority ids `[ids from judgment draft]`.

## Hard rules

- **Read-only.** Never edit, commit, push, comment, review, label, close or merge. Never write in
  the audited clone. To execute, copy the head: `git -C CLONE archive origin/pr/N | tar -x -C SCRATCH/pr-N`.
- **GitHub is REST only.** `gh api --method GET repos/...`; threads via `pulls/N/ccr/review_threads`,
  bodies via `pulls/comments/ID`; job logs via `actions/jobs/ID/logs`.
- **No secret values** in any field; give the locator only.
- **Exact heads.** Judge the `head_sha` in the snapshot. If the head moved, stop: the parent re-collects.

## What every PR record must contain

| Field | Rule |
|---|---|
| `scope_fidelity` | **Every** changed file, one disposition each. `SCOPE_EXTENSION` must be named by a finding's `implementation_surfaces`. The assembler refuses a missing file. |
| `ci` | Every failing check with causality from its job log. Set `finding_id` when a finding explains it; only linked failures enter `failed_check_evidence`. |
| `review_threads` | Every thread, resolved or not, with a semantic disposition proven on the head. UI state is evidence, not closure. |
| `validation_runs` | Exact `tested_revision` (40-hex) or `UPSTREAM` for out-of-repo checks. Set `discriminates_against_base` only when the same tests were run on the base and failed. |
| `readiness` | `READY` only when you found nothing blocking and judged the head mergeable. The assembler still checks the ruleset gates on the head before projecting READY. |

## What every finding must contain

- `authority`: a declared authority id; `merge_blocking_basis` must name the rule that gates merge.
- `evidence[]`: exact locators. `proves` lists only what that record discriminates. At least one
  CONFIRMED record proves `finding_origin`; blocking findings need `merge_blocking_basis`; a
  mutation-eligible fix needs `implementation_surface`. TEST/CI/RUNTIME records carry `revision`
  and `result` or their outcome is recorded UNKNOWN.
- `implementation_surfaces`: repository paths only. Prose goes in `fact`.
- No finding from diff size alone; no conclusion without evidence; severity by consequence.

## Close-out

Before writing, re-verify every retained finding against the exact head and drop what does not
reproduce. Reply to the parent in at most 15 lines: readiness per PR, blocking findings, unknowns.

## Parent reconciliation (`judgment.json`)

The parent owns what no single lane can see: the authority table and its conflicts, the
component/boundary model (with a `control` judgment per PR for every SECURITY, POLICY_ENFORCEMENT,
VALIDATION or SOURCE_OF_TRUTH boundary), `reconcile` overrides of a lane's blocking verdict with
the cross-lane evidence that justifies them, `parent_findings` for defects that span lanes (one
rule applied unevenly, duplicated changes), and the merge order. Then run
`scripts/run_audit.py finalize`.
