---
name: l9-issue-remediation
version: "1.0.0"
description: "Issue remediator Converge — drain open issues, land on PRs, close resolved, chain /l9-pr-remediation only at open_issues=0"
before_chain: rules
strict_mode: true
---

# /l9-issue-remediation — Converge then chain remediator

Delegates to skill **`l9-issue-remediation`** in **Converge** intent.
Same contract as bare `/issues`. Diagnose is `/issues diagnose` only.

## Usage

```text
/l9-issue-remediation
/l9-issue-remediation Quantum-L9/Cursor-Governance
/l9-issue-remediation Quantum-L9/Cursor-Governance#377
```

## Contract

1. Read `skills/l9-issue-remediation/SKILL.md` and follow **Converge**.
2. Drain all automatable clusters, highest leverage first. Do not stop
   between issues. Verify each issue is real
   (`references/issue-verify.md`) before a patch; close phantoms.
3. Land fixes on the matching open PR or a new stacked PR on the newest
   (`PR_STACK=auto`). `make_pr: true` means the fix is on a GitHub PR.
4. Close when `status=fixed` (`scripts/close_resolved_issue.py`).
5. When only HUMAN/ARCHITECTURE/EXTERNAL remain, ask a recommended
   multiple-choice (**A** first) and resume after the letter.
6. Invoke `/l9-pr-remediation` **only after** bound-target `open_issues=0`:

```bash
python3 skills/l9-issue-remediation/scripts/open_issues_gate.py \
  --intent converge --issues issues.json
```

7. Never `gh pr merge` from this command. Merge stays on
   `/l9-pr-remediation` after the gate.

## Forbidden

- Diagnose-only stop
- `/l9-pr-remediation` while `open_issues != 0`
- Admin merge / force-push / history rewrite
- Mass-close HUMAN/EXTERNAL without proof
