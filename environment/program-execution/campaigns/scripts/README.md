# Scripts

**Path:** `environment/program-execution/campaigns/scripts` | **Kind:** module

## Purpose

Live campaign closeout ledger (in-repo): a projection, not an authority.

## Public interface

- `ClosureReceiptError`
- `def validate_closure_receipt(payload, campaign_id) -> dict[str, Any]` — The Controller Closure Receipt, or why it cannot be accepted.
- `def load_closure_receipt(source, campaign_id) -> dict[str, Any]`
- `def campaigns_root(explicit) -> Path`
- `def load_policy(root) -> dict[str, Any]`
- `def load_ledger(root) -> dict[str, Any]`
- `def policy_ids(policy) -> list[str]`
- `def next_campaign(root) -> dict[str, Any] | None`
- _+7 more public symbol(s)_

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=module -->
