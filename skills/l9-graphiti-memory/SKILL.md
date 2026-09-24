---
name: l9-graphiti-memory
description: "Canonical agent memory control plane (l9-graphite-memory) — readiness, namespace resolution, canonical hydrate/search, agent-lane write (ordinary: memory.write_agent, direct and ungated; conflict-sensitive: memory.phase_lock → memory.write_governed), bounded hook-lane client, operator CLI write, GMP Phase 0 MEMORY_PREFETCH, /end-session repair. Use when wiring memory, debugging hydration, checking memory health, writing a durable fact, reconciling legacy provider history, or closing a session."
disable-model-invocation: false
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, memory, control-plane, prefetch, gmp, end-session, write-agent, write-governed, two-lanes]
  owner: igor_beylin
  status: active
  version: 2.4.0
  updated: 2026-09-19
---

# Agent memory (canonical control plane)

## Purpose

Operate the one agent episodic memory: the canonical **`l9-graphite-memory`**
control plane (`memory-control-plane/v1`), reached from this repository only
through `ops/memory` (INV-03). Graphiti is a **projection memory owns**, not a
store this repository calls: the direct provider client was retired at
realignment stage C11 and deleted at C15 (nothing remains at
`ops/graphiti/graphiti_memory_client.py`), no surface holds a provider URL or bearer (stage C9), and the
resume SSOT is the canonical continuation record (`ContinuationCapsuleV2`),
never `memory-bank/`.

**One agent memory (ADR-0005, ADR-0030):** the CLI (`python -m ops.memory.cli`)
and the MCP server (`l9-graphite-memory`, stdio, package-owned entry) are
adapters to the same `MemoryService` — ONE authority, ONE canonical egress
(`ops/memory`), Graphiti a downstream projection. Consumer product graphs
(Odoo / PlasticOS Neo4j / Gate) are **out of band** — never Cursor agent
episodic memory.

**Caller taxonomy (ADR-0030 items 7–9):**

| Caller | Adapter | Operation |
|--------|---------|-----------|
| Model, mid-session, ordinary durable fact | MCP `l9-graphite-memory` | `memory.write_agent` (no phase_lock) |
| Model, mid-session, conflict-sensitive fact | MCP `l9-graphite-memory` | `memory.phase_lock` → `memory.write_governed` |
| Model, reading | MCP `memory.search` / `memory.hydrate`, or `memcli search` / `memcli hydrate` | read-only |
| SessionStart / sessionEnd hooks | `ops/memory` (`canonical_hydrate`, `close_session.py`) | `hydrate`, `ingest_candidate`, `close` |
| `/end-session` repair, reconciliation, diagnostics, Program Execution, human operator | `python -m ops.memory.cli` / `hydration.cli repair-write` / `make memory-reconcile-legacy` | purpose-specific; `write` is the operator form |

The memory phase-lock is a memory-write consistency precondition. It is
**never** repository-write authority (rule 96 E7/E8/E10, rule 98). Generic
`memory.ingest` and the operator CLI `write` are not the model's alternative
to `write_agent` or `write_governed`.

**Required by:** `/end-session` / skill `l9-end-session`, GMP Phase 0, the
Claude adapter hooks (`memory_prefetch.py`, `memory_writeback.py`) and the
Cursor session hooks (`ops/hooks/graphiti-*.sh`, `ops/graphiti/hydration/`).

## Interpreter and invocation (fail-closed)

Never call memory with bare `python3` from PATH. Run the CLI from the
governance clone with its locked venv, and name the repository with
`--workspace` (a namespace is repository identity, never the cwd of a shell):

```bash
GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
[ -x "$GRAPHITI_PY" ] || GRAPHITI_PY="${HOME}/Cursor-Governance/.venv/bin/python"
WS="${CURSOR_PROJECT_DIR:-$(pwd)}"
memcli() { (cd "$GOV" && PYTHONPATH="$GOV" "$GRAPHITI_PY" -m ops.memory.cli "$@" --workspace "$WS"); }
```

If `.venv` is missing: `make -C "$GOV" venv`. If memory is unbound
(`readiness` R0 fails): `make -C "$GOV" memory-binding` and read
`ops/config/memory-binding.json`; a development checkout is an explicit
opt-in (`L9_MEMORY_DEV_CHECKOUT=/path/to/l9-graphiti-memory`), never
discovered.

## Switches

| Env | Default | Meaning |
|-----|---------|---------|
| `L9_MEMORY_ENABLED` (alias `GRAPHITI_MEMORY_ENABLED`) | `1` | Master switch for hydrate + close |
| `L9_MEMORY_WRITE_GATES` (alias `GRAPHITI_WRITE_GATES`) | `0` | Hydration-only edit gates (GATES-002); never a lock |
| `L9_MEMORY_NAMESPACE_REQUEST` | unset | Explicit namespace *request*; memory authorizes it |

`~/.cursor/graphiti.env` carries switches only. It never carries a URL or a
bearer; the memory runtime resolves its own configuration (memory ADR-016).

## Two lanes, one `MemoryService` (ADR-0033, INV-03b)

- **Agent lane — you.** `memory.write_agent` (MCP) or `l9-memory write` from a
  shell is the ordinary write. It is direct and ungated: no SessionStart
  receipt, no phase, no session close, no PR step, no Cursor-Governance
  approval or receipt stands in front of it, and the fact is visible to the next
  `hydrate` / `search` immediately (real-time handoff). Cursor-Governance's
  hydration gate exempts `l9-memory` / `python -m ops.memory.cli`.
- **Hook lane — automatic machinery.** SessionStart / End, plan prefetch, PR
  publish and PE/SGD ingest go through `MemoryControlPlaneClient(surface=…)`
  under `ops/config/memory-hook-envelopes.json` (allowed ops, record classes,
  `max_records`, `max_bytes`, `provenance_required`; `principal.type=hook`).
  Cursor-Governance keeps no memory cognition of its own: the close hands the
  redacted excerpt to `l9-memory distill`.
- Both lanes end at `MemoryService`. Neither touches a provider.

## Hydrate / close alignment (ADR-0034, ADR-0035)

SessionStart and sessionEnd share one task string:
`session_task_objective(project)` → `Continue work in {folder}`. Do not
hydrate under `Resume session in {folder}`.

A healthy SessionStart with a write-namespace hint makes **four** control-plane
calls (health, hydrate, tagged continuation, 24h agent-lane search). The
fourth call is `--recorded-after <now-24h>` on the **primary namespace only**.
It fail-opens if the bound CLI does not accept the flag. Classify hits with
`ops/memory/agent_lane.py`; do not open sqlite.

sessionEnd runs the same 24h search (envelope allows `search`) and folds
agent-lane decisions / unfinished work / file paths into the
`ContinuationCapsuleV2` before `ingest_candidate`. This does not constrain
`write_agent`.

## Interactive write (agent lane)

On the `l9-graphite-memory` MCP server (rendered only when
`L9_MEMORY_INTERPRETER` is bound; `make memory-mcp-install`). ADR-0031 dual
classes — `write_agent` is the ordinary write; the governed pair is optional
and conflict-sensitive:

Never freehand: build the arguments with the agent write contract
(`l9.agent_memory_write.v1`, `ops/memory/AGENT_WRITE_CONTRACT.md`) and pass them
to the tool unchanged:

```bash
python -m ops.memory.agent_write build --namespace <write hint> --class decision \
  --content "<one atomic fact, one line>" --tag <topic> --source-id <PR/commit/ADR>
# prints {"tool": "mcp__l9-graphite-memory__memory_write_agent", "arguments": {…}}
```

```text
# ordinary / cold — no SessionStart receipt, no phase_lock
memory.write_agent     {namespace: "<memcli resolve → write_namespace_hint>",
                        content: "<one atomic fact, one line>",
                        memory_class: "insight" | "decision" | "observation" | "constraint" | "episodic" | "semantic",
                        tags: ["agent:cursor", "<topic>"], idempotency_key: "agent:<ns>:<digest>"}

# conflict-sensitive — lock then governed write
memory.phase_lock      {namespace: "<memcli resolve → write_namespace_hint>",
                        task_signature: "<task>", ttl_seconds: 1800}
memory.write_governed  {namespace, content: "<one atomic fact, one line>", task_signature,
                        memory_class: "insight" | "decision" | …,   # canonical only: no alias table here
                        tags: ["agent:cursor", "<topic>"], idempotency_key: "agent:<ns>:<digest>"}
```

`MemoryService` grants the lock only after a conflict check on the namespace
snapshot and re-verifies the digest inside the admitting transaction; a
refused lock or write is the verdict. If the MCP server is unbound, report the
gap (`memcli readiness`) — do not reroute the fact through `memory.ingest` or
the operator CLI.

## CLI (operator / hooks / deterministic adapters)

```bash
memcli health
memcli readiness --json                 # R0 PACKAGE_BOUND … R9 PROJECTION_READY
memcli resolve                          # repository identity + namespace hints (no grant)
memcli search "query" --limit 5
memcli hydrate "current task"           # typed continuation + context sections
memcli conflicts                        # evidence, never a repository mutex
memcli write "durable fact…" --kind lesson --agent-id cursor          # operator form
memcli write "…" --kind decision --idempotency-key "adr:0030"        # operator form
```

Every verdict is the canonical receipt printed as JSON beside the outcome
status (`OK`, `NO_HITS`, `REJECTED`, `QUARANTINED`, `UNAUTHORIZED_NAMESPACE`,
`CANONICAL_UNAVAILABLE`, `TIMEOUT`, `INVALID_RECEIPT`, `BINDING_FAILED`).
Exit `0` = completed (incl. `NO_HITS` / dry run), `1` = refused or unavailable,
`3` = no runtime bound.

### `write` flags (authoritative; operator / adapter CLI)

| Allowed | Not a CLI flag |
|---------|----------------|
| `--kind KIND` (memory class; legacy `pickup_context`, `pattern`, `error`, `note`, `rule` are mapped) | **`--scope`** — does not exist |
| `--group-id NS` (a request; omit to use the registry hint) | a URL, a token, a tunnel |
| `--agent-id AGENT` (or `L9_MEMORY_AGENT_ID`; stamped as tag `agent:<id>`) | a phase-lock — the CLI `write` is the operator path, not the model's governed write |
| `--tag T`, `--idempotency-key K`, `--source S`, `--dry-run` | |

Live path map: [`docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md).
Boundary: [`ops/memory/README.md`](../../ops/memory/README.md).

## Session lifecycle

1. **sessionStart** — open latch, then `ops.memory.hydration.canonical_hydrate`
   (health → hydrate → typed continuation records) composes the
   `SessionHydrationPacket` (`next=` + evidence). A stale capsule loses to the
   current git state and is not a fault. The packet carries three typed
   conditions (ADR-0032): a prior-session close-gap leads with `CLOSE_GAP` +
   `REPAIR: /end-session`; an unbound runtime leads with `ENVIRONMENT_FAULT`
   + `REPAIR: make -C ~/.cursor-governance memory-readiness`; only canonical
   memory not answering leads with `DEGRADED`.
2. **Resume** — follow hydrated `next=`; `memcli hydrate` if `DEGRADED`; repair
   the environment (not memory) on `ENVIRONMENT_FAULT`; never read
   `memory-bank/`.
3. **Session work** — atomic T2 writes: ordinary `memory.write_agent`;
   conflict-sensitive `memory.phase_lock` → `memory.write_governed`
   (arguments built by `ops.memory.agent_write`, canonical `memory_class`). Do not wait for sessionEnd.
4. **sessionEnd hook** — `graphiti-session-end.sh` → Phase A/B close:
   `ContinuationCapsuleV2` → governed candidate → `memory.close` with an
   idempotency key; the local obligation under `.l9/memory/closes/` answers
   only "do I still owe a close?" (`authority: none`).
5. **`/end-session` / `l9-end-session`** — force-retry / offline recovery only:
   `hydration.cli repair-write` (canonical write + receipt stamp).

## Proactive writes (T2)

When a durable doctrine, lesson, or ADR delta lands in-repo, write it without
waiting to be asked:

```text
memcli resolve                          # expect the repo namespace, e.g. cursor-governance
python -m ops.memory.agent_write build --namespace cursor-governance --class insight --content "…" --tag <topic>
memory.write_agent     {…the printed arguments, unchanged…}
# only when concurrent writers / snapshot consistency matter:
memory.phase_lock      {namespace: "cursor-governance", task_signature: "<task>"}
python -m ops.memory.agent_write build … --task-signature "<task>"   # tool: memory_write_governed
memory.write_governed  {…the printed arguments, unchanged…}
```

**MUST NOT** request the shared workspace namespace as a write target — memory
refuses it and the refusal is the verdict. **MUST NOT** substitute
`memory.ingest` or `memcli write` for `write_agent` / `write_governed`; those are the
deterministic-adapter and operator forms.

## GMP Phase 0

```bash
memcli conflicts
```

Declare `MEMORY_PREFETCH:` from the canonical receipt — `namespace`,
`snapshot_digest`, `checked_record_count`, `conflicts` (count or ids),
`policy_version` — never "episode names".

**Conflicts are evidence, never a repository mutex.** They never revoke
another agent's write authority and never gate an edit. Repository-write
authority comes from a dedicated worktree, a branch off fetched `origin/main`,
and the publication gate (`rules/96-multi-agent-main-bound-execution.mdc`
E7/E8). There is no agent-facing force-lock. The `memory.phase_lock` a
governed write needs is a different thing: a memory-side precondition that
gates nothing but that write.

## Legacy provider history (stage C10)

Provider-only records are reconciled through canonical admission, never read
by this repository:

```bash
make -C "$GOV" memory-reconcile-legacy EXPORT=/path/to/export.json         # dry run
make -C "$GOV" memory-reconcile-legacy EXPORT=/path/to/export.json APPLY=1
```

Admitted records carry the producer `Cursor-Governance/legacy-reconciliation`
and the tag `legacy_unverified`.

## Wiring verify

```bash
bash .cursor-commands/ops/scripts/check_governance_wiring.sh "$(pwd)"
make -C "$GOV" memory-readiness
bash .cursor-commands/ops/graphiti/test_gate_e2e_full.sh
```

## Authority

1. `CANONICAL_LAW.md` §8.2 (2026-09-06) — memory control plane is the single front door; §8.3 (2026-09-07) — interactive write contract; §8.5 (2026-09-13) — ADR-0031 dual write classes; §8.6 (2026-09-15) — two lanes, one `MemoryService` (agent lane direct and ungated; hook lane bounded)
2. `docs/decisions/ADR-0033-two-lanes-one-memoryservice.md`; `INVARIANTS.md` INV-03b; `ops/config/memory-hook-envelopes.json`
3. `docs/decisions/ADR-0031-signed-agent-mcp-write-classes.md` (cold `write_agent`; high-stakes `write_governed`); ADR-0030 items 7–9 as amended
4. `rules/03-graphiti-memory.mdc`, `98-graphiti-memory-gate.mdc`, `97-graph-layer-boundary.mdc`, `87-cursor-memory-kernel.mdc`
5. `ops/memory/README.md` (caller taxonomy), `ops/config/memory-binding.json`, `ops/graphiti/group_registry.yaml` (hints, no grants), `environment/agents/adapters/claude-code/memory/memory-enforcement.contract.json` (`interactive_memory_write`)
6. `skills/l9-end-session/SKILL.md` — session-close repair path
7. `docs/decisions/ADR-0005-one-agent-memory-domain-out-of-band.md`
