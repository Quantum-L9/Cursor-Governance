# Scripts

**Path:** `skills/l9-audit-plans/scripts` | **Kind:** subsystem

## Modules

### `refine_plans.py`

Fold or compile leftover plan todos. Never write AGENTS.md. Never harvest-write.

- `def concern_for(path, fm) -> str`
- `def leftover_todos(fm) -> list[dict[str, Any]]`
- `def rewrite_live_queue(plans_dir, root_now) -> bool`
- `def refine(plans_dir) -> dict[str, Any]`
- `def format_markdown(payload) -> str`
- `def main(argv) -> int`

### `run_audit_plans.py`

Single /l9-audit-plans invoke: shelf → refine → shelf → README.

- `def invoke(plans_dir, workspace, today) -> dict`
- `def main(argv) -> int`

### `self_test.py`

Self-test for l9-audit-plans (skill-local; not collected by root pytest).

- `def main() -> int`

### `shelf_plans.py`

Put every plans-store .plan.md on the binding shelf.

- `def apply_status(path, verdict) -> None` — Set folder/current status. Never write a parked status onto live root.
- `def shelf_dir(plans_dir, verdict) -> Path`
- `def slug_collision(dest_dir, src) -> Path` — Prefer an existing same-slug file over basename-only dest.
- `def allocate_todo_id(preferred, ids) -> str` — Keep suffixing until the folded id is unique in the destination list.
- `def leftover_todo_rows(fm) -> list[dict[str, Any]]`
- `def merge_unique_todos(src, dest) -> int` — Copy unique pending/in-progress todos from src onto dest before dest-wins.
- `def fold_retired(plans_dir, workspace, actions) -> dict[str, int]`
- `def shelf(plans_dir, workspace, today) -> dict[str, Any]`
- _+2 more public symbol(s)_

## Dependencies

**Internal:** `audit_plans`, `refine_plans`, `shelf_plans`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
