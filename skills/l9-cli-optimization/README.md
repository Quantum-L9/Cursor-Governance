# Optimize CLI PR Pack v2

Turn an underutilized, verified repository-owned capability — dormant or miswired code, off-by-default features, unread config, unused signals — into working, deployed code and a reproducible PR commit pack. Removing a verified CLI throughput bottleneck is one branch of the same mission.

Version 2 evolves the Skill from a mostly linear workflow into an adaptive evidence-driven operator:

- route by ownership, evidence state, risk, divergence, latent wiring, and write authority;
- activate only material proof obligations;
- maintain an auditable evidence and decision ledger;
- synthesize every finding into targets and leverage-ranked options;
- converge in at most three cycles;
- package code, performance evidence, deployment, rollback, and handoff together.

The Skill never bypasses provider quotas, billing, licensing, authorization, abuse controls, or external limits.

## Two modes

1. **Standard optimization (default).** Diagnose one underutilized capability, verify reachability, and package the exact change as a PR commit pack with before/after evidence, deploy/rollback, and handoff. The core pipeline refuses anything `dormant_by_design` (Identity-Lock #1).

2. **Full-throttle activation.** Enable a repository's off-by-default feature flags *at scale*, prove each against the repo's own tests in an isolated `git worktree`, back out any flag that regresses tests, and package the flip as a **review-required** PR (never auto-merged). This is a separate, self-contained mode that consciously relaxes Identity-Lock #1's `dormant_by_design` clause **for testing only** — paid for with a polarity-aware danger block-list (never flips delete/deploy/charge/auth-disable/… flags), staged-flag holds, empirical back-out, worktree isolation, and a human merge gate. The core pipeline above is untouched. See `references/full-throttle-activation.md` and `AGENTS.md`.

```bash
# plan first (mutates nothing), review the danger exclusions, then apply
python3 scripts/full_throttle.py <repo> --mode plan
python3 scripts/full_throttle.py <repo> --mode apply --test-cmd "<cmd>" --output ft.json
python3 scripts/build_flag_activation_pack.py --report ft.json --repo-root <repo> --output <dir>
```

## Nuances every operator must know

- **`dormant_by_design` is only relaxed in full-throttle mode, only for testing.** The standard PR-pack builder (`build_commit_pack.py`) still exits 2 on `dormant_by_design:true`.
- **Danger is polarity-aware.** `enable_delete=False→True` (enables a destructive action) and `disable_auth=False→True` (disables a control) are *both* danger and are never flipped.
- **"All except a danger block-list" is proven by tests, not assumed.** Any flipped flag that regresses the repo's tests is reverted and reported `empirically_unsafe`.
- **Nothing is auto-merged.** A full-throttle pack is `auto_merge=false`, labeled REVIEW REQUIRED; a human opens/merges the PR.
- **A run that flips nothing is a valid outcome** (all danger-excluded or all regress → BLOCKED pack, exit 2), not a failure to force.
- **Isolation.** All flip+test happens in a throwaway worktree; the real working tree is never mutated.

Run `python3 scripts/self_test.py` before packaging (it is the single aggregate gate and now also proves the full-throttle mode).

## Requirements

Python 3.10+. Install dependencies before running the scripts:

```bash
pip install -r requirements.txt   # jsonschema>=4, PyYAML>=6
```
