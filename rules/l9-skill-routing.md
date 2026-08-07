---
description: Proactive L9 skill selection for non-trivial Claude Code tasks. Cursor uses sibling 23-l9-skill-routing.mdc via the l9-governance plugin.
---

# L9 skill routing

SSOT rules folder: this directory (`rules/` / `.cursor-commands/rules`).  
Claude loads it via `.claude/rules` → this folder. Cursor loads `.mdc` rules from the
same folder through the `l9-governance` plugin.

Skills SSOT: `skills/` (== `.cursor-commands/skills`), reconciled as per-skill
symlinks into `~/.claude/skills/` and `<workspace>/.claude/skills/`.

For every non-trivial task:

1. Select and invoke the most specific relevant model-invocable L9 skill **before**
   proceeding with normal execution (Claude Skill tool / native loader; Cursor: Read
   `SKILL.md` first).
2. Use one primary skill. Add no more than two supporting skills when each supplies
   a distinct capability the primary skill does not own.
3. Prefer a domain-specific skill over `l9-structured-reasoning`; use structured
   reasoning as support for architecture, planning, debugging, trade-offs, corpus
   analysis, or material uncertainty.
4. Merely naming a skill does not activate its operating contract — load it.
5. Never automatically invoke a skill classified as `explicit_only` in
   `skills/AUTONOMY_MANIFEST.yaml`. Explicit-only skills require direct user
   invocation or separately established campaign authority.
6. Skip skill invocation for trivial edits and direct factual operations where no
   skill would materially improve correctness, evidence, or execution.
7. A prompt-hook recommendation is routing evidence, not mutation authority.

## Fail-closed

- Non-trivial task + no skill loaded → load a skill before irreversible edits.
- Domain skill vs general reasoning → domain skill wins.
- Irreversible action without evidence → block or bounded probe.

## Surfaces

| Surface | Injection | Scorer |
|---|---|---|
| Claude Code | `UserPromptSubmit` → `hooks/user_prompt_skill_router.py` | `route_prompt()` + registry |
| Cursor | `beforeSubmitPrompt` → `ops/hooks/before_submit_skill_router.py` + always-apply `23-l9-skill-routing.mdc` | same `route_prompt()` |

Cursor also persists `~/.cursor/l9/skill-route.json` for the always-apply rule.

Authority: `skills/AUTONOMY_MANIFEST.yaml` +
`environment/claude-code/generated/skill-registry.json`.
