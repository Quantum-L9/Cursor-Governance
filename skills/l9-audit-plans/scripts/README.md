# Scripts

**Path:** `skills/l9-audit-plans/scripts` | **Tier:** discovered

## Purpose

Fold or compile leftover plan todos. Never write AGENTS.md. Never harvest-write.



## Components

_No public classes in this path._

## Functions

- `def concern_for(path, fm) -> str`
- `def leftover_todos(fm) -> list[dict[str, Any]]`
- `def rewrite_live_queue(plans_dir, root_now) -> bool`
- `def refine(plans_dir) -> dict[str, Any]`
- `def format_markdown(payload) -> str`
- `def main(argv) -> int`
- `def invoke(plans_dir, workspace, today) -> dict`
- `def main(argv) -> int`
- `def main() -> int`
- `def apply_status(path, verdict) -> None` — Set folder/current status. Never write a parked status onto live root.
- `def shelf_dir(plans_dir, verdict) -> Path`
- `def slug_collision(dest_dir, src) -> Path` — Prefer an existing same-slug file over basename-only dest.
- `def allocate_todo_id(preferred, ids) -> str` — Keep suffixing until the folded id is unique in the destination list.
- `def leftover_todo_rows(fm) -> list[dict[str, Any]]`
- `def merge_unique_todos(src, dest) -> int` — Copy unique pending/in-progress todos from src onto dest before dest-wins.
- `def fold_retired(plans_dir, workspace, actions) -> dict[str, int]`
- `def shelf(plans_dir, workspace, today) -> dict[str, Any]`
- `def format_markdown(payload) -> str`
- `def main(argv) -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `audit_plans`, `datetime`, `hashlib`, `json`, `os`, `pathlib`, `re`, `refine_plans`, `shelf_plans`, `shutil`, `subprocess`, `sys`, `typing`

<!-- l9-module-readme: generated-from-ast -->
