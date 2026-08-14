# Stash deep analysis

Stashes are high-risk unique work. Default: **list metadata only** in audit.

## Before any stash drop

1. `git stash show -p stash@{N}` (or equivalent) summarized without secrets
2. Record deep-analysis receipt: index, WIP commit message, touched paths, tip parent
3. Prefer `git stash branch <name> stash@{N}` (extract) over drop
4. Drop only when:
   - deep-analysis receipt exists
   - user explicitly authorizes
   - `L9_GIT_STASH_DROP_AUTHORIZED=<reason>` is set

`git stash clear` is forbidden unless every entry has a deep-analysis receipt and the same auth env.
