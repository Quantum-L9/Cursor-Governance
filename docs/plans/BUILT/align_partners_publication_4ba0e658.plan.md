---
name: Align partners publication
overview: Revise the Partners-first plan in place so its baseline, logistics claim,
  and publication handoff match the live repo, and so Cursor Build publishes with
  make pr into Staging from a clean worktree.
todos:
- id: record-alignment
  content: Add the Recursive Alignment YAML record and correct the logistics claim,
    baseline, and failed P2.
  status: completed
- id: bind-publication
  content: Replace PR_STACK=auto and origin/main with a clean origin/Staging worktree
    and plain make pr, in the banner, stub, and out_of_scope/write_deny.
  status: completed
isProject: false
built: true
status: built
---

# Align the Partners-first plan to the repo

Edit only [docs/campaigns/11-03-26/PLAN Partners First Native Opportunity Matching Canonical Revision.md](docs/campaigns/11-03-26/PLAN%20Partners%20First%20Native%20Opportunity%20Matching%20Canonical%20Revision.md). Do not edit [.cursor-commands/kernels/Recursive Alignment.md](.cursor-commands/kernels/Recursive%20Alignment.md). Do not implement T02–T10, pop a stash, or run `make pr` in this revision.

The kernel stays audit-only. This update is the authorized correction of the plan. Record the audit in the plan with the kernel’s YAML fields (`audit_status`, `readiness_status`, `convergence_status`, `target_binding`, `minimum_safe_next_action`, and the rest of the output contract).

## Facts the plan currently contradicts

- Execution baseline `7d23e632` is not an ancestor of `origin/Staging` `c8e7efebb03d79e3a5b220b8a7568a750918b2ed`. Local `Staging` is still `4a6af0b` and is 36 commits behind `origin/Staging`.
- The plan file is untracked on `docs/brs-documents-logistics-ownership` at `8f599ab`. That branch is an unrelated open PR, not the publication checkout.
- `PR_STACK=auto` cannot authorize this work. `resolve_stack_tip.py` looks for pull requests into `main` and exits 2. Open pull requests target `Staging` and are siblings. [scripts/pr_stack_parent.sh](scripts/pr_stack_parent.sh) accepts `Staging` as the publication base. A non-`Staging` base must be one open parent PR.
- `contracts/SCHEMA_APPROVAL_2026-11-04.md` is not in the tree. The only copy is untracked inside `stash@{5}`. P2 is not passed. Status stays `draft`. V1–V7 stay `not_run`.
- P1 still matches this checkout: [plasticos_crm_bridge/__manifest__.py](plasticos_crm_bridge/__manifest__.py) is `19.0.3.4.19` and comments out `plasticos_matching`; [plasticos_offer/models/offer.py](plasticos_offer/models/offer.py) still comments out `match_result_id`.
- The logistics section is false. [plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md](plasticos_logistics/business_rules/BRS-POS-10-linda-logistics-commercial-and-physical-communication.md) exists, is frozen pending adoption, and has `NOT_RUN` evidence. BRS-POS-04, 05, 06–08, 11, and 12 still must not move.

## Publication handoff to write

Replace the `PR_STACK=auto` / `origin/main` instructions in the execute banner, the “Execute via Cursor Build” section, convergence next-action, and the machine stub `command_ref`.

- Start a new clean worktree with `agent_worktree_start.sh --base origin/Staging` and `L9_TASK_BASE_AUTHORIZED` set because PlasticOS integration is `origin/Staging`, not `origin/main`, and sibling Staging PRs are not a stack parent.
- Fetch `origin/Staging` at execution start. Refuse the local `Staging` ref and refuse `7d23e632`.
- After the todos: scoped commit, `l4_local.py authorize-release`, then `make pr` with no `PR_STACK`. Display the PR URL.
- Do not run `make campaign`, do not write `Lock: origin/main`, and do not stack onto `docs/brs-documents-logistics-ownership`.

## Contract edits in the same file

- Overview, metadata, mission, and immutable baseline: integration commit is fetched `origin/Staging` `c8e7efe`; old SHAs are historical drift. `baseline_verified` stays false until that fetch is repeated. `drift_detected` becomes true for `7d23e632`.
- P0 pass criterion becomes: clean worktree HEAD equals fetched `origin/Staging`. P2 status becomes failed until the ledger is on the branch. Leave P1 as still true on this checkout, and leave P3 and P4 unverified rather than passed.
- Correct the logistics paragraph to name the existing BRS-POS-10 file and its pending-adoption status. Add `plasticos_logistics/business_rules/` and `plasticos_documents/business_rules/` to `write_deny` and the machine-stub list. Add those chapters, plus “do not move BRS-POS-04, 05, 06–08, 11, 12”, to Out of scope and the stub `out_of_scope`.
- Keep the follow-on inactive. Do not add a todo. Do not mark the plan `executable`.

The feature build remains blocked on admitting the schema ledger. This revision makes the publication ceremony legal once that ledger is on the branch.

## Build evidence (auto)

- detected_at: `2026-11-05T19:19:10Z`
- conversation_id: `3daa1fcf-bcbe-4111-b358-32762565f298`
- generation_id: `f6657cee-c5ac-49ac-9852-150b535de89f`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/3daa1fcf-bcbe-4111-b358-32762565f298/3daa1fcf-bcbe-4111-b358-32762565f298.jsonl`
- todos at build time:
- `record-alignment`: completed
- `bind-publication`: completed
