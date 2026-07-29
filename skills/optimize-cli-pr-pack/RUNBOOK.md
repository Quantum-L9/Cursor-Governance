# Operator Runbook

1. Verify the target repository, base ref, worktree state, and mutation authority.
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
14. Deliver the `.tar.gz` pack, or perform authorized GitHub writes only when current-turn authorization is explicit.

## Diagnosis tooling

- `python3 scripts/scan_capabilities.py <repo>` — advisory scan for candidate underutilization gaps and entrypoints (verify before acting).
- `python3 scripts/measure.py --before <cmd> --after <cmd> [--capture]` — comparable before/after proof block (throughput or functional).

## Requirements

Python 3.10+. Install dependencies before running the scripts:

```bash
pip install -r requirements.txt   # jsonschema>=4, PyYAML>=6
```
