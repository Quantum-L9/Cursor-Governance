---
description: Bounded autonomy campaign — Phase-0 packet, parallel Tasks, background PR poll while main continues, human merge.
---

# /autonomy

Load skill **`l9-bounded-autonomy`**. Explicit-only with optional proactive **hint**
(`hint_allowed` → `source: explicit_hint`). Router may recommend Read; **packet still
required**. Recommendation ≠ mutation authority.

## Steps

1. **Create campaign authorization packet** (see skill `references/campaign-authorization-packet.md`). State it in chat (first screen). Never call it an “envelope”.
2. **Phase-0 action table** — require columns: `id`, `depends_on`, `mutation`, `lock_keys`, `isolation_key`, `kind` (`work`|`poll`).
3. **Validate** locks + lane budget (max 4 / 2 mutation) + dependency readiness.
4. **Spawn ready `work` Tasks** in one message (Protocol A).
5. **Spawn each `poll` action** as `Task` with `run_in_background: true` (Protocol B). Then **main continues** other ready work — must not block the main turn on CI; must not AwaitShell on those poll workers.
6. **Join** when closing or when user asks status (Protocol C).
7. **Merge-gate report** only; human merges. Never `gh pr merge` without explicit user approval.
8. **Optional handoff** — Graphiti-primary PICKUP fields per `campaign-handoff.md` / `/end-session`.

## Supporting skills

At most two: `l9-pr-remediation`, `l9-structured-reasoning`, and/or `l9-cli-optimization` per skill-routing.

## References

Skill pack: `skills/l9-bounded-autonomy/` (especially `pr-poll-subagent.md`, `prompt-templates.md`, `examples.md`).
Authority split SSOT: `rules/23-l9-skill-routing.mdc`.
