---
name: l9-bounded-autonomy
description: >-
  bounded autonomy campaign SOP for Cursor — parallel non-dependent Tasks,
  background PR-poll subagents while main continues, campaign authorization
  packet, join/merge-gate without autonomous merge. use when user runs
  /autonomy, needs PR convergence while continuing other work, or fans out
  independent lanes under ADR-0001 / pr-convergence budgets.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, autonomy, parallel, pr-poll, subagent, campaign, merge-gate]
  owner: igor_beylin
  status: active
  version: 1.0.0
  updated: 2026-08-02
---

# Bounded Autonomy (Cursor SOP)

> This is a Cursor host/presentation SOP. Root `autonomy/` is peer-neutral and
> authorization is bound through canonical peer topology.

## Purpose

Map Claude Code ADR-0001 / pr-convergence law onto Cursor: fan out non-dependent work and deploy background PR-poll subagents while the main agent continues — without autonomous merge.

## Core Contract

| Item | Value |
|---|---|
| Lanes | Max 4 total / 2 mutation |
| Merge | Campaign/make pr: no. `/l9-pr-remediation` Converge: yes (ordinary squash) |
| PR wait | MUST spawn background poll; main continues |
| Authority | Campaign authorization **packet** (never “envelope”) |
| Claude runtime | Untouched; bridge to `autonomy/cli.py` on Claude surface |

## MUST

1. Create a **campaign authorization packet** via `/autonomy` or explicit user campaign phrase before remediation pushes.
2. Build Phase-0 action graph (`id`, `depends_on`, `mutation`, `lock_keys`, `isolation_key`, `kind`).
3. **MUST** launch all ready independent `work` Tasks in one message (Protocol A).
   On a governed native-Cursor host, obtain a root-Autonomy admission token per
   Task via `autonomy/adapters/cursor/host_bridge.py` **before** launching and
   embed only that opaque marker (`L9_ADMISSION_TOKEN=…`) in the prompt — the
   lifecycle hooks deny uncorrelated native Tasks, and Task prose is never
   authority.
4. **MUST** proceed **L4 local autonomy** (CANONICAL_LAW §6.2 / Profile `l4_local_autonomy`): stacked-branch local commits through program/contract execution with **no mid-execution push**. After local finish → run `kernels/Recursive Alignment.md` then `kernels/Validate & Repair.md` → `ops/autonomy/l4_local.py authorize-release` → `PR_REMEDIATE=0 make pr`. Do **not** remediate. Do **not** merge. Campaign work lands on `campaign/<campaign_id>` with `PR_BASE` set to that branch — never against `main`.
5. Do **not** spawn `l9-pr-remediation` poll workers unless a human set `PR_REMEDIATE=1`.
6. Do **not** merge from `/autonomy` or the campaign path. Merge only after
   `/l9-pr-remediation` writes `ops/autonomy/authorize_merge.py --all-open`
   and each PR is green + mergeable. An L4 release receipt is not merge authority.
7. Close with Graphiti-primary PICKUP when ending campaign/session (Protocol D / handoff).

## MUST NOT

- Merge without `/l9-pr-remediation` (or `L9_MERGE_AUTHORIZED`); force-push, admin merge, weaken tests for green, commit secrets, expand scope without approval.
- Mid-execution `git push` / `gh pr create` / `make pr` before L4 `release_authorized`.
- Main and poll both pushing the same PR branch.
- Silent waiver of **push/merge** outside the packet. Local commit is standing.
- Rewrite `environment/program-execution/peer_execution/autonomy/*.py` or settings allow/deny as part of this skill’s job.

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

- [environment/contracts/autonomy/MANIFEST.yaml](../../environment/contracts/autonomy/MANIFEST.yaml) — first-class autonomy family registry (subordinate to PE)
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
- Graphiti down at close → warn and continue; do **not** fall back to memory-bank/ (retired).
