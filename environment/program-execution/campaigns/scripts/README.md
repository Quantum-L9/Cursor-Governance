# Scripts

**Path:** `environment/program-execution/campaigns/scripts` | **Tier:** discovered

## Purpose

Live campaign closeout ledger (in-repo): a projection, not an authority.



## Components

### `ClosureReceiptError`

No description

- File: `environment/program-execution/campaigns/scripts/close_campaign.py` (L55–56)
- Methods: _none_

## Functions

- `def validate_closure_receipt(payload, campaign_id) -> dict[str, Any]` — The Controller Closure Receipt, or why it cannot be accepted.
- `def load_closure_receipt(source, campaign_id) -> dict[str, Any]`
- `def campaigns_root(explicit) -> Path`
- `def load_policy(root) -> dict[str, Any]`
- `def load_ledger(root) -> dict[str, Any]`
- `def policy_ids(policy) -> list[str]`
- `def next_campaign(root) -> dict[str, Any] | None`
- `def close_campaign(root, campaign_id, closure_receipt, actor) -> dict[str, Any]` — Project a Controller closure into the campaign ledger. Never decides.
- `def archive_completed(root, campaign_id) -> Path`
- `def cmd_close(args) -> int`
- `def cmd_next(args) -> int`
- `def cmd_status(args) -> int`
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `datetime`, `json`, `pathlib`, `shutil`, `typing`

<!-- l9-module-readme: generated-from-ast -->
