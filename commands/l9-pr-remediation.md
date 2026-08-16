---
name: l9-pr-remediation
version: "1.0.0"
description: "PR Converge — remediate all open PRs in the target repo to green, then merge"
before_chain: rules
strict_mode: true
---

# /l9-pr-remediation — Converge then merge

Delegates to skill **`l9-pr-remediation`** in **Converge** intent.

Invoking this command **is** merge authorization for **all open PRs** in the
target repo. Campaigns and `/pr` (Diagnose) do not merge.

## Usage

```text
/l9-pr-remediation
/l9-pr-remediation Quantum-L9/Cursor-Governance
/l9-pr-remediation Quantum-L9/Cursor-Governance#175
```

## Contract

1. Read `skills/l9-pr-remediation/SKILL.md` and follow **Converge**.
2. Write the receipt first:

```bash
python3 ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
```

3. Remediate every open PR to green + mergeable (bounded cycles).
4. Merge each green mergeable PR oldest-first:

```bash
gh pr merge {n} --repo {owner}/{repo} --squash --delete-branch
```

5. Never `--admin`, force-push, or unpack diffs.

## Forbidden

- Diagnose-only stop
- Merge of a red or conflicted PR
- Admin merge / force-push / history rewrite
