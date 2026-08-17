<!-- L9_META
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: pipeline
tags: [campaign, pe, compile, bootstrap, l4]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-16
/L9_META -->

# PE activation pipeline

There is one live front door. Do not substitute pec, the intent compiler,
L4, or a hand-assembled compile/accept/bootstrap sequence.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

`run_campaign.py` is the tunnel. If that command exits nonzero, stop and
report the runner output. Do not continue the campaign by calling inner
scripts.

## What the runner already does

Order inside `run_campaign.py` only (not an operator checklist):

| Stage | Runner owns |
|---|---|
| stack-proof | infer API/MCP/install/Docker; Context7 then official GET; write `$HOME/.l9/primed/<id>/stack-proof.json`; refuse on miss. Runs before emit, including `until=activate`. |
| activate | brief IR or activate YAML; isolate worktrees; emit file set |
| blueprint | compile + template validate |
| admit | EVID-001 on reconciled target HEAD; accept blueprint |
| bootstrap | pec bootstrap with no draft flag; quarantine leftovers |
| arm | draft/register every task; claim TASK-001; STACK.json; push `campaign/<id>` to GitHub before execute |
| execute | pec prepare worktree; write/commit/verify/complete; claim next; task PRs require remote `campaign/<id>` |
| pr | stacked task PRs; never `PR_BASE=main`; host `make pr` after execute |
| close | pec close + host ledger + `campaigns/COMPLETED/<id>/` |

`program-execution.intent.v1` and `pe-<hash>` workspaces are refused.
`--admission-draft` is not a live path. Host-only merge is not program close.
`CAMPAIGN_UNTIL` other than the live default is refused unless
`L9_CAMPAIGN_UNTIL_DEBUG=1` (runner unit tests only).
`make campaign` is the Phase 0 admission act; `acknowledged_at` stays null
and `program_deploying` stays false. Do not forge the timestamp.

## Trees the runner names

`LAUNCH.json` is the live SSOT after arm. Do not invent a fourth tree.

| Tree | Path | Role |
|---|---|---|
| Host isolate | `$L9/gov-worktrees/<id>` on `feat/<id>` | emit files only |
| Target | `$L9/program-worktrees/<id>` | reconcile + campaign/<id> |
| Write tree | `$L9/programs/<id>/worktrees/TASK-00N` | pec prepare mutation checkout |

Never mutate the dirty primary. Never treat `--single-branch main` as the
only history once stacking is required. Do not open the operator memo.
Do not attach to a leftover `pe-<intent-hash>` workspace.

## Stop conditions

- Runner FAIL → report; do not retry with `--admission-draft`
- Dirty primary or dirty target → runner refuses; do not `git switch`
- Memo with no numbered tasks → runner STOP; do not invent tasks
- Stacked PR red → remediate that STACK.json PR only; do not leave the tunnel
