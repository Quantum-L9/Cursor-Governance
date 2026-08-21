# Cursor plans store

Machine-global Cursor plans for every workspace on this Mac.

`~/.cursor/plans` is a symlink here. Each consumer workspace still uses
`.cursor/plans` → `~/.cursor/plans`. Heal with
`ops/scripts/setup_workspace_symlinks.sh` (writes `$HOME/.cursor/l9-plans-store`).

## Naming

New and live plans are `snake_slug_M-D-YY.plan.md` (US month-day-year of the
instance, same shape as `WIP/<M-D-YY>/`). Example: `pe_unified_loop_8-20-26`.
The stamp is not a sort key and not a folder. Historical shelves may still
end in ISO `YYYY-MM-DD` or an 8-hex id — do not mass-rename them.

Companion `.plan.json` / `.activate.yaml` files stay next to their `.plan.md`.

## Shelves (existing mechanics)

Only **top-level** `*.plan.md` files are live for Cursor Build and session-start
`l9-plan-audit` (root glob only). Folders hold everything else.

| Location | Meaning |
|---|---|
| *(root)* | Live queue — scored below. New work lands here. |
| `built/` | All todos `completed` or `cancelled` |
| `backlog/` | Open work, parked — not this session's queue |
| `archive/` | Non-plan harvest and other dead weight |
| `archive/superseded/` | Older same-slug copy or body `status: superseded` |

`_TEMPLATE.plan.md` stays at the root. Do not author new plans inside the folders.

## Score law (not filename)

Cross-plan order uses mechanics already in the repo:

1. **YNP urgency** (`l9-ynp`) — open blocker / in_progress / publish+start path first.
2. **First-order leverage** (`skills/l9-plan/references/first-order-leverage.md`) —
   shared root cause > contract clarification > validation automation > local symptom.
3. Intra-plan `leverage.ranked_todo_ids` / `leverage_rank` when a PLAN_DOCUMENT exists.

Do not invent a second score schema. Do not make `pe/`, `ci/`, or date folders.

## Live queue (highest first)

1. `worktree_parent_clone_8-20-26` — shared isolation root cause (parent ≠ live SSOT)
2. `make-program-execution-start-cleanly-gap-only_8-15-26` — PE start still open
3. `pe_fast_002_prepare_8-20-26` — in_progress prepare/resume
4. `in-flight_pr_census_8-20-26` — one collision engine for sessionStart + `make pr`
5. `l4_publish_allow_8-20-26` — sole publish path
6. `pe_unified_loop_8-20-26` — loop seams on what already landed (JSON companion now dated)
7. `pe_pipeline_fix_program_8-20-26` — factory friction (JSON companion now dated)
8. `claude_code_env_contract_8-20-26` — one session contract
9. `toolchain_lock_percolation_8-20-26` — pins percolate without per-repo edits
10. `core-identical_toolchain_locks_8-20-26` — same lock family
11. `tier2-schema-proposer-tests_8-20-26` — in_progress validation (narrower)

`pipeline_assembly_fill` moved to `built/` — audit `overall_autonomy_percent: 100` and every GAP id `Resolved` on this tree. Cursor todos were never flipped.

Next play: `/ynp` against this list. Do not auto-Build from the shelf.
