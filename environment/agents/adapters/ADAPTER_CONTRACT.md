<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/ADAPTER_CONTRACT.md
layer: contract
owner: governance-control-plane
status: active
version: 1.1.0
updated: 2026-08-12
/L9_META -->

# Adapter contract (from Claude Code gold standard)

Every surface under `environment/agents/adapters/<name>/` must provide the
**same carriers** as the Claude Code gold-standard adapter at
`environment/agents/adapters/claude-code/` (transitional symlink may exist at
`environment/claude-code`). Claude Code is the thicker adapter (hooks, memory
bridge, owned scheduler); thinner adapters catch up via this contract.

| Need | Claude Code carrier | Required in each agents adapter |
|---|---|---|
| **Discover governance** | clone + `.claude/` triad / skills | README setup step that clones or points at `Quantum-L9/Cursor-Governance` |
| **Boot context** | SessionStart hook / bootstrap | `session_bootstrap.md` **or** `agents-block.md` **or** `gemini-block.md` **or** `bootstrap.template.md` |
| **Reach shared memory** | `mcp.template.json` + account env | One of: `mcp.template.json`, `mcp-connector.json`, `settings.template.json`, `config.toml.example` |
| **Identity env** | `web/environment.env.example` | `environment.env.example` with registry-matching `USER_ID` / `L9_MEMORY_AGENT_ID` / `L9_MEMORY_SOURCE` |
| **Network** | `web/network-policy.md` | Point at `docs/network-allowlist.md` (shared) |
| **Autonomy surface** | Profile + settings triad + merge_gate | Cite `ops/autonomy/surface_profile.yaml`; set `L9_GOVERNANCE_SURFACE=<adapter>`; mount Profile `session_start_block` in boot carrier; do not fork doctrine prose |

## Autonomy carrier (binding)

Shared SSOT: [`ops/autonomy/surface_profile.yaml`](../../../ops/autonomy/surface_profile.yaml).

- Env: `L9_AUTONOMY_ENABLED=true`, `L9_GOVERNANCE_SURFACE` matching the adapter name, `L9_AUTONOMY_AUTONOMOUS_MERGE=false`
- Boot text: include or reference Profile `session_start_block` (verbatim via loader preferred)
- Merge forbid: call or document `ops/autonomy/merge_gate.py` semantics
- Cursor is excluded from standing A4 (ask-first retained)

## Memory endpoint (binding)

Cloud Graphiti reachability (same Neo4j store as Cursor's SSH tunnel `:8100`):

```text
https://memory.quantumaipartners.com/graphiti/mcp
```

Auth: `Authorization: Bearer ${GRAPHITI_MCP_TOKEN}` (shared Graphiti plane token).
Writer attribution is **not** the bearer: set distinct `USER_ID` /
`L9_MEMORY_AGENT_ID` / `L9_MEMORY_SOURCE` from `agent_registry.yaml`.
Forbidden: `L9_MEMORY_HTTP_URL`, `L9_MEMORY_CLIENT_TOKEN`, `memory_client`
lifecycle side door (ADR-0006).

Env examples MUST set:

```bash
GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp
GRAPHITI_MCP_TOKEN=REPLACE_WITH_GRAPHITI_MCP_BEARER_TOKEN
```

(or an obvious `REPLACE` / `<angle>` placeholder for the token). Loopback
URLs are CLI-host-only and **must not** be the default in cloud adapter MCP
carriers or env examples.

## Identity (binding)

Values come only from `agent_registry.yaml`. Adapters never invent a second
`agent_id`. Writing identity is distinct from Cursor's `cursor_agent`.
`group_id` stays shared (repo namespace from `ops/graphiti/group_registry.yaml`).

## Executable-peer carriers (Program Execution / autonomy / readiness)

An agent declared **executable** carries three capabilities beyond the memory
contract (Executable Peer Contract v2). They are bindings, not copied files:

1. **Program Execution** — the peer's `execution.bindings` in
   `PEER_RUNTIME_BINDINGS.yaml` map each surface to a registered `worker_host`
   Program Execution adapter. The bound adapter's descriptor carries
   `identity.agent_ref` back to the agent key (the foreign key that replaces
   the old hardcoded adapter→agent map). The surface adapter answers *"how does
   this agent enter L9?"*; the program adapter
   (`environment/program-execution/adapters/<x>/`) answers *"how does the
   Controller execute a task on this host?"*.
2. **Canonical autonomy** — the peer resolves root `autonomy/` through the single
   `root-autonomy-control-plane` provider
   (`environment/program-execution/integrations/autonomy-control-plane/PROVIDER.yaml`,
   `owns_program_state: false`). Copying root `autonomy/` into an adapter is
   forbidden. **E14 exemption:** `adapters/claude-code/autonomy/` is the owned
   Claude bounded-concurrency scheduler (bridged by program-execution); it is
   not a forbidden copy of root `autonomy/`.
3. **Execution readiness** — a fresh, machine-generated readiness receipt per
   `(agent_ref, surface, adapter_id)` binding, produced by
   `probe_executable_peers.py` under `$L9_RUNTIME_ROOT/agents/readiness/`
   (default `~/.l9/agents/readiness/`). Readiness is never statically asserted
   in `agent_registry.yaml` or `PEER_RUNTIME_BINDINGS.yaml`.

`execution.required: true` (in `PEER_RUNTIME_BINDINGS.yaml`) is a strong
assertion: at least one surface is backed by a sealed, non-dormant worker
adapter. Set `required: false` with `bindings: []` for a peer whose worker
adapter is still dormant. `agent_registry.yaml` is identity-only — do not put
`execution:` blocks there. See `environment/agents/PEER_EXECUTION.md` for the
full contract and coverage matrix.

## Validators

`tools/validate_agents.py` enforces the memory-carrier contract for every
**active** thin agent adapter (`make agents-env`). `claude-code` is a thicker
adapter under `adapters/claude-code/` and is validated by `make claude-env`
plus executable-peer rules (E14 exemption for its owned scheduler). `tools/validate_executable_peers.py` enforces the
cross-registry Executable Peer Contract (rules E1-E15) against
`PEER_RUNTIME_BINDINGS.yaml`, and
`environment/program-execution/scripts/probe_executable_peers.py` proves every
`execution.required` peer has a READY binding
(`make peer-execution-conformance` runs the whole chain).
Schema-only gate: `make agents-runtime-bindings-validate`.
