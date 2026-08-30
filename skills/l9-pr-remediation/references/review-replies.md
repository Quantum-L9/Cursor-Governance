<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: review_replies
tags: [pr, review, replies, threads, resolution, leverage]
owner: igor_beylin
status: active
version: 2.4.0
updated: 2026-08-29
/L9_META -->

# Review Reply Protocol

## Purpose

After sanctioned publish, reply to every review thread with a canonical response that resolves the thread. Do not treat replies as proof the PR is mergeable.

## Non-Negotiable Rules

1. **Every thread gets a reply.** No silent fixes. No ignored comments. This includes every [code-review agent](code-review-agents.md) thread (`github-code-quality[bot]`, Copilot) — volume, Note severity, and `skip_bot_discussions` are not exemptions.
2. **Replies follow canonical format.** No freeform prose — structured responses only.
3. **Resolve threads after replying.** Unresolved threads block merge perception.
4. **HUMAN Deferred items get linked issues.** Other defers (already-fixed, out-of-diff nits marked defer) do not require a GitHub issue. Never invent issues for bot chatter.
5. **Batch summary posted as final PR comment.** One comment summarizing all actions taken.

## Canonical Reply Formats

### Format A: Fixed

Use when the finding was addressed in this cycle's commit.

```markdown
**Fixed** in {commit_sha_short}

{one-line description of what was changed}

`{file}:{line}` — {before → after summary}
```

**Example:**

```markdown
**Fixed** in `a3f8c21`

Wrapped fetch in try-catch to handle network errors gracefully.

`src/services/llm.ts:47` — bare fetch → try/catch with retry on 5xx
```

After posting → **resolve the thread**.

### Format B: Deferred

Use when the finding requires a human decision, architectural change, or is out of scope.

```markdown
**Deferred** → #{issue_number}

Reason: {why this can't be fixed in this cycle}
Scope: {what would need to change}
Proposed resolution: {suggested approach for the issue}
```

**Example:**

```markdown
**Deferred** → #14

Reason: Express vs Fastify is an architectural decision requiring owner input.
Scope: Migrate src/index.ts to Fastify OR delete src/api/ (Fastify dead code).
Proposed resolution: Consolidate on Fastify in Phase 3 — it's more feature-complete in this codebase.
```

After posting → **create the issue first**, then reply with link, then **resolve the thread**.

### Format C: Acknowledged (Discussion)

Use when the comment is a question, suggestion for future consideration, or non-actionable feedback.

```markdown
**Acknowledged** — not actioned this cycle

{brief response to the question or consideration}

Tracking: {where this is captured, if anywhere}
```

**Example:**

```markdown
**Acknowledged** — not actioned this cycle

Good point about batching the DataForSEO requests. Current implementation handles up to 50 keywords which is within their rate limit, but worth revisiting if we scale past 200.

Tracking: Added to performance backlog in #15
```

After posting → **resolve the thread** (it's been acknowledged and tracked).

### Format D: Disagreed

Use when the review comment is incorrect, a false positive, or conflicts with project requirements.

```markdown
**Disagree** — {reason category}

{explanation of why the suggestion is not applicable}

Evidence: {link to docs, type definition, or code that proves the point}
```

Reason categories:
- `false positive` — bot misread the code
- `intentional design` — the current approach is deliberate
- `conflicts with {X}` — another requirement takes precedence
- `already handled` — the concern is addressed elsewhere

**Example:**

```markdown
**Disagree** — false positive

`ctx` appears unused at declaration but is captured in the closure on line 47 and used in the async callback. The bot's scope analysis doesn't trace into closures.

Evidence: `src/pipeline/PipelineRunner.ts:47` — `ctx` referenced in `stage.run(ctx)`
```

After posting → **resolve the thread**.

## How to Post Replies

**Required remediator path** is `scripts/reply_threads.py` (not a per-thread
`gh` loop). Inspect the cited file first. Then:

```bash
# TEMPLATE — substitute after inspect. python3 -u so progress is visible.
python3 -u skills/l9-pr-remediation/scripts/reply_threads.py \
  --repo {owner}/{repo} --input {threads.json}
```

The helper:

- refuses any thread without `inspected: true` (Law 9)
- batches GraphQL `addPullRequestReviewThreadReply` then `resolveReviewThread`
  (chunk of 6; reply phase before resolve phase)
- times out each `gh` spawn at 30s
- flushes every progress line
- posts the per-PR batch summary unless `--no-summary`

Do **not** spawn one REST `/comments/{id}/replies` plus one
`resolveReviewThread` per thread. That is 2N cold `gh` starts, silent if
stdout is buffered, and looks hung (2026-08-30: 18 threads / 107s / no
output until exit).

Single-thread fallback (one thread only, or the helper is unavailable):

### Reply to inline (diff) comments

```bash
gh api --timeout 30s /repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body="{canonical_reply}"
```

### Reply to review-level comments

```bash
gh pr comment {pr_number} --repo {owner}/{repo} --body "{reply}"
```

### Resolve a thread (GraphQL)

```bash
gh api --timeout 30s graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }
' -f threadId="{thread_node_id}"
```

To get the thread node ID:

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            isResolved
            comments(first: 1) {
              nodes { body author { login } }
            }
          }
        }
      }
    }
  }
' -f owner={owner} -f repo={repo} -F pr={pr_number}
```

Match threads to findings by comment body content, then resolve using the `id` field.
Repeat with `after: $cursor` until `pageInfo.hasNextPage` is false. A first-page-only
query is a protocol failure when more than 100 threads exist.

### Create a deferred issue (HUMAN Deferred only)

```bash
gh issue create --repo {owner}/{repo} \
  --title "Deferred from PR #{pr_number}: {short description}" \
  --body "{full context from review comment + proposed resolution}" \
  --label "deferred,from-review"
```

## Batch Summary Comment

After all individual thread replies, post ONE summary comment on the PR:

```markdown
## PR Remediation — Cycle {N} Summary

**Commit:** `{sha_short}` | **Findings processed:** {total} | **CI gates:** {count} passed locally

### Fixed ({count})
| Finding | File | Change |
|---------|------|--------|
| {id} | `{file}:{line}` | {one-line} |
| {id} | `{file}:{line}` | {one-line} |

### Deferred ({count})
| Finding | Reason | Issue |
|---------|--------|-------|
| {id} | {reason} | #{issue_number} |

### Acknowledged ({count})
| Finding | Response |
|---------|----------|
| {id} | {one-line} |

### Disagreed ({count})
| Finding | Reason |
|---------|--------|
| {id} | {reason category}: {one-line} |

---
*Local verify: {N} gates, all exit 0 | Threads resolved: {count}/{total}*
```

## Downstream Leverage Created

Each reply creates specific downstream value:

| Reply Type | Leverage |
|-----------|----------|
| **Fixed** | Searchable commit-to-comment link; future grep finds the decision |
| **Deferred** | Backlog item with full context; prioritizable; traceable |
| **Acknowledged** | Bot training signal (Code Quality / Copilot / CodeRabbit); knowledge captured |
| **Disagreed** | Bot training signal (reduces future false positives); documents intentional design |
| **Batch summary** | Release note fragment; audit trail; merge confidence signal |

## Ordering

1. Reply to all **Fixed** threads first (quick, no decisions needed).
2. Create issues for **HUMAN Deferred** items only, then reply with links.
3. Reply to **Acknowledged** threads.
4. Reply to **Disagreed** threads (most thought required).
5. Post the batch summary comment last.
6. Resolve all threads.

## Validation

Before proceeding to convergence check:
- [ ] Every unresolved thread has a reply posted
- [ ] Every `github-code-quality[bot]` / Copilot thread has a canonical reply
- [ ] Every thread is resolved (via GraphQL mutation), including HUMAN (do not merge that PR until decided)
- [ ] Every HUMAN Deferred item has a linked issue
- [ ] Review-thread pagination complete (`hasNextPage` false)
- [ ] Batch summary comment posted on the PR
- [ ] Reply count matches finding count
