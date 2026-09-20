# Scripts

**Path:** `skills/l9-git-work-preserve/scripts` | **Tier:** discovered

## Purpose

Diagnose unique value of a ref vs baseline (default origin/main).



## Components

### `ExtractError`

Fail-closed extract/apply error. ``code`` is the process exit status.

- File: `skills/l9-git-work-preserve/scripts/extract_path_union.py` (L22–27)
- Methods: _none_

## Functions

- `def diagnose(repo, ref, baseline, do_fetch) -> dict`
- `def main() -> int`
- `def path_on_baseline(repo, baseline, rel) -> bool`
- `def name_status(repo, baseline, ref) -> list[tuple[str, str]]` — Return (status_letter, path) for baseline...ref. Renames use the new path.
- `def load_allowlist(path) -> dict[str, Any] | None`
- `def classify_rows(repo, baseline, rows) -> tuple[list[dict[str, str]], list[dict[str, str]]]`
- `def apply_allowlist(derived_copy, derived_skip, allowlist) -> tuple[list[dict[str, str]], list[dict[str, str]], bool]`
- `def show_blob(repo, ref, rel) -> bytes | None`
- `def apply_copy(repo, ref, dest, copy) -> list[str]`
- `def extract_plan(repo) -> dict[str, Any]`
- `def main() -> int`
- `def fetch_origin(repo, baseline) -> dict` — Refresh remote-tracking refs so novelty is judged against current origin.
- `def porcelain_path(line) -> str`
- `def is_skip_noise(rel) -> bool`
- `def is_wiring_noise(rel) -> bool`
- `def remote_url(repo) -> str`
- `def discover_worktrees(repo, extra_roots) -> list[Path]`
- `def path_on_baseline(repo, baseline, rel) -> bool`
- `def classify_path(rel) -> str`
- `def inspect_worktree(wt) -> dict[str, Any]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `datetime`, `diagnose_ref_value`, `git_fetch`, `hashlib`, `json`, `os`, `pathlib`, `re`, `repo_hygiene`, `subprocess`, `sys`, `tempfile`, `typing`

<!-- l9-module-readme: generated-from-ast -->
