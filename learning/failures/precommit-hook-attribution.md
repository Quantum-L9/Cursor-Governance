# Failure: "files were modified by this hook" blamed a read-only validator

**Date:** 2026-08-14
**Surface:** `make pr` gate (`ops/scripts/run_pr_gate.sh`), pre-commit 4.5.1
**Cost:** repeated gate failures plus at least one debugging cycle spent
auditing `ops/scripts/validate_governance_symlinks.sh`, which never wrote to the
repository at all.

## What the tool said

```
symlinks check.........................Failed
- hook id: symlinks-check
- files were modified by this hook
```

## What was actually true

1. **The message names a time window, not an author.** `_run_single_hook`
   captures `git diff` before and after each hook and reports `files_modified =
   diff_before != diff_after` (`pre_commit/commands/run.py`). Anything that
   writes during a hook's execution is attributed to that hook. `symlinks-check`
   has the widest window in this hook set — it delegates to
   `check_governance_wiring.sh`, which does a `git fetch` and a Graphiti resolve
   — so it absorbs the blame for concurrent writers. Its only write is
   `mkdir -p "$HOME/.cursor/plans"`, outside the repository.
2. **The real writers were backgrounded reconcilers.**
   `ops/hooks/session_start_bootstrap.sh` launches `install_ide_profile.sh`
   (writes `.vscode/settings.json` and the AGENTS.md formatter block) and
   `setup_claude_code_plugins.sh` (writes `.claude/settings.json`) with no lock.
3. **The gate's own tolerance was dead code.** `run_pr_gate.sh` called
   pre-commit bare under `set -e`. pre-commit exits non-zero for
   `files_modified or bool(retcode)`, so the gate died before reaching the
   `classify_generated_dirtiness.sh` branch written to absorb exactly this case.
4. **The two detectors measured different things.** pre-commit compares tracked
   unstaged changes; the gate compared `git status --porcelain`, which also sees
   untracked files. Untracked churn tripped the gate but could never have
   produced pre-commit's message.

## What changed

- `ops/scripts/lib/repo_write_lock.sh` — the gate holds it; reconcilers yield.
- `run_pr_gate.sh` captures pre-commit's exit code and separates a real hook
  exit code from a modified tree, then classifies, attributes, and retries once.
- `ops/scripts/attribute_tree_writers.sh` — replays `read_only` hooks under the
  lock and prints who actually wrote, plus a `.l9/pr/gate-dirtiness.json` receipt.
- `ops/config/precommit-hook-contract.json` — every hook declared `read_only` or
  `writer`, so a validator can be mechanically exonerated instead of audited.

## Transferable lesson

When a tool names a culprit, check whether it *measured* authorship or merely
*observed a window*. Diffing around an interval attributes to time, not to
agency. Any such message needs a concurrency answer before a code audit.
