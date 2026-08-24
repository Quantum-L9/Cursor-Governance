# Value diagnosis

For each candidate ref:

1. Refresh the baseline (`--fetch`). Ahead counts are only as honest as the ref
   they are measured against; a stale `origin/main` routinely overstates unpushed
   work by a wide margin.
2. `git log --oneline origin/main..<ref>` — how many commits, not how much value.
3. `git diff --stat origin/main...<ref>` — the touched path set.
4. **`git cherry -v origin/main <ref>`** — required, not optional. `-` marks a
   commit whose patch id is already upstream, `+` one that is not.
5. Content absorption for the paths from step 3: relative to the **merge base**,
   does every line the ref added now appear upstream, and every line it removed
   now absent?
6. Emit diagnosis receipt (see `output-receipt.schema.yaml`).

## Why steps 4 and 5 are both needed

They fail in opposite directions, and each covers the other's blind spot.

`git cherry` is **exact**: identical patch ids mean the work certainly landed.
It sees cherry-picks and rebases. It cannot see work that landed *reimplemented*
— different bytes, same substance — which is the ordinary outcome when a branch
is redone on main and the original is left behind.

Content absorption sees exactly that case, and is a **heuristic**. It compares
against the merge base, not whole files, because a ref that trails the baseline
by hundreds of commits holds a stale copy of nearly everything; comparing file
contents would report all that stale text as "work the baseline is missing." A
rename, a reindent, or a coincidentally-matching line will still fool it.

Absorption may only ever argue that a ref is **redundant** — it is never evidence
that a ref is unique. But be precise about what that does and does not buy:

By construction, absorption fires **while `git cherry` is still reporting `+`**.
Reimplemented work has different patch ids; that disagreement is the whole reason
absorption is consulted. So absorption *does* move a ref cherry called novel into
`archive_ref`, and a single added line that happens to exist somewhere upstream is
enough to do it. The classification is therefore a **claim about content, not a
licence to delete**. Safety comes from what consumers do with `redundancy_basis`,
not from the class alone: only `patch_id` may authorise removal.

## Classification

| Class | Rule | Confidence | Basis |
|-------|------|------------|-------|
| `unknown` | Baseline does not resolve — novelty unprovable | `unknown` | — |
| `archive_ref` | Commits ahead, every patch already upstream by id | `high` | `patch_id` |
| `archive_ref` | Commits ahead, every changed line absorbed upstream | `medium` | `content_superset` |
| `prune_candidate` | Zero commits ahead | `high` | — |
| `keep_push` | Any commit ahead not accounted for above | `high` | — |

A mixed ref — some patches upstream, some not — stays `keep_push` unless *every*
line it touched is absorbed. One unaccounted line is enough to keep a branch.

Never classify `prune_candidate` when confidence is unknown, and never let an
unresolvable baseline fall through to a prune class: no baseline means keep.

## What consumers must do with the basis

| Basis | May authorise delete? | Why |
|-------|----------------------|-----|
| `patch_id` | Yes, under `prune-policy.md` | Patch ids match exactly |
| `content_superset` | **No** — report for review only | A coincidental line match is indistinguishable from real absorption |

`/ff` implements this split: `patch_id` refs go to its `superseded` bucket,
`content_superset` refs to `review`, which is printed and never deleted nor
offered a force-delete command.

## Known blind spot

Generated manifests (sha256 digests, lockfile hashes) are recomputed rather than
copied, so their lines never match and they read as unabsorbed. That biases
toward **keeping** a branch, which is the safe direction — but it does mean a
branch whose only remaining delta is regenerated hashes will not classify
`archive_ref` on absorption alone.
