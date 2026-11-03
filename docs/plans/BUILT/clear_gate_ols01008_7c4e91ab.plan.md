---
name: Clear four Gate OLS errors
overview: Clear the four OLS01008 errors on get_gate_client_config_from_env by passing
  the same four Odoo-owned fields as one unpacked dict. The installed SDK already
  accepts them through **overrides.
todos:
- id: unpack-overrides
  content: Pass the four Odoo-owned Gate fields through one unpacked dict in build_gate_client_config,
    and bump plasticos_gate to 19.0.1.9.6.
  status: completed
- id: pin-assertion
  content: Update the canonical-contract assertion so it still requires the gate destination
    pin without keyword-argument syntax.
  status: completed
- id: prove-dump
  content: Run the Gate source tests, the readiness check, and make odools-diagnostics.
    Do not publish.
  status: completed
isProject: false
built: true
status: built
---

# Clear the four Gate OLS01008 errors

Architecture is already settled. The installed SDK at `.venv` defines `get_gate_client_config_from_env(**overrides)` and `GateClientConfig` already has `local_node`, `timeout_seconds`, `max_timeout_ms`, and `allowed_gate_destination`. OdooLS still reports OLS01008 on the four keyword arguments at [plasticos_gate/services/gate_config.py](plasticos_gate/services/gate_config.py) lines 337–342. Pointing the analyzer at this venv does not clear them: the dump already ran with `.venv/bin/python`.

Do not edit the SDK. Do not construct `GateClientConfig` in Odoo. Do not publish.

MEMORY_PREFETCH: namespace `ib-odoo-19`, snapshot `f9e69f08f9a92e10ba5df37f8f63f47d30e1253bc3ddb67f9174c8c12c3bc5d2`, 62 records, 0 conflicts, policy `memory-phase-lock/v2`.

## Call shape

In `build_gate_client_config`, keep the SDK builder and the same four values. Pass them as one dict:

```python
overrides = {
    "local_node": ODOO_NODE_NAME,
    "timeout_seconds": timeout,
    "max_timeout_ms": int(MAX_GATE_TIMEOUT_SECONDS * 1000),
    "allowed_gate_destination": "gate",
}
return get_gate_client_config_from_env(**overrides)
```

Bump [plasticos_gate/__manifest__.py](plasticos_gate/__manifest__.py) from `19.0.1.9.5` to `19.0.1.9.6`.

## Assertion

[tests/test_gate_canonical_contract.py](tests/test_gate_canonical_contract.py) line 200 requires the source text `allowed_gate_destination="gate"`. Change that assertion to require `"allowed_gate_destination": "gate"` in `gate_config.py`. The pin stays. The keyword-argument spelling is what OLS01008 flags.

`tests/test_gate_sdk_invocation.py` and `tests/test_gate_canonical_env.py` only require the call `get_gate_client_config_from_env(` and forbid `GateClientConfig(`. Those stay true.

## Proof

- `.venv/bin/ruff check` and `ruff format` on the two edited Python files.
- `python3 -m pytest tests/test_gate_sdk_invocation.py tests/test_gate_canonical_env.py tests/test_gate_canonical_contract.py`
- `python3 scripts/check_external_intelligence_readiness.py`
- `make odools-diagnostics`

Done when those four OLS01008 rows are absent. The remaining warnings and the four nested-class information notes stay. If the unpacked dict is still reported as OLS01008, stop. Do not add a second wrapper or rebuild `GateClientConfig` in Odoo.

## Build evidence (auto)

- detected_at: `2026-10-30T19:09:46Z`
- conversation_id: `06fa6ff5-82a5-4b90-bd44-c56e3e13c041`
- generation_id: `110ad348-a33a-4d74-967b-ad5b32014a86`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/06fa6ff5-82a5-4b90-bd44-c56e3e13c041/06fa6ff5-82a5-4b90-bd44-c56e3e13c041.jsonl`
- todos at build time:
- `unpack-overrides`: completed
- `pin-assertion`: completed
- `prove-dump`: completed

