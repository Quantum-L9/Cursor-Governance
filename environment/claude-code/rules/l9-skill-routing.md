---
description: Proactive L9 skill selection for non-trivial Claude Code tasks.
---

# L9 skill routing

The governance clone is the canonical source for L9 skills. Claude Code discovers
managed copies or links under `.claude/skills/` or `~/.claude/skills/`.

For every non-trivial task:

1. Select and invoke the most specific relevant model-invocable L9 skill before
   proceeding with normal execution.
2. Use one primary skill. Add no more than two supporting skills when each supplies
   a distinct capability the primary skill does not own.
3. Prefer a domain-specific skill over `l9-structured-reasoning`; use structured
   reasoning as support for architecture, planning, debugging, trade-offs, or
   material uncertainty.
4. Invoke a skill through Claude Code's Skill tool. Merely naming or reading a skill
   does not activate its operating contract.
5. Never automatically invoke a skill classified as `explicit_only` in
   `skills/AUTONOMY_MANIFEST.yaml`. Explicit-only skills require direct user
   invocation or separately established campaign authority.
6. Skip skill invocation for trivial edits and direct factual operations where no
   skill would materially improve correctness, evidence, or execution.
7. A prompt-hook recommendation is routing evidence, not mutation authority. Tool,
   repository, commit, push, merge, deployment, credential, and production rules
   remain independently binding.
