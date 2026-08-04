# MEMORY_VALIDATION_GAPS

The two governance validators PASS on this environment while Graphiti memory is non-functional. They validate *shape and wiring parity*, never the *live memory boundary*.

| existing_validator | claimed_guarantee | actual_proof_scope | false_positive_path | missing_negative_case | recommended_hardening |
|---|---|---|---|---|---|
| `validate_memory_enforcement.py` | "memory enforcement contract is valid and wired" | contract JSON-schema conformance; hook basenames present in **settings.template.json**; referenced scripts exist & `py_compile` | A hook that reads the wrong hydrate key (`records`/`hits` vs `sections`) and injects nothing still passes — the validator never calls the server, never inspects a `hydrate` result, never checks `additionalContext` content | (a) fails when hydrate result has no `records`/`hits`; (b) fails when a populated namespace yields `hydrated_records=0`; (c) fails when `additionalContext` lacks section text; (d) fails when `l9-shared-memory` is not in the MCP registry | Add a live-boundary phase: hydrate a known ephemeral test namespace, assert `sections` key + non-zero count + section text in emitted context; assert `claude mcp list` (or `--mcp-config`) contains `l9-shared-memory`; validate the **deployed** `settings.json`, not just the template |
| `validate_skill_activation.py` | "proactive skill activation is structurally and behaviorally sound" | registry freshness (manifest hash); frontmatter name/description; invocation-tier disjointness; router fixtures; router unit tests | The `l9-graphiti-memory` skill routes and loads, but its doctrine targets a transport the environment doesn't use and the tools it prescribes aren't registered — none of that is checked | (a) fails when a SKILL.md references an MCP server/tool name that is not in `mcp.template.json`/contract; (b) fails when a referenced file path in a skill does not resolve on the install surface | Add a doctrine-vs-runtime lint: every server/tool/env name a memory-class skill cites must exist in the active `mcp.template.json`/`memory-enforcement.contract.json`; resolve referenced file paths against the installed skill location |

## Core invariant violated
> "A validator checking file presence cannot prove session memory operation." — both validators do exactly that. Presence + wiring-parity are necessary but not sufficient; neither exercises hydrate result parsing, context exposure, MCP registration, or cross-session persistence.

## Negative-proof checklist the hardened validators must satisfy (currently all missing)
- [ ] fails when the Graphiti skill is missing / frontmatter invalid — *partially covered by activation validator; extend to memory-class doctrine*
- [ ] fails when the skill is installed but not discoverable at the deployed path
- [ ] fails when a required MCP **tool/server name mismatches** the active contract
- [ ] fails when the **MCP server is unregistered** in the runtime (`--mcp-config`/`claude mcp list`)
- [ ] fails when the SessionStart hook is **unregistered in the deployed settings.json**
- [ ] fails when the **endpoint is wrong** / unreachable (distinct from empty)
- [ ] fails when **authentication is invalid** (401/403), not silently "empty memory"
- [ ] fails when **hook output is malformed** / not valid SessionStart JSON
- [ ] fails when **prefetch parses the wrong result key** (the MEM-001 case)
- [ ] fails when **hydrated content is not injected** into `additionalContext` (the MEM-002 case)
- [ ] fails when **writeback ingest does not persist** (round-trip in a test namespace)
