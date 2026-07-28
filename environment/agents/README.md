<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/README.md
layer: doc
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-28
/L9_META -->

# environment/agents — L9 Multi-Agent Environment

One work environment replicated across every LLM surface; one shared memory;
unique agent IDs; role-scoped work; no overlap, no duplication.

## Layout

```
environment/agents/
├── agent_registry.yaml        # SSOT: WHO writes memory (identity + role)
├── DESIGN.md                  # architecture and binding contracts
├── HANDOFF.md                 # session handoff / resume context
├── docs/
│   ├── WORK_CLAIM_PROTOCOL.md # anti-duplication claim protocol
│   └── MEMORY_TOPOLOGY.md     # one server, N surfaces (routable HTTPS)
├── adapters/
│   ├── manus/                 # active — connector + env + bootstrap
│   ├── codex/                 # planned — config.toml + AGENTS.md block
│   ├── gemini/                # planned — settings.json + GEMINI.md block
│   └── generic/               # onboarding template for any future surface
└── tools/
    ├── render_principals.py   # registry + local tokens -> auth_tokens.json
    ├── validate_agents.py     # N-agent validator (wire as `make agents-env`)
    └── test_validators.py     # self-test suite (7/7 passing)
```

Existing surfaces are unchanged: Cursor keeps `.cursor-commands` +
`ops/graphiti`; Claude Code keeps `environment/claude-code/`. Their registry
entries record deployed identities (`legacy_token_env`) so nothing breaks.

## Quick start (operator)

```bash
# 1. Validate the registry and adapters
python3 environment/agents/tools/validate_agents.py

# 2. Issue tokens (one per agent, >=24 chars, NEVER committed)
#    ~/.config/l9-memory/agent_tokens.local.json: {"manus": "...", ...}

# 3. Render server principals and deploy per docs/MEMORY_TOPOLOGY.md
python3 environment/agents/tools/render_principals.py \
  --registry environment/agents/agent_registry.yaml \
  --tokens ~/.config/l9-memory/agent_tokens.local.json \
  --out ~/.config/l9-memory/auth_tokens.json

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
