# Lib

**Path:** `ops/scripts/lib` | **Kind:** subsystem

## Modules

### `__init__.py`

Shared helpers for governance ops scripts.

### `dirtiness.py`

Shared classification of worktree dirtiness paths.

- `def normalize(path) -> str`
- `def is_scratch_path(path) -> bool`
- `def protected_root_files(root) -> set[str]` — Repository-root files registered in the append-only protection policy.
- `def classify_path(root, path) -> str` — One of: scratch, generated, protected, source. ``root`` is the tree being
- `def decode_git_quoted_path(path) -> str` — Decode C-style escapes in git status quoted paths (octal + \n \t \" \\).
- `def porcelain_path(line) -> str` — Extract the path from a `git status --porcelain` line, handling renames.

### `rule_frontmatter.py`

Shared Cursor rule (.mdc) frontmatter parsing.

- `ParsedRule`
- `def parse_rule(path) -> ParsedRule`
- `def normalize_globs(value) -> list[str] | None` — Return glob patterns as a list.
- `def always_apply_is_true(metadata) -> bool`
- `def emit_native_frontmatter(metadata) -> str` — Emit Cursor-native frontmatter: description, globs, alwaysApply.
- `def activation_class(metadata, globs) -> str` — Return always | paths | agent_requested for projection decisions.

### `wave_prefix.py`

Prefix stdin lines with ``[wave:NAME] `` and tee the raw bytes to a log.

- `def prefix_stream(name, log_path) -> int`
- `def main(argv) -> int`

### `workspace_roots.py`

One answer to: which repositories is this session working in?

- `RootSelection` — What `workspace_roots` chose, and what it left behind and why.
- `def is_repository(path) -> bool` — True when `path` is a git checkout root.
- `def select_workspace_roots(workspace) -> RootSelection` — `workspace_roots`, plus the roots it excluded and the rule that did it.
- `def workspace_roots(workspace) -> list[Path]` — Repository roots inside `workspace`, in resolution order.
- `def projection_roots(workspace) -> list[Path]` — Mount roots a project-scope projection must reconcile.
- `def adopted_projection_roots(workspace, relative_target, state_name, exclude_targets) -> list[Path]` — Ancestors of `workspace` that already hold a projection of this adapter.

## Entrypoints

- `bind_memory_interpreter.sh`
- `cursor_plans_store.sh`
- `fetch_receipt.sh`
- `gh_auth_probe.sh`
- `gh_graphql.sh`
- `gh_subscribe_pr.sh`
- `git_remote_head.sh`
- `path_contracts.sh`
- `plugin_siblings.sh`
- `precommit_log.sh`
- `repo_write_lock.sh`
- `resolve_pr_stack.sh`
- `retire_leftover_launchagents.sh`
- `rules_overlay.sh`
- `run_with_timeout.sh`
- `session_git_excludes.sh`
- `ssot_machine_local_keep.sh`
- `surface_detect.sh`
- `workspace_kind.sh`
- `workspace_link_health.sh`

## Dependencies

**External:** `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
