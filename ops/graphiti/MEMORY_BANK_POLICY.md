# memory-bank/ Git Policy

- **Target repo, never governance:** `memory-bank/` always lives at
  `$CURSOR_PROJECT_DIR/memory-bank/` — the workspace/repo currently open, i.e.
  the *consumer* repo. It is never written into the Cursor-Governance clone
  (`$GLOBAL_COMMANDS` / `~/.cursor-governance`). See
  `ops/hooks/session_start_bootstrap.sh` / `session_start_memory_orchestrator.sh`
  (`append_repo_memory_bank()`) and `ops/hooks/graphiti-session-end.sh` — both
  resolve the target via `CURSOR_PROJECT_DIR`, not a governance-relative path.
- **Append, never overwrite:** every sessionEnd write to `activeContext.md`,
  `tasks.md`, `progress.md`, and `tech-debt.md` MUST append a new dated
  section — never truncate/replace the whole file (a `cat >` full-file
  overwrite silently destroys any detail an agent added manually during the
  session). `ops/hooks/graphiti-session-end.sh` seeds `activeContext.md` with
  a header only on first creation; every later run appends an
  `## Append — sessionEnd <ts>` section. `85-workflow-state-bridge.mdc`
  governs periodic manual pruning/consolidation when the file exceeds ~1
  screen — that consolidation is also append-based (rewrite the "current
  state" summary as a new top section, don't delete prior sessions' history
  outright).
- **Gitignore check is mandatory before relying on git-tracking:** this
  machine's *global* `~/.gitignore_global` may exclude `memory-bank/` even
  when the target repo's own `.gitignore` doesn't. Before assuming
  `memory-bank/` is trackable, run `git check-ignore -q memory-bank/activeContext.md`
  in the target repo; if it's ignored, add a repo-local negation to that
  repo's `.gitignore` (after any blanket ignore rule):
  ```
  !/memory-bank/
  !/memory-bank/**
  ```
  `ops/hooks/graphiti-session-end.sh`'s `ensure_memory_bank_trackable()` does
  this automatically and idempotently on every sessionEnd fire.
- **PlasticOS (`ib-odoo-19`):** `memory-bank/` is **git-tracked** — commit manually after sessionEnd T0 updates.
- **Other repos:** scaffold locally; track in git only when explicitly enabled in `group_registry.yaml`.
- **Never auto-commit** from hooks — hooks write files; human or explicit `make commit` only.
- **Push via clean branch when the working branch is dirty/diverged:** if the
  target repo's current branch has a large unrelated uncommitted diff (don't
  touch it — see governance rules on not silently rebasing/discarding user
  work), commit and push the `memory-bank/` + `.gitignore` change from an
  isolated `git worktree` off a fresh copy of the repo's default branch
  instead, and open a normal PR. Do not entangle T0 tracking with unrelated
  in-flight work.
- **Scaffold rule:** `setup_workspace_symlinks.sh` copies template only when files missing — never overwrite existing.
