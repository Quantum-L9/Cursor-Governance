# Failure: make pr died on unwired gov worktrees

**Date:** 2026-08-15 (landed 2026-08-17)
**Surface:** `make pr` (`symlinks-check` + `run_pr_gate.sh` local-activation)
**Cost:** push never ran; IDE-profile WARN looked like the gate.

## What the tool said

```
WARN: IDE profile not yet applied — run: bash .../install_ide_profile.sh ".../gov-worktrees/..."
RESULT: FAIL — run /wire governance
FAIL: governance wiring or sessionEnd hook incomplete
FAIL: pre-commit hook(s) failed:
  symlinks-check (exit 1)
```

## What was actually true

1. `make pr` is fail-closed: `pr-check` then `open_pr_after_gate.sh`. A failed
   `pr-check` never pushes.
2. The IDE-profile line is warn-only and was printed last, immediately before
   `RESULT: FAIL`. It was not the gate.
3. Checkers treated any workspace whose realpath was not
   `$HOME/.cursor-governance` as a **consumer**, then required gitignored
   `.cursor-commands` / `.cursor/plans` / `.cursor/governance` that SessionStart
   never creates on a worktree.
4. A worktree of this repo is still the governance tree (`ssot_checkout`), not
   a product consumer. Auto-wiring it as a consumer is the wrong patch.

## What changed

- `ops/scripts/lib/workspace_kind.sh` classifies `ssot` | `ssot_checkout` |
  `consumer` from identity files + realpath (not `$HOME/.l9/gov-worktrees/`
  alone).
- `check_governance_wiring.sh`, `validate_governance_symlinks.sh`, and
  `run_pr_gate.sh` skip consumer-link requirements on `ssot_checkout`.
- SSOT tip / dirty / unpushed is WARN-only on `ssot_checkout`.
- RESULT prints before the `non-blocking` WARN footer. Wrappers no longer
  blame sessionEnd unless that check failed.
- Regression: `ops/scripts/tests/test_workspace_kind.sh`.
