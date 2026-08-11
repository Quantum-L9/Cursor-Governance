---
name: issues
version: "1.0.0"
description: "Issues Diagnose — org open-issue readiness and blockers via l9-issue-remediation"
before_chain: rules
auto_chain: ynp
strict_mode: true
---

# /issues — Issues Diagnose

Delegates to skill **`l9-issue-remediation`** in **Diagnose** intent (read-only).

## Usage

```text
/issues
/issues Quantum-L9/SEO-Bot
/issues Quantum-L9/SEO-Bot#5
```

## Contract

1. Read `skills/l9-issue-remediation/SKILL.md` and follow **Diagnose** + [references/diagnose-workflow.md](../skills/l9-issue-remediation/references/diagnose-workflow.md).
2. Fleet default: all non-archived `Quantum-L9/*` via `scripts/fleet_discover.py`.
3. **Never** run Converge (fix/push/close/comment-as-fix) from `/issues` alone — that requires explicit remediate/fix/unblock/babysit intent or an autonomy packet.
4. PR green/merge remains **`l9-pr-remediation`** / `/pr`.

## Forbidden

- Alignment %, gap matrix, deep-eval theater
- Closing issues or committing from this slash alone
- Inventing root `TODO.md` files
