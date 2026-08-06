<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [plan, ticket, template, doc-surface]
status: active
version: 2.2.0
updated: 2026-08-06
/L9_META -->

# Engineering ticket template (reference)

## List format

```markdown
# [Descriptive title]

## Description
[What to build and why]

## Technical context
[Constraints, architecture, dependencies]

## Acceptance criteria
1. [Testable criterion]
2. [Testable criterion]
3. [When human/agent contracts change: README / AGENTS.md / peer surfaces updated or N/A justified]

## Testing
- [What to verify]

## Dependencies
- [Blockers or linked work]
```

## Given-When-Then format

```markdown
### Scenario: [name]
Given [precondition]
When [action]
Then [expected result]
```

## Rules

- Title summarizes the work in one line.
- Acceptance criteria must be testable.
- Suggest implementation approach without over-prescribing.
- Link designs, APIs, and related tickets.
- When the change alters agent-facing or human-facing contracts, include a doc/root surface AC (or explicit N/A). Prefer `l9-update-agent-docs` / `l9-wire-skill-into-repo` for those rewrites at implementation time.
