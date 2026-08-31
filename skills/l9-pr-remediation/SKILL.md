---
name: l9-pr-remediation
description: diagnose or converge github prs — remediator path is precommit-repo then git push, then a stack-safe oldest-first merge train. board verdict is ops/autonomy/pr_board.py, never a check conclusion alone. do not run make pr or make pr-check. use when a campaign left prs unmergeable, the user invokes /l9-pr-remediation, or they ask to fix, remediate, babysit, converge, or merge failing prs.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, pr, ci, code-review, github-code-quality, copilot, diagnose, sonarcloud, codeql, debt, remediation, concurrent, github, makefile]
  owner: igor_beylin
  status: active
  version: 4.5.0
  updated: 2026-08-30
---

# PR Remediation

## Purpose

One pack, two intents: **Diagnose** (read-only readiness) or **Converge** (failing → green → merged). No packaging theater.

Converge is **REMEDIATE_ALL then MERGE_TRAIN**. It is not remediate-and-merge each PR as it turns green. [references/run-contract.md](references/run-contract.md).

| Intent | Mutates | Triggers | Behavior |
|--------|---------|----------|----------|
| **Diagnose** | no | review / readiness / blockers / `/pr` / “ready to merge?” | Fetch PR+reviews+CI; overlap advisory; slim verdict; **never** commit/push/merge |
| **Converge** | yes | `/l9-pr-remediation` / fix / remediate / babysit / merge failing PRs | Min preflight → remediate the open set → stack-safe oldest-first merge train |

Invoking this skill (or `/l9-pr-remediation`) is merge authorization for **all open PRs** in the target repo. Campaigns and `make pr` only publish. They do not merge. Load [references/merge-advise.md](references/merge-advise.md).

### Intent precedence (hard)

1. If `/l9-pr-remediation` or mutate language is present (`fix`, `remediate`, `babysit`, `push`, `merge` failing PRs, autonomy packet) → **Converge**.
2. Else if review/readiness/blockers/`/pr` → **Diagnose** only.
3. Ambiguous mixed ask without mutate verbs → **Diagnose**; ask one question before Converge.

## Target

All **open** PRs in the target `{owner}/{repo}`. A single `{owner}/{repo}#{pr}` argument still starts there, then continues through the remaining open PRs. Inventory the full set before the first merge. If no PR exists and Converge points at baseline debt/alerts: open a PR, then continue.

## Makefile capability graph (this host)

Remediation is **not** the `make pr` ceremony. do not run `make pr`. Do not run `make pr-check`. Those verbs stay the campaign / feature publish path. This skill must not invoke `make pr`. `make pr` is not the remediator publish path.

**Remediator PUBLIC** (only these as shipping verbs):

| Verb | Meaning | This skill |
|------|---------|------------|
| `make precommit-repo` | Changed-file hooks plus locked `ruff check` / `ruff format --check`. No pytest. No conformance. | **Local verify.** Blocks commit. |
| `git push` | Update the already-open PR branch. | **Publish.** Existing PR only. Pathspecs on the commit. |
| `make improve` | Kernel revision (`l4-begin` / record-kernels / authorize). | Optional, when kernels apply. Not a publish path. |

**Ceremony — do not invoke from this skill:** `make pr`, `make pr-check`, `PR_REMEDIATE=0 make pr`, `make pr-full`, pytest, peer-execution conformance, L4 `begin` / `record-kernels` / `authorize-release` as a publish ritual.

**INTERNAL** — do not invoke as shipping commands: `pr-preflight`, `precommit`, `pr-full`, `pre-commit install`.

Failure loop: diagnose → fix → (`make improve` if kernels apply) → `make precommit-repo` → commit → `git push` **once**. If hooks rewrite files, commit the rewrite and re-run `make precommit-repo` once. Pytest and conformance stay on CI.

If no PR number exists (baseline debt case): same verify, `git push` the branch, then `gh pr create` only to obtain a number. That create is the exception, not `make pr`. Not the remediator publish path for an already-open PR.

## Diagnose

Load [references/diagnose-workflow.md](references/diagnose-workflow.md). Optional focused lenses: [references/review-angles.md](references/review-angles.md). List unanswered **code-review agent** comments (`github-code-quality[bot]`, Copilot) as review blockers — [references/code-review-agents.md](references/code-review-agents.md). Report file-overlap across open PRs as advisory. Do not merge.

**Forbidden in Diagnose:** commit, push, force-push, edit worktree for fixes, alignment %, gap matrix, deep-eval, index theater, babysit loops, `gh pr merge`.

## Converge — Inputs → Actions

| Signal | Source | Action |
|--------|--------|--------|
| CI failures | `gh run view --log-failed`, annotations | Fix codebase root cause |
| Review + inline | `gh api` reviews/comments | Validate against current code; fix or reply |
| Code-review agents | `github-code-quality[bot]`, Copilot review logins | Inspect **every** comment; fix if validated; reply to all — [references/code-review-agents.md](references/code-review-agents.md) |
| Workflows | `.github/workflows/*.yml` | Read-only gate discovery |
| SonarCloud | `scripts/sonar_fetch.py` | Lazy: only if configured **and** check failing / blocking. Output under `$PWD`. |
| CodeQL | `scripts/codeql_fetch.py` | Lazy: only if check failing or alerts open |
| Lint/type/test/build debt | `scripts/debt_audit.py` + repo toolchain | Lazy: only if toolchain/baseline red |

## Converge — Outputs (per PR that changes code)

- One `RUN_CONTRACT` for the run (first status; reuse until invalidated)
- One structured remediation plan (inline ledger) per PR being edited
- One commit, one sanctioned publish (success path)
- Canonical replies on every thread; all threads resolved
- Short convergence status with timing counters

No tarballs, run-report schemas, issue-file bundles, or exemplary packaging.

## Authority Order

1. Latest user instruction and explicit PR/scope
2. Current repository source and tests
3. Required-check logs and branch-protection evidence
4. Human review, then **code-review agents** (`github-code-quality[bot]`, Copilot), then other blocking bots, then newer/higher-confidence comments
5. Scanner API evidence confirmed against current source
6. Host Makefile public verbs, then this skill + references
7. Unknown — do not invent; note and continue independent work

## Kernel bind (compressed)

Applies `kernels/Diagnose First Kernel.md`, `kernels/Validate & Repair.md`, and `kernels/Recursive Alignment.md` to this pack. Do not load those files mid-run unless a conflict appears.

| Kernel | Binding |
|--------|---------|
| Diagnose First | Inspect the current PR (head SHA, checks, threads, cited files) before any edit. Verify root cause from trusted evidence. Label missing values `Unknown`. Brace tokens (`{owner}/{repo}`) are templates, not executable. Do not combine opaque diagnose+mutate. |
| Validate & Repair | Smallest source-aligned fix. No stubs, suppressions, or fabricated checks. Report only validation that ran: `Passed` / `Failed` / `Skipped` / `Unknown` / `NotApplicable`. Local `make precommit-repo` is not remote CI. |
| Recursive Alignment | One command surface (Makefile PUBLIC verbs). One venv authority (`UV_PYTHON` native). One merge authority (`merge_gate` + oldest-first stack-safe). Generated registries are companions, not a second protocol. |

## Laws (Converge)

1. **Diagnose First, then min preflight.** Required once (read-only except the Converge receipt): command surface, venv fingerprint, PR inventory + overlap, known blockers, verify path. Emit `RUN_CONTRACT` and reuse it. Do not re-census the fleet. Per-PR: ingest + diagnose (observed / expected / root cause / Unknown) **before** any edit of that PR. Lazy Sonar/CodeQL/debt unless that check is failing or configured-and-blocking. Resume discovery on unexpected failure, scope change, env drift, or topology change. [references/run-contract.md](references/run-contract.md).
2. **One-and-done per PR, then a safety valve.** Success path is **one** plan, **one** commit, **one** CI run per PR. Max three cycles; never start cycle 4. Extra cycles are only for signals that did not exist at plan time.
3. **Codebase only.** Repair source, tests, fixtures, package deps. Never edit `.github/workflows/**`, actions, runners, permissions, secrets, OIDC, branch protection, check wiring, or CI-only infra. Never add `continue-on-error` or skip conditions to “heal” CI. Pipeline blockers: record one line in the status and keep remediating everything else.
4. **Ownership before edit — and ownership is not the board.** Load [references/ownership-boundary.md](references/ownership-boundary.md). Ownership answers **one** question: may I patch this file? Edit only `CODEBASE`. `ENVIRONMENT` (interpreter/arch/ABI/venv) is not a code defect — run the venv preflight once and continue. Ownership never decides what happens to the PR; `edit=CI_PIPELINE` is not `board=leftover`. A pipeline you may not patch can still be a PR GitHub will merge.
5. **Plan the PR, then patch that PR.** No edits on a PR until its ingested findings have dispositions. Independent clusters run in parallel into one worktree batch. A locked `Remediation-Cycle` / plan whose files still match is executed, not rewritten.
6. **One commit, one remediator publish.** Zero if nothing codebase-safe remains. Never commit-per-finding, never publish to probe CI, never `--no-verify`. Remediator publish **is** `git push` of the already-open PR branch. Do not run `make pr`. Campaign / feature work that is not this skill still must not use raw `git push` when its cached publish target is `make pr`.
7. **Local verify blocks commit.** Local verify **is** `L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo` (changed-file hooks plus ruff). That env makes `make pr-check` fail closed so this skill cannot enter the reader wave. Do not run `make pr-check`. Do not run pytest or conformance. Do not require all-files pre-commit. Never `--no-verify`. Record the result as `Passed` / `Failed` / `Unknown`. Remote CI is independent confirmation — do not claim remote `Passed` from local `Passed`.
8. **Own until merged.** Subscribe to every in-scope open PR at preflight. The human is **not** watching. After publish: record the head SHA and continue independent PRs, then **stay on the train**. Poll `gh pr view` / `gh pr checks` every 15s (cap `max_wait_snapshots`) until `mergeStateStatus=CLEAN` or a CODEBASE-red required check appears (then the next cycle). Never finish with “re-invoke `/l9-pr-remediation` when CI turns green.” A 404/422 on the GitHub subscription API does not waive ownership. Poll workers never merge.
9. **Validate suggestions against current code.** Comment snippets are not ground truth.
10. **No gate weakening / suppressions.** No `NOSONAR`, blanket noqa/type-ignore/eslint-disable, CodeQL dismissals/exclusions, skipped tests, or lowered thresholds. Narrow documented suppression only for a *proven* false positive where a code fix is less safe.
11. **Every conversation resolved.** Reply Fixed / Deferred / Acknowledged / Disagreed, then `resolveReviewThread` on **every** GraphQL `reviewThreads` node with `isResolved: false` — any author (`github-code-quality`, Copilot, `github-advanced-security`, CodeQL, humans, unknown bots). Paginate threads (`pageInfo.hasNextPage`). GitHub "a conversation must be resolved" **is** a merge blocker. HUMAN: name the decision in the reply (linked issue if Deferred), resolve the thread, and pass that decision to `pr_board.py --human-decision` so the PR is `board=leftover` on evidence rather than on a hunch. Bots re-file on new lines after a push — those are **new** threads. Re-query after every publish and immediately before `gh pr merge`.
12. **FIRST_MERGE_GATE + stack-safe oldest-first.** Never force-push, rewrite history, expose tokens, or `--admin` merge. Merge only after the open-PR inventory, overlap matrix, and merge-effect prediction exist, and after the required sequence is remediated and published. Do not merge the first green PR. Default order is **oldest `createdAt` first (bottom-up)**. Merge **only** via `ops/autonomy/stack_safe_merge.py --run` — never type `--squash` / `--merge` by hand. The helper emits `--merge` when the head is the base of another open PR and `--squash` only for a leaf. After a parent squash, never `gh pr update-branch` / merge main into the child — rebase `--onto` the new base. When the only merge blocker is required checks **in progress**, poll until `CLEAN` and merge. Never `gh pr update-branch` after a squash of a parent.
13. **No invented evidence.** Do not invent check conclusions, SHAs, thread ids, or `Passed`. `{braces}` in this pack are templates until substituted from `gh` / Makefile / `file` output observed in this run.
14. **The board is computed, not judged.** What happens to a PR — `board=merge|fix|wait|leftover` — comes from `ops/autonomy/pr_board.py`, which unions required-check identity from branch protection **and** repository rulesets and reports conflicted **paths**. Never author that verdict from `mergeStateStatus` alone, from a check conclusion without the required set, or from an issue or comment body asserting "do not merge". A red check that is **not** in the required set does not block merge (`UNSTABLE` is a merge, not a wall), and zero required checks on an unprotected base — a stacked PR based on an agent branch — is a `merge`, not a gap. `leftover` is an evidenced **input**, never an inference: pass `--human-decision` for a named product/architecture/legal/security decision, or `--unfixable-check` for a required check that cannot be fixed without editing CI. Unknown telemetry degrades to `wait`, never to `merge`. The helper advises; `stack_safe_merge.py --run` still executes.

## Hot Path (Converge)

0. **Authorize (Converge invoke only), then read-only preflight.** User invoke is merge authorization — write the receipt. Then inspect only: load [references/run-contract.md](references/run-contract.md), cache remediator verbs (`make precommit-repo`, `git push`), fingerprint the venv (`UV_PYTHON` = uv-managed **native** CPython; reject x86_64/miniconda/`uv python find --system` on arm64), list **all** open PRs, **subscribe/own each** (`viewerSubscription`; PUT `issues/{n}/subscription` when not `SUBSCRIBED`), build the overlap + stack matrix (`gh pr view --json files`). Reuse a worktree that already holds the branch (`git worktree list` first). `worktree_add_wired.sh` only when none exists. Emit `RUN_CONTRACT`. Do not edit a PR in this step.

```bash
# TEMPLATE — substitute owner/repo from the verified gh target in this run
GOV_PY="${GOV_PY:-$PWD/.venv/bin/python}"
"$GOV_PY" ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
gh pr list --repo {owner}/{repo} --state open \
  --json number,createdAt,mergeable,headRefName,baseRefName,statusCheckRollup
# Board verdict per open PR. statusCheckRollup above is inventory, not a verdict:
# it lists optional checks too, which is how an optional red check became a
# "blocker" that merged fine on the next attempt.
"$GOV_PY" ops/autonomy/pr_board.py --repo {owner}/{repo} --pr {n} --json
```

Reuse a locked plan / `Remediation-Cycle:` trailer when files still match. If no PR and the user wants baseline debt/alerts fixed: create branch, remediate, `git push`, then `gh pr create` only to obtain a number.

1. **Discover gates (read-only).** Cache remediator verify=`make precommit-repo` and remediator publish=`git push`. Do not cache `make pr-check` or `PR_REMEDIATE=0 make pr` as this skill's verbs. Do not edit CI surfaces.
2. **Diagnose the PR about to be edited.** Failed CI + annotations, human reviews, every bot comment, every CRA thread. Read cited files at the current head. Record observed / expected / root cause / Unknown. Sonar/CodeQL/debt only when failing or configured-and-blocking. No edits yet. Snapshot `gh pr view` once. [references/signal-ingestion.md](references/signal-ingestion.md) + [references/code-review-agents.md](references/code-review-agents.md).
3. **Classify + write that PR's plan.** Ownership then severity; `disposition: fix` requires a verified root cause. Companions if touching `pec/*`, `skills/*`, or `rules/*`. [references/finding-classifier.md](references/finding-classifier.md) + [references/remediation-plan.md](references/remediation-plan.md).
4. **Fix the planned batch.** All `disposition: fix` clusters. Skip HUMAN / CI_PIPELINE / ENVIRONMENT (note them). [references/fix-engine.md](references/fix-engine.md). Independent PRs may be remediated in parallel after the overlap matrix exists. Do not commit yet. Do not merge yet.
5. **Local verify (blocks commit).** `L9_REMEDIATOR=1 PR_BASE=origin/main make precommit-repo`. If hooks rewrite files, commit the rewrite and re-run once. ≤5 iterations. Never `--no-verify`. Never `make pr-check`. Never `make precommit` / `--all-files`.
6. **One commit, one remediator publish.** Explicit `git add` of planned files only. Never `git add -u` / `-A`. Never `git reset --hard`. `git push` the already-open PR branch. Trailer `Remediation-Cycle: {repo}#{pr}/cycle-1`. Poll workers never merge. Ignore `merge_eligible` whose SHA is older than HEAD or older than the last repo merge.
7. **Reply + resolve.** Every thread, any author. Inspect cited files first.
   Then `python3 -u skills/l9-pr-remediation/scripts/reply_threads.py --repo {owner}/{repo} --input {threads.json}`
   (GraphQL batch, 30s `gh` timeout, flushed progress, batch summary).
   Do not loop REST reply + `resolveReviewThread` per thread.
   [references/review-replies.md](references/review-replies.md).
8. **Next PR immediately, then own the wait.** [references/convergence-loop.md](references/convergence-loop.md). Re-query `reviewThreads` (paginated). Reply + resolve re-files. **Do not merge** because this one PR is green. Repeat 2–8 for remaining in-scope PRs. After REMEDIATE_ALL, stay subscribed and poll required checks on the train — do not stop.
9. **MERGE_TRAIN** only after FIRST_MERGE_GATE. Oldest `createdAt` first. Immediately before each `gh pr merge`, re-run `pr_board.py` (the board is per head SHA, so an earlier verdict is stale), re-query `reviewThreads`, and re-run the stack probe (is this head the base of another open PR?). Zero `isResolved: false` required. `board=merge` → merge it. `board=fix` → back to step 2 for that PR. `board=wait` → keep polling; it is not a finish. `board=leftover` → that PR only, and only with the declaration that produced it.

```bash
# NEVER type --squash yourself. The helper probes children and emits
# --merge for a stack parent, --squash only for an unstacked leaf.
"$GOV_PY" ops/autonomy/stack_safe_merge.py --repo {owner}/{repo} --pr {n} --run
```

Never `--admin`. Never unpack diffs. Never merge-as-you-go. Never `gh pr update-branch` after a squash of a parent. An unpredicted `CONFLICTING` after a merge means the overlap preflight failed — rebuild the remaining matrix before the next merge.

## Done When (Converge)

Mission is `open_prs=0` — an empty `gh pr list --state open` on the target repo, the same shape as the issue remediator's `open_issues=0`. Anything short of that names the PRs still open and the declaration that keeps each one open.

On the final observed head SHA of each open PR, then after the train (or a documented independence merge):

- remediations published via `git push`, and every open PR carries a fresh `pr_board.py` verdict at that head. Only `board=leftover` PRs stay unmerged, and only with the `--human-decision` / `--unfixable-check` declaration that produced them. `board=wait` (required checks still in progress) is this skill's job: poll until `CLEAN`, then merge. Do not leave a green-or-pending board with a reinvoke YNP.
- no unpredicted merge conflict
- no unresolved GraphQL `reviewThreads` (any author; pagination complete)
- Sonar/CodeQL/debt: confirmed codebase root causes fixed when those surfaces were in scope; remote scanner closure claimed only when observed
- green mergeable PRs in the train are **merged** (oldest first, stack-safe)
- worktree clean
- status names remaining blockers and the six timing counters

## Generated-artifact heal (same publish path)

This is not a second publish path. Same `make precommit-repo` plus `git push`.

- After any merge that touched generated paths — or whenever
  `.l9/pr/regen-required.txt` is non-empty (written by the `merge=l9-generated`
  driver) — run `"$PWD/.venv/bin/python" ops/scripts/sync_generated_artifacts.py --force`.
  When `environment/program-execution/MANIFEST.json` is in the set, also run
  `environment/program-execution/scripts/generate_manifest.py` then
  `validate_manifest.py` (PASS required). Then `make precommit-repo`, commit,
  `git push`. A merge is not complete while the marker lists paths.
- File-by-file architecture audit is forbidden unless
  `git diff --name-only --diff-filter=U` lists a path that is not in
  `GENERATED_PATH_PREFIXES` ([generated-heal.md](references/generated-heal.md)).
- Same-agent overlapping work routes into the existing open PR branch.
- See `rules/53-pr-overlap-guardrail.mdc`.

## Resource Map

### Diagnose
- [references/diagnose-workflow.md](references/diagnose-workflow.md)
- [references/code-review-agents.md](references/code-review-agents.md)
- [references/review-angles.md](references/review-angles.md)
- [references/merge-advise.md](references/merge-advise.md)
- [references/run-contract.md](references/run-contract.md)

### Converge
- [references/run-contract.md](references/run-contract.md) — preflight, Makefile surface, venv, topology
- `ops/autonomy/pr_board.py` — board authority (`merge|fix|wait|leftover` + receipt)
- [references/ownership-boundary.md](references/ownership-boundary.md) — edit axis only
- [references/remediation-plan.md](references/remediation-plan.md)
- [references/signal-ingestion.md](references/signal-ingestion.md)
- [references/finding-classifier.md](references/finding-classifier.md)
- [references/fix-engine.md](references/fix-engine.md)
- [references/code-review-agents.md](references/code-review-agents.md)
- [references/review-replies.md](references/review-replies.md)
- [scripts/reply_threads.py](scripts/reply_threads.py)
- [references/convergence-loop.md](references/convergence-loop.md)
- [references/generated-heal.md](references/generated-heal.md)
- [references/validation-gates.md](references/validation-gates.md)
- [references/sonarcloud-remediation.md](references/sonarcloud-remediation.md)
- [references/debt-remediation.md](references/debt-remediation.md)
- [references/codeql-remediation.md](references/codeql-remediation.md)
- [scripts/sonar_fetch.py](scripts/sonar_fetch.py)
- [scripts/debt_audit.py](scripts/debt_audit.py)
- [scripts/codeql_fetch.py](scripts/codeql_fetch.py)
- [scripts/self_test.py](scripts/self_test.py)

## Defaults

```yaml
max_cycles: 3
one_and_done: true
max_local_verify_iterations: 5
parallel_clusters: true
parallel_independent_prs: true   # after overlap matrix; never parallelize merge
ci_pipeline_policy: note_and_skip   # edit axis only; never a board verdict
board_authority: ops/autonomy/pr_board.py
board_values: [merge, fix, wait, leftover]
board_from_rollup_alone: false
leftover_requires_declaration: true
done_predicate: open_prs=0
verify: make precommit-repo
publish: git push                # already-open PR branch
improve: make improve            # optional kernels; not publish
merge_on_converge: true
own_until_merged: true
subscribe_open_prs: true
poll_interval_seconds: 15
max_wait_snapshots: 32
forbid_reinvoke_handoff: true
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
```

## Failure Handling

### Diagnose
- PR number missing → STOP; ask or list open PRs
- Skip review comments → BLOCK verdict; fetch comments first
- CI logs unavailable → note `Unknown` for CI; still report reviews/blockers
- User asks to merge during Diagnose → refuse; point at `/l9-pr-remediation` (Converge)

### Converge
- Native-ext / cryptography import fail → `ENVIRONMENT`; run venv preflight once; do not edit source; do not unpin lock pins; do not symlink a failing SSOT venv; do not use `uv python find --system`
- Remediator `git push` of an already-open PR branch is the sanctioned publish (CANONICAL_LAW §6.2.4). Do not switch to `make pr` when a push is denied — fix the denial. Campaign / feature work that is not this skill still must not treat raw `git push` as its publish path when `make pr` exists.
- `git add -u` / `reset --hard` denied → stage explicit paths only
- CI logs missing → retry annotations/job logs once; if ownership unknown, note and continue other clusters
- Rate limit → honor reset, retry once, continue
- Fix breaks a gate → revert that fix, defer with reason, keep the rest of the batch (still one commit)
- Partial publish to probe CI → protocol violation
- Local `Passed` / remote `Failed` → classify ownership from logs; environment delta or new post-push comments → next cycle; unrun local gate → protocol failure; never edit workflows to skip the job; do not rewrite local `Passed` as remote `Passed`
- Scanner identity/pagination/path-blocked → stop that scanner cluster; continue others (do not block Converge when that check is green)
- Poll worker `merge_eligible` on a stale SHA → ignore; never merge from it
- Squash denied because head is a stack parent → merge children first, retarget, or `--merge`; do not `update-branch`
- Unpredicted `CONFLICTING` after a merge → rebuild remaining overlap; do not continue the train blindly
- Required checks still pending after FIRST_MERGE_GATE → poll; do not hand off
- Max cycles → report remaining items; do not start cycle 4

## Final Status (required)

### Diagnose
Verdict · blockers · warnings · key review concerns · overlap advisory · YNP (Diagnose YNP must not emit a merge command)

### Converge
`RUN_CONTRACT` summary · plan finding counts · commits this PR (must be 1 on success) · `make precommit-repo` result · head SHA · fixed clusters · PRs merged · `open_prs` remaining with each one's `pr_board.py` verdict and reason (quote the receipt, not prose) · remaining CODEBASE / CI_PIPELINE / HUMAN / ENVIRONMENT edit-axis notes · scanner pending-remote if any · counters:

- `time_to_first_useful_action`
- `blocked_command_attempts`
- `environment_repair_count`
- `ci_run_count`
- `merge_conflict_count`
- `repeated_command_count`

## Validation

```bash
# pack self_test is stdlib-only (structural). Prefer the locked interpreter when present.
"${GOV_PY:-$PWD/.venv/bin/python}" skills/l9-pr-remediation/scripts/self_test.py
```
