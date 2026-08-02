# Protocol A — Parallel non-dependent fan-out

## Purpose

Execute independent ready work concurrently via Cursor `Task` subagents without conflicting writes.

## Rules

1. Build a Phase-0 action list **before** any Task launch.
2. Each action declares: `id`, `depends_on[]`, `mutation` (true|false), `lock_keys[]`, `isolation_key` (if mutation), `kind` (`work` | `poll`).
3. Dependency readiness comes only from `depends_on` — never guess.
4. Two actions may run in parallel only if: all dependencies are done; no shared write lock; under lane budget (**max 4** total Tasks, **max 2** mutation).
5. Conflicting write locks serialize. Distinct `isolation_key` values permit isolated mutation lanes (`best-of-n-runner` or worktree-scoped prompts).
6. **Launch all ready `work` Tasks in a single assistant message.** Serializing independent ready work is a protocol violation.
7. Each Task prompt includes: exact objective, allowed files, forbidden files, validation command, return schema.
8. Return schema (required):

```yaml
status: done | blocked | failed
files_touched: [paths]
evidence: string
blockers: [string]
```

9. After returns: if file overlap or lock conflict appears, serialize merge of results; do not claim join success until resolved.
10. For independent CI job failures, reuse `skills/l9-ci-ops/references/parallel-ci-triage.md` (one Task per independent job).

## Lane budget

| Kind | Cap |
|---|---|
| Total concurrent Tasks | 4 |
| Mutation Tasks (`mutation: true`) | 2 |
| Read-only / poll | Fill remaining lanes |
