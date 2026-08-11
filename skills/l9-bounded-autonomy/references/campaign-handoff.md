# Protocol D — Campaign handoff (Graphiti-primary)

Harvests PR #43 / `l9-end-session`: Graphiti is the sole resume SSOT. `memory-bank/` is retired.

## When closing a campaign or session

1. Health-check Graphiti.
2. If healthy: write **one** PICKUP episode (and atomic lessons) to Graphiti.
3. If Graphiti fails: warn and continue handoff/backup — do **not** write `memory-bank/`.

## PICKUP fields for autonomy campaigns

Include at least:

| Field | Content |
|---|---|
| `packet_id` | Campaign authorization packet id |
| `declared_prs` | Open PR numbers still in play |
| `lock_owners` | Which Task/poll owns which `pr:<n>` / path locks |
| `join_status` | pending / joined / blocked |
| `merge_gate` | eligible / not_eligible + failing items |
| `next_actions` | Concrete next steps for the following session |
| `blockers` | Escalations from poll workers (≤3 cycle caps, design questions) |

## Redis

Still set session context for cross-window resume when ending a full session (`l9-end-session` Redis step).
