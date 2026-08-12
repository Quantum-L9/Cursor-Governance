# Phase 0 autonomy rail — unpromoted delta

**Status:** backlog (not live)  
**Promote into:** `environment/program-execution/core/`  
**Do not treat as SSOT.** Live PE base templates already exist; this folder is
only the Phase 0 / LL-001–004 rail that never landed.

## What this is

Extracted from the former WIP PE v2 pack. Contains only files that encode the
Phase 0 deploy-preflight / autonomy rail (GATE-000, `PHASE0_USER_CONFIG`, stop
taxonomy, error/authz codes, `AUTONOMY_BRIDGE`, `test_autonomy_rail.py`, and
related blueprint/controller law deltas).

## WIP-only artifacts (absent from live core)

- `program-execution-blueprint-template/PHASE0_USER_CONFIG.yaml`
- `program-execution-blueprint-template/schemas/phase0-user-config.schema.json`
- `program-execution-controller-template/references/AUTONOMY_BRIDGE.md`
- `tests/test_autonomy_rail.py`
- `LEARNED_LESSONS.md`

## Promotion notes

1. Diff each file against the matching path under
   `environment/program-execution/core/` — live runtime (`pec/controller.py` etc.)
   has evolved past the old pack; **merge forward**, do not overwrite live with
   older controller code (not included here).
2. Keep adapters/integrations/conformance under `environment/program-execution/`
   untouched unless a rail rule explicitly requires a bridge update.
3. After promotion + validation (`make program-execution-core-validate` and
   related gates), delete this folder.
