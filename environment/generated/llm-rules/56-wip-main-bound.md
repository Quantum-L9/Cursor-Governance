---
description: WIP packs are main-bound — author them on main, commit the same turn they appear, and land them on origin/main before anything consumes them. Never leave a WIP-only pack on a feature or campaign branch.
---

# WIP is main-bound

`WIP/` is a tracked corpus on `main` (`rules/15-work-tracking.mdc`). A WIP-only
pack that exists solely on a feature or campaign branch is invisible to every
other clone and worktree that tracks `main` — including the next session that is
supposed to execute it. The pack is an **input** to later work, so it has to be
on `main` before anything consumes it.

Org invariant: `L9-ORG-014` in [`ORG_INVARIANTS.yaml`](../ORG_INVARIANTS.yaml).

## MUST

- Author WIP in a checkout whose HEAD is `main` (`WIP/<M-D-YY>/<topic>/`).
- Commit the pack with explicit pathspecs in the same turn it appears — not at
  the end of the session, not "once the feature branch is done" (rule 49).
- Land it on `origin/main` in the same session through the sanctioned publish
  path (`PR_REMEDIATE=0 make pr`, then merge). A WIP-only changeset carries no
  code risk, so there is no reason to hold it.
- If a pack is discovered on a feature or campaign branch, copy the bytes onto a
  `main`-based branch and publish that separately. Leave the feature branch to
  its code.
- Verify main visibility before treating a pack as delivered:

```bash
git fetch origin main --quiet
git ls-tree -r --name-only origin/main -- "WIP/<M-D-YY>/<topic>/"
```

Empty output means the pack is not on `main` and is not delivered.

## MUST NOT

- Leave a WIP-only pack on a feature or campaign branch past the turn that
  created it.
- Mix a WIP-only pack into a feature branch's code commits, where it lands only
  when that branch merges — and disappears if it does not.
- Treat a preserve ref (`refs/l9/preserved/**`), `l9/dirt-shelf`, a stash, or
  `$HOME/.cursor/l9-ff-hold/` as WIP delivery. Those are parks, not
  distribution.
- Assume another worktree can see the pack because it is committed *somewhere*.
- `git push origin main` directly. Direct main push stays forbidden
  (`rules/96-multi-agent-main-bound-execution.mdc` E3); "push main" here means
  land the WIP commit on `origin/main` through `make pr` in the same session.

<!-- generated-from: rules/56-wip-main-bound.mdc; do-not-edit -->
