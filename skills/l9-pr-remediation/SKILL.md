---
name: l9-pr-remediation
description: diagnose or converge github prs — plan the open-pr fleet once (pr_fleet.py), remediate every non-conflicting pr in one subagent wave, verify with precommit-repo then git push, fully resolve sonarcloud findings (never merge-blocking), then a stack-safe oldest-first merge train on pr_board.py verdicts. do not run make pr or make pr-check. use when a campaign left prs unmergeable, the user invokes /l9-pr-remediation, or they ask to fix, remediate, babysit, converge, or merge failing prs.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pr, ci, code-review, github-code-quality, copilot, diagnose, sonarcloud, codeql, debt, remediation, concurrent, subagents, github, makefile]
  owner: igor_beylin
  status: active
  version: 5.0.0
  updated: 2026-09-04
---

# PR Remediation

## Purpose

One pack, two intents: **Diagnose** (read-only readiness) or **Converge** (failing → green → merged). Straight line, no campaign, no Program Execution, no packaging theater.

Converge is **PLAN → WAVES (REMEDIATE_ALL) → MERGE_TRAIN**. It is not remediate-and-merge each PR as it turns green. [references/run-contract.md](references/run-contract.md).

| Intent | Mutates | Triggers | Behavior |
|--------|---------|----------|----------|
| **Diagnose** | no | review / readiness / blockers / `/pr` / “ready to merge?” | Fetch PR+reviews+CI; overlap advisory; slim verdict; **never** commit/push/merge |
| **Converge** | yes | `/l9-pr-remediation` / fix / remediate / babysit / merge failing PRs | Fleet plan → remediation waves → stack-safe oldest-first merge train |

Invoking this skill (or `/l9-pr-remediation`) is merge authorization for **all open PRs** in the target repo. Campaigns and `make pr` only publish. They do not merge. Load [references/merge-advise.md](references/merge-advise.md).

### Intent precedence (hard)

1. If `/l9-pr-remediation` or mutate language is present (`fix`, `remediate`, `babysit`, `push`, `merge` failing PRs, autonomy packet) → **Converge**.
2. Else if review/readiness/blockers/`/pr` → **Diagnose** only.
3. Ambiguous mixed ask without mutate verbs → **Diagnose**; ask one question before Converge.

## Target

All **open** PRs in the target `{owner}/{repo}`. A single `{owner}/{repo}#{pr}` argument still starts there, then continues through the remaining open PRs. The fleet is inventoried once before the first merge. If no PR exists and Converge points at baseline debt/alerts: open a PR, then continue.

## Deterministic owners (this host)

Prose never recomputes what these helpers compute. Each one is read-only advice or a bounded executor; none of them is a scheduler, a lease store, or a campaign.

| Concern | Owner | Never |
|---|---|---|
| Fleet inventory, stack edges, path overlap, merge order, safe waves, assignments, result acceptance | `ops/autonomy/pr_fleet.py` (`plan` / `assign` / `accept` / `model`) | edit, push, merge |
| Board verdict per PR (`merge` / `fix` / `wait` / `leftover`) | `ops/autonomy/pr_board.py` | merge |
| Merge execution and stack safety | `ops/autonomy/stack_safe_merge.py --run` behind `ops/autonomy/merge_gate.py` | `--admin`, hand-typed `--squash` |
| Merge authorization receipt | `ops/autonomy/authorize_merge.py --all-open` | expire-less receipts |
| Concurrency caps | `ops/autonomy/execution_profile.py` (read by `pr_fleet.py waves`) | numbers in this pack |
| Subagent roles, result schema, acceptance | `environment/agents/cursor-subagents/` + `environment/agents/results/` (called by `pr_fleet.py accept`) | narrative completion |
| Thread replies | `scripts/reply_threads.py` | per-thread `gh` loops |

## Makefile capability graph (this host)

Remediation is **not** the `make pr` ceremony. do not run `make pr`. Do not run `make pr-check`. Those verbs stay the campaign / feature publish path. This skill must not invoke `make pr`. `make pr` is not the remediator publish path.

**Remediator PUBLIC** (only these as shipping verbs):

| Verb | Meaning | This skill |
|------|---------|------------|
| `L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo` | Changed-file hooks plus locked `ruff check` / `ruff format --check`. No pytest. No conformance. | **Local verify.** Blocks commit. |
| `git push` | Update the already-open PR branch. | **Publish.** Existing PR only. Pathspecs on the commit. |
| `make improve` | Kernel revision. | Optional, when kernels apply. Not a publish path. |

**Ceremony — do not invoke from this skill:** `make pr`, `make pr-check`, `PR_REMEDIATE=0 make pr`, `make pr-full`, pytest, peer-execution conformance, L4 `begin` / `record-kernels` / `authorize-release` as a publish ritual. INTERNAL targets (`pr-preflight`, `precommit`, `pr-full`, `pre-commit install`) are not shipping commands.

Failure loop: diagnose → fix → (`make improve` if kernels apply) → `make precommit-repo` → commit → `git push` **once**. If hooks rewrite files, commit the rewrite and re-run `make precommit-repo` once. Pytest and conformance stay on CI.

If no PR number exists (baseline debt case): same verify, `git push` the branch, then `gh pr create` only to obtain a number. That create is the exception, not `make pr`.

## Diagnose

Load [references/diagnose-workflow.md](references/diagnose-workflow.md). Optional focused lenses: [references/review-angles.md](references/review-angles.md). List unanswered **code-review agent** comments (`github-code-quality[bot]`, Copilot) as review blockers — [references/code-review-agents.md](references/code-review-agents.md). Report file-overlap across open PRs as advisory (`pr_fleet.py plan --json` is the fastest way to get it). Do not merge.

**Forbidden in Diagnose:** commit, push, force-push, edit worktree for fixes, alignment %, gap matrix, deep-eval, index theater, babysit loops, `gh pr merge`.

## Converge — Inputs → Actions

| Signal | Source | Action |
|--------|--------|--------|
| Fleet | `pr_fleet.py plan --board` | One receipt: inventory, topology, merge order, waves, board per head |
| CI failures | `gh run view --log-failed`, annotations | Fix codebase root cause |
| Review + inline | `gh api` reviews/comments | Validate against current code; fix or reply |
| Code-review agents | `github-code-quality[bot]`, Copilot review logins | Inspect **every** comment; fix if validated; reply to all — [references/code-review-agents.md](references/code-review-agents.md) |
| Workflows | `.github/workflows/*.yml` | Read-only gate discovery |
| SonarCloud | `scripts/sonar_fetch.py` with the environment `SONAR_TOKEN` | **Always when `sonar-project.properties` exists.** Resolve every confirmed issue on the PR head in the same commit. Never a merge blocker. [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md) |
| CodeQL | `scripts/codeql_fetch.py` | Lazy: only if check failing or alerts open |
| Lint/type/test/build debt | `scripts/debt_audit.py` + repo toolchain | Lazy: only if toolchain/baseline red |

## Converge — Outputs (per PR that changes code)

- One fleet receipt for the run (`.l9/pr/fleet.json`; reused until a head moves)
- One structured remediation plan (inline ledger) per PR being edited
- One commit, one remediator publish (success path)
- One accepted result document per delegated assignment (`pr_fleet.py accept`)
- Canonical replies on every thread; all threads resolved
- Short convergence status with timing counters

No tarballs, run-report schemas, issue-file bundles, or exemplary packaging.

## Authority Order

1. Latest user instruction and explicit PR/scope
2. Current repository source and tests
3. Required-check logs and branch-protection evidence (`pr_board.py`)
4. Human review, then **code-review agents** (`github-code-quality[bot]`, Copilot), then other blocking bots, then newer/higher-confidence comments
5. Scanner API evidence confirmed against current source (SonarCloud is work, never a wall)
6. Host Makefile public verbs and the deterministic owners above, then this skill + references
7. Unknown — do not invent; note and continue independent work

## Kernel bind (compressed)

Applies `kernels/Diagnose First Kernel.md`, `kernels/Validate & Repair.md`, and `kernels/Recursive Alignment.md` to this pack. Do not load those files mid-run unless a conflict appears.

| Kernel | Binding |
|--------|---------|
| Diagnose First | Inspect the current PR (head SHA, checks, threads, cited files) before any edit. Verify root cause from trusted evidence. Label missing values `Unknown`. Brace tokens (`{owner}/{repo}`) are templates, not executable. Do not combine opaque diagnose+mutate. |
| Validate & Repair | Smallest source-aligned fix. No stubs, suppressions, or fabricated checks. Report only validation that ran: `Passed` / `Failed` / `Skipped` / `Unknown` / `NotApplicable`. Local `make precommit-repo` is not remote CI. |
| Recursive Alignment | One command surface (Makefile PUBLIC verbs). One venv authority (`UV_PYTHON` native). One merge authority (`merge_gate` + oldest-first stack-safe). One fleet owner (`pr_fleet.py`). Autonomy doctrine is `environment/contracts/autonomy`; subagent roles and results are `environment/agents/cursor-subagents`. Generated registries are companions, not a second protocol. |

## Laws (Converge)

1. **Diagnose First, then one fleet plan.** Required once: `pr_fleet.py plan --board` (inventory, files, stack edges, overlap, merge order, waves, board per head, fingerprint), command surface, venv fingerprint, subscribe each PR. Emit `RUN_CONTRACT` from the receipt and reuse it. Re-plan only when the fingerprint changes (a head moved, a PR opened or merged) — never by hand. Per PR: ingest + diagnose (observed / expected / root cause / Unknown) **before** any edit of that PR. [references/run-contract.md](references/run-contract.md).
2. **Launch the whole safe wave, then keep working.** Every PR in `waves.first_wave.remediate` gets its own bounded assignment (`pr_fleet.py assign --kind remediate`) and launches in **one** message; PRs blocked by a claim conflict get recon now and remediation in the next wave; `board=wait` PRs get a background watcher. The main agent takes one remediation itself when a lane is free, otherwise the merge-train preflight — it never idles on a background wave. Caps come from the execution profile via the planner, never from this pack. [references/fleet-waves.md](references/fleet-waves.md).
3. **One-and-done per PR, then a safety valve.** Success path is **one** plan, **one** commit, **one** CI run per PR. Max three cycles; never start cycle 4. Extra cycles are only for signals that did not exist at plan time.
4. **Codebase only.** Repair source, tests, fixtures, package deps. Never edit `.github/workflows/**`, actions, runners, permissions, secrets, OIDC, branch protection, check wiring, or CI-only infra. Never add `continue-on-error` or skip conditions to “heal” CI. Pipeline blockers: record one line in the status and keep remediating everything else. Assignments carry these as `forbidden_paths`; a result that touched one is rejected.
5. **Ownership before edit — and ownership is not the board.** Load [references/ownership-boundary.md](references/ownership-boundary.md). Ownership answers **one** question: may I patch this file? Edit only `CODEBASE`. `ENVIRONMENT` is not a code defect — run the venv preflight once and continue. Ownership never decides what happens to the PR; `edit=CI_PIPELINE` is not `board=leftover`.
6. **Plan the PR, then patch that PR.** No edits on a PR until its ingested findings have dispositions. A locked `Remediation-Cycle` / plan whose files still match is executed, not rewritten.
7. **One commit, one remediator publish.** Zero if nothing codebase-safe remains. Never commit-per-finding, never publish to probe CI, never `--no-verify`. Remediator publish **is** `git push` of the already-open PR branch. Do not run `make pr`.
8. **Local verify blocks commit.** Local verify **is** `L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo`. Do not run `make pr-check`, pytest, conformance, or all-files pre-commit. Record `Passed` / `Failed` / `Unknown`. Remote CI is independent confirmation — never claim remote `Passed` from local `Passed`.
9. **Results are documents, not sentences.** Every delegated assignment returns one `l9.cursor-subagent.result.v1` document; `pr_fleet.py accept` judges it against the assignment (identity, base SHA, role, writable scope, read-only roles report no changes) and preserves `partial` / `blocked` / `failed`. "Done" in chat is not completion. A rejected result is re-assigned or taken over by the main agent — never trusted.
10. **Own until merged, in the background.** Subscribe to every in-scope open PR at preflight. After a publish record the head SHA, launch (or keep) a watcher for that PR, and move to the next ready PR. Poll workers and watchers never merge. Never finish with “re-invoke `/l9-pr-remediation` when CI turns green.”
11. **Validate suggestions against current code.** Comment snippets are not ground truth.
12. **No gate weakening / suppressions.** No `NOSONAR`, blanket noqa/type-ignore/eslint-disable, CodeQL dismissals/exclusions, skipped tests, or lowered thresholds. Narrow documented suppression only for a *proven* false positive where a code fix is less safe.
13. **SonarCloud: resolve fully, block never.** When `sonar-project.properties` exists, fetch the PR's issue set with the environment `SONAR_TOKEN` on every Converge, confirm each issue against the head, fix every confirmed one in the same commit, and re-query after the head is analysed. A red Sonar check is not in the required set unless `pr_board.py` says so; it never holds the train. Unfixable residue is a Deferred reply plus the issue handoff, not a stopped merge.
14. **Every conversation resolved.** Reply Fixed / Deferred / Acknowledged / Disagreed, then `resolveReviewThread` on **every** GraphQL `reviewThreads` node with `isResolved: false` — any author. Paginate threads (`pageInfo.hasNextPage`). GitHub "a conversation must be resolved" **is** a merge blocker. HUMAN: name the decision, resolve, and pass it to `pr_board.py --human-decision`. Bots re-file on new lines after a push — those are **new** threads. Re-query after every publish and immediately before each merge.
15. **FIRST_MERGE_GATE + stack-safe oldest-first.** Never force-push, rewrite history, expose tokens, or `--admin` merge. Merge only after the fleet receipt exists and the required sequence is remediated and published. Order is `merge_order` from the receipt (oldest `createdAt`, parents before children). Merge **only** via `ops/autonomy/stack_safe_merge.py --run`. After a parent squash, never `gh pr update-branch` — rebase `--onto` the new base. When the only blocker is required checks **in progress**, the watcher owns the wait; merge when `CLEAN`.
16. **No invented evidence.** Do not invent check conclusions, SHAs, thread ids, or `Passed`. `{braces}` in this pack are templates until substituted from `gh` / helper / `file` output observed in this run.
17. **The board is computed, not judged.** `board=merge|fix|wait|leftover` comes from `ops/autonomy/pr_board.py` (required-check identity from branch protection ∪ rulesets ∪ required workflows; conflicted **paths**). Never author it from `mergeStateStatus` alone, from a check conclusion without the required set, or from an issue body. A red check outside the required set does not block merge (`UNSTABLE` is a merge). `leftover` is an evidenced **input**: `--human-decision` or `--unfixable-check`. Unknown telemetry degrades to `wait`, never to `merge`.
18. **Above-paygrade is an issue, not a question.** After best-effort, `HUMAN` / unfixable required `CI_PIPELINE` / unfixable `ENVIRONMENT` → `gh issue create`, launch `l9-issue-remediation`, continue independent PRs. Do not ask the human to unblock. [references/issue-handoff.md](references/issue-handoff.md).

## Hot Path (Converge)

0. **Authorize, then plan the fleet (read-only).** User invoke is merge authorization — write the receipt. Load [references/run-contract.md](references/run-contract.md). Cache remediator verbs, fingerprint the venv (`UV_PYTHON` = uv-managed **native** CPython; never `uv python find --system`). Then one planner call; subscribe every PR it lists (`ops/scripts/lib/gh_subscribe_pr.sh`, runs in parallel; a classified GraphQL refusal does not waive ownership). Reuse a worktree that already holds a branch (`git worktree list`); `worktree_add_wired.sh` only when none exists. Emit `RUN_CONTRACT` from the receipt. Do not edit a PR in this step.

```bash
# TEMPLATE — substitute owner/repo from the verified gh target in this run
GOV_PY="${GOV_PY:-$PWD/.venv/bin/python}"
"$GOV_PY" ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
"$GOV_PY" ops/autonomy/pr_fleet.py plan --repo {owner}/{repo} --board --json
#   → .l9/pr/fleet.json: prs, stack_edges, overlap, merge_order, boards, waves, velocity
```

1. **Discover gates (read-only).** Cache verify=`make precommit-repo`, publish=`git push`. Do not cache `make pr-check` or `PR_REMEDIATE=0 make pr`. Do not edit CI surfaces.
2. **Launch wave 1 in one message.** For every PR in `waves.first_wave.remediate`: `pr_fleet.py assign --kind remediate --pr {n} --record --prompt`, then launch the managed `l9-pr-remediation` Task (background) with that prompt. For every PR in `first_wave.recon`: `--kind recon` → `l9-recon`. For every PR in `first_wave.watch`: `--kind watch` → `l9-recon` watcher. Then continue: the main agent remediates one lane itself only if the cap left one free, else prepares the merge train. [references/fleet-waves.md](references/fleet-waves.md).
3. **Per PR (inside a lane): diagnose.** Failed CI + annotations, human reviews, every bot comment, every CRA thread, SonarCloud issue set for the PR (authenticated). Read cited files at the current head. Record observed / expected / root cause / Unknown. No edits yet. [references/signal-ingestion.md](references/signal-ingestion.md) + [references/code-review-agents.md](references/code-review-agents.md).
4. **Classify + write that PR's plan.** Ownership then severity; `disposition: fix` requires a verified root cause. Companions if touching `pec/*`, `skills/*`, or `rules/*`. [references/finding-classifier.md](references/finding-classifier.md) + [references/remediation-plan.md](references/remediation-plan.md).
5. **Fix the planned batch.** All `disposition: fix` clusters, Sonar issues included, inside the assignment's allowed paths. Skip HUMAN / CI_PIPELINE / ENVIRONMENT after best-effort — open the issue handoff, continue. [references/fix-engine.md](references/fix-engine.md) + [references/issue-handoff.md](references/issue-handoff.md).
6. **Local verify (blocks commit).** `L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo`. If hooks rewrite files, commit the rewrite and re-run once. ≤5 iterations. Never `--no-verify`, `make pr-check`, `make precommit`, `--all-files`.
7. **One commit, one remediator publish.** Explicit `git add` of planned files only. Never `-u` / `-A`. Never `git reset --hard`. `git push` the already-open PR branch. Trailer `Remediation-Cycle: {repo}#{pr}/cycle-1`.
8. **Reply + resolve.** Every thread, any author. Inspect cited files first. `python3 -u skills/l9-pr-remediation/scripts/reply_threads.py --repo {owner}/{repo} --input {threads.json}`. [references/review-replies.md](references/review-replies.md).
9. **Return the document; accept it.** A lane ends by writing its `l9.cursor-subagent.result.v1` document. The main agent runs `pr_fleet.py accept --assignment {id} --result {doc.json}`; `ACCEPTED` closes the lane, `ACCEPTED_INCOMPLETE` keeps the PR in the next wave, `REJECTED` re-assigns. Then launch the next wave (`mutation_waves[k]`) the same way, re-plan only if the fingerprint changed. [references/convergence-loop.md](references/convergence-loop.md).
10. **MERGE_TRAIN** after REMEDIATE_ALL. Walk `merge_order`. Immediately before each merge re-run `pr_board.py` for that head, re-query `reviewThreads`, and let `stack_safe_merge.py` probe children. `board=merge` → merge. `board=fix` → back to step 3 for that PR. `board=wait` → the watcher owns it; merge on `CLEAN`. `board=leftover` → that PR only, with its declaration and issue handoff; the train continues. After any merge that touched generated paths, heal per [references/generated-heal.md](references/generated-heal.md).

```bash
# NEVER type --squash yourself. The helper emits --merge for a stack parent,
# --squash only for an unstacked leaf.
"$GOV_PY" ops/autonomy/stack_safe_merge.py --repo {owner}/{repo} --pr {n} --run
```

Never `--admin`. Never unpack diffs. Never merge-as-you-go. An unpredicted `CONFLICTING` after a merge means the head moved — re-plan (fingerprint) before the next merge.

## Done When (Converge)

Mission is `open_prs=0` — an empty `gh pr list --state open` on the target repo. Anything short of that names the PRs still open and the `pr_board.py` receipt that keeps each one open.

- every remediation published via `git push`; every delegated result accepted (no lane closed on narrative)
- every open PR carries a fresh `pr_board.py` verdict at its final head; only `board=leftover` stays unmerged, each with its declaration **and** an opened issue handed to `l9-issue-remediation`
- no unpredicted merge conflict; no unresolved GraphQL `reviewThreads` (any author; pagination complete)
- SonarCloud: every confirmed issue on each converged head fixed; remote closure claimed only when observed after analysis; residue deferred with an issue, never left silent
- green mergeable PRs merged oldest first, stack-safe; worktrees clean
- status names remaining blockers, the fleet fingerprint, and the six timing counters

## Generated-artifact heal (same publish path)

Not a second publish path. After any merge that touched generated paths — or whenever `.l9/pr/regen-required.txt` is non-empty — run `"$PWD/.venv/bin/python" ops/scripts/sync_generated_artifacts.py --force` (plus `generate_manifest.py` / `validate_manifest.py` when `environment/program-execution/MANIFEST.json` is in the set), then `make precommit-repo`, commit, `git push`. File-by-file audit only for a non-generated unresolved path. [references/generated-heal.md](references/generated-heal.md), `rules/53-pr-overlap-guardrail.mdc`.

## Resource Map

### Diagnose
- [references/diagnose-workflow.md](references/diagnose-workflow.md)
- [references/code-review-agents.md](references/code-review-agents.md)
- [references/review-angles.md](references/review-angles.md)
- [references/merge-advise.md](references/merge-advise.md)
- [references/run-contract.md](references/run-contract.md)

### Converge
- [references/run-contract.md](references/run-contract.md) — preflight, Makefile surface, venv, fleet receipt
- [references/fleet-waves.md](references/fleet-waves.md) — wave launch, assignments, result acceptance, watchers
- `ops/autonomy/pr_fleet.py` — fleet owner (`plan` / `assign` / `accept` / `model`)
- `ops/autonomy/pr_board.py` — board authority (`merge|fix|wait|leftover` + receipt)
- `ops/autonomy/stack_safe_merge.py` — merge executor
- [references/ownership-boundary.md](references/ownership-boundary.md) — edit axis only
- [references/remediation-plan.md](references/remediation-plan.md)
- [references/signal-ingestion.md](references/signal-ingestion.md)
- [references/finding-classifier.md](references/finding-classifier.md)
- [references/fix-engine.md](references/fix-engine.md)
- [references/code-review-agents.md](references/code-review-agents.md)
- [references/review-replies.md](references/review-replies.md) + [scripts/reply_threads.py](scripts/reply_threads.py)
- [references/convergence-loop.md](references/convergence-loop.md)
- [references/generated-heal.md](references/generated-heal.md)
- [references/validation-gates.md](references/validation-gates.md)
- [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md) + [scripts/sonar_fetch.py](scripts/sonar_fetch.py)
- [references/codeql-remediation.md](references/codeql-remediation.md) + [scripts/codeql_fetch.py](scripts/codeql_fetch.py)
- [references/debt-remediation.md](references/debt-remediation.md) + [scripts/debt_audit.py](scripts/debt_audit.py)
- [references/issue-handoff.md](references/issue-handoff.md) — above-paygrade → `gh issue create` + `l9-issue-remediation`
- `environment/contracts/autonomy/MANIFEST.yaml` — surface doctrine + merge gate
- `environment/agents/cursor-subagents/DELEGATION_CONTRACT.yaml` — roles, result schema, handoff
- [scripts/self_test.py](scripts/self_test.py)

## Defaults

```yaml
max_cycles: 3
one_and_done: true
max_local_verify_iterations: 5
fleet_owner: ops/autonomy/pr_fleet.py
fleet_receipt: .l9/pr/fleet.json
replan_on: fingerprint_change          # a head moved, a PR opened or merged
wave_launch: all_ready_non_conflicting  # one message; caps from execution_profile.py
concurrency_caps_owner: ops/autonomy/execution_profile.py
result_acceptance: pr_fleet.py accept   # never narrative
ci_pipeline_policy: note_and_skip       # edit axis only; never a board verdict
board_authority: ops/autonomy/pr_board.py
board_values: [merge, fix, wait, leftover]
board_from_rollup_alone: false
leftover_requires_declaration: true
done_predicate: open_prs=0
verify: make precommit-repo
publish: git push                       # already-open PR branch
improve: make improve                   # optional kernels; not publish
merge_on_converge: true
own_until_merged: true
subscribe_open_prs: true
watcher_role: recon                     # read-only background lane per waiting PR
forbid_reinvoke_handoff: true
sonarcloud:
  when: sonar-project.properties exists
  token: SONAR_TOKEN from the environment (never printed, never pasted)
  merge_blocking: false
  resolve: all confirmed issues on the head, same commit
local_verify:
  prefer_makefile: true
  makefile_primary: precommit-repo
  cited_paths_required: true
  require_precommit_all_files: false
  require_precommit_all_hooks: false
  forbid_no_verify: true
  forbid_workflow_run_replay: true
merge:
  first_merge_gate: true
  oldest_created_at_default: true
  stack_safe: true
  squash_when_unstacked: true
issue_handoff: true
issue_handoff_skill: l9-issue-remediation
forbid_ask_human_to_unblock: true
```

## Failure Handling

### Diagnose
- PR number missing → STOP; ask or list open PRs
- Skip review comments → BLOCK verdict; fetch comments first
- CI logs unavailable → note `Unknown` for CI; still report reviews/blockers
- User asks to merge during Diagnose → refuse; point at `/l9-pr-remediation` (Converge)

### Converge
- `pr_fleet.py plan` fails (`FAIL:`) → no wave; fix the telemetry (REST route, repo slug) — never plan by hand
- Native-ext / cryptography import fail → `ENVIRONMENT`; run venv preflight once; do not edit source; do not unpin lock pins; do not use `uv python find --system`
- Remediator `git push` denied → fix the denial (CANONICAL_LAW §6.2.4); never switch to `make pr`
- `git add -u` / `reset --hard` denied → stage explicit paths only
- Result document rejected (`pr_fleet.py accept`) → the lane did not complete; re-assign with the reason or take the PR into the main lane
- Head SHA moved under a lane → its document is `blocked`; re-plan the fleet (fingerprint) and re-assign
- `SONAR_TOKEN` absent → fetch runs unauthenticated and says so; record `authenticated: false`, resolve what is visible, note the gap in status — do not paste a token
- CI logs missing → retry annotations/job logs once; if ownership unknown, note and continue other clusters
- Rate limit → honor reset, retry once, continue
- Fix breaks a gate → revert that fix, defer with reason, keep the rest of the batch (still one commit)
- Local `Passed` / remote `Failed` → classify from logs; environment delta or new post-push comments → next cycle; unrun local gate → protocol failure
- Poll worker / watcher `merge_eligible` on a stale SHA → ignore; never merge from it
- Squash denied because head is a stack parent → merge children first, retarget, or `--merge`; do not `update-branch`
- Unpredicted `CONFLICTING` after a merge → re-plan; do not continue the train blindly
- Max cycles → report remaining items; do not start cycle 4
- HUMAN / unfixable required CI / ENVIRONMENT still broken after best-effort → `gh issue create`, launch `l9-issue-remediation`, continue independent PRs

## Final Status (required)

### Diagnose
Verdict · blockers · warnings · key review concerns · overlap advisory · YNP (Diagnose YNP must not emit a merge command)

### Converge
`RUN_CONTRACT` summary (fleet fingerprint, wave sizes, caps owner) · plan finding counts · commits this PR (must be 1 on success) · `make precommit-repo` result · head SHA · fixed clusters (Sonar included) · accepted / rejected result documents · PRs merged · `open_prs` remaining with each one's `pr_board.py` verdict (quote the receipt) · remaining CODEBASE / CI_PIPELINE / HUMAN / ENVIRONMENT edit-axis notes · counters:

- `time_to_first_useful_action`
- `blocked_command_attempts`
- `environment_repair_count`
- `ci_run_count`
- `merge_conflict_count`
- `repeated_command_count`

## Validation

```bash
# pack self_test is stdlib-only (structural + wiring). Prefer the locked interpreter.
"${GOV_PY:-$PWD/.venv/bin/python}" skills/l9-pr-remediation/scripts/self_test.py
"${GOV_PY:-$PWD/.venv/bin/python}" -m pytest -q tests/ops/autonomy/test_pr_fleet.py
```
