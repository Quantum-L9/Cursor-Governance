---
name: Fix venv sync hook blocking
overview: Stop the session-start hook from blocking on a multi-minute `uv sync` when `.venv` doesn't exist yet, and collapse the duplicate bootstrap hook registration that doubles the cost.
todos:
  - id: fix-venv-block
    content: "Edit ops/hooks/session_start_bootstrap.sh: split the venv sync into a fast synchronous verify path (when .venv exists) and a backgrounded run_reconciler path (when it doesn't)"
    status: completed
  - id: fix-dedupe
    content: "Edit ops/scripts/setup_workspace_symlinks.sh: generalize the sessionStart retire filter to strip any command variant containing session-start-bootstrap.sh, not just the exact template string"
    status: completed
  - id: run-symlinks-setup
    content: Run bash ops/scripts/setup_workspace_symlinks.sh to reconcile the live ~/.cursor/hooks.json and collapse the duplicate bootstrap entry
    status: completed
  - id: validate
    content: "Validate: make venv works standalone; simulate the hook with and without .venv present; run check_governance_wiring.sh"
    status: completed
isProject: false
---

# Fix: venv-sync blocking the sessionStart hook

## Root causes (from prior diagnosis)

1. [ops/hooks/session_start_bootstrap.sh](ops/hooks/session_start_bootstrap.sh) lines 100-110 run `uv sync --locked --extra dev` **synchronously**, inside a hook capped at a 30s timeout (`~/.cursor/hooks.json`). This violates the file's own stated invariant (lines 18-21: "Slow reconcilers ... are backgrounded ... so they can never stall or fail a session") — every other slow step in this script goes through `run_reconciler`; the venv block was left out when it was added in `6de4f8b`. A cold-cache first build (~7 min for the 48-package lock, dominated by the langgraph stack) blows the budget and the hook gets killed mid-sync.
2. `~/.cursor/hooks.json` currently has **two** `sessionStart` entries both running `session-start-bootstrap.sh` (plain, and prefixed `GOVERNANCE_SYNC_PUSH=0`), so the (already too-slow) sync fires twice per session. The merge/dedupe logic in [ops/scripts/setup_workspace_symlinks.sh](ops/scripts/setup_workspace_symlinks.sh) lines 337-343 only strips the exact string `./hooks/session-start-bootstrap.sh`, so the env-var-prefixed variant survives every reconcile.

## Fix 1 — fast-path / background-path split for the venv block

In `ops/hooks/session_start_bootstrap.sh`, replace the always-synchronous block with: synchronous *verify* sync when `.venv` already exists (cheap, warm-cache, keeps PATH correct for the rest of the hook chain), background the *first* build via the existing `run_reconciler` helper when it doesn't:

```bash
if command -v uv >/dev/null 2>&1 && [ -f "$GC/uv.lock" ]; then
  if [ -x "$GC/.venv/bin/python3" ]; then
    if ( cd "$GC" && uv sync --locked --extra dev >/dev/null 2>&1 ); then
      export PATH="$GC/.venv/bin:$PATH"
      PARTS+=("venv: locked (uv.lock)")
    else
      PARTS+=("venv: uv sync --locked failed — run: cd \"$GC\" && uv sync --extra dev")
    fi
  else
    run_reconciler bash -c "cd \"$GC\" && uv sync --locked --extra dev"
    PARTS+=("venv: not yet built — background sync started; run 'make venv' in $GC for foreground + wait")
  fi
fi
```

Self-heals: the next session start (after the background sync finishes) hits the fast path and PATH gets set normally. No change needed to `run_reconciler` itself or to `Makefile`'s `venv`/`lint` targets — `make venv` already runs the same `uv sync` in the foreground with no timeout, which remains the correct way to force+wait synchronously.

## Fix 2 — collapse duplicate bootstrap hook registration

In `ops/scripts/setup_workspace_symlinks.sh`, generalize the retire filter (currently exact-match only) to strip **any** variant of the bootstrap command, not just the literal template string:

```python
hooks = data.setdefault("hooks", {})
ss = hooks.setdefault("sessionStart", [])
ss = [e for e in ss if e.get("command") != "./hooks/session-start-memory-orchestrator.sh"]
bootstrap_entry = {"command": bootstrap_cmd, "timeout": 30}
ss = [bootstrap_entry] + [
    e for e in ss
    if "session-start-bootstrap.sh" not in (e.get("command") or "")
]
hooks["sessionStart"] = ss
```

This collapses both `./hooks/session-start-bootstrap.sh` and `GOVERNANCE_SYNC_PUSH=0 ./hooks/session-start-bootstrap.sh` down to the one canonical entry on the next reconcile, leaving the unrelated `./hooks/code-graph-health.sh` entry untouched.

## Validation

- `bash ops/scripts/setup_workspace_symlinks.sh` (run from inside this repo) — cleans up the live `~/.cursor/hooks.json`, confirm only one `session-start-bootstrap.sh` entry remains under `sessionStart`.
- `make venv` — confirm it still works standalone (foreground, unaffected by the hook change).
- Manually source/simulate `ops/hooks/session_start_bootstrap.sh` twice: once with `.venv` removed (confirm it reports the new "not yet built — background sync started" part and returns fast, well under 30s) and once with `.venv` present (confirm it still reports "venv: locked (uv.lock)" and PATH is set).
- `bash ops/scripts/check_governance_wiring.sh "$(pwd)"` — confirm wiring checks still pass against the modified hooks.json shape.

## Out of scope

- No change to `AGENTS.md`'s activation narrative (§2.1) — it currently omits the venv-sync step entirely; worth a follow-up doc fix but unrelated to this bug and not required for it.
- No new dedicated test harness for `session_start_bootstrap.sh` (repo has fixture selftests for `install_ide_profile.sh`/backup gate but none for this hook yet) — flagged as a possible future addition, not part of this fix.
