---
name: l9-graphiti-memory
description: Canonical agent memory control plane (l9-graphite-memory) — readiness, namespace resolution, canonical hydrate/search/write, GMP Phase 0 MEMORY_PREFETCH, /end-session repair. Use when wiring memory, debugging hydration, checking memory health, reconciling legacy provider history, or closing a session.
disable-model-invocation: false
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, memory, control-plane, prefetch, gmp, end-session]
  owner: igor_beylin
  status: active
  version: 2.0.0
  updated: 2026-09-06
---

# Agent memory (canonical control plane)

## Purpose

Operate the one agent episodic memory: the canonical **`l9-graphite-memory`**
control plane (`memory-control-plane/v1`), reached from this repository only
through `ops/memory` (INV-03). Graphiti is a **projection memory owns**, not a
store this repository calls: the direct provider client was retired at
realignment stage C11 (`ops/graphiti/graphiti_memory_client.py` is a
tombstone), no surface holds a provider URL or bearer (stage C9), and the
resume SSOT is the canonical continuation record (`ContinuationCapsuleV2`),
never `memory-bank/`.

**One agent memory (ADR-0005, ADR-0030):** the CLI (`python -m ops.memory.cli`)
and the MCP server (`l9-graphite-memory`, stdio, package-owned entry) are
transports to the same store. Consumer product graphs (Odoo / PlasticOS Neo4j /
Gate) are **out of band** — never Cursor agent episodic memory.

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

## CLI

```bash
memcli health
memcli readiness --json                 # R0 PACKAGE_BOUND … R9 PROJECTION_READY
memcli resolve                          # repository identity + namespace hints (no grant)
memcli search "query" --limit 5
memcli hydrate "current task"           # typed continuation + context sections
memcli conflicts                        # evidence, never a repository mutex
memcli write "durable fact…" --kind lesson --agent-id cursor
memcli write "…" --kind decision --idempotency-key "adr:0030"
```

Every verdict is the canonical receipt printed as JSON beside the outcome
status (`OK`, `NO_HITS`, `REJECTED`, `QUARANTINED`, `UNAUTHORIZED_NAMESPACE`,
`CANONICAL_UNAVAILABLE`, `TIMEOUT`, `INVALID_RECEIPT`, `BINDING_FAILED`).
Exit `0` = completed (incl. `NO_HITS` / dry run), `1` = refused or unavailable,
`3` = no runtime bound.

### `write` flags (authoritative)

| Allowed | Not a CLI flag |
|---------|----------------|
| `--kind KIND` (memory class; legacy `pickup_context`, `pattern`, `error`, `note`, `rule` are mapped) | **`--scope`** — does not exist |
| `--group-id NS` (a request; omit to use the registry hint) | a URL, a token, a tunnel |
| `--agent-id AGENT` (or `L9_MEMORY_AGENT_ID`; stamped as tag `agent:<id>`) | |
| `--tag T`, `--idempotency-key K`, `--source S`, `--dry-run` | |

Live path map: [`docs/MEMORY_PIPELINE_MAP.md`](../../docs/MEMORY_PIPELINE_MAP.md).
Boundary: [`ops/memory/README.md`](../../ops/memory/README.md).

## Session lifecycle

1. **sessionStart** — open latch, then `ops.memory.hydration.canonical_hydrate`
   (health → hydrate → typed continuation records) composes the
   `SessionHydrationPacket` (`next=` + evidence). A stale capsule loses to the
   current git state; a prior-session close-gap leads with `DEGRADED` +
   `REPAIR: /end-session` (ADR-0028).
2. **Resume** — follow hydrated `next=`; `memcli hydrate` if degraded; never
   read `memory-bank/`.
3. **Session work** — atomic T2 writes (`--kind lesson|insight|decision`).
   Do not wait for sessionEnd.
4. **sessionEnd hook** — `graphiti-session-end.sh` → Phase A/B close:
   `ContinuationCapsuleV2` → governed candidate → `memory.close` with an
   idempotency key; the local obligation under `.l9/memory/closes/` answers
   only "do I still owe a close?" (`authority: none`).
5. **`/end-session` / `l9-end-session`** — force-retry / offline recovery only:
   `hydration.cli repair-write` (canonical write + receipt stamp).

## Proactive writes (T2)

When a durable doctrine, lesson, or ADR delta lands in-repo, write it without
waiting to be asked:

```bash
memcli resolve                          # expect the repo namespace, e.g. cursor-governance
memcli write "…" --kind lesson --agent-id cursor
```

**MUST NOT** request the shared workspace namespace as a write target — memory
refuses it and the refusal is the verdict. Prefer the CLI over raw MCP tools.

## GMP Phase 0

```bash
memcli conflicts
```

**Conflicts are evidence, never a repository mutex.** They never revoke
another agent's write authority and never gate an edit. Repository-write
authority comes from a dedicated worktree, a branch off fetched `origin/main`,
and the publication gate (`rules/96-multi-agent-main-bound-execution.mdc`
E7/E8). There is no agent-facing force-lock.

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

1. `CANONICAL_LAW.md` §8.2 (2026-09-06) — memory control plane is the single front door
2. `docs/decisions/ADR-0030-memory-control-plane-single-front-door.md`
3. `rules/03-graphiti-memory.mdc`, `98-graphiti-memory-gate.mdc`, `97-graph-layer-boundary.mdc`
4. `ops/memory/README.md`, `ops/config/memory-binding.json`, `ops/graphiti/group_registry.yaml` (hints, no grants)
5. `skills/l9-end-session/SKILL.md` — session-close repair path
6. `docs/decisions/ADR-0005-one-agent-memory-domain-out-of-band.md`
