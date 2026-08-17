<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: code_review_agents
tags: [pr, review, github-code-quality, copilot, replies]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-16
/L9_META -->

# Code-Review Agents

## Purpose

Treat selected GitHub review bots as **code-review agents**, not optional scanner chatter. Every comment they leave must be inspected, validated against current source, fixed when valid, and replied to. Silent skip is a protocol violation.

This class exists because GitHub Code Quality and Copilot code review post **inline PR review comments**. They are not Sonar/CodeQL API clusters and they are not skippable bot discussion.

## Membership (closed set)

Match on `user.login` / `author.login` (with or without the `[bot]` suffix):

| Login | Product | Finding type |
|-------|---------|--------------|
| `github-code-quality[bot]` | GitHub Code Quality | Rules-based CodeQL quality findings on the PR diff. Comments carry severity **Error**, **Warning**, or **Note**, often with an autofix suggestion. |
| `copilot[bot]` | GitHub Copilot code review | AI-powered review comments (legacy login). |
| `copilot-pull-request-reviewer[bot]` | GitHub Copilot code review | AI-powered review comments (current login). |

Do **not** invent extra members. CodeRabbit, Gemini, `github-actions[bot]`, SonarCloud, and unknown logins stay on the ordinary bot/human path in [signal-ingestion.md](signal-ingestion.md).

If Copilot is not enabled, `github-code-quality[bot]` is still a full member. Absence of Copilot comments does not relax this protocol.

## Mandatory path (every comment)

For each unresolved thread or issue comment from a member:

1. **Ingest.** Capture id, thread id, path, line, body, severity label if present, suggestion block if present. Do not pre-filter on "actionable body", `nit:`, Note severity, or coverage/overview wording.
2. **Inspect.** Read the cited file and surrounding current source. Comment snippets and autofix patches are not ground truth ([SKILL.md](../SKILL.md) Law 9).
3. **Analyze.** Classify ownership (`CODEBASE` / `CI_PIPELINE` / `ENVIRONMENT` / `HUMAN` / `FALSE_POSITIVE`) then validity: confirmed defect, already fixed, false positive, or human decision.
4. **Fix if validated.** Confirmed `CODEBASE` findings enter this cycle's concurrent batch. Apply an autofix only after it is correct on current source. Do not weaken gates or suppress to close the thread.
5. **Reply always.** Every member comment gets a canonical reply (Fixed / Deferred / Acknowledged / Disagreed) per [review-replies.md](review-replies.md). Volume is not an exemption.

`skip_bot_discussions` does **not** apply to this class. A Note, nit, coverage overview, or "have you considered" comment from a member is still inspected and replied to. It may be Acknowledged or Disagreed; it may not be dropped.

## Severity (Code Quality only)

`github-code-quality[bot]` labels are advisory for priority, not a skip switch:

| Label | Default disposition when validated |
|-------|-----------------------------------|
| **Error** | `actionable` — fix this cycle unless ownership is HUMAN / CI_PIPELINE |
| **Warning** | `actionable` — fix this cycle when the change is local and correct |
| **Note** | inspect; fix when the suggestion is correct and low-risk; otherwise reply Acknowledged or Disagreed |

A ruleset quality gate may already block merge on Error/Warning. That does not excuse unanswered Notes.

Copilot comments have no severity label. Treat each as `actionable` until inspection proves otherwise, then reply.

## Surfaces

Ingest all three. Do not stop at reviews with `CHANGES_REQUESTED`.

```bash
# Inline review comments (primary Code Quality surface)
gh api repos/{owner}/{repo}/pulls/{pr}/comments --paginate \
  --jq '.[] | select(.user.login|test("github-code-quality|copilot"; "i")) | {id, user: .user.login, path, line, body, created_at}'

# Review summaries
gh api repos/{owner}/{repo}/pulls/{pr}/reviews --paginate \
  --jq '.[] | select(.user.login|test("github-code-quality|copilot"; "i")) | {id, user: .user.login, state, body}'

# Issue comments on the PR
gh api repos/{owner}/{repo}/issues/{pr}/comments --paginate \
  --jq '.[] | select(.user.login|test("github-code-quality|copilot"; "i")) | {id, user: .user.login, body, created_at}'
```

Then walk GraphQL `reviewThreads` and keep every unresolved thread whose first comment author is a member — including threads the REST "actionable body" filter would have dropped.

Check-run annotations from a Code Quality check are extra evidence, not a substitute for comment threads. If a finding exists only as an annotation, fix it when validated; reply only when a thread exists.

## Merge gate

CRA membership does **not** define the GitHub merge gate. Converge must not squash-merge while **any** GraphQL `reviewThreads` node has `isResolved: false` — any author, including `github-advanced-security` / CodeQL re-files after a push.

A CRA member thread also still needs a canonical `<!-- l9-remediation:... -->` reply.

Diagnose must list unanswered member comments as review blockers.

## Completeness check

- [ ] Every member login present on the PR is attributed as `code_review_agent` (not `human`, not skippable chatter)
- [ ] Comment count for members matches ingested finding count (no actionable-body drop)
- [ ] Each member finding has inspect + validity + ownership
- [ ] Validated codebase findings are in the cycle batch
- [ ] Each member thread has a canonical reply
