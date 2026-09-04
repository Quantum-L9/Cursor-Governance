<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/README.md
layer: doc
owner: governance-control-plane
status: active
version: 1.1.0
updated: 2026-07-31
/L9_META -->

# environment/agents — L9 Multi-Agent Environment

One work environment replicated across every LLM surface; one shared memory;
unique agent IDs; role-scoped work; no overlap, no duplication.

**Claude Code stays at `environment/agents/adapters/claude-code/`** (thicker peer of
`environment/ide/`). This pack thickens Manus / Codex / Gemini / generic to
the same deployable contract (`adapters/ADAPTER_CONTRACT.md`).

Live memory: `https://memory.quantumaipartners.com` — see `docs/DEPLOY.md`.

## Layout

```
environment/agents/
├── agent_registry.yaml        # SSOT: WHO writes memory (identity + role)
├── DESIGN.md                  # architecture and binding contracts
├── HANDOFF.md                 # session handoff / resume context
├── docs/
│   ├── DEPLOY.md              # operator checklist (validate → C1 → surfaces)
│   ├── MEMORY_TOPOLOGY.md     # Option A LIVE HTTPS topology
│   ├── network-allowlist.md   # egress hosts for cloud sandboxes
│   └── WORK_CLAIM_PROTOCOL.md # anti-duplication claim protocol
├── adapters/
│   ├── ADAPTER_CONTRACT.md    # three-carrier contract (from claude-code)
│   ├── cursor/                # active — thin Cursor-IDE binding (install + receipt + SessionStart spec)
│   ├── manus/                 # active — connector + env + bootstrap + setup
│   ├── codex/                 # active — MCP + config.toml + AGENTS block
│   ├── gemini/                # active — settings + GEMINI block + setup
│   └── generic/               # onboarding template for any future surface
└── tools/
    ├── render_principals.py   # registry + local tokens -> auth_tokens.json
    ├── validate_agents.py     # N-agent validator (`make agents-env`)
    └── test_validators.py     # self-test suite
```

Existing surfaces are unchanged: Cursor keeps `.cursor-commands` +
`ops/graphiti`; Claude Code keeps `environment/agents/adapters/claude-code/`. Their registry
entries record deployed identities (`legacy_token_env`) so nothing breaks.

**Workspace-group contract (aligned with the hardened `ops/graphiti` gate):**
the shared workspace group is `igor-workspace` — the same value as
`ops/graphiti/group_registry.yaml`'s `workspace_group`, and the two files
must never diverge. On the deployed MCP stack, direct
`graphiti_memory_client.py write` to that group is rejected unconditionally
(only bootstrap's integration-edge mirror writes there), explicit `group_id`
overrides that contradict the resolved repo match fail closed, and path
hints match whole path segments only. Server-side namespace grants rendered
by `tools/render_principals.py` apply to the planned `l9-graphiti-memory`
control-plane server and do not bypass that gate — see `DESIGN.md` §6.

## Quick start (operator)

```bash
# 1. Validate the registry and adapters
python3 environment/agents/tools/validate_agents.py

# 2. Issue tokens (one per agent, >=24 chars, NEVER committed)
#    ~/.config/l9-memory/agent_tokens.local.json: {"manus": "...", ...}

# 3. Render server principals and deploy per docs/MEMORY_TOPOLOGY.md
#    --registry/--tokens/--out are RELATIVE paths under trusted roots only.
python3 environment/agents/tools/render_principals.py \
  --root environment/agents \
  --out-dir ~/.config/l9-memory \
  --registry agent_registry.yaml \
  --tokens agent_tokens.local.json \
  --out auth_tokens.json

# 4. Wire each surface using its adapters/<name>/README.md
```

## Adding an agent

Follow `adapters/generic/README.md`: one registry entry → validate → one
token → render → one env block + bootstrap. Nothing else is hand-edited.

## Integration notes (for the PR)

Suggested branch `feat/multi-agent-environment`. CANONICAL_LAW §2 adapter
table gains rows for Manus (active), Codex/Gemini (planned), sourced from
this registry. `Makefile` gains `agents-env: python3
environment/agents/tools/validate_agents.py`. CI job mirrors it. No existing
file is modified other than those two touch points; tokens never enter git.
