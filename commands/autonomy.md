---
description: Bounded autonomy campaign — Phase-0 packet, parallel Tasks, background PR poll while main continues, human merge.
---

# /autonomy

Load skill **`l9-bounded-autonomy`**. Explicit-only with optional proactive **hint**
(`hint_allowed` → `source: explicit_hint`). Router may recommend Read; **packet still
required**. Recommendation ≠ mutation authority.

**First-class family registry:**
[`environment/contracts/autonomy/MANIFEST.yaml`](../environment/contracts/autonomy/MANIFEST.yaml)
(SSOT map for root `autonomy/`, `ops/autonomy`, Claude scheduler). PE Controller
remains authoritative; autonomy stays `owns_program_state: false`.

## Steps

1. **Create campaign authorization packet** (see skill `references/campaign-authorization-packet.md`). State it in chat (first screen). Never call it an “envelope”.
2. **Phase-0 action table** — require columns: `id`, `depends_on`, `mutation`, `lock_keys`, `isolation_key`, `kind` (`work`|`poll`).
3. **Validate** locks + lane budget (max 4 / 2 mutation) + dependency readiness.
4. **Spawn ready `work` Tasks** in one message (Protocol A).
5. **Spawn each `poll` action** as `Task` with `run_in_background: true` (Protocol B). Then **main continues** other ready work — must not block the main turn on CI; must not AwaitShell on those poll workers.
6. **Join** when closing or when user asks status (Protocol C).
7. **Merge-gate report** only; human merges. Never `gh pr merge` without explicit user approval.
8. **Optional handoff** — Graphiti-primary PICKUP fields per `campaign-handoff.md` / `/end-session`.

## Native Cursor host admission (root-Autonomy backed)

Native `Task` launches are governed by the lifecycle hooks and the host bridge
(`autonomy/adapters/cursor/host_bridge.py`). The order is fixed:

1. **Root authority first.** Before any `Task` fires, create a pending
   admission through the host bridge: it registers/reuses a conformant cursor
   adapter session, requests a specific READY root action, obtains the root
   lease and rendered agent contract, and returns an **opaque single-use
   admission token** (`L9_ADMISSION_TOKEN=<token>`).
2. **Embed only the token** in the Task prompt. The token identifies authority
   already persisted in the root Autonomy runtime; Task prose is never
   authority and nothing else in the prompt participates in admission.
3. **preToolUse(Task)** binds the host `tool_use_id` to the pending admission;
   **subagentStart** must present the exact matching `tool_call_id` and binds
   `subagent_id`, parent conversation, model, parallel-worker flag, and git
   branch. Unknown, expired, or conflicting tokens — and any launch without a
   live root lease — are **denied** (fail closed).
4. **subagentStop** resolves through the persisted host correlation into the
   existing typed result pipeline; uncorrelated stops are quarantined with an
   immutable host-stop receipt.

Per-child *tool* mediation (each child's own tool calls authorized per-call
against the root lease) remains fail-closed until the live host protocol
proves a stable child identity at preToolUse
(`UNRESOLVED_NATIVE_CHILD_TOOL_IDENTITY`).

## Supporting skills

At most two: `l9-pr-remediation`, `l9-structured-reasoning`, and/or `l9-cli-optimization` per skill-routing.

## References

Skill pack: `skills/l9-bounded-autonomy/` (especially `pr-poll-subagent.md`, `prompt-templates.md`, `examples.md`).
Authority split SSOT: `rules/23-l9-skill-routing.mdc`.
