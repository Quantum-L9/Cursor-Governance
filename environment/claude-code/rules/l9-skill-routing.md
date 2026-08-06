---
description: Proactive L9 skill selection for non-trivial Claude Code and Cursor tasks.
---

# L9 skill routing

The governance clone is the canonical source for L9 skills. Claude Code discovers
managed copies or links under `.claude/skills/` or `~/.claude/skills/`. Cursor
discovers them via the `l9-governance` plugin / agent skill list.

For every non-trivial task:

1. Select and invoke the most specific relevant model-invocable L9 skill **before**
   proceeding with normal execution. On Cursor, that means **Read `SKILL.md` as the
   first tool action**; on Claude Code, use the Skill tool.
2. Use one primary skill. Add no more than two supporting skills when each supplies
   a distinct capability the primary skill does not own.
3. Prefer a domain-specific skill over `l9-structured-reasoning`; use structured
   reasoning as support for architecture, planning, debugging, trade-offs, or
   material uncertainty.
4. Merely naming a skill does not activate its operating contract — load it.
5. Never automatically invoke a skill classified as `explicit_only` in
   `skills/AUTONOMY_MANIFEST.yaml`. Explicit-only skills require direct user
   invocation or separately established campaign authority.
6. Skip skill invocation for trivial edits and direct factual operations where no
   skill would materially improve correctness, evidence, or execution.
7. A prompt-hook recommendation is routing evidence, not mutation authority. Tool,
   repository, commit, push, merge, deployment, credential, and production rules
   remain independently binding.

## Surfaces

| Surface | Injection | Scorer |
|---|---|---|
| Claude Code | `UserPromptSubmit` → `hooks/user_prompt_skill_router.py` | `route_prompt()` + registry |
| Cursor | `beforeSubmitPrompt` → `ops/hooks/before_submit_skill_router.py` + always-apply `rules/23-l9-skill-routing.mdc` | same `route_prompt()` |

Cursor also persists `~/.cursor/l9/skill-route.json` for the always-apply rule.
