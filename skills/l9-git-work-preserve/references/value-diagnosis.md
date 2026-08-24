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

So absorption may only ever argue that a ref is **redundant**. It is never
evidence that a ref is unique, and it never overrides a `+` into a keep.

## Classification

| Class | Rule | Confidence |
|-------|------|------------|
| `unknown` | Baseline does not resolve — novelty unprovable | `unknown` |
| `archive_ref` | Commits ahead, every patch already upstream by id | `high` (`patch_id`) |
| `archive_ref` | Commits ahead, every changed line absorbed upstream | `medium` (`content_superset`) |
| `prune_candidate` | Zero commits ahead, empty unique path set | `high` |
| `extract` | Zero commits ahead but unique paths present | `medium` |
| `keep_push` | Any commit ahead that is not accounted for above | `high` |

A mixed ref — some patches upstream, some not — stays `keep_push`. One
unaccounted patch is enough to keep a branch.

Never classify `prune_candidate` when confidence is unknown, and never let an
unresolvable baseline fall through to a prune class: no baseline means keep.

## Known blind spot

Generated manifests (sha256 digests, lockfile hashes) are recomputed rather than
copied, so their lines never match and they read as unabsorbed. That biases
toward **keeping** a branch, which is the safe direction — but it does mean a
branch whose only remaining delta is regenerated hashes will not classify
`archive_ref` on absorption alone.
