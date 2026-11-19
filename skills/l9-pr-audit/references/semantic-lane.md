<!-- L9_META
schema: 1
parent: l9-pr-audit
layer: reference
role: semantic-lane
version: 1.2.0
status: active
-->

# Semantic lane contract

A lane is one read-only subagent that judges the PRs of one group from `lanes.plan.json`
(a stack or overlapping set, the dependency-bot PRs, or a single PR). The parent agent launches
every lane in one batch, then one independent verifier lane, then reconciles them in
`judgment.json`. Lanes never write `audit.json`.

The audit exists to catch what CI and bot review miss. CI proves the tests that exist pass; bot
review reads the diff. Neither feeds hostile input, tests the PR against its base, tests related
PRs merged together, reads why a check failed, or traces the real request path. Those five
probes, and judging the PR against what the requester asked for, are the lane's job.

## Brief to hand each lane (fill the brackets)

> You are the `[lane]` semantic lane of an `l9-pr-audit` run over `[owner/repo]`, PRs `[N, ...]`.
> Run directory: `[RUN]`. Read `references/semantic-lane.md` and `schemas/lane-findings.schema.json`
> in the skill, then write exactly one file, `[RUN]/lanes/[lane].json`, valid against that schema.
>
> Inputs: `[RUN]/snapshots/pr-<n>.json` (diff, base/head content, checks, threads, approvals, body),
> `[RUN]/ledgers/pr-<n>-ledger.json` (machine obligations and falsification seeds: your checklist),
> `[RUN]/frozen-pr-set.json` (heads, stacks, overlaps, linked issues). PR heads are fetched at
> `refs/remotes/origin/pr/<n>` in `[CLONE]`.
>
> Repository law: discover it (AGENTS.md, CLAUDE.md, ARCHITECTURE/INVARIANTS docs, ADRs, CODEOWNERS,
> contracts, enforcing tests) and cite the file. Use the authority ids `[ids from judgment draft]`.

## Hard rules

- **Read-only.** Never edit, commit, push, comment, review, label, close or merge. Never write in
  the audited clone. To execute, copy the head: `git -C CLONE archive origin/pr/N | tar -x -C SCRATCH/pr-N`.
- **Transport follows `protocol.rest_only`.** Review threads come from the GraphQL `reviewThreads`
  query unless `rest_only` is true, then `pulls/N/ccr/review_threads`; if the selected transport
  fails, the collector tries the other once and exits non-zero when both fail. A GraphQL HTTP 200
  whose envelope has `errors`, a null `repository` / `pullRequest` / `reviewThreads`, or a
  malformed `nodes` / `pageInfo` is a failure, not an empty thread list. Comment ids stored from
  GraphQL are `databaseId` (the numeric REST id). Bodies travel with that node and are fetched
  again via `pulls/comments/ID` using that id, never the GraphQL node id. Job logs via
  `actions/jobs/ID/logs`. Classic branch protection is recorded only on evidence: `ABSENT`
  requires the exact 404 body `Branch not protected`; a 200 merges its required checks; every
  other result is `UNKNOWN` and withholds complete READY.
- **Admitted remediation coupling.** `scripts/collect_snapshot.py` imports `rest_only` from
  `skills/l9-pr-remediation/scripts/protocol.py`. The selector is not copied into this pack.
  That import is the one runtime dependency on `l9-pr-remediation`: transport selection only.
  It does not grant remediation, mutation, convergence, or merge. A standalone audit pack that
  is not shipped beside `l9-pr-remediation` cannot select the review-thread transport.
- **No secret values** in any field; give the locator only.
- **Exact heads.** Judge the `head_sha` in the snapshot. If the head moved, stop: the parent re-collects.

## What every PR record must contain

| Field | Rule |
|---|---|
| `scope_fidelity` | **Every** changed file, one disposition each. `SCOPE_EXTENSION` must be named by a finding's `implementation_surfaces`. The assembler refuses a missing file. |
| `ci` | Every failing check with causality from its job log. Set `finding_id` when a finding explains it; only linked failures enter `failed_check_evidence`. |
| `review_threads` | Every thread, resolved or not, with a semantic disposition proven on the head. UI state is evidence, not closure. |
| `validation_runs` | Exact `tested_revision` (40-hex) or `UPSTREAM` for out-of-repo checks. A claimed `PASS` is prose until the verification-run receipt proves a separate run executed it on the head; the assembler records it `NOT_EXECUTED` without the receipt. |
| `objective_source` | Where the requester's ask came from: `ISSUE` (linked by "Closes #N"; required when the snapshot lists linked issues, unless an `ORIGINAL_PROMPT` or `USER` ask outranks it), `ORIGINAL_PROMPT`, `USER`, or `PR_BODY` when only the author's own description exists (recorded as a gap). |
| `requirements` | The requester's ask broken into checkable requirements, each `MET`, `PARTIAL`, `NOT_MET` or `UNKNOWN` with evidence on the head. `PARTIAL`/`NOT_MET` must name a `COMPLETENESS` or `SCOPE` finding. This is the completeness verdict; there is no separate one. |
| `probes` | All five probes below, each `DONE` (with the command, input or locator and what it showed), `NOT_APPLICABLE` (with why), or `NOT_DONE` (with why). A `NOT_DONE` probe withholds READY and is recorded as a gap. A `DONE` sentence is prose: it never projects SURVIVED or PASS by itself — only the verification-run receipt does. |
| `readiness` | `READY` only when you found nothing blocking and judged the head mergeable. The assembler still checks the ruleset gates, classic branch protection resolution and the verification-run receipt on the head before projecting READY. |

## The five probes

| Probe | Do this | `NOT_APPLICABLE` only when |
|---|---|---|
| `adversarial_input` | For every value the PR newly reads from outside the process (request payload, provider/LLM output, file, env, queue message), feed wrong types, empty, oversized, traversal (`../`), and injection-shaped values through the real entry point on a disposable copy. Record inputs and outcomes. | the PR adds no new external-input path |
| `base_discrimination` | Run the PR's new or changed tests against the base revision (copy the tests onto a base checkout). They must fail there for the behavior they claim to cover. | the PR changes no production behavior |
| `merged_tree` | Merge the PR with every PR it stacks on, is stacked under, or overlaps (`frozen-pr-set.json`), then run the coupled tests and the probes that touch shared code. Use `git merge-tree --write-tree` for conflicts, then test the merged tree. | the collector records no stack or overlap edge (the assembler enforces this) |
| `ci_causality` | For every failing check, read the job log and classify it `PR_INTRODUCED`, `PR_EXPOSED`, `PRE_EXISTING` (red on the base too: re-run the check's command on the base tree, do not trust an old green) or `ENVIRONMENT`. | no check is failing on the head |
| `ingress_reachability` | Trace the changed behavior from the real ingress (route, SDK action, CLI, job) to the new code and back to the response or persisted state. File existence and unit tests with mocks are not reachability. | the PR changes no runtime path (docs, CI config, lock-only) |

## What every finding must contain

- `authority`: a declared authority id; `merge_blocking_basis` must name the rule that gates merge.
- `evidence[]`: exact locators. `proves` lists only what that record discriminates. At least one
  CONFIRMED record proves `finding_origin`; blocking findings need `merge_blocking_basis`; a
  mutation-eligible fix needs `implementation_surface`. TEST/CI/RUNTIME records carry `revision`
  and `result` or their outcome is recorded UNKNOWN.
- `implementation_surfaces`: repository paths only. Prose goes in `fact`.
- `detection`: whether CI and bot review already caught it on this head (`CAUGHT` / `MISSED` /
  `NOT_APPLICABLE`) with evidence. This is how the audit measures its own value.
- No finding from diff size alone; no conclusion without evidence; severity by consequence.

## Close-out

Before writing, re-verify every retained finding against the exact head and drop what does not
reproduce. Reply to the parent in at most 15 lines: readiness per PR, blocking findings, unknowns.

## Verification-run receipt

`SURVIVED`, `validation_result PASS`, the `VERIFICATION` audit pass and `CONVERGED` are never
projected from a READY lane or from a prose `DONE`. They require a separate run-directory receipt:
a verification run (not the semantic lane) that actually executed the probes and validations
writes `[RUN]/runs/verification/receipt.json`:

```json
{
  "schema": "l9.pr-audit.verification-run-receipt/v1",
  "head_by_pr": {"1": "<40-hex frozen head>", "2": "<40-hex frozen head>"},
  "commands": [
    {
      "command": "the command that ran",
      "head_sha": "<one frozen head>",
      "exit_code": 0,
      "measured_result": "what the command showed",
      "provenance": "independent-verifier"
    }
  ],
  "claim_ids": ["<every claim_id of the audit>"],
  "obligation_ids": ["<every obligation_id, incl. OB-O-<n>, OB-TD-<n>, OB-<cid>>"],
  "probe_ids": {"1": ["adversarial_input", "base_discrimination", "merged_tree", "ci_causality", "ingress_reachability"], "2": ["..."]},
  "observed_finding_ids": ["<finding ids re-observed>"]
}
```

The assembler reads only `runs/verification/receipt.json`. Another `runs/*/receipt.json` is not
this verification. Each command must name a frozen head, an integer exit code, a measured
result, and a provenance that is not the lane or the author. The id lists must cover every
claim, obligation, and probe before any PASS, SURVIVED, or READY is projected. Missing, unbound,
empty, or incomplete: probes and validation runs record `NOT_EXECUTED`, the VERIFICATION pass
says `verification not executed`, nothing is stamped `SURVIVED`, READY is withheld, and
`U-RECEIPT` blocks readiness and convergence.

## Independent verifier lane

After the semantic lanes, launch one verifier that authored none of the findings. Brief:

> Reproduce each merge-blocking finding in `[RUN]/lanes/*.json` on the exact head from its
> evidence alone: re-run the probe or test, re-read the cited lines. Write
> `[RUN]/lanes/verify-[verifier].json` (`schemas/finding-verification.schema.json`), binding each
> verdict to the exact head of every PR the finding affects (`pr_heads`): `REPRODUCED`,
> `NOT_REPRODUCED` (the defect does not occur as described) or `INCONCLUSIVE`, each with what you
> ran and saw. Do not add findings; report new defects to the parent in your reply.

A blocking finding that is `NOT_REPRODUCED` stops blocking; one with no `REPRODUCED` verdict stays
blocking but leaves a convergence gap. A lane may not verify its own findings.

## Parent reconciliation (`judgment.json`)

The parent owns what no single lane can see: the authority table and its conflicts, the
component/boundary model (with a `control` judgment per PR for every SECURITY, POLICY_ENFORCEMENT,
VALIDATION or SOURCE_OF_TRUTH boundary), `reconcile` overrides of a lane's blocking verdict with
the cross-lane evidence that justifies them, `parent_findings` for defects that span lanes (one
rule applied unevenly, duplicated changes), and the merge order. Then run
`scripts/run_audit.py finalize`.
