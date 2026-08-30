---
description: Use the local GitHub clone at $HOME/.cursor-governance as the sole governance root.
---

# Governance SSOT Path Contract

**Authority:** `@.cursor-commands/CANONICAL_LAW.md`

## Binding contract

The sole local governance root is the GitHub clone at `$HOME/.cursor-governance`.
The repository root is also the shared governance content root, so:

```text
$GOV_ROOT == $GLOBAL_COMMANDS == $HOME/.cursor-governance
```

There is no nested `GlobalCommands/` directory and no cloud-storage fallback.

| Layer | Requirement |
|---|---|
| SSOT working copy | `$HOME/.cursor-governance` |
| Remote | `Quantum-L9/Cursor-Governance` |
| Resolver | `ops/scripts/resolve_governance_paths.sh` |
| Workspace reference plane | `.cursor-commands` symlink to the clone root |
| Workspace activation plane | real repository-owned `.cursor/rules/` directory |
| Auto-sync | guarded fast-forward-only synchronization |

## Required resolution API

Governance scripts source `resolve_governance_paths.sh` and then call `resolve_governance_paths` or `resolve_governance_paths_or_exit` before using `$GOV_ROOT` / `$GLOBAL_COMMANDS`. Sourcing the file alone does not bind which clone is authoritative (a WARN fires at EXIT if no entry point ran). Hooks installed as real files must resolve the clone explicitly rather than deriving the root from a cloud path. Session env is loaded inside `l9_load_session_env` so non-interactive shells see `L9_GOVERNANCE_DIR`.

## Forbidden

- machine-specific `/Users/<name>/...` or `/home/<name>/...` paths;
- cloud-storage governance roots or fallback reads;
- a nested `GlobalCommands/` tree;
- deriving governance from the installed hook directory;
- whole-directory `.cursor/rules` links to global rules.

## Allowed

- `$HOME/.cursor-governance`;
- `$GOV_ROOT` and `$GLOBAL_COMMANDS` after resolver success;
- repository-relative `.cursor-commands/...` references;
- selected individual shared-rule symlinks inside a real local overlay.

Run the path and wiring validators before committing governance changes.

<!-- generated-from: rules/06-governance-ssot-paths.mdc; do-not-edit -->
