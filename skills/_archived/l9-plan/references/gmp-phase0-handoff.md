<!-- L9_META
l9_schema: 1
parent: l9-plan
tags: [plan, gmp, handoff]
status: active
version: 4.0.0
updated: 2026-08-12
/L9_META -->

# GMP Phase 0 Handoff

Map PLAN_DOCUMENT → `l9-gmp-protocol` Phase 0 lock.

| PLAN_DOCUMENT | GMP Phase 0 |
|---------------|-------------|
| todos[].id | TODO id |
| todos[].files[0] | File |
| todos[].operation | Operation (Insert\|Replace\|Delete\|Wrap\|Create) |
| todos[].anchor | Anchor |
| todos[].dependencies | Dependencies |
| todos[].task | Description |
| gmp_handoff.may_modify | MODIFICATION LOCK may-modify |
| gmp_handoff.must_not_modify | MODIFICATION LOCK must-not-modify |
| gmp_handoff.preserved_contracts | contracts preserved |
| gmp_handoff.validation_commands | Phase 4 seed commands |

Use `python3 scripts/emit_gmp_phase0.py <plan.json>`.

Rules: no placeholders; ungrounded todos must carry `blocker` and cannot be READY until resolved.
