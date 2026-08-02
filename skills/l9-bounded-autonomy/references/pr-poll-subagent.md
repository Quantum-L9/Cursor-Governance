# Protocol B — PR-poll subagent while main continues

**Centerpiece.** Waiting on CI **releases compute** but preserves locks (`waiting_external_*` in pr-convergence). Cursor maps that to a background poll Task; the main agent continues other work.

## When to spawn

- Any open PR that needs CI watch, review triage, conflict watch, or remediation-to-green.
- Any time the main agent would otherwise wait on CI / `gh pr checks --watch`.
- Multiple PRs → **one background poll Task per PR** (lock `pr:<n>`), within lane budget.

## Exact Cursor spawn contract

```text
Tool: Task
run_in_background: true
subagent_type: generalPurpose
description: "PR #<n> poll/remediate"
prompt: <from references/prompt-templates.md poll_worker; includes campaign authorization packet fields>
```

## Poll worker responsibilities

1. Loop: status → checks → comments → conflicts (babysit / pr-babysitting structure).
2. On in-scope CI failure **and** an active campaign authorization packet covering this PR: remediate via `l9-pr-remediation` / Cursor `babysit` — scoped fix → push → recheck. Cap **3** fix-push cycles then escalate to main with blockers.
3. Without a packet: **watch-only**; escalate proposed fixes to main for approval.
4. Never force-push; never merge; never weaken tests for green; never change CI workflows to hide failures; never expand campaign scope.
5. **Notify main only on:** check status change (pending→fail/pass), new actionable review comment, conflict introduced, terminal merge-eligible, or escalation. No no-op spam.

## Main-agent continue contract (non-negotiable)

After spawning poll Task(s), the main agent **immediately**:

- Continues Phase-0 ready work, user questions, or other non-conflicting Tasks.
- Does **not** poll the same PR itself in parallel (avoids duplicate pushes).
- Does **not** call `AwaitShell` waiting on the poll worker.
- Does **not** block the main turn on CI when a poll worker can own it — that is a **protocol violation**.
- May briefly check poll output later when joining, or when the user asks “status?”
- Treats the poll worker as owning lock `pr:<n>` until join or explicit hand-back.

## Poll cadence

- Prefer event-driven updates when GitHub MCP `subscribe_pr_activity` is available.
- Else exponential backoff: 30s → 60s → 120s cap.
- After 30 minutes with no state change: notify main (still watching / escalate).

## Anti-patterns

- Main agent blocking the turn on CI for a PR that has a poll worker.
- One poll worker watching multiple unrelated PRs (split them).
- Main and poll both pushing to the same branch.
- Claiming “merge-ready” before the poll worker reports terminal + join checklist.
- Using the word “envelope” for campaign authority (use **packet**).
