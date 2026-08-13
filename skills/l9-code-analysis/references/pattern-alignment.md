<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-code-analysis
layer: reference
role: analysis_kernel
tags: [analysis, patterns, standards, alignment]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
sources:
  - harvested: analysis-pattern-extract / extract_align (Suite-5 legacy)
  - absorbed: key-components/01_pattern-detector (pack scan dimensions)
--- /SKILL_META ---

Purpose:
Extract recurring code patterns in a scope and compare them to repo/L9 standards.
When the target is a skill, prompt, or workflow pack, also extract repeated
structures and reasoning-chain templates.
-->

# Pattern Alignment (extract_align)

Use after exploration or before a refactor sweep to find drift from conventions.

## Scan Dimensions

```text
├── Error handling (bare except, missing recovery)
├── Logging (print vs structured logger)
├── Async / I/O (sync in async paths)
├── Imports (top-level cross-addon vs lazy)
├── Testing (fixtures, skip anti-patterns)
├── Domain patterns (Odoo 19: list vs tree, Constraint vs _sql_constraints, etc.)
└── Pack / workflow (when target is a skill, prompt, or workflow pack)
    ├── Repeated node or section structures
    ├── Reasoning chains (if → validate → mutate → return)
    └── Reusable field / ID patterns (e.g. SM#####) grounded in repo docs
```

Load pack/workflow dimensions only when the scope contains `SKILL.md`, prompt
markdown, or workflow JSON/YAML. Do not invent a `.L9.json` parser.

## Compare Table

| Pattern | Found in scope | Repo standard | Aligned? |
|---------|----------------|---------------|----------|
| {name} | {count or example} | {AGENTS.md / rule ref} | ✅ / ❌ |

## Alignment Plan

| # | Current | Target | Files / scope |
|---|---------|--------|---------------|
| 1 | {current} | {target} | {paths} |

## Output

```markdown
## Pattern Alignment: {scope}

### Patterns Found
{table}

### Misalignments
| Issue | Files | Fix |
|-------|-------|-----|

### Alignment Plan
| # | Change | Scope | Auto-fix? |
|---|--------|-------|-----------|

→ Invoke `l9-code-maintenance` for execution sweeps when plan is approved.
```

## Rules

- Standards source order: explicit user → AGENTS.md / INVARIANTS.md / `.cursor/rules` → this reference.
- Do not invent standards not grounded in repo docs.
- One finding per root cause — deduplicate before delivering the plan.
