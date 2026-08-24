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
`l9-plan-audit` (root glob only). Folders hold everything else. On-demand
organize is `/l9-audit-plans` (not the sessionStart skill).

| Location | Meaning |
|---|---|
| *(root)* | Live queue — **current unbuilt** plans only (all todos still `pending`). New work lands here. |
| `partially-built/` | Started but not finished — at least one todo `completed` or `in_progress` |
| `built/` | All todos `completed` or `cancelled`, or frontmatter `built: true` / `status: completed` |
| `backlog/` | Open unbuilt work, parked — not current |
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

Current unbuilt only. Partial work is in `partially-built/` (`pe_fast_002_prepare_8-20-26`, `tier2-schema-proposer-tests_8-20-26`, `plan_kernel_auto-pass_3d1d3ae4`).

1. `worktree_parent_clone_8-20-26` — shared isolation root cause (parent ≠ live SSOT)
2. `make-program-execution-start-cleanly-gap-only_8-15-26` — PE start still open
3. `in-flight_pr_census_8-20-26` — one collision engine for sessionStart + `make pr`
4. `l4_publish_allow_8-20-26` — sole publish path
5. `pe_unified_loop_8-20-26` — loop seams on what already landed (JSON companion now dated)
6. `pe_pipeline_fix_program_8-20-26` — factory friction (JSON companion now dated)
7. `claude_code_env_contract_8-20-26` — one session contract
8. `toolchain_lock_percolation_8-20-26` — pins percolate without per-repo edits
9. `core-identical_toolchain_locks_8-20-26` — same lock family
10. `plan_template_org_fields_8-20-26` — project leverage fields into plan frontmatter
11. `infisical_gha_oidc_conformance_8-20-26` — OIDC on the existing secrets plane
12. `ra_root-docs_pointer_09ff9571` — Recursive Alignment pointer, not dump
13. `pe_eie_scoped_campaign_5469bc8f` — EIE scoped campaign

`pipeline_assembly_fill_8-20-26` is in `BUILT/`. The still-open
`pipeline_assembly_fill_25e09ac8` stays in `backlog/` (todos still pending).

Next play: `/ynp` against this list. Do not auto-Build from the shelf.
