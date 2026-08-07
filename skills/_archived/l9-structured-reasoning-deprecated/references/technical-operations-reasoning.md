<!-- L9_META
l9_schema: 1
parent: l9-structured-reasoning
origin: migrated-from profiles/reasoning_technical_operations.md v2.1
sources: [profiles/reasoning_technical_operations.md]
tags: [reasoning, tool-selection, api-evaluation, mcp, architecture-decision]
status: active
/L9_META -->

# Technical Operations Reasoning

Reasoning for **tool selection, API integration, and architecture evaluation** grounded in the actual
codebase. Use when the decision is "which tool / library / service / approach", not "why is this
broken" (→ [systematic-debugging.md](systematic-debugging.md)) and not "how deep should I think"
(→ [reasoning-modes.md](reasoning-modes.md)).

Loop: **Align → Hydrate → Analyze → Decide → Implement**

## Block 1 — Define the objective

- Restate the task or decision in your own words.
- What does success look like functionally?
- Constraints: time, scale, legacy systems, compliance.
- Expected artifact: decision memo, code scaffold, config?

## Block 2 — Hydrate codebase context

Read the architecture; do not infer it.

| Need | Tool |
|---|---|
| Project shape | `Glob` on `**/*` or read the tree |
| Locate a concern | `Grep` for `docker`, `auth`, `env`, the library name |
| Load specifics | `Read` on infra, config, API files |

Scan for: `package.json`, `pyproject.toml`/`requirements.txt`, `Dockerfile`, `terraform/`,
`.env.template`, `.github/`, `infra/`, `api/`.

## Block 3 — Decompose

- Split the decision into parts: integration, compatibility, performance, security, observability.
- Name the evaluation points ("Tool A or Tool B for this endpoint?").
- Map which services, files, interfaces, pipelines it touches.
- List unknowns — what is *not* in the repo that might matter.

Every engineering problem is several problems wearing one name.

## Block 4 — Choose evaluation lenses

Pick the protocol that matches the risk (see Protocols below). Evaluate against: latency,
modularity, security, vendor lock-in, ecosystem maturity. Weigh team skillset and prior tooling —
`Grep` for libraries already in use before introducing a new one.

## Block 5 — Execute the analysis

- `Read` the relevant service files, configs, prior decisions.
- `Grep` existing usage of the candidate tool or pattern.
- Compare real implementations across services.
- Assess integration complexity and blast radius.
- State assumptions explicitly where context is missing.

The answer is often already written in the repo — search before speculating.

## Block 6 — Synthesize the recommendation

Present: recommended path, trade-offs, confidence (1–10). Provide a short form ("Use X because Y")
plus long-form rationale, and name the files to create or change. If the decision is architectural
and durable, write it up via `l9-architecture-decision-records`.

## Block 7 — Validate against stress cases

- Behavior under load.
- Cost of partial failure.
- Rollback and observability path.
- Are the assumptions confirmed by the codebase?
- "What breaks if this ships today?"

## Block 8 — Plan codebase actions

New files, modified configs, init scripts. Document dependencies, affected services, next steps.

## Block 9 — Identify operational risks

Blast radius on production failure. New runtime, security, or dependency risk. How it is monitored,
logged, escalated. Precedent or prior failure pattern in the repo.

Operational debt is invisible until it hurts.

## Block 10 — Team fit and maintainability

- Will the team support this over time? Does it match current tooling?
- Does it increase onboarding complexity or add unfamiliar patterns?
- **Will the next agent session understand why this choice was made?**
- Is the rationale recorded where it will be found?

## Protocols

### Tool selection

Meets current requirements · aligns with team skillset · maintained and documented · ecosystem
maturity · reasonable performance footprint · licensing and security reviewed.

### MCP tool selection

**Before using any MCP tool — enumerate, do not grab the first that works.**

1. **List** — all tools on that server (`GetMcpTools` with the server id).
2. **Compare** — what each does, what shape it returns, cost.
3. **Match** — which fits the Block 1 objective and returns the right data structure.
4. **Validate** — does existing usage or config support this choice?
5. **Execute** — state why this tool, and what was rejected.

Worked example — "extract structured data from docs":

| Tool | Output | Best for |
|---|---|---|
| `firecrawl_scrape` | Markdown | Reading docs |
| `firecrawl_extract` | Structured JSON per schema | **Queryable data ✅** |
| `firecrawl_map` | URL list | Discovery |
| `firecrawl_crawl` | Many pages | Large sites |

Objective is a structured knowledge base → `firecrawl_extract`, because it returns JSON against a
declared schema. `scrape` would force re-parsing prose.

### API integration

Clear docs and versioning · sandbox or mock mode · stable auth and retry behavior · idempotency and
observability · known issues · compatible with current services.

### Technology evaluation

Aligns with system architecture · supports rollout and rollback · low vendor lock-in · scalable on
current infra · supports logging and monitoring · healthy community.

## Closing rule

Reason transparently, ground every claim in codebase evidence, and plan the integration. Think in
paths and decisions, not abstractions. **Never rush to the first tool that works — enumerate,
compare, then choose.**
