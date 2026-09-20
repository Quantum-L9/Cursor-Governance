# Lib

**Path:** `ops/scripts/lib` | **Tier:** discovered

## Purpose

Shared helpers for governance ops scripts.



## Components

### `ParsedRule`

No description

- File: `ops/scripts/lib/rule_frontmatter.py` (L19–23)
- Methods: _none_

### `RootSelection`

What `workspace_roots` chose, and what it left behind and why.

- File: `ops/scripts/lib/workspace_roots.py` (L54–69)
- Methods: _none_

### Shell entrypoints

- `ops/scripts/lib/bind_memory_interpreter.sh`
- `ops/scripts/lib/cursor_plans_store.sh`
- `ops/scripts/lib/fetch_receipt.sh`
- `ops/scripts/lib/gh_auth_probe.sh`
- `ops/scripts/lib/gh_graphql.sh`
- `ops/scripts/lib/gh_subscribe_pr.sh`
- `ops/scripts/lib/git_remote_head.sh`
- `ops/scripts/lib/path_contracts.sh`
- `ops/scripts/lib/plugin_siblings.sh`
- `ops/scripts/lib/precommit_log.sh`
- `ops/scripts/lib/repo_write_lock.sh`
- `ops/scripts/lib/resolve_pr_stack.sh`
- `ops/scripts/lib/retire_leftover_launchagents.sh`
- `ops/scripts/lib/rules_overlay.sh`
- `ops/scripts/lib/run_with_timeout.sh`
- `ops/scripts/lib/session_git_excludes.sh`
- `ops/scripts/lib/ssot_machine_local_keep.sh`
- `ops/scripts/lib/surface_detect.sh`
- `ops/scripts/lib/workspace_kind.sh`
- `ops/scripts/lib/workspace_link_health.sh`

## Functions

- `def normalize(path) -> str`
- `def is_scratch_path(path) -> bool`
- `def protected_root_files(root) -> set[str]` — Repository-root files registered in the append-only protection policy.
- `def classify_path(root, path) -> str` — One of: scratch, generated, protected, source. ``root`` is the tree being
- `def decode_git_quoted_path(path) -> str` — Decode C-style escapes in git status quoted paths (octal + \n \t \" \\).
- `def porcelain_path(line) -> str` — Extract the path from a `git status --porcelain` line, handling renames.
- `def parse_rule(path) -> ParsedRule`
- `def normalize_globs(value) -> list[str] | None` — Return glob patterns as a list.
- `def always_apply_is_true(metadata) -> bool`
- `def emit_native_frontmatter(metadata) -> str` — Emit Cursor-native frontmatter: description, globs, alwaysApply.
- `def activation_class(metadata, globs) -> str` — Return always | paths | agent_requested for projection decisions.
- `def prefix_stream(name, log_path) -> int`
- `def main(argv) -> int`
- `def is_repository(path) -> bool` — True when `path` is a git checkout root.
- `def select_workspace_roots(workspace) -> RootSelection` — `workspace_roots`, plus the roots it excluded and the rule that did it.
- `def workspace_roots(workspace) -> list[Path]` — Repository roots inside `workspace`, in resolution order.
- `def projection_roots(workspace) -> list[Path]` — Mount roots a project-scope projection must reconcile.
- `def adopted_projection_roots(workspace, relative_target, state_name, exclude_targets) -> list[Path]` — Ancestors of `workspace` that already hold a projection of this adapter.

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `dataclasses`, `functools`, `json`, `pathlib`, `sys`, `typing`, `yaml`

<!-- l9-module-readme: generated-from-ast -->
