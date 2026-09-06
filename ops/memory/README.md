# `ops/memory` — the Cursor memory boundary

Campaign: **Cursor-Governance ↔ l9-graphiti-memory canonical realignment**
(`CURSOR_GOVERNANCE_MEMORY_CONTROL_PLANE_REALIGNMENT_BUILD_PLAN`). This
package is stage **C1 — dependency and egress foundation**. No lifecycle
cutover happens here; `ops/graphiti/` still serves SessionStart/SessionEnd
until C3–C6.

## Rule

Every memory byte leaving this repository crosses a public
`l9-graphite-memory` contract before it can become durable or reach a
projection, and every memory byte entering it is retrieved through that same
authority. Cursor-Governance never knows how to call Graphiti.

```
Cursor / Claude lifecycle
        │
        ▼
Cursor session composition           (ops/graphiti/hydration — unchanged at C1)
        │
        ▼
MemoryControlPlaneClient            (ops/memory/control_plane_client.py)
        │  one `l9-memory <op>` per call; exit code + receipt = verdict
        ▼
l9-memory (bound CLI)                (ops/memory/runtime_binding.py proves which one)
        │
        ▼
MemoryService  →  canonical store  →  outbox  →  optional Graphiti projection
```

## Modules

| Module | Owns | Never |
|---|---|---|
| `runtime_binding.py` | exact package, interpreter, console script, contract signal | PATH-first CLI, sibling checkout discovery, floating refs |
| `control_plane_client.py` | request → command → typed receipt; S-07 failure taxonomy | ranking, dedup, admission, authorization, provider calls |
| `receipts.py` | consumer-side views over canonical receipts (`raw` kept) | a second schema |
| `namespace_context.py` | repository identity, write hint (exactly one), read hints | any grant or denial |
| `session_contracts.py` | `ContinuationCapsuleV2` (`cursor.continuation/v2`), governed-candidate envelope | provider vocabulary |
| `diagnostics.py` | readiness R0 `PACKAGE_BOUND` … R9 `PROJECTION_READY` | "Graphiti is up" == healthy |

## Binding (INV-11)

`ops/config/memory-binding.json` states what Cursor expects: distribution,
version, control-plane contract (`memory-control-plane/v1`), required CLI
operations, and the exact memory git SHA this stage was proven against. The
binding is verified at runtime, never assumed:

```bash
make memory-binding              # proof shape from plan §7
make memory-readiness            # R0..R9; MEMORY_VERIFY_MCP=1 runs the real handshake
L9_MEMORY_DEV_CHECKOUT=/path/to/l9-graphiti-memory make memory-readiness   # explicit dev opt-in
```

Interpreter resolution order: explicit argument → `L9_MEMORY_DEV_CHECKOUT`
(`runtime_mode=development_checkout`, reported, never silent) →
`L9_MEMORY_INTERPRETER` → the governance runtime interpreter. A package served
from outside the interpreter's own environment without the opt-in is
**unbound**, as is a wrong version, a wrong contract, a CLI that predates
`capabilities`, or a CLI whose reported version disagrees with the import.

**Production pin status.** The plan binds production to an immutable release
artifact locked in `uv.lock`. That artifact does not exist yet: the memory
package is not published to an index, and this repository's CI installs with
`uv sync --locked --no-build`, which refuses a git source distribution. The
pin therefore lands at stage **M2** (release `MEMORY_TARGET_VERSION`), after
which `memory-binding.json` moves from the git SHA to the release tag and
`pyproject.toml` / `uv.lock` carry the dependency. Until then the binding is
integration-grade by construction and says so in `binding_status`.

## Egress firewall (INV-03)

```bash
make memory-egress-check                       # warning mode: inventory, exit 0
MEMORY_EGRESS_ENFORCE=1 make memory-egress-check   # stage C11 posture: exit 1 on unlisted/expired
```

`ops/scripts/validate_memory_egress_boundary.py` scans production code and
configuration for `GRAPHITI_MCP_URL`, `GRAPHITI_MCP_TOKEN`,
`search_memory_facts`, `search_nodes`, `search_facts`, `add_memory`,
`add_episode`, `delete_episode`, `graphiti.write_governed`. Every legacy
site is named in `ops/config/memory-egress-allowlist.json` with the stage
that deletes it and an expiry; `tests/ops/memory/test_egress_boundary.py`
fails on any new unlisted site, so the inventory can only shrink.

## Continuation capsule (plan §12)

`ContinuationCapsuleV2` is the structured successor of the provider-only
`PICKUP|objective=…|next=…` string. Cursor owns the schema; memory owns
admission, storage, identity, supersession, and receipts. It crosses the
boundary as a governed candidate (`session_continuation` class,
`namespace_local` visibility, lossless `structured_payload`; memory ADR-082)
and is recovered from record metadata on the next hydrate. Current git state
always wins over a stale capsule (`is_stale_for`).

## Proof

`tests/ops/memory/test_cross_repo_lifecycle.py` is the exact-head cross-repo
lifecycle (plan §35): bind → health → no-hit hydrate → admit capsule →
duplicate replay → hydrate retrieves it → lossless recovery → close dry run →
close commit → idempotent close replay → fan-in denial. It runs against the
real memory runtime when `L9_MEMORY_DEV_CHECKOUT` is set, with provider
variables removed from the environment.
