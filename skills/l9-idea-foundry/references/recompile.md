# Incremental Foundry resume and recompile

Load this reference only when a prior `docs/idea-origin/FOUNDRY_INDEX.json` exists for the same pre-birth product.

## Purpose

Reuse validated intermediate results when their governing inputs are unchanged. Do not rerun expensive semantic work merely because Foundry is invoked again.

This is a pre-birth optimization. After remote birth, use the repository's normal planning and change workflow; Foundry origin artifacts become supporting evidence.

## Reuse order

Evaluate from upstream to downstream. The first invalid layer invalidates everything after it.

| Layer | Reuse only when |
|---|---|
| `AUTHORITY_MAP` | source inventory digest is unchanged, no explicit current operator instruction changes authority, and referenced external authority has not become stale |
| beneficiary/reuse map | authority semantic digest is unchanged and owner evidence is still current or immutable |
| Harvest | donor identity/revision, beneficiary contract, and accepted authority are unchanged; Harvest receipt remains valid |
| `IMPLEMENTATION_BLUEPRINT` | authority/reuse/Harvest inputs are unchanged and architecture evidence remains applicable |
| Plan Simple plan | blueprint semantic digest is unchanged **and** Plan Simple's own baseline/preconditions still hold |
| code validation | plan digest and exact code state are unchanged; the validation profile still applies |
| `FOUNDRY_INDEX` | regenerate whenever any indexed artifact changes |
| freeze receipt | never reuse after any tracked payload change |
| birth payload contract | recompile from the exact frozen source whenever the payload revision changes |

## Explicit invalidators

Invalidate regardless of matching file hashes when any of these occur:

- current user changes scope, objective, anti-goals, or acceptance criteria,
- a referenced upstream L9 owner changes incompatibly,
- an UNKNOWN becomes resolved in a way that changes behavior,
- Plan Simple baseline no longer matches the staging state,
- template/factory contract changed materially,
- previous evidence is stale, disputed, or no longer reachable.

## Resume statuses

Use only:

- `FRESH`: no prior index applies.
- `RESUME`: same compile lineage; continue from the last incomplete state.
- `RECOMPILE`: an upstream input changed; return to the earliest invalid layer.
- `BLOCKED`: reuse safety cannot be established and required evidence cannot be refreshed.

Do not call a run `RESUME` merely because a directory with the same repository name exists.

## Downstream leverage

The point of the index is not archival ceremony. It should let a future agent answer, without rereading the whole idea pack:

- What was the accepted product intent?
- Which upstream owners were deliberately reused?
- Which plan was executed?
- Which capabilities map to which code and tests?
- What is still unknown/deferred?
- Which exact artifact changed since the prior compile?

If the index cannot answer those questions through its refs/digests, repair the indexed contract instead of adding another summary file.
