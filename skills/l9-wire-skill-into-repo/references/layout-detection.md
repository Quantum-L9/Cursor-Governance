<!-- L9_META
l9_schema: 1
parent: l9-wire-skill-into-repo
layer: reference
role: layout_detection
tags: [wiring, registry, layout, detection]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-06-06
/L9_META -->

# Layout Detection

Run from the repository root. Stop at the first matching profile or merge when multiple coexist.

## Profile A — Claude Code pack with L9 globals

**Signals**

- `.claude/README.md` with **L9 Global Skills** and/or **Project Skills** tables
- Optional: `.claude/adapters/plasticos-repo-wiring.md`

**Wiring targets**

1. L9 globals → **L9 Global Skills** table + `AGENTS.md`
2. Project skills → **Project Skills** table + `AGENTS.md`
3. `.claude/agents/*.md` `skills:` lists (selective)

## Profile B — Cursor project skills

**Signals**

- `.cursor/skills/` exists or user chose project scope under `.cursor/skills/{name}/`

**Wiring targets**

1. `AGENTS.md` Skills table (if present)
2. Any repo-local skill index (search for `| Skill |` tables in `.cursor/` docs)
3. Cursor rules that enumerate skills (rare — update only if an explicit list exists)

## Profile C — AGENTS.md-only

**Signals**

- No `.claude/README.md` but `AGENTS.md` has Agent Skills / Skills section

**Wiring targets**

1. `AGENTS.md` only
2. Subagent files if discovered via grep for `skills:` in `*.md` under `.claude/agents/` or `.cursor/agents/`

## Profile D — No agent config

**Signals**

- No `AGENTS.md`, no `.claude/README.md`, no skill tables

**Action**

- For **project** skills: tell the user which file should be created (prefer `AGENTS.md` Skills table) and offer to scaffold one row — do not invent a full agent framework.
- For **global** skills: wiring complete after pack validation.

## Ambiguity

When both `.claude/` and `.cursor/` skill roots exist:

- Register project skills in **both** indexes if both are maintained in the repo.
- If only one index is actively used, prefer the one referenced by `AGENTS.md` and `.claude/README.md`.
