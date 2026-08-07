<!-- L9_META
l9_schema: 1
origin: folded from governance-v2 dev-systematic-debugging
tags: [debugging, root-cause, bisect, isolation]
status: active
/L9_META -->

# Systematic Debugging

Debug methodically with evidence, not by randomly changing code. Five-step loop:

1. **Reproduce** — get exact trigger steps, expected vs actual, confirm it's consistent (not flaky), record environment. If you can't reproduce it, you can't fix it — ask for details.
2. **Isolate** — narrow where the bug lives:
   - *Binary search the codebase*: disable half the system → does it persist? Recurse into the half that still fails.
   - *Git bisect*: `git bisect start; git bisect bad; git bisect good <sha>` → test each midpoint → `git bisect good|bad` → `git bisect reset`.
   - *By layer*: frontend vs backend (network tab) vs DB (query directly) vs API (curl) vs component (render in isolation).
3. **Hypothesize** — form one specific, testable claim: "X is caused by Y because Z" (e.g. "`userId` is null because auth middleware doesn't run on this route"), not "something's wrong with the data".
4. **Test the hypothesis** — smallest possible probe (log/breakpoint at the suspected spot, inspect the suspect variable). Wrong → return to step 3 with new info. Right → you've found it.
5. **Fix and verify** — apply the minimal fix, confirm the original repro no longer triggers, check for regressions, and add a test that would have caught it.

## Tool-by-scenario

| Scenario | Tactic |
|---|---|
| "It worked before" | `git bisect` |
| "Don't know where this runs" | log entry/exit of suspect functions |
| "Data looks wrong" | inspect at each transformation step |
| "Only fails in prod" | compare env/versions, check logs, repro locally with prod-like data |
| "Intermittent" | look for race conditions, timing, uninitialized state |
| "Useless error" | grep the codebase for where that error is thrown |

## Common patterns
Off-by-one (indices/pagination/date ranges); null/undefined (missing optional chaining); race conditions; stale closures; type coercion (`==` vs `===`); missing `await`; environment mismatch.

## Rules
Never guess — verify with evidence. Fix the root cause, not the symptom. After 15 minutes without progress, step back and re-isolate. Record what you tried so you don't repeat failed approaches.
