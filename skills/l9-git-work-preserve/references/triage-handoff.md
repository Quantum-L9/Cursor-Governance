# Triage handoff (`/ff` → this pack)

`/ff` is `l9-repo-sync`'s command and stays that way. It catches a named clone
up to `origin/main` **in place** and parks anything unique rather than deleting
it. That is the correct default, and it has a consequence: the preserve refs
accumulate and nothing in `/ff` ever looks at them again.

This pack is the other half. `/ff` decides *what to keep*; triage decides
*what keeping it still buys you*.

## What `/ff` parks

Written by `skills/l9-repo-sync/scripts/ff.sh`:

| Ref | Holds |
|---|---|
| `refs/l9/preserved/ff/<stamp>` | HEAD when unique commits existed |
| `l9/ff-preserve-<stamp>` | branch at that same commit |
| `refs/l9/preserved/ff-dirty/<stamp>` | `git stash create` object for dirty tracked paths |
| `$HOME/.cursor/l9-ff-hold/<clone>/<stamp>/` | file copies (not a ref; out of scope here) |

The first three are commit-ish, so they diagnose exactly like any other ref.

## Running it

```bash
python3 skills/l9-git-work-preserve/scripts/triage_preserved_refs.py \
  --repo "$(pwd)" --fetch
```

`--fetch` refreshes origin once for the whole run. Without it the verdicts are
provisional and the receipt says so (`fetched: false`).

## Buckets

Each ref is classified by `diagnose_ref_value.py` — patch-id evidence and line
absorption, never a commit count or a date. See `value-diagnosis.md`.

| Bucket | Class / basis | Meaning |
|---|---|---|
| `novel` | `keep_push` | Still holds work not accounted for upstream — the reason `/ff` parked it |
| `superseded` | `archive_ref` / `patch_id` | Every patch is upstream, exactly. Eligible for `prune-execute` |
| `review` | `archive_ref` / `content_superset` | Lines look absorbed but patch ids disagree — human reads it |
| `merged` | `prune_candidate` | Zero commits ahead |
| `unproven` | `unknown` | Baseline unresolvable — keep |

## Triage does not delete

There is no delete path in `triage_preserved_refs.py`; the receipt states
`deletes_performed: 0`. A `superseded` verdict makes a ref *eligible* for
removal, it does not perform one — that still runs through `prune-policy.md`
with its own authorisation and receipt hash.

`review` exists because absorption fires while `git cherry` still reports the
commits novel, so one added line that happens to exist somewhere upstream is
enough to land a ref there. Those are printed for a person, and no force-delete
command is offered for them.

## What a `novel` ref means

It means `/ff` was right to park it and the work is still only here. Publishing
it is the sanctioned path (`PR_REMEDIATE=0 make pr` — never a raw push), and it
is a separate decision from triage: this script reports, it does not publish.
