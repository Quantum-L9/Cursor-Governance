# Scripts

**Path:** `skills/l9-issue-remediation/scripts` | **Kind:** subsystem

## Modules

### `close_resolved_issue.py`

Close a GitHub issue that is already resolved — evidence-gated.

- `def validate_close() -> str` — Return the resolved reason or raise SystemExit.
- `def main() -> int`

### `cluster_rank.py`

Rank issue clusters by leverage (shared cause first).

- `def cluster_issues(issues) -> list[dict]` — Group by explicit links; rank shared-cause / cross-repo / severity / oldest.
- `def main() -> int`

### `fleet_discover.py`

Discover non-archived GitHub org repos via gh (stdlib + gh CLI).

- `def discover(org, limit) -> list[dict]`
- `def main() -> int`

### `issue_ingest.py`

Ingest open GitHub issues for a fleet or single repo via gh (read-only).

- `def main() -> int`

### `open_issues_gate.py`

Hard gate: remediator may chain /l9-pr-remediation only at open_issues=0.

- `def may_chain_pr_remediation(open_issue_count, intent) -> dict`
- `def main() -> int`

### `post_issue_comment.py`

Post a canonical l9-issue-remediation unblock comment via GitHub API.

- `def main() -> int`

### `pr_landing.py`

Decide where an issue fix lands: matching open PR, else stacked on newest.

- `def pr_matches_issue(pr, issue_id, changed_paths) -> bool`
- `def decide_landing(issue_id, open_prs, changed_paths) -> dict` — Return landing action for one issue in one owning repo.
- `def main() -> int`

### `self_test.py`

Contract tests for l9-issue-remediation remediator automation. Stdlib only.

- `def test_close_gates() -> None`
- `def test_cluster_rank_shared_cause_first() -> None`
- `def test_command_open_issues_gate() -> None`
- `def test_pr_landing() -> None`
- `def test_open_issues_gate() -> None`
- `def test_comment_sends_user_agent() -> None`
- `def test_skill_defaults() -> None`
- `def main() -> int`

## Dependencies

**Internal:** `close_resolved_issue`, `cluster_rank`, `open_issues_gate`, `post_issue_comment`, `pr_landing`, `safe_https`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
