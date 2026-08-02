# Worked examples

## Example 1 — Poll PR while main continues (especially)

**Phase-0**

| id | kind | depends_on | mutation | lock_keys | notes |
|---|---|---|---|---|---|
| packet | — | — | — | — | Create campaign authorization packet covering PR #44 |
| poll-44 | poll | [] | false | pr:44 | Background poll/remediate |
| draft-plan | work | [] | true | docs/next-plan.md | Unrelated ready work |

**Execute**

1. Create packet (`created_by: /autonomy`).
2. In one turn: spawn `Task` with `run_in_background: true` for poll-44 using `poll_worker` template.
3. **Immediately** continue draft-plan (or other ready work) on main — do not AwaitShell on poll; do not `gh pr checks --watch` on #44.
4. When joining: read poll terminal report; run merge-gate checklist; ask human to merge if eligible.

**Violation:** main sits on CI for #44 while poll-44 exists.

---

## Example 2 — Parallel CI jobs + background poll

**Context:** PR #99 failing `lint` and `test` independently.

| id | kind | depends_on | mutation | lock_keys |
|---|---|---|---|---|
| fix-lint | work | [] | true | src/a.ts |
| fix-test | work | [] | true | src/b.test.ts |
| poll-99 | poll | [fix-lint, fix-test] | false | pr:99 |

**Execute**

1. Create packet for PR #99.
2. Launch fix-lint and fix-test as parallel Tasks in **one** message (no shared locks).
3. After both return done: spawn background poll-99; main continues other ready work or user Q&A.
4. Poll remediates residual CI under packet (≤3 cycles) or escalates.
5. Join → merge gate → human merge.
