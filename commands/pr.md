---
name: pr
version: "14.0.0"
description: "PR Diagnose — digest first, then l9-pr-remediation readiness (read-only, no merge)"
before_chain: rules
auto_chain: ynp
strict_mode: true
---

# /pr — PR Diagnose

Runs **`l9-pr-digest`** first, then skill **`l9-pr-remediation`** in **Diagnose** intent (read-only).

`/pr` never merges. Converge is skill **`/l9-pr-remediation`** or explicit remediate language.

## Usage

```text
/pr #45
/pr #45,#46
```

## Contract

1. Identify the PR(s). STOP if none.
2. **Digest first.** Read `skills/l9-pr-digest/SKILL.md` and run the skill (Claude Code `/l9-pr-digest`, or this same machine path):

```bash
python3 skills/l9-pr-digest/scripts/pr_digest.py \
  --repo {owner}/{repo} --pr-number {n} --workspace "$PWD" \
  --output .l9/pr/pr-digest-result.json
python3 skills/l9-pr-digest/scripts/require_digest.py \
  --path .l9/pr/pr-digest-result.json --mode diagnose
```

   Do **not** pass `--quiet`. Show the `[digest]` finding stream and the 11-section unpack in chat. The JSON file is the remediator handoff, not the human report.
   If the head moved, discard the stale file and re-run. A valid non-READY decision still continues into Diagnose.
3. Read `skills/l9-pr-remediation/SKILL.md` and follow **Diagnose** + [references/diagnose-workflow.md](../skills/l9-pr-remediation/references/diagnose-workflow.md). Consume the digest packet; do not re-invent intent, expansion, or CI conclusions the digest already bound.
4. Optional focused lenses: [references/review-angles.md](../skills/l9-pr-remediation/references/review-angles.md).
5. **Never** unpack PR diffs into the worktree. **Never** run Converge (fix/push/merge) from `/pr` alone — that requires **`/l9-pr-remediation`** or explicit remediate/fix/babysit intent.

## Forbidden

- Alignment %, gap matrix, deep-eval theater
- Babysit / CI fix loops from this slash alone
- Manual file write from `gh pr diff`
- Skipping the digest when a PR number is known
