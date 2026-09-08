<!-- L9_META
l9_schema: 1
parent: l9-audit-plans
tags: [audit-plans, concern]
status: active
version: 1.0.0
/L9_META -->

# Plan concern prefixes

`concern_for` matches the first exclusive prefix on the filename (longest
prefix wins). `uncategorized` never folds and never compiles.

## Same-repo concerns

| Concern | Prefix |
|---|---|
| ceremony | `ceremony_` |
| publish | `publish_` |
| remediator | `remediator_` |
| close_sgd | `close_sgd` |
| memory_outbox | `memory_outbox` |
| reasoning | `reasoning_` |
| ff | `ff_` |
| session_end | `session_end_` |

## Other-repo (stay `stale`, never harvested)

`n8n_`, `odoo_`, `website_`, `constellation_`, `plastic_`, `emma_`, `seo_`
