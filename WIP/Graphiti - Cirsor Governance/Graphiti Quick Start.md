<!-- L9_META
l9_schema: 1
parent: l9-graphite-memory
layer: docs
role: quickstart
tags: [setup, install, onboarding]
owner: platform
status: active
version: 1.0.0
updated: 2026-07-05
/L9_META -->

# Quick Start

Get L9 Graphite Memory running in under 5 minutes.

## Prerequisites

- Python 3.10+
- An [Infisical](https://infisical.com) machine identity (Universal Auth) with access to your project
- A [Zep Cloud](https://www.getzep.com) API key stored in Infisical under the key `ZEP_API_KEY`

## 1. Clone and Install

```bash
git clone https://github.com/Quantum-L9/L9-Graphite-Memory.git
cd L9-Graphite-Memory
pip install -e ".[all]"
```

## 2. Set Bootstrap Environment Variables

Only three variables are needed on the machine. Everything else comes from the Infisical vault at runtime.

```bash
export INFISICAL_CLIENT_ID="your-machine-identity-client-id"
export INFISICAL_CLIENT_SECRET="your-machine-identity-client-secret"
export INFISICAL_PROJECT_ID="your-infisical-project-id"
```

## 3. Run Pre-flight Check

```bash
bash scripts/preflight.sh
```

All 8 gates should pass (or pass with warnings if Zep key is vault-only).

## 4. Wire Your Agent

**Cursor:**
```bash
python scripts/write_cursor_config.py
```

**Claude Desktop:**
```bash
python scripts/write_claude_config.py
```

Both scripts write the MCP server entry to the agent's config file. Restart the agent to connect.

## 5. Verify

In your agent, call the `health` tool:

```
Use the l9-graphite-memory health tool
```

Expected response:
```json
{
  "healthy": true,
  "transport": "zep",
  "version": "0.2.0"
}
```

## One-Shot Install (Alternative)

If you prefer a single command that does steps 1-4:

```bash
bash scripts/install.sh
```

## Available MCP Tools

| Tool | Description |
|------|-------------|
| `search` | Query the knowledge graph for facts |
| `write` | Write episodes/facts to the graph |
| `health` | Check connectivity and status |
| `bootstrap` | Seed a group with repo manifest data |
| `phase_lock` | Run conflict check and grant GMP phase lock |
| `conflicts` | Check for conflicting facts in a group |

## Activate Memory in Another Repo

To install memory hooks and rules in a target repository:

```bash
bash scripts/activate_gate.sh /path/to/target-repo
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `INFISICAL_CLIENT_ID not set` | Export the 3 bootstrap vars |
| `zep-python not installed` | `pip install l9-graphite-memory[zep]` |
| `Transport unhealthy` | Check `ZEP_API_KEY` is in Infisical vault |
| `rate limited` | Wait 2 seconds between writes (circuit breaker) |

## Next Steps

- Read [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design
- Read [docs/custom-ontology.md](docs/custom-ontology.md) to extend the knowledge graph schema
- Read [docs/adr/](docs/adr/) for architectural decision records
