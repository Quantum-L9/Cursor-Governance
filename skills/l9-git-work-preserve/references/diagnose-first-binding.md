# Diagnose-First binding

**Full kernel SSOT:** `kernels/Diagnose First Kernel.md`
**Law:** `CANONICAL_LAW.md` §11 (append may correct the source-kernel path).

## Binding rules for this skill

1. **Discovery before mutation** — inventory + diagnosis receipts before extract or prune-execute.
2. **No fire-and-hope** — never delete a ref because it looks stale.
3. **Unknown ⇒ keep** — if unique value cannot be proven absent, do not prune.
4. **Auth is layered** — user confirmation alone is insufficient for stash drop / prune-execute; require env auth + receipt hash.
5. **Isolation** — on a shared dirty clone, prefer worktree extract; do not checkout thrash.

## Classification outputs

| Class | Meaning |
|-------|---------|
| `keep_push` | Unique commits; push or open PR |
| `extract` | Unique paths/commits should be moved to a new branch |
| `harvest` | Unique dirty/untracked/WIP across sibling worktrees; classify then port |
| `archive_ref` | Preserve tip SHA in receipt; optional tag; do not delete yet |
| `prune_candidate` | No unique commits vs `origin/main` **and** diagnosis receipt says so |
