---
description: After make pr opens a PR, campaign path ends green + merge-ready; /l9-pr-remediation authorizes merge and publishes via precommit-repo plus git push
---

# make pr → green merge-ready; /l9-pr-remediation → merge

Default publish path is `make pr` (Autonomy Surface Profile
`campaign_execution` / `l4_local_autonomy.post_push`). Remediates defaults
to 1 after the PR opens. `PR_REMEDIATE=0` is opt-out only.

Agents MUST:

1. Use `make pr` (any capitalization) so Makefile checkers run before push.
   The `pr` target is the **governance** Makefile's, always — reach it with
   `l9 pr` / `make -C "$GOV" pr WS="$PWD"` regardless of the workspace repo's
   own Makefile. A consumer repo needs **no** `pr`/`pr-check` target; do not
   add one, and do not fall back to a raw `git push` where one is absent.
2. Do **not** force `PR_REMEDIATE=0`. Unset remediates is 1 (poll to green
   + merge-ready). Pass `PR_REMEDIATE=0` only to skip the poll worker.
3. For Program Execution campaigns, set `PR_BASE` to
   `origin/campaign/<campaign_id>` — never open those PRs against `main`.
4. Campaign / `make pr` end state: every published PR is **green and
   merge-ready**. Do **not** merge from that path.
5. When the user invokes **`/l9-pr-remediation`** (or attaches the skill
   with Converge intent): merge **is** authorized for **all open PRs** in
   the target repo. Remediator publish is **not** `make pr`. Local verify
   is `make precommit-repo` (hooks plus ruff). Publish is `git push` of the
   already-open PR branch. Do not run `make pr-check`, pytest, or
   conformance. Write the receipt, converge each PR, then merge
   bottom-up:

```bash
python3 ops/autonomy/authorize_merge.py --repo <owner/name> --all-open \
  --reason "l9-pr-remediation invoked"
gh pr merge <n> --repo <owner/name> --squash --delete-branch
```

`ops/autonomy/merge_gate.py` allows ordinary `gh pr merge` after that
receipt (or `L9_MERGE_AUTHORIZED`). Force-push, hard-reset, and
`--admin` stay denied.

**Both merge transports are governed.** `gh pr merge` is a GraphQL call; where
GraphQL is unavailable (a session gateway serving only a pinned set of
PR-review operations 403s it) the merge that runs is the REST endpoint:

```bash
gh api -X PUT repos/<owner>/<name>/pulls/<n>/merge -f merge_method=merge
```

The gate recognises that form — and the `curl` spelling of it — as a merge,
resolving owner/name/number from the endpoint path so the receipt check and the
stack-safety probe both apply. Name `merge_method` explicitly: an unspecified
method is treated as ancestry-breaking and is denied for a stack parent, which
is why `stack_safe_merge.py` selects it in code rather than leaving it to a
server-side default. A transport that the gate cannot see is not a licence to
use it — reach for `stack_safe_merge.py` first.

Stacked PRs (operator default 2026-08-15):

- When a PR is already open for the workstream, the next PR **stacks on the
  open PR's head** (`ops/scripts/stack_pr.py base`). Merge order is
  **bottom-up**; older PRs first.
- Rebase and conflict resolution are **forbidden**. Disjoint scopes keep the
  stack mergeable; if scopes overlap, stop and re-plan.
- One feature branch per program; exclusive worktree lease per mutating agent
  (`surface_profile.pr_stacking`, `CAMPAIGN_EXECUTION_POLICY.pr_stacking`).

`make pr` writes `.l9/pr/pr-remediation-handoff.json` plus
`L9_AGENT_REQUIRED` when remediates=1 (the default). Follow that handoff:
poll to green + merge-ready. Standing campaign contract is still no merge.
`/l9-pr-remediation` Converge / `authorize_merge.py` is the merge path.
`PR_REMEDIATE=0` skips the handoff marker.

**Push authorization:** when the user invokes `make pr` (any capitalization),
that counts as explicit approval for the push + PR open performed by
`ops/scripts/open_pr_after_gate.sh` (overrides the generic “ask before push”
default for this one command path only).

## Gate dirtiness semantics (do not misread pre-commit)

pre-commit exits non-zero for **two unrelated reasons** —
`files_modified or bool(retcode)`:

- `- exit code: <n>` — a hook genuinely failed. The gate FAILs and names it.
- `- files were modified by this hook` — the tracked worktree changed during
  that hook's **wall-clock window**. It does **not** identify the writer.

The gate therefore classifies rather than aborts. Generated/scratch churn is a
WARN to stage; non-generated dirt is attributed, quiesced, retried once, then
FAILed with exact paths.

**Never audit the named hook first.** Run the attribution and read the receipt:

```bash
bash ops/scripts/attribute_tree_writers.sh "$(pwd)" <status-before-file> <precommit-log>
cat .l9/pr/gate-dirtiness.json
```

A hook declared `read_only` in `ops/config/precommit-hook-contract.json` that
shows no delta on replay is exonerated — look for a concurrent writer in the
repo-write lock ledger instead. `L9_GATE_STRICT_LEGACY=1` restores the old
abort-on-any-non-zero behavior.


## Failure loop and gate receipt (2026-08-17)

Do **not** treat `make pr-check` then `make pr` as the happy path. That
sequence is a teaching failure: on an unchanged tree the receipt skip
prevents a second pytest, but agents must not type the extra command.
Happy path: finish → scoped-commit → `make pr`. `pr-check` /
`OPEN_PR=0 make pr` remain diagnose-only. `make precommit-repo` is an
internal leaf of the gate, not a post-commit ritual.
Diagnose is `OPEN_PR=0 make pr`; do not run `pr-check` after `precommit-repo`.

```bash
make pr
```

`pr-check` is the INTERNAL gate leaf. GitHub mutation stays `make pr` only.

<!-- generated-from: rules/48-make-pr-remediation.mdc; do-not-edit -->
