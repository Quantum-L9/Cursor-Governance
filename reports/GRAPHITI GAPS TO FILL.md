GMP-GRAPHITI complete. All phases ran read-only; signed report at `reports/GMP-Report-GRAPHITI-20260630.md`.

## Verdict: `CRITICAL`

Graphiti's **infrastructure is healthy** but the **MCP tool plane is dead** — so it can neither read nor write. That's a BLOCKER-class failure → `CRITICAL` per the Phase-4 rule.

**Health:** `healthy=false · liveness=true · tool_plane=false · circuit=closed`
**Group:** `cursor-governance` (registry, readonly=false)
**Blockers: 3 · Gaps: 3 · Misalignments: 3**

### The one root cause
The server responds `200` on `/healthcheck` but **404 on `/`, `/mcp`, and `/mcp/`**. The tunnel is OPEN (port 8100), the LaunchAgent is loaded, the circuit is CLOSED, group resolution is correct, gate logic passes, and dry-runs build fine — but every real tool call (`search`, `stats`, `write`) returns `HTTP 404`. The Graphiti MCP server on the VPS is simply **not serving the tool route**.

### 🔴 Blockers (all one fix)
- **G6** tool plane 404 · **G10** search 404 (both `cursor-governance` + `igor-workspace`) · **G11** stats/Neo4j 404. All resolve by restoring the `/mcp/` route on the VPS.

### 🟠 Gaps
- **G1** `GRAPHITI_MCP_TOKEN=EMPTY` (will 401 later if auth is enforced; not the current cause) · **G13** `WRITE_GATES=0` (intended default) · **G15** no `memory-bank/` scaffold in this workspace.

### 🟡 Misalignments
- **G5 (headline)** server up but `/mcp/` not serving tools · **G8** editing clone origin is `Quantum-L9/Cursor-Governance` vs registry canonical `cryptoxdog/Cursor-Governance` (glob still matches) · **G16** env missing `MEMORY_DISTILL_TOKEN_BUDGET`, extra `GRAPHITI_SSH_KEYCHAIN_SERVICE` (Keychain-backed secrets — explains why `NEO4J_*`/`OPENAI_API_KEY` aren't in the env file).

**Same ground-truth deviation as before:** the GMP's `GOV="$HOME/.cursor-governance"` is a logs dir; I diagnosed the real wired SSOT (`$HOME/Dropbox/cursor governance/GlobalCommands`) and documented it. Secrets reported only as `SET/EMPTY/MISSING` — no values printed. G12b (live round-trip) was correctly skipped since `RUN_LIVE` wasn't set.

**Zero repo drift** (Phase 5): SSOT porcelain unchanged (still the pre-existing 10), no `e2e-test.json` leftover, workspace untouched.

**Smallest next action:** restart the Graphiti MCP server on VPS `46.62.243.82` so `/mcp/` serves the tool plane, then re-run `graphiti_memory_client.py health` until `"healthy": true`.

---

## Actionable checklist (derived from GMP-Report-GRAPHITI-20260630.md, evidence IDs cited)

Status as of 2026-06-30 diagnosis. Not re-verified live since (git status on the Dropbox-synced SSOT clone hangs under load — re-check manually before acting).

### 🔴 Blockers — must fix first (all one root cause)
- [ ] **G6/G10/G11** — Restart the Graphiti MCP server on VPS `46.62.243.82:8100` so it serves the tool route at `/mcp/` (currently `/`, `/mcp`, `/mcp/` all 404; only `/healthcheck` responds). This alone should clear `search`, `stats`, and `write`.

### 🟠 Gaps
- [ ] **G1** — Set `GRAPHITI_MCP_TOKEN` in `~/.cursor/graphiti.env` (currently `EMPTY`) before the server enforces bearer auth.
- [ ] **G13** — No action required now; `GRAPHITI_WRITE_GATES=0` is the correct state while the tool plane is down. Only flip to `1` after a soak per `GATES-002-ACTIVATION.md`, and only after G6 is fixed.
- [ ] **G15** — Scaffold `memory-bank/` (run `setup_workspace_symlinks.sh` from the workspace root) if T0 resume state is wanted here.

### 🟡 Misalignments
- [ ] **G5** — Same fix as G6 (headline: server up, tool route not mounted).
- [ ] **G8** — Reconcile the open editing clone's `origin` (`git@github.com:Quantum-L9/Cursor-Governance.git`) against the registry's canonical `cryptoxdog/Cursor-Governance`, or add `Quantum-L9` to `group_registry.yaml` if the org split is intentional.
- [ ] **G16** — Add `MEMORY_DISTILL_TOKEN_BUDGET` to `~/.cursor/graphiti.env` (present in `graphiti.env.example`, missing from the live env) or update the example if the Keychain-backed model (`GRAPHITI_SSH_KEYCHAIN_SERVICE`) has superseded it.

### ✅ SSOT uncommitted work-in-progress (found during Phase 5 drift check, 2026-06-30) — RESOLVED 2026-07-04
The GlobalCommands SSOT clone had **10 uncommitted changes** at diagnosis time, clustered around Graphiti env/hook loading. This was committed and pushed to `main` in `3f65eb4` ("chore(governance): session-end sync 2026-07-04") before this push — same file set (`graphiti_memory_client.py`, `graphiti.env.example`, `graphiti_common.sh`, `session_start_bootstrap.sh`, `install_cursor_hooks_bootstrap.sh`, `graphiti_env_loader.py`, `graphiti.env.defaults`, `ops/graphiti/docs/`, `ensure_graphiti_tunnel.sh`, `init_graphiti_machine_env.sh`). No outstanding action.
- [ ] **Not yet re-verified:** whether this new Keychain-backed env loader (`graphiti_env_loader.py`, `MACHINE-ENV-POLICY.md`) actually fixes the G6/G10/G11 tool-plane 404 blocker above. It ships *client-side* env loading; the 404 is a *server-side* VPS routing issue. Re-run `health` after picking up `3f65eb4` to confirm this is still open.

### Cross-references
- Full evidence matrix (G1–G16, masked config, raw endpoint probes): `GMP-Report-GRAPHITI-20260630.md`
- Companion whole-system diagnosis (Python syntax errors, SSOT dirty-tree detail, D-check matrix): `GMP-Report-DIAG-20260630-system-diagnosis.md`
- Build history this regressed from: `GMP-GRAPHITI-GLOBAL-001-FINAL-DECLARATION.md`, `GMP-GRAPHITI-GATES-002-FINAL-DECLARATION.md`, `GMP-GRAPHITI-FILEPACK-003.md` (each now cross-linked back to this diagnosis).