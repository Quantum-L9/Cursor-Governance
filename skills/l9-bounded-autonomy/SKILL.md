---
name: l9-bounded-autonomy
description: >-
  bounded autonomy campaign SOP for Cursor — parallel non-dependent Tasks,
  background PR-poll subagents while main continues, campaign authorization
  packet, join/merge-gate without autonomous merge. use when user runs
  /autonomy, needs PR convergence while continuing other work, or fans out
  independent lanes under ADR-0001 / pr-convergence budgets.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, autonomy, parallel, pr-poll, subagent, campaign, merge-gate]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-02
disable-model-invocation: true
---

# Bounded Autonomy (Cursor SOP)

## Purpose

Map Claude Code ADR-0001 / pr-convergence law onto Cursor: fan out non-dependent work and deploy background PR-poll subagents while the main agent continues — without autonomous merge.

## Core Contract

| Item | Value |
|---|---|
| Lanes | Max 4 total / 2 mutation |
| Merge | Human only (`autonomous_merge: false`) |
| PR wait | MUST spawn background poll; main continues |
| Authority | Campaign authorization **packet** (never “envelope”) |
| Claude runtime | Untouched; bridge to `autonomy/cli.py` on Claude surface |

## MUST

1. Create a **campaign authorization packet** via `/autonomy` or explicit user campaign phrase before remediation pushes.
2. Build Phase-0 action graph (`id`, `depends_on`, `mutation`, `lock_keys`, `isolation_key`, `kind`).
3. **MUST** launch all ready independent `work` Tasks in one message (Protocol A).
4. **MUST** spawn `Task` with `run_in_background: true` for each PR that needs CI/review watch (Protocol B). After spawn, **main continues** — must not block the main turn on CI; must not `AwaitShell` waiting on that poll worker.
5. Join before merge-ready claims; report merge gate; never merge without explicit user approval (Protocol C).
6. Close with Graphiti-primary PICKUP when ending campaign/session (Protocol D / handoff).

## MUST NOT

- Autonomous merge, force-push, admin merge, weaken tests for green, commit secrets, expand scope without approval.
- Main and poll both pushing the same PR branch.
- Silent waiver of commit/push outside the packet.
- Rewrite `environment/claude-code/autonomy/*.py` or settings allow/deny as part of this skill’s job.

## Authority Order

1. User instructions
2. Campaign authorization packet + Phase-0 graph
3. ADR-0001 + `pr-convergence.json` (via doctrine-map)
4. This SKILL.md and references
5. Supporting skills (`l9-pr-remediation`, optional others per skill-routing)

## Compact Workflow

```text
Packet → Phase-0 → validate locks/budgets
→ spawn ready work Tasks (parallel, one message)
→ spawn background poll Tasks (run_in_background)
→ main continues other ready work
→ join → merge-gate report → human merge
→ Graphiti-primary handoff
```

## Resource Map

- [references/doctrine-map.md](references/doctrine-map.md)
- [references/campaign-authorization-packet.md](references/campaign-authorization-packet.md)
- [references/parallel-nondependent.md](references/parallel-nondependent.md)
- [references/pr-poll-subagent.md](references/pr-poll-subagent.md)
- [references/prompt-templates.md](references/prompt-templates.md)
- [references/join-and-merge-gate.md](references/join-and-merge-gate.md)
- [references/claude-code-bridge.md](references/claude-code-bridge.md)
- [references/skill-routing.md](references/skill-routing.md)
- [references/campaign-handoff.md](references/campaign-handoff.md)
- [references/examples.md](references/examples.md)

## Failure Handling

- Lock conflict → serialize; do not guess.
- Poll exceeds 3 remediation cycles → escalate with blockers.
- No packet → poll watch-only; escalate pushes to main.
- Graphiti down at close → memory-bank fallback only (no dual-write).
