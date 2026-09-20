# Scripts

**Path:** `skills/l9-issue-remediation/scripts` | **Tier:** discovered

## Purpose

Close a GitHub issue that is already resolved — evidence-gated.



## Components

_No public classes in this path._

## Functions

- `def validate_close() -> str` — Return the resolved reason or raise SystemExit.
- `def main() -> int`
- `def cluster_issues(issues) -> list[dict]` — Group by explicit links; rank shared-cause / cross-repo / severity / oldest.
- `def discover(org, limit) -> list[dict]`
- `def may_chain_pr_remediation(open_issue_count, intent) -> dict`
- `def pr_matches_issue(pr, issue_id, changed_paths) -> bool`
- `def decide_landing(issue_id, open_prs, changed_paths) -> dict` — Return landing action for one issue in one owning repo.
- `def test_close_gates() -> None`
- `def test_cluster_rank_shared_cause_first() -> None`
- `def test_command_open_issues_gate() -> None`
- `def test_pr_landing() -> None`
- `def test_open_issues_gate() -> None`
- `def test_comment_sends_user_agent() -> None`
- `def test_skill_defaults() -> None`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `close_resolved_issue`, `cluster_rank`, `datetime`, `json`, `open_issues_gate`, `os`, `pathlib`, `post_issue_comment`, `pr_landing`, `re`, `safe_https`, `shutil`, `subprocess`, `sys`, `urllib.error`, `urllib.parse`, `urllib.request`

<!-- l9-module-readme: generated-from-ast -->
