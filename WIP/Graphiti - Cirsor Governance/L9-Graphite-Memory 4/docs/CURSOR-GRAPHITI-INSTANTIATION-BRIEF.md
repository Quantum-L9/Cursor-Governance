# Graphiti Instantiation in Cursor — Requirements Brief

**Purpose:** Checklist of everything required for Graphiti memory to load in Cursor (tunnel → health → prefetch → memory-bank).  
**Authority:** `ops/graphiti/DEPLOY.md`, `03-graphiti-memory.mdc`, `CANONICAL_LAW.md`  
**Updated:** 2026-06-24

---

## 1. VPS (C1 Hetzner — one-time)

| # | Requirement | Detail |
|---|-------------|--------|
| 1.1 | **Host reachable** | `46.62.243.82` (SSH as `root`) |
| 1.2 | **Install path** | `/opt/graphiti-cursor` |
| 1.3 | **Docker stack running** | `docker compose --env-file graphiti.env up -d` |
| 1.4 | **Graphiti MCP bound loopback** | `127.0.0.1:8100` on VPS |
| 1.5 | **VPS `graphiti.env` secrets** | `OPENAI_API_KEY`, `GRAPHITI_MCP_TOKEN`, Neo4j password — never commit |
| 1.6 | **Healthcheck green on VPS** | `curl -sf -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8100/healthcheck` |
| 1.7 | **L9 decommissioned** | No port conflict with archived `/opt/l9` stack |

---

## 2. Mac — SSH tunnel (required every session unless LaunchAgent)

| # | Requirement | Detail |
|---|-------------|--------|
| 2.1 | **SSH private key** | One of: `~/.ssh/Hetzner-C1-nopass`, keychain service `graphiti-c1-ssh-key`, or repo `.env.local` `C1_SSH` (extracted at runtime) |
| 2.2 | **Key permissions** | `chmod 600` on key file |
| 2.3 | **Tunnel command** | `ssh -N -L 8100:127.0.0.1:8100 -i $KEY root@46.62.243.82` |
| 2.4 | **Local port open** | `127.0.0.1:8100` reachable (`nc -z 127.0.0.1 8100`) |
| 2.5 | **Auto-ensure (recommended)** | `ops/hooks/ensure_graphiti_tunnel.sh` — called by `sessionStart` bootstrap hook |
| 2.6 | **Always-on (optional)** | `GRAPHITI_TUNNEL_AUTOSTART=1` in `~/.cursor/graphiti.env` → LaunchAgent `com.cursor.graphiti-tunnel` via `setup_workspace_symlinks.sh` |

---

## 3. Mac — `~/.cursor/graphiti.env` (machine-level — NOT per repo)

**Repo clones do not need a graphiti env file.** See `docs/MACHINE-ENV-POLICY.md`.

One-time per Mac:

```bash
bash .cursor-commands/ops/scripts/init_graphiti_machine_env.sh
```

| Layer | Path | Purpose |
|-------|------|---------|
| L0 Defaults | `graphiti.env.defaults` | Auto-loaded safe URLs/ports (in git) |
| L1 Machine | `~/.cursor/graphiti.env` | Optional overrides |
| L2 Secrets | `~/.cursor/secrets/graphiti.env` or Keychain | `GRAPHITI_MCP_TOKEN` |

---

## 4. Governance wiring (required for hooks + CLI paths)

| # | Requirement | Command / path |
|---|-------------|----------------|
| 4.1 | **Dropbox GlobalCommands SSOT** | `$HOME/Dropbox/Cursor Governance/GlobalCommands/` |
| 4.2 | **Repo symlink** | `.cursor-commands` → GlobalCommands |
| 4.3 | **User symlinks** | `~/.cursor/skills`, `~/.cursor/commands`, `~/.cursor/rules` → GlobalCommands |
| 4.4 | **Wire script** | `bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh` |
| 4.5 | **Bootstrap installer (no symlinks yet)** | `bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/install_cursor_hooks_bootstrap.sh"` |

---

## 5. Cursor hooks (required for sessionStart prefetch)

| # | Requirement | Detail |
|---|-------------|--------|
| 5.1 | **`~/.cursor/hooks.json`** | `sessionStart` → `./hooks/session-start-bootstrap.sh` |
| 5.2 | **Bootstrap hook (real file)** | `~/.cursor/hooks/session-start-bootstrap.sh` — not a symlink |
| 5.3 | **Tunnel ensure** | Bootstrap calls `ensure_graphiti_tunnel.sh` before health |
| 5.4 | **Memory orchestrator** | Bootstrap delegates to `session_start_memory_orchestrator.sh` |
| 5.5 | **sessionEnd** | `graphiti-session-end.sh` + `governance-backup.sh` registered |
| 5.6 | **sessionStart orchestrator** | `session-start-memory-orchestrator.sh` in hooks (prefetch + memory-bank excerpt) |

Registered automatically by `setup_workspace_symlinks.sh` or `install_cursor_hooks_bootstrap.sh`.

---

## 6. Repo memory-bank (T0 resume — required)

| # | Requirement | Detail |
|---|-------------|--------|
| 6.1 | **`memory-bank/` directory** | Repo root — scaffolded by wire script or bootstrap |
| 6.2 | **`activeContext.md`** | T0 SSOT — read on sessionStart, written on sessionEnd |
| 6.3 | **Template source** | `ops/graphiti/memory-bank-template/` |
| 6.4 | **Git policy** | PlasticOS: tracked; other repos: local unless `group_registry.yaml` says otherwise |

---

## 7. Group resolution (required for writes; reads use fallback)

| # | Requirement | Detail |
|---|-------------|--------|
| 7.1 | **`group_registry.yaml`** | `ops/graphiti/group_registry.yaml` — maps repo → `group_id` |
| 7.2 | **Repo match** | Git remote or path hint must match a registry entry, or set explicit env |
| 7.3 | **Forbidden groups** | Never use: `main`, `default`, `test`, empty string |
| 7.4 | **Fallback** | Unmatched repos → `igor-workspace` readonly (reads OK, writes blocked) |

Add repo entry to `group_registry.yaml` for full read/write (e.g. Enrichment.Inference.Engine).

---

## 8. CLI + verification (prove instantiation)

Run from repo root after tunnel + env:

```bash
# 1. Tunnel
bash .cursor-commands/ops/hooks/ensure_graphiti_tunnel.sh

# 2. Health (liveness + MCP tools)
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health

# 3. Group resolve
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py resolve

# 4. Session prefetch (same as hook)
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py inject "session start"

# 5. Full wiring gate
bash .cursor-commands/ops/scripts/check_governance_wiring.sh "$(pwd)"

# 6. Gate E2E (optional, pre-GATES-002 flip)
bash .cursor-commands/ops/graphiti/test_gate_e2e_full.sh
```

**Healthy instantiation:** `health` → `liveness_ok: true` and `tools.reachable: true`.  
**Degraded (tunnel only):** `liveness_ok: true` but MCP 404 — fix VPS MCP route or URL trailing slash.

---

## 9. Rules + skills (agent behavior)

| Asset | Path |
|-------|------|
| Graphiti memory rule | `.cursor-commands/rules/03-graphiti-memory.mdc` |
| Graph layer boundary | `.cursor-commands/rules/97-graph-layer-boundary.mdc` |
| Graphiti memory gate | `.cursor-commands/rules/98-graphiti-memory-gate.mdc` |
| Skill | `.cursor-commands/skills/l9-graphiti-memory/SKILL.md` |

---

## 10. Minimal first-time setup (copy-paste)

```bash
# Machine bootstrap (once — no repo symlinks needed)
bash "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/install_cursor_hooks_bootstrap.sh"

# Client env
cp "$HOME/Dropbox/Cursor Governance/GlobalCommands/ops/graphiti/graphiti.env.example" ~/.cursor/graphiti.env
# Edit: GRAPHITI_MCP_TOKEN, GRAPHITI_SSH_KEY, GRAPHITI_TUNNEL_AUTOSTART=1

# SSH key (if using repo .env.local C1_SSH — or place key at ~/.ssh/Hetzner-C1-nopass)

# Per repo
cd /path/to/repo
bash .cursor-commands/ops/scripts/setup_workspace_symlinks.sh   # or auto-wired by sessionStart bootstrap

# Verify
python3 .cursor-commands/ops/graphiti/graphiti_memory_client.py health
```

Reload Cursor — new chats trigger `sessionStart` bootstrap (wire → tunnel → health → prefetch → memory-bank).

---

## 11. Common failure modes

| Symptom | Fix |
|---------|-----|
| `Connection refused` on 8100 | Start tunnel: `bash ~/.cursor/graphiti-tunnel.sh` |
| `HTTP 404` on `/mcp` | Check VPS MCP route; use `GRAPHITI_MCP_URL=http://127.0.0.1:8100/mcp/` |
| `fallback_readonly` group | Add repo to `group_registry.yaml` or set explicit group env |
| Hooks not firing | Run `install_cursor_hooks_bootstrap.sh`; reload Cursor |
| No prefetch context | Confirm `GRAPHITI_MEMORY_ENABLED=1` and `sessionStart` in `~/.cursor/hooks.json` |
| Write gates blocking | `GRAPHITI_WRITE_GATES=0` until GATES-002 soak complete |

---

*See also: `DEPLOY.md`, `GATES-002-ACTIVATION.md`, `MEMORY_BANK_POLICY.md`*
