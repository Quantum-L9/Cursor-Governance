# `ops/memory` — the Cursor memory boundary

Campaign: **Cursor-Governance ↔ l9-graphiti-memory canonical realignment**
(`CURSOR_GOVERNANCE_MEMORY_CONTROL_PLANE_REALIGNMENT_BUILD_PLAN`). Stage
**C12 (complete)**: canonical hydration is the SessionStart authority,
canonical close is the SessionEnd authority, the package-owned
`l9-graphite-memory` server is the only memory MCP server on every surface,
the Claude adapter hooks and the Cursor write gates read canonical evidence
only, no surface holds a provider URL or bearer, the direct provider client is
a tombstone, and the egress scanner enforces. No production path reads or
writes a provider; Graphiti receives records only through canonical projection
(the C5 cutover, plan §41), and no rollback restores a direct write (plan §30).
Law: `CANONICAL_LAW.md` §8.2, `docs/decisions/ADR-0030-memory-control-plane-single-front-door.md`.

## Rule

Every memory byte leaving this repository crosses a public
`l9-graphite-memory` contract before it can become durable or reach a
projection, and every memory byte entering it is retrieved through that same
authority. Cursor-Governance never knows how to call Graphiti.

```
Cursor / Claude lifecycle
        │
        ▼
Cursor session composition           (ops/graphiti/hydration/compile_session_packet.py)
        │
        ▼
canonical_hydrate                    (ops/memory/hydration.py)
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
| `namespace_context.py` | repository identity, write hint (exactly one), read hints incl. the registry's `shared_read_namespaces`; the sole producer since C2 (the legacy resolver shim was deleted at C11) | any grant or denial |
| `cli.py` | `python -m ops.memory.cli health\|resolve\|search\|write\|hydrate\|conflicts\|readiness` — the operator, GMP and Program Execution front door; every verdict is the canonical receipt printed beside the outcome status | a provider, a credential, a grant |
| `legacy_reconciliation.py` | provider-only history classified A–G and admitted through canonical ingress tagged `legacy_unverified` | reading a provider |
| `session_contracts.py` | `ContinuationCapsuleV2` (`cursor.continuation/v2`), governed-candidate envelope | provider vocabulary |
| `hydration.py` | `canonical_hydrate`: health → hydrate (fan-in requested, narrowed on denial) → tag-selected continuation records → newest valid capsule as evidence, stale when HEAD moved | provider search, gap-filling from a projection, reviving superseded records |
| `session_state.py` | `~/.cursor/l9-memory-session-state/<session>.json`: session id, task signature, namespace request, receipt digests, explicit task satisfactions; `authority: none`; the hydration-only predicate the Cursor write gates read | any claim of memory truth; any lock |
| `mcp_instantiation.py` | `~/.cursor/mcp.json` as a real per-machine file rendered from `environment/mcp/master.mcp.json`; drops the retired `graphiti-memory` key; delegates the memory entry to `l9-memory client cursor install/verify` against the bound runtime | authoring the memory entry |
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
make memory-egress-check        # enforce mode since C11: exit 1 on any unlisted or expired site
```

`ops/scripts/validate_memory_egress_boundary.py` scans production code and
configuration for `GRAPHITI_MCP_URL`, `GRAPHITI_MCP_TOKEN`,
`search_memory_facts`, `search_nodes`, `search_facts`, `add_memory`,
`add_episode`, `delete_episode`, `graphiti.write_governed`. Since stage C11
the allowlist (`ops/config/memory-egress-allowlist.json`, `mode: enforce`)
names only negative checks, the scanner's own self-references, and two
operator-owned files (the protected provider compose file and the secret
inventory row); `tests/ops/memory/test_egress_boundary.py` fails on any
unlisted site and on any entry that is not `never`/`operator`.

## Continuation capsule (plan §12)

`ContinuationCapsuleV2` is the structured successor of the provider-only
`PICKUP|objective=…|next=…` string. Cursor owns the schema; memory owns
admission, storage, identity, supersession, and receipts. It crosses the
boundary as a governed candidate (`session_continuation` class,
`namespace_local` visibility, lossless `structured_payload`; memory ADR-082)
and is recovered from record metadata on the next hydrate. Current git state
always wins over a stale capsule (`is_stale_for`).

## Session close (plan §15, §16)

`ops/graphiti/hydration/close_session.py`: gather → `ContinuationCapsuleV2`
→ governed candidate (`ingest-governed-candidate`) → receipt validated →
close summary → `memory.close` with `cursor-close:<namespace>:<session>:<head>`
as idempotency key → `CloseReceipt` validated → local obligation
`closed_canonically`. The obligation (`<project>/.l9/memory/closes/<session>.json`)
answers only "do I still owe a close?": it carries the namespace requested,
the capsule digest, the continuation verdict and reference, the canonical
operation id, the idempotency key, failure class and retry count, with
`authority: none`. It is written `close_incomplete` *before* `memory.close`
runs, so an interrupted close is visible and `retry-close` replays it under
the same key (one logical close). Phase B promotions (lesson/insight/decision)
use the generic canonical `write` with per-item idempotency keys.

## MCP instantiation (stage C7) and surface realignment (stage C8)

```bash
make memory-mcp-check                       # drift report for ~/.cursor/mcp.json, writes nothing
make memory-mcp-install                     # real file (replaces the old symlink), memory entry via the package
MEMORY_VERIFY_MCP=1 make memory-mcp-install # + the package's own stdio handshake proof
```

The master inventory never authors the memory entry. Every renderer (Cursor,
Claude Desktop) hands it to `l9-memory client cursor install --path …` against
the runtime `runtime_binding.py` proved, so the same atomic, digest-backed,
secret-free entry lands on every surface; Claude Code's project template
declares the identical argv gated on `L9_MEMORY_INTERPRETER`. The retired
`graphiti-memory` front door is dropped from every rendered file and rejected
by `validate_claude_env.py`, `environment/agents/tools/validate_agents.py`, the
repo hygiene check and the governance self-check.

On Claude Code the lifecycle hooks (`memory_prefetch.py`, `memory_writeback.py`)
reach memory only through `memory/memory_bridge.py` → `ops/memory`; the Cursor
write gates (`ops/graphiti/graphiti_gate_lib.py`) read the canonical session
state and nothing else. A subagent inherits its parent's evidence read-only:
it never hydrates under its own identity, never writes state, never closes
(`memory_writeback` records `skipped_subagent`).

## Secret isolation (stage C9) and legacy reconciliation (stage C10)

No surface holds a provider URL or bearer. The Cursor hooks load switches
only (`ops/hooks/graphiti_common.sh`), the bootstraps and readiness emitter
probe `ops/memory/diagnostics.py` instead of an HTTP front door, the adapter
examples and `agent_registry.yaml` name the control plane and not a
transport, `ops/secrets/capabilities.yaml` registers no memory capability,
and `control_plane_client.py` strips any stale provider variable from the
memory CLI's environment. `tests/ops/memory/test_secret_isolation.py` holds
all of that.

Provider-only history is reconciled through canonical admission, never read
by this repository: an export (`cursor.legacy-provider-export/v1`, produced
outside the boundary) is classified A–G by `ops/memory/legacy_reconciliation.py`
and the B (continuation) and C (durable) classes are admitted with the
producer `Cursor-Governance/legacy-reconciliation` and the tag
`legacy_unverified` (`make memory-reconcile-legacy EXPORT=…`, dry run by
default). The offline distill worker and the generated-data ingress cross the
same control plane. `ops/config/memory-canonical-epoch.json` records the
epoch from which the provider is a projection memory owns.

## Legacy deletion (stage C11) and law convergence (stage C12)

Deleted: the provider client (a tombstone remains at
`ops/graphiti/graphiti_memory_client.py`, exit 2, naming the replacement),
the provider env plane (`graphiti_env_loader.py`, `graphiti.env.defaults`,
`graphiti.env.example`, `init_graphiti_machine_env.sh`), the shadow reader in
`compile_session_packet.py`, `group_resolver.py`, `episode_contract.py` (PII
redaction now `ops/graphiti/hydration/redaction.py`), `outcome_label.py`,
`prune.py`, `transcript_distiller.py`, `mcp.json.example`, and their tests.
`python -m ops.memory.cli` is the executable successor for every interactive,
GMP, Program Execution and skill path; the runtime reporter's memory row and
`check_governance_wiring.sh` read the binding, not a client.

Law: `CANONICAL_LAW.md` §8.2 (2026-09-06), `AGENTS.md` "Memory control
plane" amendment, ADR-0030, rules `03` / `87` / `98`, skill
`l9-graphiti-memory` v2.0.0, `docs/MEMORY_PIPELINE_MAP.md`,
`docs/DEGRADED_MODE_CONTRACT.md` dated memory section.

## Proof

`tests/ops/memory/test_cross_repo_lifecycle.py` is the exact-head cross-repo
lifecycle (plan §35): bind → health → no-hit hydrate → admit capsule →
duplicate replay → hydrate retrieves it → lossless recovery → close dry run →
close commit → idempotent close replay → fan-in denial. It runs against the
real memory runtime when `L9_MEMORY_DEV_CHECKOUT` is set, with provider
variables removed from the environment.
