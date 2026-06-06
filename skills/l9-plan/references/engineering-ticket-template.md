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
