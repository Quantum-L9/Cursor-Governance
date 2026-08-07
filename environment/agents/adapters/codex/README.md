<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/adapters/codex/README.md
layer: adapter
owner: governance-control-plane
status: active
version: 1.1.0
updated: 2026-07-31
/L9_META -->

# Codex Adapter — L9 governance node on OpenAI Codex (cloud + CLI)

Registry identity: `agents.codex` (`agent_id=codex`, `user_id=codex_agent`,
role `implementer`, **active**). Contract: `../ADAPTER_CONTRACT.md`.

| Need | Carrier |
|---|---|
| Skill discovery | git-tracked `AGENTS.md` in each governed repo |
| Boot context | `agents-block.md` appended to `AGENTS.md` |
| Shared memory | `mcp.template.json` / `config.toml.example` + `environment.env.example` |
| Network | `docs/network-allowlist.md` |
| Operator steps | **`setup.md`** |
| Autonomy surface | `ops/autonomy/surface_profile.yaml` via `agents-block.md` + env |

## Autonomy

Codex mounts the shared Autonomy Surface Profile (CANONICAL_LAW §6.1): standing
A4 when `L9_GOVERNANCE_SURFACE=codex` and `L9_AUTONOMY_ENABLED=true`. Merge
remains human-only (`ops/autonomy/merge_gate.py` semantics). See
`../ADAPTER_CONTRACT.md` autonomy carrier.

## Setup

1. Prerequisite: live memory `https://memory.quantumaipartners.com` (`docs/DEPLOY.md`).
2. Issue `L9_MEMORY_TOKEN__CODEX`, render principals, sync to C1.
3. CLI: merge `config.toml.example` into `~/.codex/config.toml` and export env
   from `environment.env.example`.
4. Cloud: same env + MCP from `mcp.template.json`.
5. Append `agents-block.md` to governed repos' `AGENTS.md`.

## Role limits (implementer)

Code implementation and PR remediation in `assigned_groups` only. Must claim
before starting (`WORK_CLAIM_PROTOCOL.md`); no promotion; writes with
`user_id=codex_agent`, `source=codex` only.
