# Graphiti Machine Env Policy

**Problem:** `graphiti.env.example` looks like something you copy per repo — but secrets cannot travel with git clones, and requiring manual setup on every clone is not sustainable.

**Solution:** Three-layer config where **repo clones need zero graphiti env files**.

---

## Layer model

| Layer | Location | In git? | When set |
|-------|----------|---------|----------|
| **L0 Defaults** | `ops/graphiti/graphiti.env.defaults` | Yes (GlobalCommands) | Never edit per machine — safe URLs/ports/hosts |
| **L1 Machine** | `~/.cursor/graphiti.env` | No | Once per Mac |
| **L2 Secrets** | `~/.cursor/secrets/graphiti.env` OR Keychain | No | Once per Mac |
| **L3 Repo** | `.env.local` `C1_SSH` only (optional) | No (gitignored) | Per repo if no machine SSH key |

**Repo clones:** Wire symlinks → sessionStart bootstrap → Graphiti works if L1/L2 exist on that Mac.

---

## What clones do NOT need

- No `graphiti.env` in repo root
- No copying `graphiti.env.example` into the project
- No `GRAPHITI_MCP_TOKEN` in repo files
- No manual tunnel command if bootstrap + LaunchAgent configured

---

## One-time machine setup

```bash
# Step 1 — machine env (idempotent)
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/init_graphiti_machine_env.sh"

# Step 2 — store MCP token (pick ONE)
security add-generic-password -a "$USER" -s graphiti-mcp-token -w "YOUR_VPS_TOKEN"
# OR: edit ~/.cursor/secrets/graphiti.env

# Step 3 — SSH key (pick ONE)
# Place key at ~/.ssh/Hetzner-C1-nopass (chmod 600)
# OR keychain: graphiti-c1-ssh-key
# OR gitignored repo .env.local C1_SSH (auto-extracted on session start)

# Step 4 — hooks (once)
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/install_cursor_hooks_bootstrap.sh"
```

---

## Per-repo clone (only this)

```bash
git clone ...
cd repo
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/setup_workspace_symlinks.sh"
# OR: open in Cursor — sessionStart bootstrap auto-wires symlinks
```

Graphiti env is inherited from the Mac — not recreated per clone.

---

## How loading works

**Python** (`graphiti_memory_client.py`):

1. `graphiti_env_loader.load_graphiti_env()`
2. Apply `DEFAULTS` (non-secret)
3. Load `~/.cursor/graphiti.env` if present
4. Load `~/.cursor/secrets/graphiti.env` if present
5. Keychain fallback for `GRAPHITI_MCP_TOKEN`

**Bash hooks** (`graphiti_common.sh`, `ensure_graphiti_tunnel.sh`):

1. Source `graphiti.env.defaults`
2. Source machine + secrets files
3. Keychain token fallback

---

## VPS vs Mac secrets

| Variable | Mac | VPS |
|----------|-----|-----|
| `GRAPHITI_MCP_URL` | `http://127.0.0.1:8100/mcp/` | N/A |
| `GRAPHITI_MCP_TOKEN` | Keychain or secrets file | `/opt/graphiti-cursor/graphiti.env` |
| `OPENAI_API_KEY` | **Never** | VPS only |
| `NEO4J_PASSWORD` | **Never** | VPS only |
| SSH key | `~/.ssh/` or keychain | N/A |

---

## Verify after clone

```bash
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
python3 -c "import sys; sys.path.insert(0,'.cursor-commands/ops/graphiti'); from graphiti_env_loader import env_status; import json; print(json.dumps(env_status(),indent=2))"
```

---

## Anti-patterns

| Don't | Do instead |
|-------|------------|
| Commit `graphiti.env` to any repo | Machine + keychain |
| Copy example into each clone | `init_graphiti_machine_env.sh` once |
| Put VPS `OPENAI_API_KEY` on Mac | VPS `graphiti.env` only |
| Require `/start-session` before env exists | `sessionStart` bootstrap + defaults |

---

*Related: `CURSOR-GRAPHITI-INSTANTIATION-BRIEF.md`, `graphiti.env.example`, `init_graphiti_machine_env.sh`*
