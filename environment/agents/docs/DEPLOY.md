<!-- L9_META
l9_schema: 1
repo: Quantum-L9/Cursor-Governance
path: environment/agents/docs/DEPLOY.md
layer: doc
owner: governance-control-plane
status: active
version: 1.0.0
updated: 2026-07-31
/L9_META -->

# Deploy checklist — multi-agent memory (Option A live)

Claude Code stays at `environment/claude-code/`. This checklist wires every
**other** registry agent onto the same control plane.

## Already live (operator ground truth)

| Item | Value |
|---|---|
| Public URL | `https://memory.quantumaipartners.com` |
| MCP path | `/mcp` |
| C1 service | `l9-memory-server` → `127.0.0.1:8200` |
| TLS | Caddy on C1 |
| Auth | Bearer principals from `auth_tokens.json` |
| Local tokens | `~/.config/l9-memory/agent_tokens.local.json` (mode 600, never git) |

## 1. Validate pack

```bash
make -C "$HOME/.cursor-governance" agents-env
# or:
python3 environment/agents/tools/validate_agents.py
python3 environment/agents/tools/test_validators.py
```

Expect: validator PASS; self-tests all pass.

## 2. Issue / refresh per-agent tokens (local)

```bash
# ~/.config/l9-memory/agent_tokens.local.json — one unique ≥24-char token per agent_id
# Keys must match registry agent keys: cursor, claude-code, manus, codex, gemini
python3 environment/agents/tools/render_principals.py \
  --root environment/agents \
  --out-dir "$HOME/.config/l9-memory" \
  --registry agent_registry.yaml \
  --tokens agent_tokens.local.json \
  --out auth_tokens.json
```

## 3. Sync principals to C1 (requires explicit human approval)

```bash
# ONLY after operator says approved — copies auth_tokens.json to the server
scp -i ~/.ssh/Hetzner-C1-nopass \
  "$HOME/.config/l9-memory/auth_tokens.json" \
  root@46.62.243.82:/opt/l9-memory/config/auth_tokens.json
ssh -i ~/.ssh/Hetzner-C1-nopass root@46.62.243.82 \
  'systemctl restart l9-memory-server && curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8200/healthz'
```

## 4. Wire each surface

| Agent | Adapter README | Paste |
|---|---|---|
| Claude Code | `environment/claude-code/web/` (unchanged path) | env + `setup.sh` |
| Manus | `adapters/manus/README.md` | env + connector + bootstrap |
| Codex | `adapters/codex/README.md` | env + config.toml / MCP + AGENTS block |
| Gemini | `adapters/gemini/README.md` | env + settings merge + GEMINI block |

Identity values must match `agent_registry.yaml`. Token = that agent's own
bearer only.

## 5. Smoke test (per agent)

```bash
# Unauth must 401; authed MCP initialize/tools path must succeed
curl -sS -o /dev/null -w "%{http_code}\n" https://memory.quantumaipartners.com/healthz
curl -sS -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer <WRONG>" \
  https://memory.quantumaipartners.com/mcp
```

Then from the surface: call a memory read/search tool; confirm episodes
attribute to that agent's `user_id` / `agent_id`, never `cursor_agent`.
