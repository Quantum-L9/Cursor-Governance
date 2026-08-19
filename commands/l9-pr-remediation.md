---
name: l9-pr-remediation
version: "1.1.0"
description: "PR Converge — makefile pr-check then pr, remediate all open PRs, stack-safe oldest-first merge"
before_chain: rules
strict_mode: true
---

# /l9-pr-remediation — Converge then merge

Delegates to skill **`l9-pr-remediation`** in **Converge** intent.

Invoking this command **is** merge authorization for **all open PRs** in the
target repo. Campaigns, `make pr`, and `/pr` (Diagnose) do not merge.

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
GOV_PY="${GOV_PY:-$PWD/.venv/bin/python}"
"$GOV_PY" ops/autonomy/authorize_merge.py --repo {owner}/{repo} --all-open \
  --reason "l9-pr-remediation invoked"
```

3. Fingerprint venv (`UV_PYTHON` = uv-managed native CPython; reject miniconda / `--system`).
4. Local verify is `UV_PYTHON=<native> make pr-check`. Publish is
   `UV_PYTHON=<native> PR_REMEDIATE=0 make pr`. Never raw `git push`.
5. Remediate every open PR to green + mergeable (bounded cycles).
6. Merge each green mergeable PR **oldest-first**, stack-safe:

```bash
# squash only when this head is not the base of another open PR
gh pr merge {n} --repo {owner}/{repo} --squash --delete-branch
# stacked parent: children first, retarget, or --merge
```

7. Never `--admin`, force-push, unpack diffs, or `gh pr update-branch` after
   squash-merging a parent.

## Forbidden

- Diagnose-only stop
- Merge from `/pr` / Diagnose
- Merge of a red or conflicted PR
- Admin merge / force-push / history rewrite
- `make precommit` / `--all-files` as the public gate
