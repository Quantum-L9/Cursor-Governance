# Protocol D — Skill routing

Harvests PR #41 / `rules/23-l9-skill-routing.mdc` (Claude projection: `environment/generated/llm-rules/l9-skill-routing.md`) for bounded-autonomy campaigns.

## Composition

1. **Primary:** `l9-bounded-autonomy` only (this skill).
2. **Supporting:** at most **two** of:
   - `l9-pr-remediation` — remediation loop inside poll workers
   - `l9-structured-reasoning` — plan/trade-off support
   - `l9-cli-optimization` — dormant-capability lanes when that is the lane’s job
3. Prefer the most specific supporting skill; do not stack redundant ones.

## Explicit-only

- This skill has `disable-model-invocation: true`.
- Never auto-invoke from a prompt-hook recommendation alone.
- Start via `/autonomy` or explicit user campaign request.
- A routing hint is **evidence**, not mutation authority.

## Trivial skip

Skip launching a full autonomy campaign for trivial edits (typo, show file, rename one symbol) where no parallel/poll benefit exists.
