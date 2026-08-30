<!-- L9_META
l9_schema: 1
parent: l9-issue-remediation
layer: reference
role: unblock_breadcrumb
tags: [issues, pickup, graphiti, session-reference, comment, close]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-29
/L9_META -->

# Unblock Breadcrumb Contract

Mandatory Converge closeout. Order: **PICKUP → issue comments → close if
resolved → conditional session-ref**.

## 1. Graphiti PICKUP (required)

Write via Cursor Graphiti front door / `l9-end-session` PICKUP shape:

```text
PICKUP|date=YYYY-MM-DD|task={what was unblocked}|files={paths}|next={resume action}|blocker={remaining or none}|gmps={ids or none}|outcome={fixed|partial|blocked}
```

If the write fails → status `BLOCKED_PICKUP`. Still post issue comments. **Do not**
claim Converge complete.

## 2. Issue comment (required on every cluster issue)

Use `scripts/post_issue_comment.py`. Body template:

```markdown
## l9-issue-remediation unblock

**Cluster:** {cluster_id}
**Ownership:** {CODEBASE|CROSS_REPO|…}
**Owning repo:** {owner}/{repo}
**Change:** {commit_sha or PR url or "none — HUMAN/EXTERNAL"}
**Unblocked for resume:** {next agent action in one line}
**Remaining:** {none | HUMAN/EXTERNAL note}

<!-- l9-issue-remediation: cluster={cluster_id}; cycle={N}; status={fixed|partial|blocked} -->
```

Never include secret values, tokens, or `.env` contents.

## 3. Close if resolved (required when status=fixed)

If the marker `status=fixed`, the GitHub issue **must not stay OPEN**.

Use `scripts/close_resolved_issue.py` (comment + `gh issue close --reason completed`).

- Converge: close when the fix is **on a PR or already landed** (`--on-pr` /
  `--commit` / `--merged-pr`). Do not wait for remediator merge.
- Diagnose: close already-resolved only (linked PR merged, or defect gone on
  default) with the same evidence flags.
- HUMAN / EXTERNAL: refuse unless `--reason superseded|duplicate|already-fixed|not-reproducible|does-not-exist`
  plus proof.

Done-when **fails** if `status=fixed` and the issue is still OPEN.

## 4. Root session-reference markdown (conditional)

Path: repo-root `TODO.md`.

- **If the file exists:** prepend (or refresh) a **session reference** section:

```markdown
## Issue unblock (session reference)

**Cluster:** {owner}/{repo}#{n} (+ linked)
**Owning fix:** {commit or PR}
**Next:** {resume action}
**Pickup:** Graphiti PICKUP written {date}
```

- **If the file does not exist:** skip. Do not create `TODO.md`.

Idempotent: refresh the same heading body; do not spawn duplicate sections.

## Done-when interaction

| Breadcrumb | Missing | Converge status |
|------------|---------|-----------------|
| PICKUP | failed | `BLOCKED_PICKUP` |
| Issue comment | failed | not converged |
| status=fixed and issue still OPEN | close skipped | not converged |
| Session-ref | file absent | ok (skipped) |
| Session-ref | file present, update failed | not converged |
