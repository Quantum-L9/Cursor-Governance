# Execution Plan — RC2 / MEM-003: register `l9-shared-memory` so the interactive memory-tool path exists

**Mode:** plan · **Skill:** l9-plan · **Repo:** Quantum-L9/Cursor-Governance · **Owner surface:** `environment/claude-code/`
**Author date:** 2026-08-04 · **Depends on:** #68 (merged — RC1 fixed; hook path works)

---

## Pre-Validation

| Check | Command | Result |
|---|---|---|
| Baseline tree clean | `git -C /home/user/Cursor-Governance status --porcelain` | PASS — clean (audit branch merged to `main`) |
| Repo gate exists | `grep -n '^pr pr-check:' Makefile` | PASS — `make pr` / `make pr-check` present (Makefile:171) |
| Env validator exists | `environment/claude-code/validate_claude_env.py` | PASS — already checks `mcp.template.json` (env-ref, non-loopback); no runtime MCP check yet |
| Launcher strict-MCP? | earlier `ps` of the session launcher | PASS(evidence) — **no `--strict-mcp-config`** ⇒ user-scope `~/.claude.json` mcpServers are merged with `--mcp-config` |
| User-scope MCP slate | `~/.claude.json` | PASS — `mcpServers: []`, 0 projects (clean; nothing to collide) |
| Network allowlist | `web/network-policy.md` | PASS — `memory.quantumaipartners.com` already allowlisted |
| Full `make pr-check` | (implementation gate) | **SKIPPED — plan-only phase, no edits yet**; REQUIRED before any PR (see Final Validation) |

---

## Objective

Make the **interactive** memory path real: a fresh Claude Code session (managed/CCR, CLI, Web, Mobile) exposes `mcp__l9-shared-memory__*` tools so the model can read/write memory on demand — the second entry point named in ADR-0003, which #68 left open. The **hook path already works** post-#68; this plan does **not** touch it.

**Root gap (proven):** `render.claude.json` specifies two MCP carriers — CLI = *user-scope* `claude mcp add-json`, web/mobile = git-tracked `.mcp.json`. `setup.sh` implements only the `.mcp.json` copy. The managed CCR launcher builds its MCP set from account connectors via `--mcp-config` and never reads a home-dir `.mcp.json`, so on that surface **nothing registers** → `claude mcp list` is empty → no memory tools.

---

## Scope

### In
- User-scope registration of `l9-shared-memory` during setup/bootstrap (the missing CLI carrier).
- A **runtime readiness** check that fails loudly when the server is absent (presence-is-not-proof; the MEM-005 lesson).
- Secret-safety proof (no literal bearer token on disk).
- Docs + an ADR recording the per-surface registration decision.
- Empirical verification on the **actual managed surface**.

### Out (explicit)
- The hook path (`memory_prefetch.py` / `memory_client.py` / gate / lock) — unchanged; already correct.
- Any transport/identity/contract change to the memory service (`l9-graphiti-memory`) — none.
- Account-connector provisioning **code** — that is an operator UI action (documented as Path B fallback, not automated).
- Network-policy changes — host already allowlisted.
- Changing `--strict-mcp-config` or the launcher (out of this repo's tree).

---

## Success Criteria (falsifiable)

1. In a **fresh** managed session, `claude mcp list` shows `l9-shared-memory` as **connected**.
2. The model can call a memory tool (e.g. `mcp__l9-shared-memory__memory.search`) and get a valid result.
3. `grep -r` over `~/.claude.json` and any rendered MCP config shows **only** `${L9_MEMORY_CLIENT_TOKEN}` env-refs — **no literal token**.
4. Re-running setup is **idempotent** — no duplicate server, no error.
5. `validate_claude_env.py` (extended) **FAILS** when `l9-shared-memory` is not registered/reachable, and PASSES when it is; `validate_memory_enforcement.py` still PASSES.
6. Hook path unaffected: SessionStart prefetch still hydrates + injects (regression check).

---

## Decompose — TODO

| # | Task | Files | Effort | Risk |
|---|---|---|---|---|
| T1 | Add user-scope registration step to setup: extract the `l9-shared-memory` object from `mcp.template.json` and run `claude mcp add-json --scope user l9-shared-memory <obj>`, **only** when `claude` CLI is present, `L9_MEMORY_HTTP_URL`+`L9_MEMORY_CLIENT_TOKEN` are set, and it is not already registered (idempotent guard via `claude mcp get`). Keep the existing `.mcp.json` copy for the web/consumer surface. | `environment/claude-code/web/setup.sh` | M | Med |
| T2 | Runtime readiness check: when `claude` CLI + `L9_MEMORY_*` are available, assert `claude mcp get l9-shared-memory` resolves; classify **blocking** on CLI/managed surfaces, **advisory** where the CLI is absent (web/mobile pre-clone). Never a silent pass. | `environment/claude-code/validate_claude_env.py` | S | Low |
| T3 | Secret-safety assertion: after T1, verify the stored server object retains the `${...}` env-ref (no expanded token on disk); add it to T2's checks. | `validate_claude_env.py` | S | Med |
| T4 | Idempotency + failure semantics: guard against double-registration; on `claude mcp add-json` failure emit a clear WARN, never abort setup (fail-open setup, fail-closed readiness). | `web/setup.sh` | S | Low |
| T5 | Document **Path B fallback** (operator adds `l9-shared-memory` as a managed-environment connector in account settings) with the exact server JSON, for surfaces where user-scope is not honored. | `environment/claude-code/web/README.md`, `environment/claude-code/README.md` | S | Low |
| T6 | ADR recording the per-surface registration decision (CLI/managed = user-scope `claude mcp add-json`; web/mobile = git-tracked `.mcp.json`; account-connector fallback). Supersedes the "RC2 open" note in ADR-0003. | `docs/decisions/ADR-0005-interactive-memory-mcp-registration.md` (new) | S | Low |
| T7 | (Optional) Update `render.claude.json` note to reflect that setup now performs the user-scope registration (close the doc/impl gap). | `environment/claude-code/render.claude.json` | XS | Low |

---

## Dependencies

```
T1 ──▶ T3 ──▶ T2 ──▶ (M1 gates)
T1 ──▶ T4
T1,T2 ──▶ M2 (empirical, fresh session)  ──▶ [go] T5,T6,T7 ──▶ M3 PR
                                          └─▶ [no-go: user-scope ignored] Path B (T5) ──▶ re-verify
```
- **Blocker/unknown:** whether the managed launcher honors user-scope `~/.claude.json` at runtime (evidence says yes — non-strict — but must be proven on the live surface at M2). This single checkpoint decides Path A vs Path B.

---

## Milestones

- **M1 — Implemented & locally green.** T1–T4 done; `make pr-check` PASS; both validators PASS; idempotent re-run; no token on disk.
- **M2 — Proven on the real surface (go/no-go).** Fresh managed session: `claude mcp list` shows `l9-shared-memory` **and** a `mcp__l9-shared-memory__*` tool call returns a valid result. If NOT → user-scope isn't honored on this surface → pivot to **Path B** (account connector), then re-verify.
- **M3 — Documented & shipped.** T5–T7; ADR-0005; PR to `main`, drive to green, resolve review comments.

---

## Checkpoints (go/no-go evidence gates)

- **C1 (exit M1):** `make pr-check` PASS · `validate_claude_env.py` FAILS-when-absent / PASSES-when-present · `grep` finds no literal token · second setup run adds nothing.
- **C2 (exit M2):** live `claude mcp list` contains `l9-shared-memory` **and** an on-demand memory tool call succeeds in a session that did **not** manually register it. FAIL ⇒ Path B.
- **C3 (exit M3):** PR green (Lint/Test/Sonar/Semgrep/CodeQL/Copilot) · hook-path regression check passes · ADR-0005 links from ADR-0003.

---

## Checklist (atomic)

- [ ] T1 setup.sh registers `l9-shared-memory` user-scope, gated + idempotent
- [ ] T4 double-run adds no duplicate; add-json failure WARNs, never aborts setup
- [ ] T3 stored config keeps `${L9_MEMORY_CLIENT_TOKEN}` env-ref (no literal token)
- [ ] T2 validator fails when server absent, passes when present; blocking vs advisory per surface
- [ ] M2 fresh session: `claude mcp list` shows `l9-shared-memory`
- [ ] M2 fresh session: model calls `mcp__l9-shared-memory__memory.search` successfully
- [ ] Regression: SessionStart prefetch still hydrates + injects (hook path unaffected)
- [ ] T5 Path B fallback documented with exact server JSON
- [ ] T6 ADR-0005 written; ADR-0003 "RC2 open" note updated to point at it
- [ ] `make pr-check` PASS pre-PR; PR opened only on green

---

## Final Validation (post-implementation gates)

- `make pr-check` (alias `make pr`) — **required**, changed-files scanners, no commit/push until green.
- `python3 environment/claude-code/validate_claude_env.py` — PASS (now includes MCP readiness).
- `python3 environment/claude-code/validate_memory_enforcement.py` — PASS (unchanged hook path).
- Live: `claude mcp list` and one `mcp__l9-shared-memory__*` tool call in a **fresh** session (C2).
- Secret scan: no literal bearer token in `~/.claude.json` / rendered MCP config.
- Governed writes: acquire the `cursor-governance` phase-lock before commit/push (memory gate), as in #68.

---

## Recommend (next step)

- This plan **edits code** → hand off to **`l9-gmp-protocol`** for locked phase-by-phase execution with an evidence report (do not implement in plan mode).
- **Sequencing:** land T1–T4 + validator behind M2's empirical gate **before** writing the ADR as "Accepted" — because M2 may force Path B, which changes the decision ADR-0005 records.
- Load **`l9-ynp`** if you want the single highest-leverage next action; otherwise the first execution step is **T1** (setup.sh user-scope registration) under GMP.

### Key residual risks to carry into execution
- **R1 (Med):** a surface may run `--strict-mcp-config` ⇒ user-scope ignored ⇒ Path B (account connector) is the only route there. *M2 is the detector.*
- **R2 (Med):** `claude mcp add-json` might expand `${...}` at add-time ⇒ token on disk. *T3 detects; if so, prefer registering the env-ref form or rely on runtime expansion only.*
- **R3 (Low-Med):** managed provisioning could regenerate `~/.claude.json` after setup ⇒ registration lost. *M2 persistence check; if volatile ⇒ Path B.*
