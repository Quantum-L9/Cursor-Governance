---
name: Issue remediator automation
overview: "Cut remediator (not Diagnose) friction: drain all issues highest-leverage first, land fixes on the matching open PR or a new stacked PR on the newest PR, close until open_issues=0, and only then chain `/l9-pr-remediation`. Diagnose stays an opt-in inventory and never starts that chain."
todos:
  - id: close-resolved
    content: Add close_resolved_issue.py; wire breadcrumb Done-when so status=fixed cannot leave the GitHub issue OPEN; Diagnose may close already-resolved only
    status: completed
  - id: cluster-queue
    content: Replace max_clusters=1 with leverage-ranked queue of all automatable clusters; update classifier + ingest/rank script
    status: completed
  - id: make-pr-default
    content: "Land each fix on the existing open PR it belongs on, else open a new stacked PR on the newest open PR (PR_STACK=auto). make_pr: true. Fixes #n in the PR body."
    status: completed
  - id: chain-pr-remediation
    content: Remediator slash ONLY invokes /l9-pr-remediation after bound-target open_issues=0. Diagnose never chains. HUMAN/EXTERNAL still open = do not chain.
    status: completed
  - id: slash-routing
    content: Rewrite /issues to Converge-by-default + /issues diagnose; add /l9-issue-remediation slash; flip AUTONOMY_MANIFEST; append AGENTS.md fragment
    status: completed
  - id: tests-checklist
    content: Add self_test for close gates + rank order + command contract; update validation-checklist
    status: completed
isProject: false
kernel_pass:
  bound_path: issue_remediator_automation_8f9fbbf0.plan.md
  improve:
    kernel: kernels/Improve.md
    ran_at: 2026-08-30T02:30:00Z
    body_sha256: "51094f35c943387a06b1fa77509d2c908bad73a02fa77d1fdd1bf84ec91791ac"
    deltas:
      - "Applied Improve.md on /ff shelf: leftover untracked corpus kept as archive; no promotion into live skills or ops."
  recursive_alignment:
    kernel: kernels/Recursive Alignment.md
    ran_at: 2026-08-30T02:30:20Z
    body_sha256: "51094f35c943387a06b1fa77509d2c908bad73a02fa77d1fdd1bf84ec91791ac"
    deltas:
      - "Applied Recursive Alignment.md: shelf is WIP/plans leftover after catch-up; does not compete with CANONICAL_LAW or AGENTS.md."
  validate_repair:
    kernel: kernels/Validate & Repair.md
    ran_at: 2026-08-30T02:30:40Z
    body_sha256: "51094f35c943387a06b1fa77509d2c908bad73a02fa77d1fdd1bf84ec91791ac"
    deltas:
      - "Applied Validate & Repair.md: secret globs excluded; copies stay in the named clone; no fabricated completeness."
---
# Issue remediator: resolve, PR, merge

## Why this is stuck today

[`commands/issues.md`](commands/issues.md) is Diagnose-only and **forbids close**. [`skills/l9-issue-remediation/SKILL.md`](skills/l9-issue-remediation/SKILL.md) Converge comments via [`scripts/post_issue_comment.py`](skills/l9-issue-remediation/scripts/post_issue_comment.py) but never calls `gh issue close`. Defaults are `max_clusters_per_invoke: 1` and `pr_policy: handoff` (a note, not a run). There is **no** `/l9-issue-remediation` slash — only `/issues`. [`commands/commands-index.md`](commands/commands-index.md) already claims “Diagnose / Converge”; the command file does not.

This is skill/command work on the **current checkout**. Do not run `make campaign`. Do not write `Lock: origin/main = <sha>`. Hook catalog for code in scope: [`.pre-commit-config.yaml`](.pre-commit-config.yaml). Pathspecs only (rule 49) — this tree is dirty with unrelated `ff` / `WIP/` work.

## Target contract (after Build)

```text
/issues  or  /l9-issue-remediation     (remediator / Converge)
        │
        ▼
ingest + rank clusters by leverage
        │
        ├─ already-resolved → comment + close
        ├─ CODEBASE / CROSS_REPO → fix → land on matching open PR
        │                              or new stacked PR on newest PR
        └─ HUMAN / EXTERNAL → comment; leave open (blocks chain)
        │
        ▼
re-ingest until bound-target open_issues == 0
        │
        │  Diagnose / auditor NEVER enters this box
        ▼
/l9-pr-remediation Converge (owning repos that have the stacked PRs)
        │
        ▼
merge (authorize_merge + stack_safe_merge)
```

**Opt-out Diagnose (auditor):** `/issues diagnose` (or “what’s blocking?”) — inventory only, **except** already-resolved close (hygiene, not a fix). Diagnose **never** invokes `/l9-pr-remediation`.

## Hard gate: remediator chains PR remediation only at open_issues=0

This is not “after the last CODEBASE cluster” and not “when only HUMAN remain.”

- Bound target = named `{owner}/{repo}` or the default fleet (`Quantum-L9/*` non-archived).
- After each close, re-count **open GitHub issues** on that bound target (`issue_ingest` / `gh issue list --state open`).
- **`/l9-pr-remediation` runs if and only if `open_issues == 0`.** Zero means zero. The remediator slash does not start that skill earlier to “get a head start” on PRs.
- If any issue is still OPEN (including HUMAN / EXTERNAL), status is `BLOCKED_OPEN_ISSUES` — keep remediating or breadcrumb the leftover. Do **not** chain.
- Diagnose / auditor slash never evaluates this gate for the purpose of starting remediator.

Implication: Converge must **close** resolved issues when the fix is already on a PR (or already-fixed on default), not after merge. Waiting for `Fixes #n` auto-close on merge would make `open_issues=0` unreachable before the remediator runs (deadlock). Close first, then chain.

## Decided defaults (replace current YAML)

- `max_clusters_per_invoke: all` — drain every CODEBASE / CROSS_REPO / already-resolved cluster in the bound fleet (or named repo). Highest leverage first.
- `make_pr: true` — every CODEBASE fix is published onto a PR (existing or new stacked). See PR landing rule below.
- `chain_pr_remediation: after_open_issues_zero` — invoke [`commands/l9-pr-remediation.md`](commands/l9-pr-remediation.md) Converge **only** after the hard gate. That command is merge authority (`authorize_merge.py --all-open`, then `stack_safe_merge.py`). Issue skill still **must not** `gh pr merge`.
- `close_resolved: true` — close is mandatory when evidence says the issue is done. Not optional, not “comment only.” Required to reach `open_issues=0`.

Per-cluster cycle cap stays **3**. HUMAN / EXTERNAL stay open unless superseded/duplicate/already-fixed **with proof** — leftover OPEN issues block the remediator chain. CI-pipeline / workflow edits stay skipped.

## PR landing rule (explicit)

Fixes do **not** always open a fresh PR against `main`. After local verify:

1. **Belong on an existing open PR** — same owning repo, and the open PR already owns that cluster / path / issue (body refs `Fixes #n` / same files / same branch). Commit and push onto **that** PR branch. Do not open a sibling PR for the same fix. This is remediator-publish (`git push` of the already-open branch), not a second `make pr`.
2. **Otherwise** — open a **new stacked PR on top of the newest open PR** in that repo (`PR_STACK=auto` / stack tip). Use `PR_REMEDIATE=0 make pr` so the new PR’s base is the newest open PR, not a fork from `origin/main` when a stack exists. PR body lists `Fixes #n` / `Fixes owner/repo#n` for every issue in the cluster.
3. No open PRs in that repo → `PR_STACK=` / `PR_BASE=origin/main` is allowed (first PR).
4. Sibling open-PR chains still fail closed (existing overlap gate). Do not invent a second stack.

`make_pr: true` means “the fix is on a GitHub PR,” not “always run `make pr` even when the matching PR already exists.”

## Leverage rank (cluster, not raw issue)

Today [`issue_ingest.py`](skills/l9-issue-remediation/scripts/issue_ingest.py) sorts by label severity then `updated_at`. Add cluster ranking (extend ingest or new `scripts/cluster_rank.py`):

1. Shared root cause that unblocks the most linked issues
2. Cross-repo blast (one owner fix, many consumers)
3. Severity (`critical` > `high` > …)
4. Oldest updated as tie-break

Drain that queue in order. Independent owning repos may run in parallel; dependent clusters stay serial.

## Close-on-resolved (the slash bug)

Add [`skills/l9-issue-remediation/scripts/close_resolved_issue.py`](skills/l9-issue-remediation/scripts/close_resolved_issue.py):

- Require `--issue owner/repo#n` plus evidence (`--merged-pr`, `--commit`, or `--reason superseded|duplicate|already-fixed` with a proof string)
- Post the existing unblock comment (status `fixed`) then `gh issue close --reason completed`
- Refuse HUMAN / EXTERNAL unless the reason is `superseded` / `duplicate` / `already-fixed` **with** proof (merged PR, tip SHA, or “not a live defect”)
- Dry-run for tests; never print tokens

Wire it into:

- Diagnose (auditor): after ingest, close issues whose linked PR is merged or whose defect is gone on default (the `.github#60` class). Still no remediator chain.
- Converge (remediator): close when the fix is **on a PR or already landed** — so `open_issues` can reach 0 **before** `/l9-pr-remediation`. Do not wait for remediator merge or GitHub auto-close.

Update [`references/unblock-breadcrumb.md`](skills/l9-issue-remediation/references/unblock-breadcrumb.md): PICKUP → comment → **close if resolved** → conditional `TODO.md`. Done-when fails if status is `fixed` and the issue is still OPEN.

Law 9 stays: never mass-close HUMAN. Close is evidence-gated, not “close everything open.” Leftover HUMAN/EXTERNAL OPEN issues keep `open_issues > 0` and therefore block the remediator chain.

## Slash + routing

- Rewrite [`commands/issues.md`](commands/issues.md) to Converge-by-default (mirror [`commands/l9-pr-remediation.md`](commands/l9-pr-remediation.md) shape). `/issues diagnose` keeps the current Diagnose workflow minus the “never close” line for already-resolved.
- Add [`commands/l9-issue-remediation.md`](commands/l9-issue-remediation.md) — missing sibling of `/l9-pr-remediation`. Same Converge contract. Do not hand-edit [`commands/COMMANDS_MANIFEST.yaml`](commands/COMMANDS_MANIFEST.yaml); regenerate.
- Flip [`skills/AUTONOMY_MANIFEST.yaml`](skills/AUTONOMY_MANIFEST.yaml) `issue_remediation` route: `/issues` and `/l9-issue-remediation` are Converge positives; “diagnose issues” / “what’s blocking” stay Diagnose. Regenerated `ops/generated/skill-registry.json` follows.

Intent precedence becomes:

1. `/issues`, `/l9-issue-remediation`, or mutate verbs → Converge (all clusters, land on PR, close, chain **only if** `open_issues=0`)
2. `diagnose` / readiness / “what’s blocking?” → Diagnose + already-resolved close only
3. Ambiguous bare “issues” after this land → Converge (friction cut)

## Skill / ref edits (same pack)

- [`SKILL.md`](skills/l9-issue-remediation/SKILL.md) — Defaults, Laws 1/9/10, Hot Path 4–7, Done When, Final Status; `chain_pr_remediation: after_open_issues_zero`; PR landing rule; `chain_pr_remediation: after_open_issues_zero`; PR landing rule
- [`references/convergence-loop.md`](skills/l9-issue-remediation/references/convergence-loop.md) — re-count open issues after each close; chain remediator **only** when `open_issues=0`
- [`references/handoff-to-pr-remediation.md`](skills/l9-issue-remediation/references/handoff-to-pr-remediation.md) — remediator-only; forbidden until `open_issues=0`; Diagnose never calls it
- [`references/diagnose-workflow.md`](skills/l9-issue-remediation/references/diagnose-workflow.md) — already-resolved close allowed; still no commit/push/fix
- [`references/finding-classifier.md`](skills/l9-issue-remediation/references/finding-classifier.md) — sticky selection becomes a ranked queue, not “pick one”
- [`references/validation-checklist.md`](skills/l9-issue-remediation/references/validation-checklist.md) — drop “sticky ≤ 1” and “Diagnose only”

## AGENTS.md (append-only)

Append a named fragment (`L9_ISSUE_REMEDIATE_AUTOMATION_V1`). Do not fold or delete existing paragraphs. State: remediator `/issues` / `/l9-issue-remediation` Converge-by-default; `/issues diagnose` is auditor (no remediator chain); close-on-resolved; land on matching open PR or stacked PR on newest; `/l9-pr-remediation` only after `open_issues=0`; issue skill never merges itself.

`AGENTS.md` is `additive_only`. Prefer append so `ALLOW-ROOT-DELETION` is unnecessary.

## Tests (no pack tests exist today)

Add `skills/l9-issue-remediation/scripts/self_test.py` (or pytest next to scripts):

- Close script: refuse HUMAN without proof; accept merged-PR / on-PR evidence on dry-run
- Cluster rank: shared-cause cluster outranks a lone low-severity issue
- Command contract: remediator `commands/issues.md` / `commands/l9-issue-remediation.md` require `open_issues=0` before any `/l9-pr-remediation` invoke; Diagnose file/path never chains
- PR landing: matching open PR wins; else stack on newest open PR (`PR_STACK=auto`)

Local verify: that self-test plus `ruff` on the new/changed Python. Do not run a second full `make pr` gate on an unchanged tree after publish.

## Out of scope

- Merging from the issue skill
- Editing `.github/workflows/**` or branch protection
- Executing the pending fleet closeout of ~48 live issues ([`docs/plans/pending/fleet_issue_closeout_fc1fa34f.plan.md`](docs/plans/pending/fleet_issue_closeout_fc1fa34f.plan.md)) — this plan only changes the automation so a later `/issues` can do that
- Fake-closing HUMAN / EXTERNAL product or secrets work
- Changing `/pr` (stays Diagnose)

## Stress / rollback

If Converge-by-default `/issues` is too wide, the rollback is: restore Diagnose-only `/issues` and keep `/l9-issue-remediation` as the mutate slash. Close-on-resolved, PR landing, and the `open_issues=0` gate stay on the remediator slash.

If close is too aggressive: require on-PR or merged-PR evidence only (drop “source looks fixed” Diagnose close) and keep superseded/duplicate closes.

If leftover HUMAN issues permanently block the remediator chain, that is the intended gate — do not weaken to “automatable subset = 0.” Resolve or evidence-close those issues first.

## Execute via Cursor Build

Press **Build**. Work in the **current checkout**.

- Do not run `make campaign`.
- Do not admit a Program Lock or Controller lease.
- Do not write `Lock: origin/main = <sha>`.
- Do not open a new worktree from tip as a planning requirement.
