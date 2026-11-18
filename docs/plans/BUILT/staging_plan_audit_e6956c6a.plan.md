---
name: Staging plan audit
overview: GAR audit of the agent-rule plan against origin/Staging. The v3 constitution
  it deletes rules to match is not the checked-out file, so the in-place revision
  binds Staging and blocks those deletions.
todos:
- id: gar-run
  content: 'Write the GAR decision and plan-simple PLAN_DOCUMENT: intervention reconsideration,
    baseline origin/Staging 209bf83c3ef9c8c8fa137c872874515dac3dc9e1, status preflight_blocked,
    original rule deletions cancelled.'
  status: completed
- id: revise-in-place
  content: Project cursor-build markdown onto /Users/ib-mac/.cursor/plans/agent_rule_realignment_07c524c1.plan.md
    from a Staging worktree. If the pipeline binds the sudo branch, write the audited
    projection directly and record that.
  status: completed
- id: stop
  content: Confirm the revised file authorizes no INVARIANTS.md or rule edits, then
    stop. Do not branch, commit, or open a PR.
  status: completed
isProject: false
built: true
status: built
---

# Staging-bound audit of the agent-rule plan

Revise [agent_rule_realignment_07c524c1.plan.md](/Users/ib-mac/.cursor/plans/agent_rule_realignment_07c524c1.plan.md) in place. Do not create a second slug. Do not edit `INVARIANTS.md`, `.cursor/rules/`, `AGENTS.md`, or `CLAUDE.md` in this pass.

GAR (`l9-global-architect` 0.8.4) judgment: `INTERVENTION_RECONSIDERATION_REQUIRED`. The original intervention is "strip a draft wrapper and delete layer, integer-foreign-key, and universal-noupdate doctrine because root `INVARIANTS.md` is already ACTIVE v3." That constitution is not on Staging. Replacing the intervention with "edit the rules anyway" or "quietly retarget v2.2.0" is forbidden.

## Bind

Immutable baseline is `origin/Staging` at `209bf83c3ef9c8c8fa137c872874515dac3dc9e1`. Local `Staging` matches that SHA (`0 0`).

The checkout this audit ran in is `fix/sudo-authorization-markers` at `e8fc691d`. `INVARIANTS.md` is the same blob as Staging (`3abc00c3…`). `run_plan_pipeline.py --workspace .` would stamp that feature branch. Do not. Open PR #395 (`claude-mobile/amazing-archimedes-tx7b4g`, README rewrite) is a different chain. Do not stack this plan on it. PlasticOS publication stays a later branch from Staging into Staging, and only after a reconsidered intervention is admitted.

## What Staging actually has

Root [INVARIANTS.md](INVARIANTS.md) is **Status: Constitutional, Version 2.2.0** (2026-08-30). There is no `Status: ACTIVE`, no `Version: 3.0.0`, no `POS-INV-*` ids, and no draft-admission wrapper to delete. `BAN001` is invariant 20 and stays untouched.

Live law the original plan would delete:

- Invariant 4 requires reference data in XML with `noupdate="1"`.
- Invariant 7 requires higher layers to depend on lower layers and prints the five-layer diagram.
- Invariant 19 already forbids `plasticos_buyer_match_engine` and local matcher authority. That addon is absent. Gate remains the intelligence path.

Observations that are true and still do not authorize the deletions:

- [plasticos_offer/models/offer.py](plasticos_offer/models/offer.py) uses `intake_id = fields.Many2one`. [plasticos_intake/models/intake_match.py](plasticos_intake/models/intake_match.py) still stores `offer_id` as `Integer`.
- [tests/test_repo_dependency_integrity.py](tests/test_repo_dependency_integrity.py) states it does not assert depends order by layer. `test_depends_order_respects_layers` is not in `tests/`. Rule 81 still cites that missing test. Cycles stay with `ci/check_circular_deps.py`.
- Rules 10 and 35 exist. Rule 35 is `alwaysApply: true` and defers external-engine integration. Rule 82 still says cross-layer references use Integer, not Many2one. Rule 98 still names build `36099032`. `AGENTS.md` is `additive_only` in [ops/config/root-file-protection.json](ops/config/root-file-protection.json).
- `docs/campaigns/PlasticOS_Native_First_BRS_v1.0.0_2026-10-25` does not exist on Staging. v3 drafts live under `docs/campaigns/future-add-ons/` and are not the root constitution.

Executing the original todos would make agent text contradict the constitution the plan claims to bind.

## In-place revision

Overwrite the same file through the plan-simple cursor-build projection (`kind: simple`, `execute_via: cursor-build`, `status: current`). Body metadata status is `preflight_blocked`. Keep the filename.

Replace the six pending todos with one blocked todo: record the falsified premise and do not mutate instruction files. Cancel the original deletion, activation, `AGENTS.md`, and alignment-test work as not executable against this baseline.

Required sections the current prose lacks, filled from this audit: metadata, architect framing, immutable baseline (full Staging SHA, branch `Staging`, dirty `false` on that ref), objective, capability preflight, execution envelope (`autonomous_merge: false`, network none, secrets none), side effects (the plan file only), architecture impact (no addon or rule change), rollback (restore the previous plan text), complexity, DAG, property evidence, stress, out of scope, convergence.

Objective success property: a reader of the revised plan can see that rule and constitution edits are not authorized, and that the baseline SHA is Staging `209bf83c3ef9c8c8fa137c872874515dac3dc9e1`.

Execute-via section: press Build only to confirm the block. Build must not edit rules or `INVARIANTS.md`, must not branch from the sudo checkout, and must not run `make campaign`.

Handoff after the file is written: stop. A later realignment needs a new First-Order decision against the Staging constitution, or an admitted v3 landing that this plan does not perform.

## Writer

Prefer `run_plan_pipeline.py` with `--execute-via cursor-build`, `--out-md` set to the existing plan path, and `--workspace` pointed at a detached worktree of `209bf83c3ef9c8c8fa137c872874515dac3dc9e1` so the renderer records Staging. Run the memory prefetch and `write_plan_run.py` first, from the governance clone.

If that pipeline stamps `fix/sudo-authorization-markers`, or refuses a blocked document, do not accept the wrong SHA. Write the audited projection directly into the existing file and say the receipt was not produced.

## Build evidence (auto)

- detected_at: `2026-11-06T17:39:00Z`
- conversation_id: `6dabbc83-f09a-475b-a8b7-a7ab71c8e2ee`
- generation_id: `627a594e-def8-415a-b474-bd88c8836b44`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/6dabbc83-f09a-475b-a8b7-a7ab71c8e2ee/6dabbc83-f09a-475b-a8b7-a7ab71c8e2ee.jsonl`
- todos at build time:
- `gar-run`: completed
- `revise-in-place`: completed
- `stop`: completed
