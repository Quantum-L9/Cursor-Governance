# Archived inline Python origin/HEAD binder

**Status:** **RETIRED AND NON-EXECUTABLE**
**Retired:** 2026-09-13
**Live owner:** [`ops/scripts/lib/git_remote_head.sh`](../../lib/git_remote_head.sh)

This document preserves the removed inline Python algorithm for audit and
migration review. It is deliberately Markdown rather than importable Python.
No live module may copy or call this algorithm. The active Python hygiene path
calls the helper CLI, and the regression barrier verifies that Python contains
none of its Git discovery, fetch, or bind operations.

```text
if origin/HEAD is missing:
  inspect `git ls-remote --symref origin HEAD`
  parse the advertised refs/heads/<default>
  validate the branch name
  fetch +refs/heads/<default>:refs/remotes/origin/<default>
  run git remote set-head origin -a
```

The exact executable form is preserved in the preceding commit history and
was removed from `ops/scripts/repo_hygiene.py` when the single-path helper was
sealed. This archive must not be imported, executed, copied into a new helper,
or moved back into an active source directory.

**Restoration rule:** Repair the shared helper and its tests. Do not restore a
second implementation in Python.
