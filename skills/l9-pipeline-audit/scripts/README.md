# Scripts

**Path:** `skills/l9-pipeline-audit/scripts` | **Kind:** subsystem

## Modules

### `audit_pipeline.py`

Classify plans, WIP, and PE campaigns with the same component verdicts.

- `def resolve_gov_root(workspace, explicit) -> Path`
- `def resolve_tracked_plans_dir(workspace) -> Path` — Prefer .cursor/plans → docs/plans (tracked), then ~/.cursor/plans.
- `def scan_plans(plans_dir, workspace, window_days) -> list[dict[str, Any]]`
- `def scan_wip(wip_root) -> list[dict[str, Any]]`
- `def scan_campaigns(campaigns_root) -> list[dict[str, Any]]`
- `def rank_next(findings, plans_dir) -> list[dict[str, Any]]` — Family execute order: one slot per surface, then fill. Cap 3.
- `def archive_landed_wip(wip_root, rows, cap) -> list[str]` — Move inventory-landed WIP only. possible-landed stays for harvest.
- `def archive_spent_plans(plans_dir, cap) -> list[str]` — Move spent root plans. Do not touch harvestable mixed donors.
- _+4 more public symbol(s)_

### `audit_plans.py`

Audit Cursor .plan.md files for recent unbuilt / stale plans.

- `PlanFinding`
- `def resolve_plans_dir(workspace, explicit) -> Path`
- `def workspace_head(workspace) -> str | None` — Resolve HEAD without spawning git (sessionStart must stay fast/fail-open).
- `def parse_frontmatter(text) -> tuple[dict[str, Any], str]`
- `def frontmatter_marks_built(fm) -> bool` — Explicit built/stale markers win over todo inference.
- `def is_unbuilt(todos, fm) -> bool`
- `def todo_counts(todos) -> tuple[int, int, int]`
- `def slug_key(path) -> str | None`
- _+12 more public symbol(s)_

### `audit_plans_self_test.py`

Self-test for absorbed audit_plans.py (skill-local; not collected by root pytest).

- `def run_audit(plans_dir, workspace) -> subprocess.CompletedProcess[str]`
- `def skill_validation_scripts() -> list[str]`
- `def main() -> int`

### `harvest_plan_invariants.py`

Emit compiled packets from already-harvested invariants.

- `def concern_for(name) -> str`
- `def extract_invariants(path) -> dict[str, Any]`
- `def compile_by_concern(extractions) -> dict[str, list[dict[str, str]]]`
- `def reject_implementation(payload) -> None`
- `def emit_compiled_plan() -> None`
- `def main(argv) -> int`

### `run_intelligence_harvest.py`

Bind and inventory donors through l9-intelligence-harvest, then emit packets.

- `def bind_request(request_path, bound_path) -> dict[str, Any]`
- `def inventory_donor(donor) -> dict[str, Any]`
- `def emit_wip(concern, invariants, dest) -> None`
- `def emit_campaign_intent(concern, invariants, dest) -> None`
- `def main(argv) -> int`

### `self_test.py`

Self-test for l9-pipeline-audit (skill-local; not collected by root pytest).

- `def main() -> int`

## Dependencies

**Internal:** `audit_plans`, `harvest_plan_invariants`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
