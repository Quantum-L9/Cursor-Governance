---
name: issues
version: "2.0.0"
description: "Issues remediator — drain open issues, land on PRs, close resolved, chain /l9-pr-remediation only at open_issues=0"
before_chain: rules
strict_mode: true
---

# /issues — Issue remediator (Converge)

Delegates to skill **`l9-issue-remediation`** in **Converge** intent.

## Usage

```text
/issues
/issues Quantum-L9/SEO-Bot
/issues Quantum-L9/SEO-Bot#5
/issues diagnose
/issues diagnose Quantum-L9/SEO-Bot
```

## Contract (Converge — default)

1. Read `skills/l9-issue-remediation/SKILL.md` and follow **Converge**.
2. Fleet default: all non-archived `Quantum-L9/*` via `scripts/fleet_discover.py`.
3. Drain **all** automatable clusters, highest leverage first
   (`scripts/cluster_rank.py`).
4. Land each fix on the matching open PR, else a new stacked PR on the newest
   open PR (`PR_STACK=auto` / `PR_REMEDIATE=0 make pr`).
5. Close resolved issues (`scripts/close_resolved_issue.py`) when the fix is
   on a PR. `status=fixed` must not stay OPEN.
6. Re-count open issues. Invoke `/l9-pr-remediation` **only if**
   `open_issues == 0`:

```bash
python3 skills/l9-issue-remediation/scripts/open_issues_gate.py \
  --intent converge --issues issues.json
```

Zero means zero. Leftover HUMAN/EXTERNAL OPEN issues are `BLOCKED_OPEN_ISSUES`.
This skill never `gh pr merge`.

## Auditor opt-out

`/issues diagnose` (or “what’s blocking?”) is Diagnose only:
[references/diagnose-workflow.md](../skills/l9-issue-remediation/references/diagnose-workflow.md).
Already-resolved close is allowed. Diagnose **never** invokes
`/l9-pr-remediation`.

## Forbidden

- Alignment %, gap matrix, deep-eval theater
- Merging PRs from this slash
- Chaining `/l9-pr-remediation` while `open_issues != 0`
- Inventing root `TODO.md` files
- Mass-closing HUMAN/EXTERNAL without superseded/duplicate/already-fixed proof
