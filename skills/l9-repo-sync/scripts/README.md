# Scripts

**Path:** `skills/l9-repo-sync/scripts` | **Tier:** discovered

## Purpose

Shelf leftover corpus after /ff: untracked and dirty-tracked.



## Components

### `OpenShelfPR`

No description

- File: `skills/l9-repo-sync/scripts/ff_shelf.py` (L39–43)
- Methods: _none_

### Shell entrypoints

- `skills/l9-repo-sync/scripts/ff.sh`

## Functions

- `def run(cmd) -> subprocess.CompletedProcess[str]`
- `def is_shelf_path(rel) -> bool`
- `def collect_untracked(clone) -> list[str]`
- `def collect_dirty_tracked(clone) -> list[str]` — Copyable dirty-tracked corpus. Deletions are not rsync sources.
- `def collect_dirty_deleted(clone) -> list[str]`
- `def collect_shelf_paths(clone) -> list[str]`
- `def apply_shelf_deletions(shelf, deleted) -> None`
- `def write_untracked_list(clone, paths) -> Path`
- `def files_from_ok(list_path, clone) -> None`
- `def build_rsync_argv(clone, shelf, list_path) -> list[str]`
- `def build_add_argv(shelf, list_path) -> list[str]`
- `def build_commit_argv(shelf, message) -> list[str]`
- `def load_open_shelf_prs(path) -> list[OpenShelfPR]`
- `def gh_login() -> str`
- `def github_repo_slug(clone) -> str`
- `def gh_open_shelf_prs(clone) -> list[OpenShelfPR]`
- `def resolve_shelf_branch(prs, author, stamp) -> tuple[str, str]` — Return (branch, action) where action is append or stamp.
- `def worktree_for_branch(clone, branch) -> Path | None`
- `def sha256_file(path) -> str | None`
- `def blob_sha256(repo, rev, rel) -> str | None`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `dataclasses`, `datetime`, `hashlib`, `json`, `os`, `pathlib`, `re`, `subprocess`, `sys`, `tempfile`

<!-- l9-module-readme: generated-from-ast -->
