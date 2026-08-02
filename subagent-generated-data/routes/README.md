# Routes

Destination route definitions for the L9 Subagent-Generated Data Law
(`law/SUBAGENT_GENERATED_DATA_LAW.md`, §15–§16).

`canonical-routes.yaml` is the machine-readable registry consumed by
`runtime/routing_engine.py`. Each of the nine canonical routes declares:

- `purpose` — what leverage the route provides (law §15);
- `owner` — the authority domain this law routes *into* but does not own (law §34);
- `accepts` — the generated-data classes that may land here (law §7);
- `promotes_to` — the Tier-3 asset a promoted unit becomes (law §26).

Routing rules enforced by the runtime:

- A unit with no route is invalid unless its decision is `reject` (SGD-017).
- `architecture` promotion requires designated authority (§16.5, SGD-014).
- `evidence` and `reject` do not inject into future context (SGD-011); units
  targeting only those need no invalidation conditions.
- `reject` must carry a reason (SGD-009).

Route ownership is authoritative here; the routing map in
`runtime/classifier.py` (`CLASS_TO_ROUTES`) must stay consistent with the
`accepts` lists in `canonical-routes.yaml`. The conformance test
`tests/test_sgd_routes.py` enforces that consistency.
