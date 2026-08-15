# Agent Execution Prompt — L4 Autonomy (plan.pe.pipeline-fixes.v1)

Download this file and paste it into an agent session (Claude Code or Cursor)
with L4 local autonomy enabled to execute the approved plan
`plan.pe.pipeline-fixes.v1` (repair the Program Execution pipeline).

---

## PROMPT (paste verbatim)

You are executing the operator-approved plan `plan.pe.pipeline-fixes.v1`:
"Repair the Program Execution pipeline (compile→admit→verify loop + gate fixes)".
The full plan text is at `/Users/macm2/.claude/plans/cozy-hopping-raccoon.md`
(in Cursor: `.cursor/plans/cozy-hopping-raccoon.md`). Treat the plan's
Execution envelope, Success properties SP-01..SP-08, and Out-of-scope sections
as binding authority. Execute under L4 local autonomy doctrine:

1. **Preflight (read-only).** Lock the baseline:
   - `git -C $HOME/.cursor-governance fetch origin main`
   - record `git -C $HOME/.cursor-governance rev-parse origin/main` (full SHA);
   - if it differs from the plan's locked SHA, STOP and report drift.
   - Confirm a clean dedicated worktree exists on branch `pe/pipeline-fixes`
     created from `origin/main` (rule 46: KERNEL/PE overlay landings always a
     new branch from origin/main — never the primary clone's dirty tree).
2. **L4 begin** on that worktree:
   `python3 $HOME/.cursor-governance/ops/autonomy/l4_local.py --workspace <worktree> begin --contract-id plan.pe.pipeline-fixes.v1 --base origin/main`
3. **Execute the plan's todos in DAG order** (critical path:
   todo-01 → todo-02 → todo-03/04 → todo-05 → todo-09 → todo-10; todo-06,
   todo-07 parallel lanes; todo-08 only after todo-06). Mutations are confined
   to the plan's write_allow envelope:
   - `environment/program-execution/scripts/` + `core/…-controller-template/` +
     `core/…-blueprint-template/schemas/` (new additive files only)
   - `ops/autonomy/` + `tests/ops/autonomy/`
   - `environment/agents/adapters/claude-code/hooks/`
   Never touch: `ops/secrets`, campaign ledgers, the primary clone's dirty
   files, existing schema required fields (no validator relaxation).
4. **Prove before claiming.** After each todo, run the plan's evidence
   commands and record results:
   - `python3 -B -m unittest scripts.tests.test_compile_campaign_source` (PE root, PYTHONPATH=PE_ROOT)
   - `python3 -B -m unittest discover -s core/program-execution-controller-template/scripts/tests -p 'test_*.py'`
   - `python3 -m pytest tests/ops/autonomy/ -q`
   - `make program-execution-core-validate program-execution-campaign-schema`
   - `PYTHONPATH=<PE_ROOT> python3 -B scripts/run_conformance.py` + `scripts/validate_manifest.py`
   - `make sync-generated` after adding any file under `environment/program-execution/`
     (plus regenerate a core template's own `MANIFEST.yaml` via its
     `scripts/instantiate.py` `write_manifest` when that template changed).
   A todo is complete only when its success property (SP-*) passes with
   evidence, never on exit-0 alone.
5. **Kernels, then release.** On the finished tree run
   `kernels/Recursive Alignment.md` then `kernels/Validate & Repair.md`
   (audit + repair passes), then:
   `python3 $HOME/.cursor-governance/ops/autonomy/l4_local.py --workspace <worktree> record-kernels`
   `python3 $HOME/.cursor-governance/ops/autonomy/l4_local.py --workspace <worktree> authorize-release`
6. **Publish.** Scoped commit (explicit pathspecs only, never `git add -A`),
   then `cd <worktree> && OPEN_PR=1 PR_REMEDIATE=0 PR_BASE=origin/main make pr`
   (governance repo only — this plan creates NO new repositories and lands
   NOTHING in the Odoo repo). If the L4 hook denies because the session
   workspace holds another session's release receipt, STOP and ask the
   operator for `L9_LOCAL_PUSH_AUTHORIZED=<reason>` — never set it yourself.
7. **Converge.** Remediate via `l9-pr-remediation` to merge-eligible; merge
   open PRs bottom-up only after direct, in-session operator authorization
   (human-set `L9_MERGE_AUTHORIZED`). Autonomous merge stays false
   everywhere else.

**Stop conditions (report, do not improvise):** baseline drift; any blocking
SP fails; envelope breach; validator weakening required; another live session
prunes or mutates your worktree (rule 49 — re-create from your pushed branch,
never fight over the shared clone); Graphiti/memory gate denies a governed
write with no operator path.

**Definition of done:** SP-01..SP-08 all passed with recorded evidence; branch
pushed; PR green+mergeable (or merged bottom-up after direct, in-session
operator authorization);
rollback contract still valid; no out-of-scope diffs.

---

## Context (why this plan exists)

During campaign `l9-ecosystem-fix-plan` (2026-08-14/15) the Program Execution
pipeline required six classes of manual operator intervention: the compiler
emitted blueprints that failed instantiated validation four ways; acceptance
and evidence collection had no tools; controller verify only saw dirty
worktrees; the L4 gate could not see release receipts in other worktrees; the
memory front-door could not be repaired mid-session; and the isolation gate
matched heredoc data as commands. This plan closes each defect at its root.
