<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: mode_contract
tags: [macos, storage, modes, hitl, autonomy]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
/L9_META -->

# Modes

## Purpose

Define the three execution modes, their gates, and where the agent must stop.

## Mode selection

| User signal | Mode |
|-------------|------|
| diagnose / what's using disk / low disk / triage storage (no fix) | `diagnose` |
| repair / clean it / purge caches after diagnosis / HITL | `repair` |
| autonomy / no review / skip HITL / just clean it without asking | `autonomy` |
| unspecified | `diagnose` |

Never escalate diagnose → repair → autonomy without a matching user signal.

## diagnose

1. `scripts/00-diagnose.sh` — df, APFS, snapshots, Spotlight, path presence, docker/conda facts.
2. `scripts/07-inventory-noise.sh` — bounded sizes of allowlisted caches, Docker reclaimable, Trash.
3. `scripts/08-focus-layout.sh` — home and Data layout (CloudStorage skipped).
4. `scripts/01-summarize.sh` — evidence summary, no cleanup presented as already done.
5. `scripts/09-emit-findings.sh` — writes `handoffs/current/FINDINGS.txt` (human) and `findings.json` (machine).
6. Agent opens **FINDINGS.txt** for the human. Repair later reads **findings.json**.
7. **Stop.** Do not write `.env` approvals. Do not apply.

## repair

Requires `.state/diagnosis.complete` from this machine.

1. `init-env` if `.env` is missing (never overwrite an existing `.env`).
2. Select only Phase A actions from `handoffs/current/findings.json` (`repair.phase_a_actions`). Fall back to noise inventory if JSON is missing.
3. Set those action approval flags true; leave Mail/offload/delete/Spotlight reindex false.
4. Leave `APPLY_CONFIRMATION='NOT_APPROVED'`.
5. `validate` + `plan`.
6. **Stop and show the plan.** Wait for an explicit yes in chat.
7. On yes: set `APPLY_CONFIRMATION='I_APPROVE_THIS_PLAN'`, re-validate, `apply`, `verify`.
8. On no / edit: do not apply.

## autonomy

Requires the user to request autonomy in this session (or a later session that cites a trusted diagnosis).

1. Run the diagnose pipeline if no current diagnosis receipt exists.
2. Select the same allowlisted actions as repair.
3. Set `APPLY_CONFIRMATION='I_APPROVE_THIS_PLAN'` and `AUTONOMY_CONFIRMATION='I_AUTHORIZE_SAFE_NOISE_PURGE'`.
4. `validate` + `plan` + `apply` + `verify` without a second ask.
5. Still fail closed on Unknown, digest mismatch, or non-allowlisted actions.

`AUTONOMY_CONFIRMATION` is written by `run autonomy` only. Repair must not set it.

## Confirmation values

| Variable | diagnose | repair (pre-HITL) | repair (post-yes) | autonomy |
|----------|----------|-------------------|-------------------|----------|
| `TRIAGE_MODE` | `diagnose` | `repair` | `repair` | `autonomy` |
| `APPLY_CONFIRMATION` | `NOT_APPROVED` | `NOT_APPROVED` | `I_APPROVE_THIS_PLAN` | `I_APPROVE_THIS_PLAN` |
| `AUTONOMY_CONFIRMATION` | `NOT_AUTHORIZED` | `NOT_AUTHORIZED` | `NOT_AUTHORIZED` | `I_AUTHORIZE_SAFE_NOISE_PURGE` |

## Agent reporting

After diagnose, report:

```
Storage triage — diagnose
Host: <name>  Free: <N> GiB of <total>
Reclaimable noise (allowlisted): ~<X> GiB
- brew/npm/pip/conda caches …
- docker unused containers/images …
- trash …
Proposed repair actions: purge_stale_caches, docker_prune_unused, empty_trash
Next: say "repair" to plan with HITL, or "autonomy" to purge without review.
```
