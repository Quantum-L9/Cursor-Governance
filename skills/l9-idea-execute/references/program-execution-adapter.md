# Program Execution adapter

## Status

**EVOLVING EXECUTOR CONTRACT. VERIFY LIVE BEFORE EVERY MUTATING HANDOFF.**

This file records the 2026-09-02 baseline and the discovery procedure. When Program Execution changes, update this adapter reference and regression fixtures without redesigning the rest of `l9-idea-execute`.

## Live discovery order

Inspect current `Quantum-L9/Cursor-Governance` main, prioritizing:

1. `skills/l9-pe-campaign-activate/SKILL.md`
2. `skills/l9-pe-campaign-activate/references/source-contract.md`
3. `skills/l9-pe-campaign-activate/references/pipeline.md`
4. `environment/program-execution/scripts/campaign_input.py`
5. current `Makefile` campaign target/front door
6. current PE schemas only when the public adapter contract points to them

Do not use historical WIP or old plans as authority over current live files.

## 2026-09-02 baseline

Observed current public front door:

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

Current activation skill states that this is the only live Program Execution campaign front door. PE owns Blueprint/Program Lock, readiness, worktrees, provider-neutral execution, Controller verification, evidence, and **local commits only**.

Publication and merge are outside PE's authority on this baseline.

Current structured activate input is centered on one `target.repository_id` plus tasks. The current campaign-brief implementation plan explicitly states that its v1 compiler is single-target and multi-repo campaigns are out of scope.

Therefore:

```yaml
baseline_capabilities:
  single_target: true
  multi_target: false
```

This is a baseline observation, not a permanent assumption.

## Compatibility gate

For each PE-shaped execution unit:

1. derive target repositories and dependency topology from the Execution Graph;
2. inspect current live PE admission contract;
3. record an Adapter Capability Snapshot;
4. run `scripts/check_adapter_capability.py` against the unit and snapshot;
5. if compatible, compile current PE-native `INTENT` without losing source semantics;
6. invoke only current `make campaign INTENT=...` or its future explicitly documented replacement;
7. if incompatible, return `EXECUTOR_CAPABILITY_GAP`.

## Multi-repo invariant

Never convert one atomic multi-repository campaign into:

```text
campaign A(repo1) + campaign B(repo2) + campaign C(repo3)
```

merely because current PE is single-target. Doing so would move wave scheduling, joins, rollback ordering, and terminal convergence into Idea Execute.

Keep the campaign blocked until PE can represent it or the user explicitly changes the architecture/atomicity.

## Native input choice

Prefer structured machine input when the current PE public contract supports it because Idea Execute already holds structured requirements and dependencies.

Do not serialize structured authority into prose merely to make another compiler rediscover it unless the current live PE contract requires prose.

Do not hand-author PE internals beyond the documented public input.

## Terminal boundary

On the 2026-09-02 baseline, successful PE execution terminates at verified local commits. Do not treat that as push, PR, merge, or production deployment.
