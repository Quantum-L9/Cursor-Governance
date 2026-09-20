# Scripts

**Path:** `skills/l9-pipeline-audit/scripts` | **Tier:** discovered

## Purpose

Classify plans, WIP, and PE campaigns with the same component verdicts.



## Components

### `PlanFinding`

No description

- File: `skills/l9-pipeline-audit/scripts/audit_plans.py` (L41–49)
- Methods: _none_

## Functions

- `def resolve_gov_root(workspace, explicit) -> Path`
- `def resolve_tracked_plans_dir(workspace) -> Path` — Prefer .cursor/plans → docs/plans (tracked), then ~/.cursor/plans.
- `def scan_plans(plans_dir, workspace, window_days) -> list[dict[str, Any]]`
- `def scan_wip(wip_root) -> list[dict[str, Any]]`
- `def scan_campaigns(campaigns_root) -> list[dict[str, Any]]`
- `def rank_next(findings, plans_dir) -> list[dict[str, Any]]` — Family execute order: one slot per surface, then fill. Cap 3.
- `def archive_landed_wip(wip_root, rows, cap) -> list[str]` — Move inventory-landed WIP only. possible-landed stays for harvest.
- `def archive_spent_plans(plans_dir, cap) -> list[str]` — Move spent root plans. Do not touch harvestable mixed donors.
- `def run() -> dict[str, Any]`
- `def format_session_start(payload, budget) -> str`
- `def format_markdown(payload) -> str`
- `def main(argv) -> int`
- `def resolve_plans_dir(workspace, explicit) -> Path`
- `def workspace_head(workspace) -> str | None` — Resolve HEAD without spawning git (sessionStart must stay fast/fail-open).
- `def parse_frontmatter(text) -> tuple[dict[str, Any], str]`
- `def frontmatter_marks_built(fm) -> bool` — Explicit built/stale markers win over todo inference.
- `def is_unbuilt(todos, fm) -> bool`
- `def todo_counts(todos) -> tuple[int, int, int]`
- `def slug_key(path) -> str | None`
- `def collect_newer_slugs(paths) -> set[str]`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `audit_plans`, `collections`, `dataclasses`, `harvest_plan_invariants`, `json`, `os`, `pathlib`, `re`, `shutil`, `subprocess`, `sys`, `tempfile`, `time`, `typing`

<!-- l9-module-readme: generated-from-ast -->
