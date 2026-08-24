# Diagnose-First binding

**Full kernel SSOT:** `kernels/Diagnose First Kernel.md`
**Law:** `CANONICAL_LAW.md` §11 (append may correct the source-kernel path).

## Binding rules for this skill

1. **Discovery before mutation** — inventory + diagnosis receipts before extract or prune-execute.
2. **No fire-and-hope** — never delete a ref because it looks stale.
3. **Unknown ⇒ keep** — if unique value cannot be proven absent, do not prune. An
   unresolvable baseline is an unknown, not an empty diff.
4. **Auth is layered** — user confirmation alone is insufficient for stash drop / prune-execute; require env auth + receipt hash.
5. **Isolation** — on a shared dirty clone, prefer worktree extract; do not checkout thrash.
6. **Judge against a fetched baseline** — a count taken against a stale
   `origin/main` is not a diagnosis. Fetch, or record `fetched: false` and treat
   the verdict as provisional.
7. **Counting commits is not proving value** — a branch whose work already landed
   still reports commits ahead. Redundancy needs patch-id or absorption evidence.

## Classification outputs

| Class | Meaning |
|-------|---------|
| `keep_push` | Commits ahead that are not accounted for upstream; push or open PR |
| `extract` | Unique paths/commits should be moved to a new branch |
| `archive_ref` | Commits ahead but the work already landed — by patch id (`high`) or by line absorption (`medium`). Tip SHA preserved in the receipt; `git branch -d` will refuse it, so removal is force-delete under `prune-policy.md` |
| `prune_candidate` | No unique commits vs `origin/main` **and** diagnosis receipt says so |
| `unknown` | Baseline unprovable — keep the ref |
