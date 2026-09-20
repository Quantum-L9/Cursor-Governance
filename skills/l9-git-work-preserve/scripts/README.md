# Scripts

**Path:** `skills/l9-git-work-preserve/scripts` | **Kind:** subsystem

## Modules

### `diagnose_ref_value.py`

Diagnose unique value of a ref vs baseline (default origin/main).

- `def diagnose(repo, ref, baseline, do_fetch) -> dict`
- `def main() -> int`

### `extract_path_union.py`

Path-union extract of leftover committed paths vs a fetched baseline.

- `ExtractError` — Fail-closed extract/apply error. ``code`` is the process exit status.
- `def path_on_baseline(repo, baseline, rel) -> bool`
- `def name_status(repo, baseline, ref) -> list[tuple[str, str]]` — Return (status_letter, path) for baseline...ref. Renames use the new path.
- `def load_allowlist(path) -> dict[str, Any] | None`
- `def classify_rows(repo, baseline, rows) -> tuple[list[dict[str, str]], list[dict[str, str]]]`
- `def apply_allowlist(derived_copy, derived_skip, allowlist) -> tuple[list[dict[str, str]], list[dict[str, str]], bool]`
- `def show_blob(repo, ref, rel) -> bytes | None`
- `def apply_copy(repo, ref, dest, copy) -> list[str]`
- _+2 more public symbol(s)_

### `git_fetch.py`

Best-effort origin fetch shared by the inventory and diagnosis scripts.

- `def fetch_origin(repo, baseline) -> dict` — Refresh remote-tracking refs so novelty is judged against current origin.

### `harvest_worktree_dirt.py`

Classify dirty/untracked paths across sibling worktrees for harvest.

- `def porcelain_path(line) -> str`
- `def is_skip_noise(rel) -> bool`
- `def is_wiring_noise(rel) -> bool`
- `def remote_url(repo) -> str`
- `def discover_worktrees(repo, extra_roots) -> list[Path]`
- `def path_on_baseline(repo, baseline, rel) -> bool`
- `def classify_path(rel) -> str`
- `def inspect_worktree(wt) -> dict[str, Any]`
- _+3 more public symbol(s)_

### `inventory_git_work.py`

Inventory git work: unpushed, dirty, worktrees, orphans, stale, stashes.

- `def inventory(repo, baseline, do_fetch) -> dict`
- `def main() -> int`

### `pack_self_test.py`

Fixture self-test for l9-git-work-preserve scripts.

- `def run(cmd, cwd, env) -> subprocess.CompletedProcess[str]`
- `def build_fixture(tmp) -> Path`
- `def build_redundancy_fixture(tmp) -> Path` — Branches whose work already reached main by two different routes.
- `def build_remote_fixture(tmp) -> Path` — A repo with a real (path) remote, so --fetch exercises the network-free path.
- `def check_inventory(repo, errors) -> None`
- `def check_baseline_cases(repo, errors) -> None`
- `def check_redundancy(repo, errors) -> None`
- `def check_real_fetch(repo, errors) -> None`
- _+8 more public symbol(s)_

### `prune_execute.py`

Auth-gated leftover prune: preserve-ref, then worktree, then local branch.

- `def load_receipts(paths) -> list[dict]`
- `def receipt_authorizes_prune(receipt) -> tuple[bool, str]`
- `def classify_targets(git, receipts) -> list[dict]`
- `def apply_targets(git, rows, report) -> None`
- `def main(argv) -> int`

### `prune_open_pr_copies.py`

Unlink untracked shipped copies of open-PR blobs across sibling worktrees.

- `def sha256_file(path) -> str | None`
- `def sha256_blob(repo, rev, rel) -> str | None`
- `def kernel_normalize(text) -> str` — Zero kernel receipt fields so leftover vs open-PR plan bodies can match.
- `def kernel_normalized_sha256(data) -> str | None`
- `def is_plan_md(rel) -> bool`
- `def path_key(rel) -> str` — Case-fold only the documented docs/plans/built vs BUILT alias.
- `def skip_path(rel) -> bool`
- `def head_has_path(repo, rel) -> bool`
- _+7 more public symbol(s)_

### `triage_preserved_refs.py`

Triage the refs `/ff` parked, using the same evidence as ref diagnosis.

- `def preserved_refs(repo) -> list[str]` — Every ref `/ff` parks, in a stable order.
- `def triage(repo, baseline, do_fetch) -> dict`
- `def main() -> int`

### `validate_pack_structure.py`

Validate l9-git-work-preserve pack structure.

- `def main() -> int`

## Dependencies

**Internal:** `diagnose_ref_value`, `git_fetch`, `repo_hygiene`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
