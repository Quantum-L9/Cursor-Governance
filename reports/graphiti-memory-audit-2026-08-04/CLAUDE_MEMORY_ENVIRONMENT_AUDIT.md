# CLAUDE_MEMORY_ENVIRONMENT_AUDIT

Hostile recursive audit of the Cursor-Governance Claude Code custom environment and the Graphiti memory activation chain. Read-only. No source/config/remote mutation occurred.

> **Follow-up (2026-08-04):** RC1 (MEM-001/002) is fixed in this branch — `memory_prefetch.py` now reads `sections` via one-contract client accessors and injects the hydrated content (verified live: hook reported "1 section(s) hydrated" and surfaced the record). The client↔server contract is pinned by `environment/claude-code/tests/test_memory_client_contract.py`, executed by `validate_memory_enforcement.py`. The architecture decision (keep two entry points, unify the contract) is formalized in `docs/decisions/ADR-0003` and `ADR-0004`. RC2 (MEM-003, register `l9-shared-memory` on the managed surface) remains open.

## Executive verdict
**`MULTIPLE_ROOT_CAUSES_CONFIRMED`.** Graphiti memory is inert in a Claude Code session for two independent, each-sufficient reasons, both owned by **Quantum-L9/Cursor-Governance** (the consumer), not by the memory service:

1. **RC1 (HIGH, deterministic):** `memory_prefetch.py` parses the `memory.hydrate` response with the wrong keys (`records`/`hits` instead of `sections`) and never injects the returned `sections` into `additionalContext`. SessionStart therefore always reports "0 record(s) hydrated" and exposes **no** memory content, regardless of server data.
2. **RC2 (HIGH):** the `l9-shared-memory` MCP server is **not registered** in this managed (CCR) environment. The runtime `--mcp-config` contains only account connectors (github, calendar, vercel, anthropic-meta). No `mcp__l9-shared-memory__*` tools exist → no interactive read/write.

The memory **service is healthy** (`l9-graphite-memory 2.2.0`, sqlite store healthy, graphiti projection circuit closed). The `l9-graphiti-memory` repo does **not** own either root cause.

## Exact environment and revisions
| Item | Value |
|---|---|
| Host | Linux vm 6.18.5-fc-v18 x86_64; user `root`; HOME `/root`; cwd `/home/user` |
| Claude Code | 2.1.221 |
| Python (hooks) | 3.11.15 (stdlib-only hooks; `l9_graphite_memory` intentionally not installed locally) |
| **Runtime governance authority** | `/root/.cursor-governance` @ **main `3c9ba5c`** (this is what hooks/skills resolve to) |
| Cursor-Governance working clone | `/home/user/Cursor-Governance` @ branch `claude/graphiti-memory-audit-0vnnuv` `1cccf49` |
| l9-graphiti-memory working clone | `/home/user/l9-graphiti-memory` @ branch `claude/graphiti-memory-audit-0vnnuv` `c0dd23b` |
| Installed memory service | `https://memory.quantumaipartners.com/mcp` → `l9-graphite-memory 2.2.0`, schema 2.1.0 |
| Activation | Managed CCR launcher: `claude --settings /root/.claude/launcher-settings.json --mcp-config /tmp/mcp-config-cse_*.json --add-dir …`; project settings `/home/user/.claude/settings.json` |

**Revision-separation note:** runtime behavior observed here is the **installed_custom_environment** at governance `main@3c9ba5c` + service `2.2.0`. The audit branch `1cccf49` in the working clone carries the *same* `SKILL.md` digest and same hook code paths for the surfaces implicated (verified: SKILL.md sha256 identical between `/root/.cursor-governance` and `/home/user/Cursor-Governance`). No open PR was substituted for default-branch behavior.

## Expected memory architecture (from mcp.template.json, SKILL.md, contract)
- HTTP MCP "control plane" `l9-shared-memory` at `${L9_MEMORY_HTTP_URL}/mcp` with Bearer identity; `alwaysLoad:true`.
- SessionStart prefetch hydrates governed namespace(s) and surfaces context; PreToolUse gate requires a receipt; Stop hook writes a session episode; interactive `mcp__l9-shared-memory__*` tools for on-demand read/write.
- Identity: `group_id` (namespace) shared across agents; write identity derived from bearer (`agent_id=claude-code`).

## Actual installed architecture
- **Two disjoint paths.** (a) Hooks path: `settings.json` SessionStart→`memory_prefetch.py`→`memory_client.py` (stdlib JSON-RPC)→`/mcp`; Stop→`memory_writeback.py`→`memory.ingest`. (b) Interactive MCP path: **absent** (no `l9-shared-memory` in the runtime MCP set).
- Skills: `/home/user/.claude/skills/*` symlink→`/root/.cursor-governance/skills/*`; `l9-graphiti-memory` present, discoverable, and it **did** load this session. `.l9-managed-skills.json` lists it (mode `symlink`).
- Env: `L9_MEMORY_HTTP_URL=https://memory.quantumaipartners.com`, `L9_MEMORY_CLIENT_TOKEN` set, `L9_MEMORY_AGENT_ID=claude-code`. `GRAPHITI_MEMORY_ENABLED` **unset**; `~/.cursor/graphiti.env` **missing** (these belong to the *legacy Cursor* path the SKILL describes, not the active HTTP path).

## Setup and activation trace
- `web/setup.sh` is the *documented* activator (Web/Mobile "paste" flow). In this managed CCR session it is **not** the actual activation path: settings/skills were provisioned (settings.json + skill symlinks + `.l9-managed-skills.json` present), but `setup.sh` step 3.5's `.mcp.json` copy did not apply (no `/home/user/.mcp.json`), and MCP comes from `--mcp-config`. So the "install the memory MCP" step has **no effect** in this environment. GATE_002: partial — settings/skills installed; MCP registration step is a no-op here.

## Skills installation and discovery
- Source skill exists (`skills/l9-graphiti-memory/SKILL.md`), installed via symlink, digest matches source (`03f8885…`), discovered, and activatable (loaded this turn; router recommended it). **No shadowing** copy on the Claude discovery path (other `SKILL.md` copies exist only inside the `l9-graphiti-memory` repo under `skill/` and `tools/phase6/`, which are not on Claude's skill path). GATE_003/004: skill *plumbing* PASS.

## skills/l9-graphiti-memory/SKILL.md doctrine analysis (mandatory surface)
The normative doctrine describes the **legacy Cursor/self-hosted VPS** path, not the active Claude Code HTTP path:
- CLI `python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py …`; config `~/.cursor/graphiti.env`; flags `GRAPHITI_MEMORY_ENABLED`/`GRAPHITI_WRITE_GATES`; SessionStart `session_start_memory_orchestrator.sh`; VPS `46.62.243.82` + SSH tunnel.
- **None** of these are the active runtime: the live path is `memory_prefetch.py`/`memory_client.py` over `L9_MEMORY_HTTP_URL` to `l9-shared-memory` with tools `memory.hydrate/search/ingest/health/…`. SKILL.md never mentions `L9_MEMORY_HTTP_URL`, `l9-shared-memory`, `memory.quantumaipartners.com`, or the `memory.*` tool names. An operator following SKILL.md would (a) see `GRAPHITI_MEMORY_ENABLED` unset and conclude memory is OFF, and (b) attempt to enable/debug a path this environment does not use. **SKILL_DOCTRINE_DRIFT — CONFIRMED (MEDIUM/HIGH).**

## Skill-to-hook wiring
The active SessionStart chain is `session_start_claude_governance.sh` + `memory_prefetch.py` (from `settings.json`). SKILL.md points at `session_start_memory_orchestrator.sh` (Cursor). The skill's operating contract is **not** wired to the hooks that actually run.

## Skill-to-MCP wiring
SKILL.md's tool contract is the legacy CLI subcommands; the active server advertises `memory.*` MCP tools. The interactive MCP that would expose them is unregistered (RC2). So the skill's read/write instructions have no runtime tool to bind to in-session.

## Configuration precedence
Effective config: launcher `--settings /root/.claude/launcher-settings.json` + project `/home/user/.claude/settings.json` (hooks, env, permissions, skillOverrides) + runtime `--mcp-config` (MCP). `~/.claude.json` is empty for projects/MCP. No `.mcp.json`. There is no stale/duplicate hook or skill on the active paths. The one precedence defect is that the **memory MCP registration model (repo `.mcp.json`/user-scope) is outside the precedence chain the launcher actually reads** (`--mcp-config`).

## Hook lifecycle trace
- SessionStart fires both hooks (confirmed: banner text + receipt written this session).
- `memory_prefetch.py` reached the server and returned successfully (receipt `status:prefetched`), i.e. no exception → success branch, not DEGRADED.
- Stop `memory_writeback.py` is gated on a fresh receipt (present) → it **will** attempt `memory.ingest` into `cursor-governance` at session end; failures are swallowed to stderr (fail-open) — masks ingest failures.
- Fail-open is intentional (never block a session) but, combined with RC1, means a *silent* zero-memory session that still reports "ENFORCED."

## Memory orchestration trace
`resolve_namespaces` reads `L9_MEMORY_NAMESPACES` (unset) → falls back to contract `default_namespaces:["cursor-governance"]`. Namespace is a **static default**, not derived from repo/group identity (the `group_registry.yaml` resolver — explicit_env → git_remote_match → path_hint_match — is not used by the claude-code prefetch). In a home-dir workspace with no repo, "cursor-governance" is simply the hardcoded default. Endpoint/transport/auth construction in `memory_client.py` is correct (https-only guard, bearer, streamable-HTTP `data:` frame parsing, exact `memory.*` tool names). The client is sound; the **consumer hook** misuses its result (RC1).

## Client–server contract trace
- `initialize` → `l9-graphite-memory 2.2.0`. `tools/list` advertises `memory.ingest/hydrate/search/health/…` — matches `memory_client.py` names exactly (no tool-name mismatch on the client).
- `memory.health` → sqlite healthy, **records: 11**, projection `graphiti-http-mcp` healthy, circuit closed, `outbox_backlog: 11`.
- `memory.hydrate` → `{sections, tokens_used, …}` (no `records`/`hits`). **This is the exact contract the prefetch hook violates (RC1).**
- `memory.search(cursor-governance)` → `status:complete, hits:[]`, all strategies/stores succeeded → genuine 0 hits for this principal/namespace.

## Runtime reproductions (evidence-bearing)
- **R1 install:** settings+skills installed; MCP registration no-op → PARTIAL.
- **R2 first session:** SessionStart fired, prefetch ran, receipt written, banner "0 record(s) hydrated", **no memory content injected** → FAIL (RC1).
- **R3 skill activation:** `l9-graphiti-memory` skill loaded; but required MCP tools absent → doctrine can't operate (RC2).
- **R4 interactive read:** no memory tools available → cannot retrieve on demand → FAIL (RC2).
- **R6 second session (implicit):** because RC1 discards content and RC2 removes tools, a fresh session cannot surface any prior memory → FAIL.
- **R7 service-unavailable path:** on exception the hook emits a clear DEGRADED banner (good classification) — but the *empty-success* path (RC1) is indistinguishable from "no memory," which is the trap.
- **R8 auth-failure:** `memory_client.rpc` raises `MemoryError(HTTP 401/403)` → prefetch DEGRADED (not silently empty) — this path is correctly classified.

## First failing boundary
`memory.hydrate result → prefetch record-count/context-injection` (`memory_prefetch.py:48-63`). It is the earliest proven incorrect state transition that yields the visible "0 record(s) hydrated" + no content, and it masks any upstream (namespace/data) state. RC2 is a parallel first-failing boundary for the interactive-tools symptom (`activation → MCP registry`).

## Root cause / contributing defects / rejected hypotheses
See `MEMORY_ROOT_CAUSE.md` and `CLAUDE_MEMORY_DEFECT_REGISTER.yaml`.
- **Rejected:** "service down/unreachable" (healthz 200, initialize+health OK); "skill not installed/discoverable" (loaded, digest-matched, in managed manifest); "skill frontmatter invalid" (router routed it, activation validator passes); "tool-name mismatch in memory_client" (names match server); "transport/endpoint wrong in client" (https guard + `/mcp` correct, RPC succeeds); "GRAPHITI_MEMORY_ENABLED unset breaks it" (that flag governs the *legacy* client, not the active hook path — a doctrine artifact, not the runtime gate).

## Validation integrity
`validate_memory_enforcement.py` and `validate_skill_activation.py` both PASS while memory is non-functional: they check file presence, schema/wiring parity against `settings.template.json`, and router fixtures — **never the live memory boundary, hydrate result shape, context injection, or MCP registry.** See `MEMORY_VALIDATION_GAPS.md`.

## Confirmed gaps and cracks (summary)
RC1 schema/injection defect; RC2 missing MCP registration for managed surface; SKILL doctrine drift; static namespace default vs group-registry resolver; fail-open masking (writeback ingest + empty-success prefetch); validators are presence/parity-only.

## Security findings
No secrets exposed in this audit (token redacted throughout; `memory_client.py` never logs the bearer; https-only guard blocks SSRF via mis-set scheme). `.claude/settings.json` correctly keeps secrets out and denies `Read(./.env)`/`Read(./.mcp.json)`. No CRITICAL security issue found.

## Minimal remediation & cross-repo order
All fixes are **Cursor-Governance-owned**; `l9-graphiti-memory` needs no change. See `CLAUDE_MEMORY_REMEDIATION_PLAN.yaml`. Order: fix RC1 (self-contained hook change) → fix RC2 (register MCP on managed surface) → harden validators → optionally reconcile SKILL.md doctrine + namespace resolution.

## Residual unknowns
Where the server's 11 records live and why `cursor-governance` is empty for the `claude-code` principal (service-side data/authorization; BLOCKED without broader authorization; no test write performed against production). Whether prior sessions' Stop-hook `memory.ingest` calls actually persisted into `cursor-governance` (fail-open swallows errors; not provable read-only without a safe test write).

## Final verdict
`MULTIPLE_ROOT_CAUSES_CONFIRMED` — RC1 and RC2 are independently proven and each alone prevents in-session Graphiti memory; the service is exonerated; minimal consumer-side remediation is defined with regression tests.
