# Reference

**Path:** `environment/program-execution/campaigns/l9-ecosystem-fix-plan/deliverables/ib-odoo_19/reference` | **Tier:** discovered

## Purpose

Reference mapper: CEG match response -> Odoo buyer-match records (TASK-004).



## Components

### `UnresolvableBuyerRef`

Raised internally when an entity_ref cannot map to a res.partner id.

- File: `environment/program-execution/campaigns/l9-ecosystem-fix-plan/deliverables/ib-odoo_19/reference/plasticos_ceg_match_mapper.py` (L45–46)
- Methods: _none_

## Functions

- `def resolve_buyer_partner_id(entity_ref) -> int` — Resolve a CEG contract entity_ref to an Odoo res.partner integer id.
- `def normalize_score(score, score_scale) -> float | None` — Normalize a candidate score to [0, 1] using the declared score_scale.
- `def map_match_response(payload) -> dict[str, Any]` — Map a CEG match response payload into Odoo buyer-match records.
- `def build_eie_converge_request(odoo_req) -> dict[str, Any]` — Map an Odoo converge request into an EIE EnrichRequest payload.
- `def map_eie_converge_response(eie_resp) -> dict[str, Any]` — Map an EIE EnrichResponse into Odoo-storable fields WITHOUT field loss.

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `re`, `typing`

<!-- l9-module-readme: generated-from-ast -->
