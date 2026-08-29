# Agent initiation — `l9-agent-doc-plane`

Copy this prompt into a **new** Cursor (or Claude Code) session. Do not run it on the dirty primary clone.

```text
You are executing Program Execution campaign `l9-agent-doc-plane`
(Continuous Agent Doc Plane) under PE + L4 autonomy.

## Load first
1. @environment/program-execution
2. @autonomy / skill `l9-bounded-autonomy`
3. Campaign pack:
   environment/program-execution/campaigns/l9-agent-doc-plane/
     INTENT.yaml
     INTENT_RESOLUTION.yaml
     CAMPAIGN_SOURCE.yaml
     AGENT_INITIATION.md   (this file — launch mechanics only)
4. Human plan (mission SSOT): ~/.cursor/plans/rich_root_agent_docs_557cc65b.plan.md
5. Skills: l9-update-agent-docs, l9-skill-compiler, l9-wire-skill-into-repo,
   kernels/Improve.md, kernels/Recursive Leverage.md, kernels/Recursive Alignment.md,
   kernels/Validate & Repair.md

## Authority
- Campaign source owns operator intent and campaign semantics.
- Intent.yaml is the goal. Intent_resolution.yaml is the derived requirement bind.
- This prompt owns launch mechanics only. It does not widen Task Card ceilings.
- Program lease is authoritative. Do not acquire a competing Graphiti task claim.
- L4: local commits only until `python3 ops/autonomy/l4_local.py authorize-release`.
- Launching this campaign / clicking Build IS merge authorization for this stack
  after green+mergeable. Older open PRs merge bottom-up first.

## W0 — do this before any product edit
1. Refuse the dirty primary (`fix/ci-required-contexts-wip-only` or any mixed WIP).
2. Work from a clean worktree of Quantum-L9/Cursor-Governance at refreshed origin/main
   on integration branch `campaign/l9-agent-doc-plane`.
   Suggested: $HOME/.l9/program-worktrees/l9-agent-doc-plane
   Pack home: environment/program-execution/campaigns/l9-agent-doc-plane/
3. Lock full SHA. Write it into the program runtime root
   $HOME/.l9/programs/l9-agent-doc-plane/ (not into the immutable CAMPAIGN_SOURCE.yaml).
4. `python3 ops/autonomy/l4_local.py begin --contract-id l9-agent-doc-plane`
5. Compile CAMPAIGN_SOURCE.yaml through the PE pair
   (Blueprint v2 + Controller v2). Validate template then instantiated.
6. Create Program Lock. Admit TASK-001 only.
7. stop_and_replan if HEAD ≠ locked SHA or Program Lock drifts.

## Execute
W0 admit → W1 Improve skill create-if-absent → W2 Recursive Leverage + wire →
W3 extractor + managed fact blocks + sync_generated_artifacts →
W4 apply library on Quantum-L9/l9-repo-template + inventory + sync_ci fetch allowlist →
W5 make pr-check / make verify → RA + VR kernels → authorize-release →
scoped PRs → l9-pr-remediation → merge this stack.

## Hard denies
- No SessionStart rewrite of the 15-file library
- No LLM rewrite of AGENTS.md in CI
- No dump of CG CANONICAL_LAW.md / ORG_INVARIANTS.yaml into the template
- No delete/rewrite of sync-ci community-health files
- No clobber of `<!-- BEGIN L9 FORMATTER OWNERSHIP` or `PROGRAM_EXECUTION_ADAPTER_LAYER_V1` blocks
- No mid-execution push
- No force-push / admin-merge / hard-reset
- No fabricated CI/hook/skill counts — extractor or Unknown

## Success
Blocking properties in CAMPAIGN_SOURCE.yaml GATE-001..006 and the plan SP-* table.
Derived facts stay accurate because make pr heals/checks managed blocks.
Authored prose is never auto-rewritten.

## Handoff
Controller recommends a terminal verdict. AUTH-001 (Igor Beylin) declares it.
Write receipts under $HOME/.l9/programs/l9-agent-doc-plane/ — not into the campaign source tree.
```

## Operator one-liner

After this pack is on a branch from `origin/main`:

```bash
# from a clean Cursor-Governance worktree
python3 ops/autonomy/l4_local.py begin --contract-id l9-agent-doc-plane
# then paste the fenced prompt above into a new agent session
```
