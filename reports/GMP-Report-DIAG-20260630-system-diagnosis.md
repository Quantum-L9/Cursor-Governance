# GMP-DIAG — Full System Diagnosis (read-only)

**ID:** GMP-DIAG | **Task:** Governance stack full-system health diagnosis | **Tier:** INFRA_TIER | **Date:** 2026-06-30 | **Status:** ✅ COMPLETE (read-only)

---

## EXECUTIVE VERDICT

**`DEGRADED`**

The governance stack is **wired and operational** — SSOT path resolution, symlink wiring, hooks registration, shell syntax, Graphiti creds gate, gate self-test, and the VPS tunnel all pass. However there are **active functional failures**:

1. **Graphiti memory read/write plane is down** — liveness/tunnel OK, but the MCP tool endpoint (`http://127.0.0.1:8100/mcp`) returns HTTP 404, so `search`/`stats`/`write` fail (dry-run + gate + resolve still work).
2. **Two ops Python scripts have hard SyntaxErrors** under this machine's `python3` 3.12.11 (fail to compile).
3. **SSOT clone tree is dirty** (10 uncommitted Graphiti-WIP changes) — housekeeping drift, not corruption.

Core wiring is intact, so this is **not** `CRITICAL` and **not** a Phase-1 halt.

---

## PHASE 0 — GROUND-TRUTH DEVIATION (documented)

The GMP hardcodes `GOV="$HOME/.cursor-governance"`. **On this machine that path is NOT the clone** — it contains only `backup.log` + `logs/` (runtime dir, no `.git`).

Per Authority Order #2 (verified ground truth outranks the doc), `GOV` was pivoted to the **real wired SSOT**:

```
GOV = $HOME/Dropbox/cursor governance/GlobalCommands
    → realpath /Users/macm2/Library/CloudStorage/Dropbox/Cursor Governance/GlobalCommands
```

Confirmed real because: (a) the resolver returns it, (b) `~/.cursor/{commands,rules,skills}` symlink into it, (c) it is a git clone on `main`. A **separate editing clone** is the open workspace (`…/Repo_Dropbox_IB/Cursor-Governance`, remote `git@github.com:Quantum-L9/Cursor-Governance.git`). All D-checks ran against the wired SSOT. This deviation is disclosed, not silent.

- **Tooling:** `python3=/Users/macm2/miniconda3/bin/python3` (3.12.11), `git=/opt/homebrew/bin/git`, `launchctl=/bin/launchctl` — all present.
- **MEMORY_PREFETCH:** attempted — `conflicts` returned `[]` but underlying `search_facts`/`search_nodes` 404'd, so prefetch is **untrustworthy** (tool plane down). No episodes cited.

---

## EVIDENCE MATRIX

| ID | Subsystem | Status | Exit | 1-line evidence |
|----|-----------|--------|------|-----------------|
| D1 | SSOT resolver | ✅ PASS | 0 | `GOV_ROOT=…/cursor governance`, `GLOBAL_COMMANDS==GOV` (GOV_ROOT = parent by design) |
| D2 | Clone integrity | ❌ FAIL | — | on `main`, files present, but tree **dirty**: 10 uncommitted changes (all `ops/graphiti|hooks|scripts`) |
| D3 | Path contract | ✅ PASS | 0 | `RESULT: PASS — wiring kernel uses $HOME/Dropbox resolution only` |
| D4 | Symlink wiring E2E | ✅ PASS | — | `validate_governance_symlinks → RESULT: PASS`; deeper wiring check warns sessionStart orchestrator absent |
| D5 | Hooks registered | ✅ PASS | 0 | sessionStart=`session-start-bootstrap.sh`; sessionEnd=`[graphiti-session-end, governance-backup]` |
| D6 | Installed bootstrap | ✅ PASS | 0 | `~/.cursor/hooks/session-start-bootstrap.sh` executable (real file, 4449B, updated 2026-06-30) |
| D7 | Guarded auto-sync | ⛔ BLOCKED | — | `governance_sync.sh` **absent**; equivalent backup exists (`session_end_governance_backup.sh` / `backup_to_github.sh`) but not run (remote:none) |
| D8 | Runtime isolation | ❌ FAIL | — | no global `core.excludesfile`; `memory-bank/`/`workflow_state` patterns not globally enforced (non-blocking) |
| D9 | Python syntax sweep | ❌ FAIL | — | 135 files; **2 SyntaxErrors** (see below) |
| D10 | Shell syntax sweep | ✅ PASS | 0 | `ALL_SH_OK` (66 `.sh` files) |
| D11 | Graphiti creds gate | ✅ PASS | 0 | `~/.cursor/graphiti.env` present → D12–D17 executed |
| D12 | Graphiti health | ❌ FAIL | 1 | `"healthy": false` — liveness OK, **MCP tool plane 404** at `/mcp` → reads/writes fail |
| D13 | Graphiti resolve+stats | ❌ FAIL | — | resolve ✅ (`group_id=cursor-governance`, registry); **stats ❌ HTTP 404** |
| D14 | Graphiti conflicts | ⚠️ PASS(degraded) | 0 | returns `{"conflicts": []}` but `search_facts/nodes` 404'd → result untrustworthy |
| D15 | Graphiti dry-runs | ✅ PASS | 0 | `write --dry-run` + `bootstrap --dry-run` built payloads, **no mutation** |
| D16 | VPS tunnel LaunchAgent | ✅ PASS | 0 | `com.cursor.graphiti-tunnel` loaded (PID 67685, 8100→46.62.243.82:8100) |
| D17 | Gate E2E self-test | ✅ PASS | 0 | `OK: graphiti gate E2E passed` |
| D18 | 10X health | ⚠️ PASS(warn) | — | 7/9 layers OK; `.cursor brain` missing, Integrity Activity Log missing, Integrity LaunchAgent not loaded |
| D19 | Startup files | ❌ FAIL | 1 | 25 "missing" — **run-context artifact** (checker needs a wired workspace root); files exist in SSOT |

**Tally: 12 PASS / 6 FAIL / 1 BLOCKED** (D14/D18 counted PASS-with-warning).

---

## GRAPHITI SECTION

- **D11 gate:** PASS — `~/.cursor/graphiti.env` present (not fabricated).
- **Liveness/tunnel:** UP — LaunchAgent `com.cursor.graphiti-tunnel` loaded; health `liveness_ok: true`.
- **Tool plane:** **DOWN** — `tools.reachable: false`, `HTTP 404: {"detail":"Not Found"}` at `http://127.0.0.1:8100/mcp`. Health verdict: `degraded: liveness OK but MCP tool plane unreachable — reads/writes will fail`.
- **Resolve:** `group_id=cursor-governance` (method `registry`, readonly false).
- **Stats:** FAIL (404). **Conflicts:** ran, `[]`, but search 404'd → not trustworthy.
- **Dry-runs:** write + bootstrap dry-run OK, no mutation. **Gate E2E:** passed.
- **Remediation:** the SSH tunnel reaches the VPS but the Graphiti MCP server is not serving the `/mcp` tool route (likely the MCP process/router on `46.62.243.82:8100` is down or mis-routed, or expects a different path). Restart/verify the Graphiti MCP server on the VPS and confirm the `/mcp` route responds; then re-run `graphiti_memory_client.py health` until `"healthy": true`.

---

## FAILED / BLOCKED CHECKS — SMALLEST NEXT ACTION

| Check | Smallest next action |
|-------|----------------------|
| **D12/D13 Graphiti tool plane 404** | On VPS `46.62.243.82:8100`, restart the Graphiti MCP server and verify the `/mcp` route serves tool calls; re-run `graphiti_memory_client.py health`. |
| **D9 Python SyntaxErrors** | Fix nested-f-string escapes in `ops/scripts/prevention_effectiveness_tracker.py:500` and `ops/scripts/closed_loop_improvement.py:431` (extract the `datetime…strftime(...)` into a local var instead of `\"…\"` inside a nested f-string). |
| **D2 dirty SSOT tree** | Review & commit (or discard) the 10 pending Graphiti-WIP changes in the SSOT clone so the SSOT is clean. |
| **D7 `governance_sync.sh` absent** | Either add `ops/scripts/governance_sync.sh`, or update this GMP matrix to target the actual mechanism (`session_end_governance_backup.sh`). |
| **D8 runtime isolation** | Set a global `core.excludesfile` (or per-repo `.gitignore`) covering `memory-bank/` + `workflow_state*` if global isolation is intended. |
| **D19 startup-files FAIL** | Run `verify-startup-files.sh` from a **wired** workspace root (with `.cursor-commands`); or fix the checker to resolve against the SSOT. |
| **D18 Integrity agent** | Load the Integrity LaunchAgent and confirm the Integrity Activity Log is being written, if that subsystem is meant to run. |

---

## UNKNOWNS (not evidenced)

- **Graphiti memory content** (episode/fact counts, conflicts) — unknowable while the tool plane 404s.
- **Whether the SSOT `commands/` sparseness is intended** — SSOT `GlobalCommands/commands/` has only 10 entries; slash commands referenced by `02-slash-commands.mdc` (e.g. `forge`, `analyze`, `gmp`, `evaluate`, `reasoning`, `consolidate`) are **not present as files** in the SSOT (also absent from the editing clone). Pre-existing; not caused by this run.
- **Open editing clone wiring** — the workspace `…/Repo_Dropbox_IB/Cursor-Governance` has **no `.cursor-commands` symlink** (unwired editing copy); active wiring is via the SSOT + `~/.cursor` symlinks.

---

## PHASE 5 — RECURSIVE VERIFY (no drift)

- SSOT tracked porcelain: **still exactly 10 entries**, byte-identical to the D2 baseline → **zero tracked drift introduced**.
- `__pycache__`: 30 **gitignored** `.pyc` entries (regenerable bytecode from D9's `py_compile` sweep) — disclosed; **no tracked repo drift**. Nothing deleted (no-delete governance honored).
- Scratch: `/tmp/gov-diag-*` removed (one D4 subshell leftover was cleaned mid-run; final state clean).
- Open workspace: untouched (HEAD `4aad3f1`); no write ops were run against it.
- New artifact: only this report.

---

## DECLARATION

```
GMP-DIAG COMPLETE — DEGRADED
Checks: 12 PASS / 6 FAIL / 1 BLOCKED
Repo drift: NONE (Phase 5 verified; only gitignored .pyc bytecode generated)
Graphiti: degraded — tunnel/liveness OK, MCP tool plane 404 at http://127.0.0.1:8100/mcp (reads/writes fail)
Next action: Restart the Graphiti MCP server on VPS 46.62.243.82:8100 and confirm the /mcp route serves tools, then re-run graphiti_memory_client.py health until healthy:true
```
