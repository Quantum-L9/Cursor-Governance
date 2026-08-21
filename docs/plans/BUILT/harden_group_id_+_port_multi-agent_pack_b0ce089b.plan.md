---
name: Harden group_id + port multi-agent pack
overview: Harden group_id repo-scoping in ops/graphiti (fail-closed resolution, segment-anchored path hints, block direct igor-workspace writes), and port the already-built WIP/l9-multi-agent-pack 2 into environment/agents/ — fixing its one real bug (hardcoded "l9-workspace" instead of the registry's actual workspace_group) and aligning it with the hardened write gate — then wire both into Makefile/CANONICAL_LAW so they're active, not just staged.
todos:
  - id: a1
    content: "group_resolver.py: reconcile explicit vs resolved repo-match, fail closed on contradiction"
    status: completed
  - id: a2
    content: "group_resolver.py: anchor path-hint matching to path segments"
    status: completed
  - id: a3
    content: "graphiti_memory_client.py cmd_write: reject igor-workspace as write target"
    status: completed
  - id: a4
    content: Add test_group_resolver.py regression tests
    status: completed
  - id: a5
    content: Add test_cli_write_gate.py regression tests
    status: completed
  - id: a6
    content: Update 98-graphiti-memory-gate.mdc and instantiation brief docs
    status: completed
  - id: b1
    content: git mv WIP/l9-multi-agent-pack 2 -> environment/agents/
    status: completed
  - id: b2
    content: Fix hardcoded l9-workspace bug in render_principals.py + test_validators.py + VALIDATION.md
    status: completed
  - id: b3
    content: Align pack docs with hardened write-gate contract, clarify dual memory-server distinction
    status: completed
  - id: b4
    content: Re-run validate_agents.py and test_validators.py from new path
    status: completed
  - id: b5
    content: Wire CANONICAL_LAW.md adapter table row + Makefile agents-env target
    status: completed
  - id: b6
    content: Remove emptied WIP directory
    status: completed
isProject: false
---

# Harden `group_id` scoping + activate the multi-agent environment pack

Two independent-but-adjacent workstreams, sequenced so the pack's docs describe the *shipped* hardened contract rather than the pre-hardening one.

## Part A — Harden `group_id` resolution (as specified, unchanged from your plan)

**Objective:** fail closed on explicit/resolved `group_id` contradictions, remove path-hint substring false positives, block direct CLI writes to `igor-workspace` outside the sanctioned bootstrap mirror.

**Files:** [ops/graphiti/group_resolver.py](ops/graphiti/group_resolver.py), [ops/graphiti/graphiti_memory_client.py](ops/graphiti/graphiti_memory_client.py)

| # | Task | Effort | Risk |
|---|------|--------|------|
| A1 | `resolve_group_id`: always compute repo-match (remote + anchored path-hint) first; if `explicit` given, require equality with the resolved match (or allow when there is no resolved match at all); contradiction → `{"group_id": None, "readonly": True, "error": "..."}` | M | Med |
| A2 | Anchor path-hint matching to `Path(cwd_str).parts` / basename instead of `hint in cwd_str` — fixes the live false-positive risk already present today (`IB_Odoo` hint in [group_registry.yaml](ops/graphiti/group_registry.yaml) would substring-match e.g. `CONTRIB_Odoo_notes`) | S | Low |
| A3 | `cmd_write`: after resolution, `if group_id == registry.get("workspace_group", "igor-workspace"): raise SystemExit(...)` — `cmd_bootstrap`'s internal `_write_episode(..., workspace_group, ...)` mirror call is untouched by design (different code path) | S | Low |
| A4 | New `ops/graphiti/test_group_resolver.py` — explicit-matches (pass), explicit-contradicts (fail closed), explicit-no-match (pass), ambiguous-match (unchanged), path-hint segment vs substring cases | M | Low |
| A5 | New `ops/graphiti/test_cli_write_gate.py` — `cmd_write --group-id igor-workspace` / `GRAPHITI_GROUP_ID=igor-workspace` both exit non-zero; bootstrap mirror unaffected | S | Low |
| A6 | Update [rules/98-graphiti-memory-gate.mdc](rules/98-graphiti-memory-gate.mdc) and `ops/graphiti/docs/CURSOR-GRAPHITI-INSTANTIATION-BRIEF.md` §7.4 to state the hardened contract | S | Low |

Dependencies: A1,A2 → A4; A3 → A5; A6 last (describes shipped behavior).

## Part B — Port `WIP/l9-multi-agent-pack 2/` → `environment/agents/`

The pack is a complete, self-consistent build (registry, adapters for manus/codex/gemini/generic, validator, renderer, docs, tests — see its own [INDEX.md](WIP/l9-multi-agent-pack%202/INDEX.md)). `environment/agents/` does not exist yet in this repo, so this is a pure addition alongside the existing `environment/claude-code/` and `environment/ide/` adapters — no overlap to reconcile. Every file's `L9_META` header already declares its final destination path, confirming this placement.

**Files:** entire `WIP/l9-multi-agent-pack 2/` tree → `environment/agents/` (git mv, preserving structure: `agent_registry.yaml`, `DESIGN.md`, `HANDOFF.md`, `README.md`, `INDEX.md`, `VALIDATION.md`, `analysis_notes.md`, `adapters/{manus,codex,gemini,generic}/`, `docs/{WORK_CLAIM_PROTOCOL,MEMORY_TOPOLOGY}.md`, `tools/{render_principals,validate_agents,test_validators}.py`)

| # | Task | Files | Effort | Risk |
|---|------|-------|--------|------|
| B1 | `git mv "WIP/l9-multi-agent-pack 2"` contents → `environment/agents/` (drop the ` 2` suffix and `WIP/` prefix) | whole tree | S | Low |
| B2 | **Fix the workspace-group bug found during review:** `render_principals.py` line 71 hardcodes `write_ns.append("l9-workspace")` instead of the registry's actual `workspace_group` (`igor-workspace`) — change to `write_ns.append(workspace)` (the variable already loaded at line 95). Update the matching assertion in `test_validators.py` line 76 and the sample output in `VALIDATION.md` line 31/38 | `environment/agents/tools/render_principals.py`, `environment/agents/tools/test_validators.py`, `environment/agents/VALIDATION.md` | S | Low — caught before merge, not a regression |
| B3 | Align pack docs with Part A's hardened contract: note in `DESIGN.md` §6 / `README.md` that direct writes to `workspace_group` (`igor-workspace`) go only through `graphiti_memory_client.py bootstrap`'s sanctioned mirror (per A3) — this pack's `render_principals.py` targets the separate `l9-graphiti-memory` control-plane server (future/planned per `HANDOFF.md` §2), not the deployed `zepai/knowledge-graph-mcp` MCP stack Part A hardens; call out this distinction explicitly so operators don't conflate the two "shared workspace" concepts | `environment/agents/DESIGN.md`, `environment/agents/README.md` | S | Low |
| B4 | Re-run `validate_agents.py` and `test_validators.py` from the new path to confirm the move + B2 fix didn't break anything (must still show `PASS` / `7/7`) | — | S | Low |
| B5 | Wire `environment/agents/` into the repo per `README.md`'s own "Integration notes": add `CANONICAL_LAW.md` §2 adapter-table rows (Manus — active; Codex, Gemini — planned), add `Makefile` target `agents-env: python3 environment/agents/tools/validate_agents.py` (peer of the existing `claude-env` target at [Makefile:45](Makefile)) | `CANONICAL_LAW.md`, `Makefile` | S | Low |
| B6 | Delete the now-empty `WIP/l9-multi-agent-pack 2/` directory | — | S | Low |

Dependencies: B1 → B2 → B3 → B4 → B5 → B6 (linear; each step assumes the prior one's on-disk state).

## Combined risks

| Risk | Mitigation |
|------|------------|
| B2's fix changes rendered `write_namespaces` output — anyone who already ran `render_principals.py` against the WIP copy has a stale `auth_tokens.json` with the wrong namespace | Pack has never been deployed (HANDOFF.md §8: "no writes have been made to any GitHub repo," server-side deploy is still an operator TODO) — no live artifact to reconcile |
| Part A's `cmd_write` guard and Part B's pack target *different* memory servers today (deployed MCP stack vs. planned `l9-graphiti-memory` HTTP server) — could look like two independent security models for "the shared bucket" | B3 makes this explicit in the ported docs rather than silently shipping two divergent namings |
| `git mv` off a path with a space (`l9-multi-agent-pack 2`) | Quote the path; verify with `git status` after move that no file was dropped (26 files in, 26 files at new path) |

## Estimate

**Part A:** ~1-1.5 hrs (as originally scoped). **Part B:** ~30-45 min (mechanical move + one bug fix + two doc edits + two wiring edits). **GMPs:** 0 for Part B (doc/registry addition, no protected-core); flag Part A per your own note if you want a full GMP for the security-boundary change.
