<!-- L9_META
l9_schema: 1
origin: folded from governance-v2 dev-parallel-exploring, dev-codebase-onboarding, dev-parallel-code-review
tags: [parallel, subagents, explore, onboarding, review]
status: active
/L9_META -->

# Parallel Subagent Patterns

Launch multiple read-only `explore` subagents in a single message so they run concurrently, each owning one area. Use for broad work where one sequential pass is slow or misses categories. For a single focused question, use Grep/SemanticSearch directly instead.

## Pattern A — Parallel exploration

Break the codebase into logical zones (frontend, backend, infra, shared) and launch one `explore` agent per zone in one message. Each agent has its own context window, so it can read many files. Use `thoroughness: "very thorough"` for comprehensive analysis. Synthesize into: tech-stack summary, data-flow description, key entry points, tech-debt concerns.

Cross-cutting variant: for "where is X handled?", launch agents at each layer (route guards, middleware, storage) simultaneously, then merge.

## Pattern B — Codebase onboarding document

Spawn 5 `explore` agents, one each for: (1) Architecture & structure, (2) Data models & DB, (3) API routes & endpoints, (4) Auth & authorization, (5) Deployment & infra. For monorepos add one agent per app/package. Synthesize into an opinionated `ONBOARDING.md`: quick-start commands, architecture, data models, API reference, auth, deployment, "start here" files, and gotchas (easy-to-miss env vars, required system deps).

## Pattern C — Four-lens parallel review

For large or risky diffs, scope the change set (`git diff --name-only <base>...HEAD`) and launch **four** `explore` subagents (`readonly: true`) in one message, each reviewing only the listed files from one lens:

- **Security** — injection (SQL/shell/XSS), authZ/authN gaps, secrets, unsafe deserialization, path traversal, SSRF, IDOR, dependency CVEs.
- **Performance** — N+1 queries, missing indexes, O(n²) loops, bundle/render impact, sync I/O on hot paths, unbounded caches.
- **Correctness** — logic/off-by-one bugs, edge cases, race conditions, error-handling gaps, breaking API changes, test gaps.
- **Readability** — naming, duplication, abstraction boundaries, unclear control flow, missing types/docs (suggestions over nitpicks).

Each returns Critical/High/Medium/Low findings as `file:line + short fix`. Main agent de-duplicates (count once at worst severity), orders by severity then fix cost, and emits a 5-bullet executive summary + actionable list. Fix only approved items via targeted non-readonly follow-ups. Complements — does not replace — human/compliance sign-off.

## Guardrails

- Keep review/explore agents read-only so parallel runs never fight over writes.
- If two agents would touch the same files, merge sequentially after the parallel pass.
- Split huge diffs by directory and run a second wave rather than cramming unrelated megadiffs into one pass.
