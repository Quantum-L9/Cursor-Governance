# MEMORY_ROOT_CAUSE — Graphiti memory in Claude Code

**Verdict:** `MULTIPLE_ROOT_CAUSES_CONFIRMED`
**Date:** 2026-08-04 · **Claude Code:** 2.1.221 · **Memory service:** l9-graphite-memory 2.2.0 (healthy)

## One-sentence root cause
Graphiti memory does not operate in a Claude Code session because of **two independent, each-sufficient failures**: (1) the SessionStart prefetch hook reads the wrong keys from the server's `memory.hydrate` response and never injects the returned context, so it *always* reports "0 records" and exposes *zero* memory content regardless of what the server holds; and (2) the interactive `l9-shared-memory` MCP server is **never registered in this managed environment**, so no `mcp__l9-shared-memory__*` tools exist for in-session read or write.

The memory **service itself is fully healthy and is not the cause.**

---

## RC1 — Prefetch parses `memory.hydrate` with the wrong schema and injects nothing (CONFIRMED, deterministic)

**First failing boundary:** edge `memory.hydrate result → prefetch record-count / context injection`, in
`environment/claude-code/hooks/memory_prefetch.py:48-63` (runtime copy: `/root/.cursor-governance/...`; identical in working tree).

**Proof (live probe against the production server):**
- `memory.hydrate("audit probe", ["cursor-governance"])` returns keys: `['receipt_id, status, task, sections, token_budget, tokens_used, search_receipt_id, result_digest, warnings, created_at]`. There is **no `records` key and no `hits` key** — the content lives under **`sections`**.
- Server source confirms it: `l9-graphiti-memory/src/l9_graphite_memory/retrieval/budget.py:90` builds the payload as `{"sections": [...]}`; `contracts/receipts.py:176` `HydrationResult.sections`. `records`/`hits` never appear in a hydrate result (`hits` is the **search** result key; `records` is an internal store count).
- The hook does: `records = bundle.get("records") or bundle.get("hits") or []` → for a hydrate payload this is **always `[]`** → `len(records)` is **always 0**.
- The hook's `additionalContext` is only two status strings ("Prefetch complete … N record(s) hydrated" + the phase-lock instruction). **`sections` is discarded — memory content is never placed into context.**

**On-disk confirmation (this session's receipt):**
`/home/user/.l9/memory/receipts/5b63f213-….json` → `{"hydrated_records": 0, "status": "prefetched", "namespaces": ["cursor-governance"]}`. This is the *success* branch (no exception), matching the SessionStart banner "0 record(s) hydrated". So the RPC succeeded; the parsing/injection is what fails.

**Consequence:** Even if `cursor-governance` were fully populated, SessionStart would still say "0 records" and inject none of it. This is the dominant, environment-independent reason "memory does not load into the session."

## RC2 — `l9-shared-memory` MCP is not registered in this managed environment (CONFIRMED)

**First failing boundary:** edge `environment activation → Claude Code MCP registry`.

**Proof:**
- `claude mcp list` → "No MCP servers configured."
- `~/.claude.json` → `projects: []`, no `mcpServers`. No `/home/user/.mcp.json`.
- The live session is launched by the managed CCR launcher with `--mcp-config /tmp/mcp-config-cse_01TkAJns2qXsviohjb1YtgGk.json`. That file's `mcpServers` are exactly: `github`, Google-Calendar, Vercel, and two Anthropic meta/toolbox servers — **`l9-shared-memory` absent**. The process `--allowed-tools` enumerates `mcp__github__*` and the connector servers but no `mcp__l9-shared-memory__*`.
- Cursor-Governance's `environment/claude-code/web/setup.sh:85-87` installs memory MCP by copying `mcp.template.json` to `.mcp.json` in the **consumer-repo working dir**; `mcp.template.json` also documents `claude mcp add-json --scope user`. In this managed launch the MCP set comes from the account's connected connectors via `--mcp-config`; the repo `.mcp.json` / user-scope registration path is **never consulted**. The two wiring models do not meet.

**Consequence:** No interactive memory tools in-session → no on-demand retrieval, no MCP writeback, no tool-based memory at all. Only the two Python hooks (SessionStart prefetch, Stop writeback), which talk to the server directly over HTTP, can touch memory — and RC1 breaks the read half of that.

---

## Why current validation missed both
`environment/claude-code/validate_memory_enforcement.py` only checks: JSON-schema conformance of the contract, that hook basenames appear in **`settings.template.json`**, and that referenced scripts exist & `py_compile`. It **never calls the server, never inspects a `hydrate`/`search` result shape, never checks context injection, and never checks the MCP registry.** So a hook that misreads the result and injects nothing, plus a missing MCP server, both pass as "PASS – memory enforcement contract is valid and wired." This is textbook presence/wiring-parity validation standing in for operational proof.

## Downstream symptom chain
`hydrate OK (sections populated server-side)` → `hook reads records/hits = []` → `receipt hydrated_records=0` + `no sections injected` → SessionStart banner "0 record(s) hydrated" → **model sees no memory**. In parallel: `no l9-shared-memory in --mcp-config` → **no memory tools** → model cannot query/write memory on demand. Net observable: "Graphiti memory is not loading / not operating."

## Minimum correct fix (owner: Quantum-L9/Cursor-Governance)
1. **RC1a** `memory_prefetch.py`: read `sections` from the hydrate result (fall back to `search().hits` only if you switch to `memory.search`); count `len(sections)`.
2. **RC1b** `memory_prefetch.py`: assemble the `sections` text (respecting `token_budget`) into the `additionalContext` string so the content actually reaches the model. Keep the receipt write.
3. **RC2** Register `l9-shared-memory` for the managed surface: emit it into the launch `--mcp-config` (managed-environment connector), or add a SessionStart step that runs `claude mcp add-json --scope user l9-shared-memory …` from `mcp.template.json`. A repo `.mcp.json` alone is insufficient for the CCR launch path — this must be proven with `claude mcp list` showing the server, not by file presence.
4. Harden the validator to exercise the live boundary (see MEMORY_VALIDATION_GAPS.md).

## Regression test (must fail before, pass after)
- Unit: feed a recorded `memory.hydrate` payload (`sections` non-empty) to the prefetch parser; assert count>0 **and** that section text appears in the emitted `additionalContext`.
- Integration: with `L9_MEMORY_HTTP_URL`/token set, run the SessionStart hook and assert the banner count equals the server's `len(sections)` and content is present.
- Environment: assert `claude mcp list` (or the runtime `--mcp-config`) contains `l9-shared-memory` before declaring the environment memory-ready.

## Confidence
- RC1: **CONFIRMED / high** — live server response shape + server source + on-disk receipt all agree.
- RC2: **CONFIRMED / high** — `claude mcp list` empty and the runtime `--mcp-config` enumerated with `l9-shared-memory` absent.

## Residual unknown (not a consumer defect; fail-closed)
The server store reports **11 records**, but `cursor-governance` (and every common namespace probed: `Cursor-Governance, igor-workspace, claude-code, global, default, l9, quantum-l9, l9-graphiti-memory`) returns **0 hits / empty sections** for the `claude-code` bearer. Whether `cursor-governance` is genuinely empty for this principal or the 11 records live under a namespace/principal not visible to this token is a **service-side data/authorization question** that cannot be resolved from the consumer without broader authorization. No test write was performed against the shared production plane (the governed `memory.*` surface exposes no delete tool, so a probe record could not be cleaned up). Marked BLOCKED for full attribution; it does **not** change RC1/RC2, which break memory even against a populated namespace.
