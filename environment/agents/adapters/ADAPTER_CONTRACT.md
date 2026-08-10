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

## Program Execution binding (peer-execution cross-link)

Beyond the three memory carriers, each adapter declares **which Program
Execution adapter the Controller uses to execute a task on this surface** via a
`program-execution.yaml` file in the adapter directory:

```yaml
schema: l9.agent-program-execution-binding.v1
agent_id: codex          # matches agent_registry.yaml (or a template id)
surface: codex
binding_kind: agent      # or "template" for copy-me generic onboarding
program_execution:
  enabled: true
  adapters: [codex-cloud]   # ids in EXECUTION_ADAPTER_REGISTRY.yaml
```

The surface adapter answers *"how does this agent enter L9?"*; the named
program adapter (`environment/program-execution/adapters/<x>/`) answers *"how
does the Controller execute a task on this host?"*. The binding must agree with
the agent's `program_execution` block in `agent_registry.yaml`, and the named
program adapters must exist in the execution registry. See
`environment/agents/PEER_EXECUTION.md` for the full contract.

## Validator

`tools/validate_agents.py` enforces the memory-carrier contract for every
**active** agent whose `adapter` is not `cursor` or `claude-code`
(`make agents-env`). `tools/peer_execution_conformance.py` enforces the
cross-registry peer-execution contract, and `tools/peer_execution_probe.py`
proves every executable peer is ready (`make peer-execution-conformance` /
`make peer-execution-probe`).
