# Adapters

Repository-class and destination adapters for the L9 Subagent-Generated Data Law
(`law/SUBAGENT_GENERATED_DATA_LAW.md`, §28, §33).

- `base.yaml` — the canonical adapter contract. Its `may_not_weaken` list
  (packet emission, provenance, classification, routing, promotion authority,
  learning closure) is binding on every adapter (law §28).
- `python.yaml`, `typescript.yaml` — repository-class adapters that specialize
  interpretation (file structure, validation authority, ownership hints,
  context selection) without weakening the base contract.
- `memory-adapter.yaml` — the destination adapter for the `memory` route,
  mapping promoted units into advisory Tier-3 memory entries under SGD-013
  (memory never overrides repository state or canonical authority).

Adapters are declarative. The runtime never reads business logic from an
adapter that would relax an invariant; the conformance test
`tests/test_sgd_adapters.py` asserts each adapter preserves the full
`may_not_weaken` set.
