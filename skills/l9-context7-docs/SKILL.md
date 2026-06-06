---
name: l9-context7-docs
description: Use Context7 documentation before coding when current library, framework, SDK, API, version-specific behavior, or unfamiliar dependency docs could prevent implementation mistakes, deprecated patterns, or debug loops.
skill_schema: 1
layer: control_plane
role: documentation_grounding
tags: [l9, context7, documentation, libraries, frameworks, sdk, api, current_docs]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-06-06
---

# Context7 Documentation Grounding

## Purpose

Ground implementation decisions in current upstream documentation before writing code when a library, framework, SDK, API, or version-specific behavior matters.

This skill exists to reduce "debug hell": check the docs before the first implementation attempt, not after code fails.

## Auto-Invoke Triggers (mandatory)

**Do not wait for "use context7".** When any trigger matches, load this skill and call Context7 MCP **before** the first implementation edit.

| Domain | Invoke when | Seed `libraryName` |
|--------|-------------|---------------------|
| FastAPI / ASGI | routes, middleware, deps, Pydantic v2, lifespan, OpenAPI | `FastAPI`, `Starlette`, `Pydantic` |
| Neo4j | Cypher, Python driver, graph sync/scoring | `Neo4j Python Driver`, `Neo4j` |
| pytest | fixtures, markers, parametrize, plugins, asyncio tests | `pytest`, `pytest-asyncio` |
| GitHub Actions | workflow YAML, expressions, composite actions, `gh` CLI | `GitHub Actions` |
| New software | unfamiliar SDK, platform, plugin, MCP server, CLI | official product name |
| Dev tooling | Docker, pre-commit, ruff, semgrep, MCP SDK, CI tools | tool's official name |

Also auto-invoke when: version-specific API, migration syntax, deprecated patterns, or errors suggesting stale/wrong API shape.

## When To Use

Use this skill when any of these are true:

- Any **Auto-Invoke Trigger** row above matches the task.
- The task mentions a library, framework, package, SDK, API, plugin, or tool whose current usage may matter.
- The code depends on version-specific behavior, deprecated APIs, migration syntax, or new framework conventions.
- The user asks to integrate, configure, upgrade, migrate, refactor around, or fix code using third-party tooling.
- You are about to add code from memory for a dependency you have not verified in this session.
- Existing errors suggest the likely cause is stale documentation, wrong API shape, wrong config format, or changed defaults.

Skip this skill when:

- The task is purely about local repo code with no external API or dependency behavior.
- The relevant source of truth is a repo rule, local file, or project invariant rather than upstream docs.
- The query would require sending secrets, credentials, personal data, private source code, or proprietary payloads to Context7.

## Context7 MCP Flow

Before calling any MCP tool, read its descriptor/schema from the MCP descriptor files.

Available server:

- `user-Context7`

Tools:

- `resolve-library-id`
- `query-docs`

### Step 1: Resolve Library ID

Call `resolve-library-id` unless the user explicitly provides a Context7 library ID in `/org/project` or `/org/project/version` format.

Required arguments:

```json
{
  "libraryName": "official library or product name",
  "query": "specific implementation task without secrets or proprietary code"
}
```

Select the library by:

- exact or close name match
- relevance to the user's task
- source reputation
- snippet coverage
- benchmark score
- requested version, if provided

Do not call `resolve-library-id` more than 3 times for one question.

### Step 2: Query Documentation

Call `query-docs` with the selected library ID.

Required arguments:

```json
{
  "libraryId": "/org/project",
  "query": "specific implementation question without secrets or proprietary code"
}
```

Do not call `query-docs` more than 3 times for one question.

## How To Apply Results

After reading docs:

1. State the selected library ID and version when relevant.
2. Extract only the rules needed for this task.
3. Compare docs against the repo's existing patterns before editing.
4. Prefer the repo pattern when both are valid; prefer upstream docs when the repo pattern is stale or deprecated.
5. If docs are ambiguous, ask a clarifying question or choose the safest minimal implementation and label uncertainty.
6. Do not paste long documentation dumps into the final response; summarize the actionable constraints.

## Output Discipline

For implementation tasks, keep the docs grounding compact:

```markdown
Context7 checked: `/org/project`
Key constraints:
- {constraint 1}
- {constraint 2}
Applied in: {file or implementation area}
```

If Context7 has no useful match, say so once and continue with repo-grounded evidence.
