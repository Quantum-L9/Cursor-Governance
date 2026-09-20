# Scripts

**Path:** `skills/l9-repo-sync/scripts` | **Kind:** subsystem

## Modules

### `ff_shelf.py`

Shelf leftover corpus after /ff: untracked and dirty-tracked.

- `OpenShelfPR`
- `def run(cmd) -> subprocess.CompletedProcess[str]`
- `def is_shelf_path(rel) -> bool`
- `def collect_untracked(clone) -> list[str]`
- `def collect_dirty_tracked(clone) -> list[str]` — Copyable dirty-tracked corpus. Deletions are not rsync sources.
- `def collect_dirty_deleted(clone) -> list[str]`
- `def collect_shelf_paths(clone) -> list[str]`
- `def apply_shelf_deletions(shelf, deleted) -> None`
- _+19 more public symbol(s)_

### `self_test.py`

Fixture self-test: /ff parks unique work and never deletes it.

- `def run(cmd, cwd, env) -> subprocess.CompletedProcess[str]`
- `def git(repo) -> None`
- `def test_behind_with_colliding_and_hold() -> int`
- `def test_ignored_colliding_untracked_is_parked() -> int` — A gitignored colliding copy must not hide a path origin/main now tracks.
- `def test_origin_only_scan_is_fixed_cost() -> int` — The performance objective, measured — not asserted in a comment.
- `def test_comm_failure_blocks_destructive_sync() -> int` — Process substitution used to swallow this; an empty set is not a result.
- `def test_sort_failure_blocks_destructive_sync() -> int`
- `def test_comm_runs_under_c_collation() -> int` — `comm` must compare in the collation its inputs were sorted with.
- _+16 more public symbol(s)_

### `validate_pack_structure.py`

Validate l9-repo-sync pack structure (this pack only).

- `def primitives_only_under_allowed_headings(text) -> list[str]` — Return primitive hits that are not under Forbidden/incident headings.
- `def main() -> int`

## Entrypoints

- `ff.sh`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
