<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/ADAPTER_CONTRACT.md
layer: contract
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Adapter contract (from Claude Code gold standard)

Every surface under `environment/agents/adapters/<name>/` must provide the
**same three carriers** that `environment/claude-code/` already ships. Claude
Code itself stays at `environment/claude-code/` (preexisting peer of
`environment/ide/`); this contract is how the thinner adapters catch up.

| Need | Claude Code carrier | Required in each agents adapter |
|---|---|---|
| **Discover governance** | clone + `.claude/` triad / skills | README setup step that clones or points at `Quantum-L9/Cursor-Governance` |
| **Boot context** | SessionStart hook / bootstrap | `session_bootstrap.md` **or** `agents-block.md` **or** `gemini-block.md` **or** `bootstrap.template.md` |
| **Reach shared memory** | `mcp.template.json` + account env | One of: `mcp.template.json`, `mcp-connector.json`, `settings.template.json`, `config.toml.example` |
| **Identity env** | `web/environment.env.example` | `environment.env.example` with registry-matching `USER_ID` / `L9_MEMORY_AGENT_ID` / `L9_MEMORY_SOURCE` |
| **Network** | `web/network-policy.md` | Point at `docs/network-allowlist.md` (shared) |

## Memory endpoint (binding)

Production control plane (non-secret):

```text
https://memory.quantumaipartners.com
```

MCP path: `/mcp`. Auth: `Authorization: Bearer ${L9_MEMORY_CLIENT_TOKEN}`.
Each agent uses **its own** token (`L9_MEMORY_TOKEN__<AGENT>` issued into
`~/.config/l9-memory/agent_tokens.local.json`, rendered into server
`auth_tokens.json`). Never share tokens across agents. Never commit tokens.

Env examples MUST set:

```bash
L9_MEMORY_HTTP_URL=https://memory.quantumaipartners.com
L9_MEMORY_CLIENT_TOKEN=REPLACE_WITH_MEMORY_CLIENT_BEARER_TOKEN
```

(or an obvious `REPLACE` / `<angle>` placeholder for the token). Loopback
URLs are local-only and **must not** be the default in any adapter MCP
carrier or env example.

## Identity (binding)

Values come only from `agent_registry.yaml`. Adapters never invent a second
`agent_id`. Writing identity is distinct from Cursor's `cursor_agent`.
`group_id` stays shared (repo namespace from `ops/graphiti/group_registry.yaml`).

## Executable-peer carriers (Program Execution / autonomy / readiness)

An agent declared **executable** carries three capabilities beyond the memory
contract (Executable Peer Contract v1). They are bindings, not copied files:

1. **Program Execution** — the agent's `execution.bindings` in
   `agent_registry.yaml` map each surface to a registered `worker_host`
   Program Execution adapter. The bound adapter's descriptor carries
   `identity.agent_ref` back to the agent key (the foreign key that replaces
   the old hardcoded adapter→agent map). The surface adapter answers *"how does
   this agent enter L9?"*; the program adapter
   (`environment/program-execution/adapters/<x>/`) answers *"how does the
   Controller execute a task on this host?"*.
2. **Canonical autonomy** — the peer resolves `autonomy/` through the single
   `root-autonomy-control-plane` provider
   (`environment/program-execution/integrations/autonomy-control-plane/PROVIDER.yaml`,
   `owns_program_state: false`). Copying an `autonomy/` implementation into an
   adapter is forbidden.
3. **Execution readiness** — a fresh, machine-generated readiness receipt per
   `(agent_id, surface, adapter_id)` binding, produced by
   `probe_executable_peers.py` under `$HOME/.l9/programs/_peer-readiness/`.
   Readiness is never statically asserted in `agent_registry.yaml`.

`execution.enabled: true` is a strong assertion: at least one surface is backed
by a sealed, non-dormant worker adapter. Set `enabled: false` with
`bindings: []` for a peer whose worker adapter is still dormant. See
`environment/agents/PEER_EXECUTION.md` for the full contract and coverage
matrix.

## Validators

`tools/validate_agents.py` enforces the memory-carrier contract for every
**active** agent whose `adapter` is not `cursor` or `claude-code`
(`make agents-env`). `tools/validate_executable_peers.py` enforces the
cross-registry Executable Peer Contract (rules E1-E15), and
`environment/program-execution/scripts/probe_executable_peers.py` proves every
enabled peer has a READY binding (`make peer-execution-conformance` runs the
whole chain).
