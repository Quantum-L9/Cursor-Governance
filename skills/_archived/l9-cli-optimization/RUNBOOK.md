# Operator Runbook

1. Verify the target repository, base ref, and worktree state.
2. Reuse the newest validated prior artifact before new research.
3. Classify bottleneck ownership, evidence state, risk, divergence, latent wiring, and output mode.
4. Run `scripts/route_optimize.py` or create the equivalent `execution_route`.
5. Build the initial evidence and decision ledger.
6. Collect all performance, wiring, divergence, resource, deployment, and validation findings.
7. Synthesize findings into `CLI-FND`, `CLI-TGT`, and `CLI-OPT` records.
8. Apply leverage scoring and freeze selected options.
9. Execute the highest-value unresolved proof obligation.
10. Update the ledger after every bounded probe, implementation, or validation action.
11. Stop when all active obligations are satisfied or a blocker is proven. Never exceed three cycles.
12. Build with `scripts/build_commit_pack.py`.
13. Validate with `scripts/validate_commit_pack.py`.
14. Deliver the `.tar.gz` pack, or perform GitHub writes autonomously when a write connector exists.

## Diagnosis tooling

- `python3 scripts/scan_capabilities.py <repo>` — advisory scan for candidate underutilization gaps and entrypoints (verify before acting).
- `python3 scripts/measure.py --before <cmd> --after <cmd> [--capture]` — comparable before/after proof block (throughput or functional).

## Full-throttle activation mode (enable off-by-default flags at scale)

A separate, opt-in mode; see `references/full-throttle-activation.md`. Never auto-merged.

1. **Inventory + classify (read-only):** `python3 scripts/flag_inventory.py <repo>`. Read the `summary`:
   - `flip_candidates` — non-danger, non-staged, runtime, *and* has a consumer.
   - `held_danger` — polarity-aware block-list (enables a dangerous action OR disables a safety control); never flipped.
   - `held_staged` — `dormant_by_design` (Identity-Lock #1); never flipped.
   - `needs_wiring` — `consumer_evidence=none`: declared but nothing reads it; flipping is a no-op — it needs a *wiring change*, not a flip. (`consumer_evidence=unknown` on a generic `enabled` leaf → verify the parent block/registry manually.)
   - `held_non_runtime` / `held_infra` — docs/deploy/monitoring config and k8s/Helm deploy toggles; surfaced but not application capability.
2. **Plan (mutates nothing):** `python3 scripts/full_throttle.py <repo> --mode plan`. Review the danger/needs_wiring/scope exclusions before applying.
3. **Apply (isolated worktree):** `python3 scripts/full_throttle.py <repo> --mode apply --test-cmd "<cmd>" --output ft.json`. Flips non-danger candidates in a throwaway `git worktree`, runs the repo's own tests, and backs out any flag that regresses them (`empirically_unsafe`).
4. **Package:** `python3 scripts/build_flag_activation_pack.py --report ft.json --repo-root <repo> --output <dir>` → a REVIEW-REQUIRED pack (`auto_merge=false`) with the real flags-off→flags-on test delta in `FULL_THROTTLE_REPORT.md`.
5. **Gate:** a human reviews/merges the PR. A run that flips nothing (all excluded or all regress) is a valid BLOCKED outcome, not a failure to force.

## Requirements

Python 3.10+. Install dependencies before running the scripts:

```bash
pip install -r requirements.txt   # jsonschema>=4, PyYAML>=6
```
