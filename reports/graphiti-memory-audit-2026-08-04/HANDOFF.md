# HANDOFF — Graphiti memory environment audit

## What was audited
The Claude Code custom-environment + Graphiti memory activation chain across **Quantum-L9/Cursor-Governance** (consumer/governance) and **Quantum-L9/l9-graphiti-memory** (service), at the exact revisions running in this managed (CCR) session. Traced end to end: activation → skills → config precedence → SessionStart hooks → memory client → live server contract → context injection → interactive tools → writeback. `skills/l9-graphiti-memory/SKILL.md` was read and treated as normative doctrine.

## Exact root-cause status
**`MULTIPLE_ROOT_CAUSES_CONFIRMED`.** Two independent, each-sufficient consumer-side defects; the memory service is healthy and exonerated.

- **RC1 (MEM-001/002, CONFIRMED):** `environment/claude-code/hooks/memory_prefetch.py` reads `records`/`hits` from a `memory.hydrate` result that only carries **`sections`**, and never injects `sections` into `additionalContext`. → SessionStart always says "0 record(s) hydrated" and surfaces no memory. Proven by live server response, server source (`budget.py:90`), and the on-disk receipt (`hydrated_records:0`).
- **RC2 (MEM-003, CONFIRMED):** `l9-shared-memory` MCP is **not registered** in this managed environment. Runtime `--mcp-config` = {github, calendar, vercel, anthropic-meta×2}; `claude mcp list` empty; no `.mcp.json`. → No `mcp__l9-shared-memory__*` tools; no interactive read/write.

First failing boundary: `memory.hydrate result → prefetch count/injection` (`memory_prefetch.py:49-63`); RC2 is a parallel first-failing boundary at `activation → MCP registry`.

## Graphiti skill status
Installed (symlink, digest `03f8885…`), discoverable, and activatable (loaded this session; router recommended it). **But** its doctrine (MEM-004) describes the legacy Cursor/VPS path (`.cursor-commands` CLI, `~/.cursor/graphiti.env`, `GRAPHITI_MEMORY_ENABLED`, VPS `46.62.243.82`, `session_start_memory_orchestrator.sh`) — not the active HTTP MCP path — so operating it as written does not drive the real memory path, and the tools it prescribes aren't registered (RC2). Plumbing PASS; effectiveness FAIL.

## Confirmed defects
MEM-001 (hydrate schema misread, HIGH), MEM-002 (no context injection, HIGH), MEM-003 (MCP unregistered, HIGH), MEM-004 (SKILL doctrine drift, MED/HIGH), MEM-005 (validator false-positive, MED). Suspected: MEM-006 (static namespace default). Blocked: MEM-007 (11 store records but cursor-governance empty for this principal — service-side).

## Repository ownership
All fixes are **Cursor-Governance-owned**. **l9-graphiti-memory needs no change** (contract-correct, healthy). MEM-007 is a service-side data/identity inventory question for the memory operators.

## Files requiring change
- `environment/claude-code/hooks/memory_prefetch.py` (FIX-1)
- managed-environment connector config + `environment/claude-code/web/setup.sh` / `mcp.template.json` (FIX-2)
- `environment/claude-code/validate_memory_enforcement.py`, `validate_skill_activation.py` (FIX-3)
- `skills/l9-graphiti-memory/SKILL.md` (FIX-4)
- `environment/claude-code/memory/memory_state.py` (FIX-5)

## Safe implementation order
1. FIX-1 hook parse+inject (self-contained, unblocks memory-into-session).
2. FIX-2 register `l9-shared-memory` on the managed surface (unblocks interactive tools) — verify with `claude mcp list`, not file presence.
3. FIX-3 harden validators so 1&2 can't regress green.
4. FIX-4 SKILL doctrine + FIX-5 namespace resolver.
5. INV-1 service-side inventory of the 11 records / claude-code authorization.

## Exact validation sequence (must fail pre-fix, pass post-fix)
1. Unit: sections-bearing hydrate fixture → count>0 and section text present in `additionalContext`.
2. Integration: live hydrate against a populated ephemeral test namespace via the SessionStart hook.
3. Environment: `claude mcp list` (or `--mcp-config`) contains `l9-shared-memory`; a memory tool is callable in-session.
4. Negative cases from `MEMORY_VALIDATION_GAPS.md` (missing MCP, wrong tool name, auth 401, malformed hook output, non-persistent writeback).

## Remaining unknowns
- Where the server's 11 records live and why `cursor-governance` is empty for the `claude-code` bearer (service-side; needs authorization).
- Whether prior Stop-hook `memory.ingest` writes persisted (fail-open swallows errors; not provable read-only).

## Approval boundaries
Governance source edits, managed-connector config, and any test write to the shared production memory plane require explicit human approval. The governed `memory.*` surface exposes no delete tool, so no cleanup path exists for a probe record — hence **no test write was performed**.

## No-mutation confirmation
No source edit, no config edit, no git add/commit/push, no PR, and no write to the memory service occurred during this audit. All findings are from read-only inspection and read-only (health/list/search/hydrate) protocol probes. Deliverables were written only to the session scratchpad (`scratchpad/audit_out/`).
