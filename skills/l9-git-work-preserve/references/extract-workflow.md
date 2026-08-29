# Extract workflow

Local-only mutation. Never deletes the source ref.

Leftover **committed** paths on a diagnosed ref (`keep_push` / preserve tip)
extract by **path-union versus the fetched baseline**, through an allowlist.
This file is not the porcelain harvest classifier
([harvest-workflow.md](harvest-workflow.md)).

1. Require a diagnosis receipt with unique commits or paths.
2. Create a dedicated worktree from fetched `origin/main` (prefer
   `ops/scripts/agent_worktree_start.sh`). Do not mutate the dirty shared clone.
3. Emit or consume an allowlist `{copy, skip}` with `{path, reason}` rows.
   Extract copies **only** the copy set. An empty copy set is a valid stop.
4. Run `scripts/extract_path_union.py --repo <src> --ref <tip> --baseline origin/main`
   (`--allowlist` when present). Copy a path iff it is in the copy set **and**
   `git cat-file -e <baseline>:<path>` fails. Path-absent, not blob-absent-only.
5. Never `git cherry-pick` a mixed leftover ref. A range that deletes or
   overwrites a path already on baseline is mixed; cherry-picking it regresses
   the baseline. Path-union of allowlisted new paths is the extract.
6. Record extract receipt: source tip SHA, new branch, worktree path, copied
   paths, skipped paths with reasons.
7. Leave the source ref intact.

Cherry-pick remains valid only when the diagnosis receipt proves **every** path
in `git diff --name-status <baseline>...<ref>` is an add (`A`) whose path is
absent on baseline. Even then, path-union of those blobs is the default and is
sufficient. Mixed ranges never cherry-pick.

Dirty/untracked leftover across sibling worktrees: use
[harvest-workflow.md](harvest-workflow.md) first, then this extract for
committed leftover trees.

Forbidden:

- reset/checkout on a dirty shared primary clone to perform extract
- whole-branch cherry-pick of a mixed leftover ref
- copying a path that exists on baseline
- treating an empty copy set as failure
