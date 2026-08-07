---
name: pr
version: "13.0.0"
description: "PR Diagnose — readiness, review comments, merge blockers via l9-pr-remediation"
before_chain: rules
auto_chain: ynp
strict_mode: true
---

# /pr — PR Diagnose

Delegates to skill **`l9-pr-remediation`** in **Diagnose** intent (read-only).

## Usage

```text
/pr #45
/pr #45,#46
```

## Contract

1. Read `skills/l9-pr-remediation/SKILL.md` and follow **Diagnose** + [references/diagnose-workflow.md](../skills/l9-pr-remediation/references/diagnose-workflow.md).
2. Optional focused lenses: [references/review-angles.md](../skills/l9-pr-remediation/references/review-angles.md).
3. Merge only after user confirm: [references/merge-advise.md](../skills/l9-pr-remediation/references/merge-advise.md).
4. **Never** unpack PR diffs into the worktree. **Never** run Converge (fix/push) from `/pr` alone — that requires explicit remediate/fix/babysit intent, make-pr handoff, or autonomy packet.

## Forbidden

- Alignment %, gap matrix, deep-eval theater
- Babysit / CI fix loops from this slash alone
- Manual file write from `gh pr diff`
