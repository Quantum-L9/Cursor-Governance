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

## Caller taxonomy (ADR-0030 items 7–9, CANONICAL_LAW §8.3)

One authority, one egress, two adapters. Who calls what:

| Caller | Adapter | Operation(s) | Role |
|---|---|---|---|
| Model, mid-session, recording a durable fact | `l9-graphite-memory` MCP server (stdio, package-owned) | `memory.phase_lock` → `memory.write_governed` | **The only model write.** `MemoryService` grants the lock after a conflict check on the namespace snapshot and re-verifies the digest inside the admitting transaction; a refused lock or write is the verdict |
| Model, reading | MCP `memory.search` / `memory.hydrate`; or `cli.py search` / `hydrate` | read | evidence only |
| SessionStart hook | `hydration.py` (`canonical_hydrate`) | `health`, `hydrate` | deterministic adapter |
| sessionEnd hook | `ops/graphiti/hydration/close_session.py` | `ingest_candidate`, `close` (idempotent, exact-request replay) | deterministic adapter |
| `/end-session` repair | `ops/graphiti/hydration/pickup_write.py` (`hydration.cli repair-write`) | canonical `write` + close-receipt stamp | deterministic adapter |
| Legacy provider history | `legacy_reconciliation.py` | canonical admission, tag `legacy_unverified` | operator |
| Diagnostics | `diagnostics.py`, `runtime_binding.py` | `readiness`, `health`, `capabilities` | operator / hooks |
| Human operator, Program Execution, GMP Phase 0 | `cli.py` (`python -m ops.memory.cli`) | `write` (operator form), `conflicts`, `resolve` | operator |
| `control_plane_client.py` `phase_lock` / `verify_phase_lock` | consumer-side view of the memory lock | governed-write precondition only | never repository authority |

Rules that follow from the table:

- The memory phase-lock is a **memory-write consistency precondition**. It
  never authorizes a source edit, never serializes git, never replaces
  worktree / branch / publication governance (`rules/96` E7/E8/E10,
  `rules/98`).
- Generic `memory.ingest` and the operator CLI `write` are **not** the model's
  alternative to `write_governed`; routing a model-authored fact through them
  to avoid the lock is a doctrine violation. An unbound MCP server is a
  reported gap (`readiness`), not a reroute.
- Deterministic adapters use purpose-specific operations over the same
  admission path; none of them is a second egress, and none carries a
  provider URL, bearer or raw provider tool.
- Machine form: `environment/agents/adapters/claude-code/memory/memory-enforcement.contract.json`
  `interactive_memory_write` (validated by `validate_memory_enforcement.py`).
  Anti-regression: `ops/scripts/validate_legacy_doctrine_residue.py`.

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
artifact locked in `uv.lock`. `v2.3.0` built and OIDC-authenticated but PyPI
rejected the `constellation` git extra (400). `v2.3.1` is the first index
upload (`publish.yml` run 34172985608, 2026-09-08). `source.ref` is the
`v2.3.1` tag, pinned to its commit by `release_evidence.memory_sha`, and
`pyproject.toml` / `uv.lock` carry `l9-graphite-memory==2.3.1`.

**`exact` means the artifact** (audit CG-P1-03). Version, contract version and
"the module lives under the interpreter prefix" are satisfied identically by
every build of a version, so a status reachable from those alone says nothing
about *which* build is installed — which is the whole question a pinned release
binding exists to answer. The status taxonomy is therefore:

| `binding_status` | Meaning |
|---|---|
| `exact` | the installed artifact **is** the audited release, proved by digest |
| `compatible` | version and contract agree; the artifact was not proved |
| `development_checkout` | an explicit dev opt-in; whatever is on disk there |
| `unbound` | refused — wrong version, wrong contract, foreign path, or a digest that *contradicts* the manifest |

Provenance is read from the installed distribution, not asserted: PEP 610
`direct_url.json` carries the archive hash pip/uv recorded for the wheel, and
`release_evidence.artifact_sha256` is what it must equal. An editable install
has no immutable artifact identity and is never `exact`. A digest that is
present and disagrees is not weak evidence but contradiction, and is refused
rather than downgraded.

`release_evidence.installed_record_digest` is a second, optional pin — a digest
over the installed `RECORD` — for installs that leave no archive hash. The
mechanism works and is tested, but **nothing pins one today, on evidence**:
three `memory-cross-repo` runs installed the byte-identical wheel (its sha256
re-verified by rebuild each time) and produced three different RECORD digests.
The installed RECORD is not a deterministic function of the wheel in that
environment, so a pin would make the binding flap between `exact` and `unbound`
on an unchanged release. Do not pin one until it is shown stable across runs.

That is why the proof job reports `compatible` rather than `exact`: `uv`
records no archive hash for the local-file install it performs. The artifact is
proved there by the job instead, and more strongly — it rebuilds the wheel from
`source.ref` and refuses any sha256 but the audited one before installing.

`L9_MEMORY_REQUIRE_EXACT_ARTIFACT=1` turns `compatible` from "usable, and
reported as unproved" into a refusal; the required cross-repo proof sets it.

**Model names belong to the release.** `CANONICAL_RECEIPT_MODELS` lists what
Cursor *requests*; the release names its own models, and several differ
(`HealthReceipt` is `HealthReport` there, `HydrationReceipt` is
`HydrationResult`, `CapabilitiesReceipt` is `ControlPlaneCapabilities`). The
mapping lives in `memory-binding.json` as `contract_model_aliases` and the
probe accepts any alias, keying the schema by the name Cursor validates under.
A name this side guessed is not a contract the release owes — so nothing
asserts that the release exports Cursor's spelling. The enforcement is
behavioural: an operation whose receipt has no canonical schema returns
`VALIDATION_UNAVAILABLE`, and the binding reasons list what the release does
export so a wrong name is diagnosable rather than mute.

**Does the receipt answer the request?** (audit MEM-P2-01, consumer half.) A
`SearchReceipt` binds the query and the namespaces memory authorized, and binds
nothing about the **tag selector** — and tags change the result set, so the
receipt cannot prove which request produced its hits. Closing that is memory's:
it owns the receipt contract. `search_identity.py` is the other end.

Two rules, and the difference is the point. A selector the receipt *echoes*
must agree with what Cursor sent, or the hits answer another question and the
outcome is `INVALID_RECEIPT`. A result-affecting selector the receipt *omits*
is recorded as **unbound** — never assumed to have matched — and under
`L9_MEMORY_REQUIRE_SEARCH_IDENTITY=1` an unbound selector is
`REQUEST_IDENTITY_UNPROVEN`, a non-success. The two verdicts stay distinct:
provably wrong is not the same as unproven.

Cursor deliberately does **not** recompute memory's `request_digest`. It would
have to guess the canonicalization — field order, tag ordering, absent versus
empty — and a guess that disagrees turns every honest receipt into a rejection.
Cursor computes its own digest for its own evidence, stamped with its own
canonicalization version, and carries memory's digest without comparing the two.
Namespaces are asymmetric on purpose: memory authorizing a *subset* of what
Cursor requested is memory doing its job, so only a namespace Cursor never
asked for is a contradiction.

**Canonical receipt validation** (audit CG-P1-02). Because the memory runtime
may be another interpreter, `import l9_graphite_memory.contracts` cannot
succeed in this process — so the binding *exports* each canonical receipt model
from the bound release as JSON Schema, and `canonical_validation.py` validates
every authoritative receipt against those before any structural view reads a
field. A violation is `INVALID_RECEIPT`; validation that was required and could
not run is `VALIDATION_UNAVAILABLE`, a distinct non-success — structural
acceptance is never a fallback. Every integration receipt records which mode
was reached (`canonical_validation`) and the schema digest it validated
against. `L9_MEMORY_REQUIRE_CANONICAL_VALIDATION=1` makes it mandatory.

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

The lexical scanner is gameable by spelling; the *shape* of the boundary is
enforced architecturally (audit P3-01) by
`tests/ops/memory/test_transport_boundary.py` on the AST and at runtime, and by
the `l9.memory-boundary-*` semgrep rules in `.semgrep/l9-pr.yml` on
`make pr-security`: no module on the memory path (`ops/memory/**`,
`close_session.py`, `pickup_write.py`, `compile_session_packet.py`,
`session_latches.py`, the Claude memory bridge) may import a network or provider
transport (`urllib`, `http`, `socket`, `ssl`, `requests`, `httpx`, `aiohttp`,
`websockets`, the MCP client SDK, `graphiti_core`, `neo4j`, `asyncio`); only
`runtime_binding.py` (the bound `l9-memory`), `namespace_context.py` (git
identity), `mcp_instantiation.py` (the memory-owned installer) and the Claude
`memory_state.py` git probe may spawn a process, always as an argv list; and
`MemoryControlPlaneClient` launches exactly `binding.memory_cli` for every
operation.

## Continuation capsule (plan §12)

`ContinuationCapsuleV2` is the structured successor of the provider-only
`PICKUP|objective=…|next=…` string. Cursor owns the schema; memory owns
admission, storage, identity, supersession, and receipts. It crosses the
boundary as a governed candidate (`session_continuation` class,
`namespace_local` visibility, lossless `structured_payload`; memory ADR-082)
and is recovered from record metadata on the next hydrate. Current git state
always wins over a stale capsule (`is_stale_for`).

Selection is **task-scoped** (audit P1-02): `select_continuation` keeps only
capsules whose `repository_identity` and `task_signature` equal the session's
(`task_signature_for(objective, repository)`, never the session id) and orders
those alone, so two tasks closed against the same repository at the same HEAD
never resume each other. `continuation_policy="repository_fallback"` is the
explicit degraded policy for a caller with no task yet (SessionStart via
`compile_session_packet`): with no task match it takes the newest repository
capsule and marks it `selection=repository_fallback` on the evidence, in the
receipt (`continuation_policy`, `continuation_excluded`) and in a warning.
`python -m ops.memory.cli hydrate --continuation-policy` exposes the knob. The
close capsule carries the task signature the session hydrated under (local
session state), so the next hydration of that task selects it.

A Phase B refinement names the Phase A record in `supersedes`
(`to_governed_candidate(supersedes=...)`, memory ADR-082 amendment; audit
P1-03). Memory validates the target and applies the transition, so one session
leaves exactly one ACTIVE continuation; a refused supersession rejects the
refinement and Phase A stays ACTIVE. `CandidateReceipt.superseded_record_ids`
reports what memory superseded.

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

The obligation also retains the **exact close request** (`close_summary`,
`close_capsule_digest`, `close_session_id`; audit P2-01), written before
`memory.close` runs. `retry_close` replays precisely that under the recorded
key — never a synthesized "retry" summary — and reads memory's replay
forensics back (`CloseReceipt.replay_payload_matched`, `stored_digest`,
`replay_digest`, `warnings`); a replay memory proves different from the stored
close is surfaced as `close replay payload drift`, never hidden behind the
idempotent status.

That surfacing is evidence, not the verdict (audit CG-P1-01). Memory preserves
the first commit under an idempotency key and returns *that* record on a
replay, so a drifted retry comes back with `status=complete` and a `record_id`
— and reading `committed` from it promoted a close request that never
committed. The conflict test now runs **ahead** of every `committed`
promotion: the client returns `IDEMPOTENCY_CONFLICT`, and the obligation goes
to `close_conflicted`, which is neither closed nor merely unfinished. Replaying
the same request cannot resolve it (memory holds a different close under that
key), so it stays a close gap for the next session. Exact replay is unchanged
and still canonical success, including after a conflict. An obligation without
the request material gets a full canonical close instead of a guessed replay.

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
close commit → exact-request close replay (payload-identical) → same-key
drift reported → fan-in denial → task-scoped resume and SessionStart
fallback; then task isolation (Task A / Task B, same repository, same HEAD),
Phase B supersession (A superseded, B active, A no longer retrievable),
refused supersession (A stays active), and a lost-response close retried
with the recorded request. It runs against a real memory runtime when
`L9_MEMORY_DEV_CHECKOUT` (development checkout) or `L9_MEMORY_INTERPRETER`
(installed wheel) is set, with provider variables removed from the
environment; `L9_MEMORY_CROSS_REPO_REQUIRED=1` turns an absent runtime into a
failure and requires the pinned wheel.

`.github/workflows/memory-cross-repo.yml` is that proof as a required,
non-skippable PR check (audit P2-02 / P1-01): it resolves `memory-binding.json`
`source.ref` on the memory remote (the `v2.3.1` release tag is peeled with
`git ls-remote`; a bare SHA is taken as is), refuses any commit other than
`release_evidence.memory_sha` so a moved tag fails rather than rebinds, clones
the memory repository at that SHA, rebuilds the wheel reproducibly under
the recorded `SOURCE_DATE_EPOCH`, refuses a digest that differs from
`release_evidence.artifact_sha256`, installs the wheel into a clean
environment bound through `L9_MEMORY_INTERPRETER`, runs the proof in required
mode with `GRAPHITI_MCP_URL` / `GRAPHITI_MCP_TOKEN` unset, fails if any case
skipped, and records the Cursor head, memory head, package version and
artifact digest in the job summary and a proof artifact
(`cursor.memory-cross-repo-proof/v1`). The live `source.ref` is the `v2.3.1`
tag (cut 2026-09-08). The earlier `v2.3.0` tag stays immutable history. Making the context required in branch protection and the `uv.lock`
artifact pin remain operator steps named in `release_evidence.operator_gated`;
the pin waits for `publish.yml` to succeed on the tag, whose first run was
rejected by the memory repository's `release` environment deployment policy
(it does not yet allow the `v*` tag pattern).
