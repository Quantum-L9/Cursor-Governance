# GMP-GRAPHITI — Deep Diagnosis (blockers · gaps · misalignments)

**ID:** GMP-GRAPHITI | **Task:** Graphiti memory-layer deep diagnosis from this machine | **Tier:** INFRA_TIER | **Date:** 2026-06-30 | **Status:** ✅ COMPLETE (read-only)

---

## EXECUTIVE VERDICT

**`CRITICAL`**

Graphiti's **infrastructure is up** (tunnel OPEN, LaunchAgent loaded, `/healthcheck` 200, circuit CLOSED, group resolves correctly, gate logic passes, dry-runs build cleanly) — **but the MCP tool plane is not served**: every tool call (`search`, `stats`, `write`) returns **HTTP 404** at `http://127.0.0.1:8100/mcp`. Graphiti therefore **cannot read or write** → BLOCKER-class failure → `CRITICAL` per Phase-4 rule. The root cause is a **MISALIGNMENT** (server up, `/mcp/` route not serving MCP tools), not missing secrets and not a dead tunnel.

- **Ground-truth deviation (documented):** GMP literal `GOV="$HOME/.cursor-governance"` is only a logs dir on this machine. Real wired SSOT used: `GOV="$HOME/Dropbox/cursor governance/GlobalCommands"` (git clone on `main`, symlinked by `~/.cursor/*`). Authority Order #2 (ground truth > doc).
- **MEMORY_PREFETCH:** skipped — G5 not healthy; `conflicts`/`search` return 404, so prefetch would be untrustworthy. No episodes cited (honestly unavailable).

---

## EVIDENCE MATRIX (secrets masked)

| ID | Layer | Status | Exit | 1-line evidence |
|----|-------|--------|------|-----------------|
| G1 | Config completeness | 🟠 GAP | 0 | `MEMORY_ENABLED=SET, MCP_URL=SET, SSH_HOST=SET, TUNNEL_PORT=SET`; **`MCP_TOKEN=EMPTY`**; `NEO4J_URI/NEO4J_PASSWORD/OPENAI_API_KEY=MISSING` (server-side/Keychain) |
| G2 | Tunnel port | ✅ PASS | 0 | `127.0.0.1:8100` → **OPEN** |
| G3 | Tunnel LaunchAgent | ✅ PASS | 0 | `com.cursor.graphiti-tunnel` loaded (PID 67685) + plist present |
| G4 | Liveness | ✅ PASS | 0 | `GET /healthcheck` → `{"status":"healthy"}` HTTP 200 |
| G5 | Two-plane health | 🟡 MISALIGN | 1 | `healthy:false, liveness_ok:true, tools.reachable:false` → server up, tool-plane not served |
| G6 | Tool plane | 🔴 BLOCKER | 1 | `tools.reachable:false`, `HTTP 404 {"detail":"Not Found"}`, endpoint `http://127.0.0.1:8100/mcp`; no tool_count |
| G7 | Group resolution | ✅ PASS | 0 | `group_id=cursor-governance, method=registry, readonly=false` |
| G8 | Registry integrity | ✅ PASS | 0 | SSOT origin `https://github.com/cryptoxdog/Cursor-Governance.git` matches pattern `*/Cursor-Governance*` (see MISALIGN note) |
| G9 | Circuit breaker | ✅ PASS | 0 | `circuit.state=CLOSED, failure_count=0` |
| G10 | Read/search round-trip | 🔴 BLOCKER | 0 | `WARN: search tool calls failed … HTTP 404` (both `cursor-governance` + `igor-workspace`); results `[]` |
| G11 | Graph stats (Neo4j) | 🔴 BLOCKER | — | `ERROR: HTTP 404` — Neo4j path unreachable via tool plane |
| G12a | Write path (dry-run) | ✅ PASS | 0 | `write --dry-run` + `bootstrap --dry-run` built payloads, **no mutation** |
| G12b | Live round-trip | ⚪ N/A | — | `RUN_LIVE` not set → opt-in skipped (no live writes, per lock) |
| G13 | Write gates + logic | ✅ PASS | 0 | `WRITE_GATES=0` (GAP by choice); `OK: graphiti gate E2E full passed` |
| G14 | Hook integration | ✅ PASS | 0 | 6 graphiti hooks registered, all scripts exist + executable |
| G15 | memory-bank scaffold | 🟠 GAP | — | no `memory-bank/` in workspace or SSOT (not scaffolded here) |
| G16 | Env drift vs example | 🟡 MISALIGN | 0 | missing `MEMORY_DISTILL_TOKEN_BUDGET`; extra `GRAPHITI_SSH_KEYCHAIN_SERVICE` |

**Health:** `healthy=false liveness=true tool_plane=false circuit=closed`
**Internal consistency (Phase 4):** `healthy == liveness_ok && tools.reachable` → `false == (true && false)` ✅ consistent.

---

## 🔴 BLOCKERS (3 — single root cause: MCP tool-plane 404)

1. **Tool plane unreachable (G6)** — *what:* MCP tool calls 404. *evidence:* health `tools.error = "HTTP 404: {\"detail\":\"Not Found\"}"`, `endpoint http://127.0.0.1:8100/mcp`; raw probes: `/healthcheck`→200 but `/`, `/mcp`, `/mcp/`→404. *remediation:* on VPS `46.62.243.82`, (re)start the Graphiti MCP server so it serves the streamable-HTTP MCP route at `/mcp/`; verify the container/process exposing `/mcp/` is running and routed (reverse-proxy/uvicorn mount). *severity:* CRITICAL.
2. **Search read fails (G10)** — *what:* `search_facts`/`search_nodes` 404. *evidence:* `WARN: search tool calls failed … HTTP 404`. *remediation:* resolves once G6 is fixed. *severity:* CRITICAL (no recall).
3. **Graph stats / Neo4j path fails (G11)** — *what:* `stats` 404. *evidence:* `ERROR: HTTP 404`. *remediation:* resolves once G6 is fixed; then confirm the MCP server reaches Neo4j (server-side creds). *severity:* CRITICAL (no graph proof).

> All three share one fix: restore the MCP tool-plane route on the VPS. Liveness proves the host+tunnel are fine; only the tool mount is missing.

---

## 🟠 GAPS (3)

1. **`GRAPHITI_MCP_TOKEN=EMPTY` (G1)** — *impact:* if the MCP server later enforces bearer auth, calls will 401 even after the route is restored. Not the current 404 cause, but should be set. *remediation:* populate `GRAPHITI_MCP_TOKEN` in `~/.cursor/graphiti.env` (or Keychain) with the server's Cursor token.
2. **Write gates OFF (G13, `WRITE_GATES=0`)** — *impact:* advisory prefetch only; Write/Shell not gated. Intended default (see `98-graphiti-memory-gate.mdc`). *remediation:* none unless GATES-002 enforcement is desired (`GRAPHITI_WRITE_GATES=1`).
3. **No `memory-bank/` scaffold (G15)** — *impact:* T0 resume SSOT absent in this workspace/SSOT. *remediation:* run `setup_workspace_symlinks.sh` from the workspace root to scaffold the 4 files.

---

## 🟡 MISALIGNMENTS (3)

1. **Headline — MCP path not serving tools (G5)** — *expected:* `GET/POST /mcp/` serves the MCP tool plane. *observed:* `/healthcheck`→200 but `/mcp/`→404; client normalizes env `…/mcp/` to `…/mcp` (both 404). *fix:* align the served route with the configured `GRAPHITI_MCP_URL` (`/mcp/`) on the VPS.
2. **Workspace remote org drift (G8)** — *expected:* registry canonical `cryptoxdog/Cursor-Governance`. *observed:* open editing clone origin `git@github.com:Quantum-L9/Cursor-Governance.git` (org `Quantum-L9`); SSOT clone correctly `cryptoxdog`. Glob pattern `*/Cursor-Governance*` still matches so resolution works, and `bootstrap --dry-run` picked up the `Quantum-L9` remote. *fix:* reconcile the editing clone's origin to `cryptoxdog` or add `Quantum-L9` to the registry if intentional.
3. **Env drift vs example (G16)** — *expected:* env superset of `graphiti.env.example` required keys. *observed:* missing `MEMORY_DISTILL_TOKEN_BUDGET`; extra `GRAPHITI_SSH_KEYCHAIN_SERVICE` (Keychain-backed SSH — explains why NEO4J/OPENAI aren't in the env file). *fix:* add `MEMORY_DISTILL_TOKEN_BUDGET` (or update the example if the Keychain model deprecates it).

---

## UNKNOWNS (not evidenced)

- **Neo4j direct reachability & auth** — only observable through the MCP tool plane, which is 404; no local Neo4j driver probe attempted (no client-side `NEO4J_URI`). Unknown until G6 restored.
- **Graph contents** (episode/fact/node counts, conflicts) — unknowable while tools 404.
- **Whether `MCP_TOKEN`/`NEO4J`/`OPENAI` are supplied via `graphiti_env_loader.py`/Keychain at runtime** — the loader + `graphiti.env.defaults` exist (untracked in SSOT) but were not exercised; env-file status reported as-is.

---

## PHASE 5 — RECURSIVE VERIFY (no drift)

- SSOT tracked porcelain: **10 entries — identical to prior baseline** → zero tracked drift introduced.
- `~/.cursor/graphiti-state/e2e-test.json`: **absent** (gate self-test cleaned up); only per-session generation state + `default.json` remain (pre-existing runtime state, not created here).
- G12b live round-trip: not run → no `sandbox-diag` group created.
- Open workspace: untouched (HEAD `4aad3f1`). New artifact: only this report.

---

## SMALLEST NEXT ACTION

SSH to the VPS (`46.62.243.82`) and restart the Graphiti MCP server so it serves the tool plane at `/mcp/`; confirm with `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8100/mcp/` returning a non-404 and then `python3 "$GOV/ops/graphiti/graphiti_memory_client.py" health` → `"healthy": true`.

---

## DECLARATION

```
GMP-GRAPHITI COMPLETE — CRITICAL
Health: healthy=f liveness=t tool_plane=f circuit=closed
Group: cursor-governance (registry, readonly=false)
Blockers: 3 | Gaps: 3 | Misalignments: 3
Repo drift: NONE (Phase 5 verified)
Next action: Restart the Graphiti MCP server on VPS 46.62.243.82 so /mcp/ serves the tool plane, then re-run health until healthy:true
```
