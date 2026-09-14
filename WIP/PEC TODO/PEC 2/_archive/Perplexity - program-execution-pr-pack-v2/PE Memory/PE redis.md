Redis in this repo is active memory (multi-agent presence, working context, pub/sub). It is not the canonical store, not Graphiti, and not SessionStart hydration. README is explicit: SQLite MemoryService works without Redis.

File	Role	Active?	Connects to
src/l9_graphite_memory/active/redis_adapters.py
RedisActiveStore (presence/context keys, TTLs, Lua CAS) and RedisAwarenessBus (exact-channel PUBLISH/SUBSCRIBE)
Code is shipped; not wired into MemoryService, MCP memory.*, or this campaign
Consumer-supplied redis:// / rediss:// (default port 6379). Keys under l9gm:active:v1:{deployment_hash}:…
src/l9_graphite_memory/active/credentials.py
Resolves Redis URL from file / password file / secret-provider callback / url_env (ADR-066)
Used only if a consumer constructs the Redis adapters
Same URL; never logs the raw secret
src/l9_graphite_memory/resources/active_memory_redis_capabilities.yaml
Least-privilege Redis 7.2+ ACL contract (allowed commands, key/channel patterns)
Manifest is live; nothing here applies it
Documents what a dedicated Redis instance must allow
tools/assurance/render_active_memory_redis_acl.py
Renders an ACL line from that manifest
Assurance tool, not runtime
Does not open a Redis connection
docs/adr/ADR-066-*.md, ADR-068-*.md, docs/ACTIVE_MEMORY_*.md
Credential + ACL + deployment contract
Docs only
Consumer must bring a private, authenticated Redis
tests/unit/active/test_credentials.py, test_redis_acl_renderer.py
Unit tests
Active in the unit suite
No live Redis
tests/conformance/active/
Adapter contract
In-memory only — fixture still says Redis is a follow-up
Does not hit Redis
What they are for: a consumer app that wants live agent presence (“who is working on what”) and awareness events. That is orthogonal to episodic/canonical memory.

What they are not connected to: Graphiti, Zep, SQLite RecordStore, PE Gate 0, or Cursor session Redis (that is a separate governance MCP cache, not this package).

How dormant it is: redis is an optional extra (pip install .[active]). RedisActiveStore / RedisAwarenessBus are intentionally not on the public SDK. There is no Redis service, compose file, or default host in this repo. A consumer must construct the adapters and point them at their own Redis 7.2+ instance.



**Do not move it out of this repo yet.** It is also **not a tool.**

Redis here is an **optional working-state / agent-awareness plane**: presence, leases, short-TTL working context, and pub/sub. ADR-065–068 put it in this package on purpose because those records are meant to **promote into canonical memory** with deployment provenance. Graphiti/Zep/SQLite are not supposed to talk to it on the read path. ADR-067 is explicit: if Redis is down, MemoryService must still work.

That is a different category from “memory,” and a different category from “a Redis tool.”

| Category | What it is | Where it belongs |
|---|---|---|
| **Canonical memory** | MemoryService → RecordStore → outbox → Graphiti/Zep | this repo (keep) |
| **Working-state / awareness** | who is live, what they are on, heartbeat, awareness events | this repo as `.[active]` until a real runtime consumer owns the Redis box |
| **Agent lifecycle** | checkpoint restore, scheduling, process supervision | **outside** this repo (ADR-028 / ADR-053 already drew that line) |
| **Tool** | `render_active_memory_redis_acl.py` | stays as an assurance helper next to the ACL manifest |
| **Redis the server** | instance, ACL, network, secrets | consumer deployment, never this repo |

The naming is what is misleading. “Active memory” sounds like a second memory SSOT. It is closer to **runtime coordination** that can later become a memory write. Same family as checkpoints: adjacent to agents, not the memory control plane.

**Why not extract now**

- There is no second consumer and no wired `promote` path yet. A new repo would be an unwired SDK.
- The adapters are already isolated: optional extra, not on the public SDK, not in the campaign.
- Moving it would force a new ADR and a promotion contract you do not have yet.

**When a move is the right call**

Move it when a real runtime (bot fleet, OpenClaw, PE workers) owns multi-agent presence **and** this repo only needs to accept a governed ingest. Then:

- **Runtime repo** owns Redis, `ActiveAgentClient`, heartbeats, ACL deploy.
- **This repo** keeps a thin promote/ingest contract plus `ActiveDeployment` provenance on the resulting memory record.

Do not create an `l9-redis` tools repo. Redis is just the backend.

**What to do now:** leave the files here, treat them as out of campaign scope, and mentally recategorize them as working-state, not memory. If you want a paper trail, that is an ADR note, not a move.


=========
You cannot flip a switch and “turn Redis on” in this repo. The designed activation path is **a consumer runtime using the SDK**, not MemoryService or MCP. The factory that was supposed to hide Redis is the missing piece.

`ActiveAgentClient` says it is built by `l9_graphite_memory.adapters.factory.ActiveMemoryFactory`. That class does not exist. `adapters/factory.py` only builds SQLite + Graphiti/Zep/none. `MemorySettings` has no `active_memory.enabled`. Conformance still runs only against in-memory. So the product is designed; the last wiring layer was never finished.

**What you already have (use this, do not rebuild it)**

| Piece | Use it as |
|---|---|
| `ActiveAgentClient` / `ActiveAgentSession` | The only public API (ADR-067) |
| `ActiveDeployment` | One process, one Redis, one identity |
| `RedisCredentialSettings` + `resolve_redis_credential` | How secrets get in (ADR-066) |
| `RedisActiveStore` / `RedisAwarenessBus` | Internal adapters (do not import from consumer app code) |
| `NullActiveStore` | What “disabled” must look like — fail closed, no fake presence |
| `InMemoryActiveStore` | Tests and local proof only |
| ACL manifest + `render_active_memory_redis_acl.py` | How the Redis box is locked down |
| `tests/conformance/active/` + `tests/external_runtime/` | The contract the Redis backend must pass |

`MemoryService.promote` is a different thing (curate a stored record). It does **not** promote Redis working-state into Graphiti. That join is specified in ADR-065 and not implemented.

---

**Phase 1 — prove the design without Redis (already possible)**

Run the existing suites. They are the designed behavior:

- session start → `ACTIVE`
- `replace_context` / `list_active` / `subscribe`
- heartbeat, lease expiry, degrade, resync
- disabled = `ActiveMemoryUnavailableError`, never silent success

That is “activated” against the in-memory reference. Redis is supposed to be a drop-in behind the same ports.

**Phase 2 — stand up Redis the way the contract requires**

In a **consumer** deploy (not this repo):

1. Dedicated Redis **7.2+**, not public, auth required, `maxmemory` + volatile eviction.
2. Pick real `deployment_id` + `trust_domain` (production rejects `test` / `example` / `changeme`).
3. Render the ACL from the manifest you already have (`render_active_memory_redis_acl.py`) with that deployment hash.
4. Put the URL in a secret file (`url_file`) or `password_file` — not a committed `.env`.
5. Install the extra: `redis>=5,<7` (`.[active]`).

**Phase 3 — finish the one missing designed object**

Add `ActiveMemoryFactory` in this package (the docstring already names it). As designed it should:

1. Read `active_memory.enabled` (does not exist yet).
2. If false → wire **null** adapters.
3. If true + `backend=redis` → `resolve_redis_credential` → construct Redis store/bus internally → return `ActiveAgentClient`.
4. If true + `backend=memory` → in-memory (dev/test only).
5. Bind exactly one `ActiveDeployment` at process start.
6. Never let consumer code import `RedisActiveStore`.

Until that factory exists, “full activation” means a consumer constructing the client the way the tests already do — which the SDK says is interim, not the designed public path.

**Phase 4 — prove Redis equals in-memory**

Do what `tests/conformance/active/conftest.py` already tells you to do: parametrize the same suite against a live Redis. Then run the deployment checklist:

- startup probe: PING, GET/SET, ZADD, PUBLISH
- stop Redis → sessions go `DEGRADED` / raise `ActiveMemoryUnavailableError`
- **canonical** `memory.write` / `memory.search` still succeed (ADR-067 / ADR-015)
- no secrets in logs (`redacted_summary()`)

**Phase 5 — use it as designed (the actual product)**

In each agent process:

```text
factory → ActiveAgentClient
  → open_session(agent_id, role, principal_id, group_ids)
    → replace_context(objective, status, working_on)
    → list_active(group_id=...)
    → subscribe(group_id=...)
```

That is presence + awareness. It does not hydrate Cursor, does not write Graphiti, and must not sit on the MemoryService hot path.

**Phase 6 — the designed join you do not have yet**

Only after Phase 4 is green: take a durable slice of `ActiveContext` and **ingest** it through MemoryService (not Redis, not Graphiti directly), stamping `deployment_id` / `trust_domain` in provenance. That is the ADR-065 promotion story. Do not bolt Redis onto `memory.hydrate`.

---

**Do not do**

- Turn Redis on inside this campaign or SessionStart.
- Import `RedisActiveStore` from app code.
- Treat `L9_MEMORY_ENABLED` as the active-memory flag (it is canonical memory).
- Point this at C1 `l9-redis` or any shared instance without the ACL + deployment hash.
- Expect MCP `memory.*` to grow Redis tools. That would mix planes.

**Honest status:** you can use everything you have today as a **library** in a consumer, with Redis constructed internally the same way tests construct in-memory. You cannot claim “fully activated as designed” until the factory, settings, and live Redis conformance exist. That is a small, bounded follow-on in this repo — not a new product and not a move-out.
=====

You cannot flip a switch and “turn Redis on” in this repo. The designed activation path is **a consumer runtime using the SDK**, not MemoryService or MCP. The factory that was supposed to hide Redis is the missing piece.

`ActiveAgentClient` says it is built by `l9_graphite_memory.adapters.factory.ActiveMemoryFactory`. That class does not exist. `adapters/factory.py` only builds SQLite + Graphiti/Zep/none. `MemorySettings` has no `active_memory.enabled`. Conformance still runs only against in-memory. So the product is designed; the last wiring layer was never finished.

**What you already have (use this, do not rebuild it)**

| Piece | Use it as |
|---|---|
| `ActiveAgentClient` / `ActiveAgentSession` | The only public API (ADR-067) |
| `ActiveDeployment` | One process, one Redis, one identity |
| `RedisCredentialSettings` + `resolve_redis_credential` | How secrets get in (ADR-066) |
| `RedisActiveStore` / `RedisAwarenessBus` | Internal adapters (do not import from consumer app code) |
| `NullActiveStore` | What “disabled” must look like — fail closed, no fake presence |
| `InMemoryActiveStore` | Tests and local proof only |
| ACL manifest + `render_active_memory_redis_acl.py` | How the Redis box is locked down |
| `tests/conformance/active/` + `tests/external_runtime/` | The contract the Redis backend must pass |

`MemoryService.promote` is a different thing (curate a stored record). It does **not** promote Redis working-state into Graphiti. That join is specified in ADR-065 and not implemented.

---

**Phase 1 — prove the design without Redis (already possible)**

Run the existing suites. They are the designed behavior:

- session start → `ACTIVE`
- `replace_context` / `list_active` / `subscribe`
- heartbeat, lease expiry, degrade, resync
- disabled = `ActiveMemoryUnavailableError`, never silent success

That is “activated” against the in-memory reference. Redis is supposed to be a drop-in behind the same ports.

**Phase 2 — stand up Redis the way the contract requires**

In a **consumer** deploy (not this repo):

1. Dedicated Redis **7.2+**, not public, auth required, `maxmemory` + volatile eviction.
2. Pick real `deployment_id` + `trust_domain` (production rejects `test` / `example` / `changeme`).
3. Render the ACL from the manifest you already have (`render_active_memory_redis_acl.py`) with that deployment hash.
4. Put the URL in a secret file (`url_file`) or `password_file` — not a committed `.env`.
5. Install the extra: `redis>=5,<7` (`.[active]`).

**Phase 3 — finish the one missing designed object**

Add `ActiveMemoryFactory` in this package (the docstring already names it). As designed it should:

1. Read `active_memory.enabled` (does not exist yet).
2. If false → wire **null** adapters.
3. If true + `backend=redis` → `resolve_redis_credential` → construct Redis store/bus internally → return `ActiveAgentClient`.
4. If true + `backend=memory` → in-memory (dev/test only).
5. Bind exactly one `ActiveDeployment` at process start.
6. Never let consumer code import `RedisActiveStore`.

Until that factory exists, “full activation” means a consumer constructing the client the way the tests already do — which the SDK says is interim, not the designed public path.

**Phase 4 — prove Redis equals in-memory**

Do what `tests/conformance/active/conftest.py` already tells you to do: parametrize the same suite against a live Redis. Then run the deployment checklist:

- startup probe: PING, GET/SET, ZADD, PUBLISH
- stop Redis → sessions go `DEGRADED` / raise `ActiveMemoryUnavailableError`
- **canonical** `memory.write` / `memory.search` still succeed (ADR-067 / ADR-015)
- no secrets in logs (`redacted_summary()`)

**Phase 5 — use it as designed (the actual product)**

In each agent process:

```text
factory → ActiveAgentClient
  → open_session(agent_id, role, principal_id, group_ids)
    → replace_context(objective, status, working_on)
    → list_active(group_id=...)
    → subscribe(group_id=...)
```

That is presence + awareness. It does not hydrate Cursor, does not write Graphiti, and must not sit on the MemoryService hot path.

**Phase 6 — the designed join you do not have yet**

Only after Phase 4 is green: take a durable slice of `ActiveContext` and **ingest** it through MemoryService (not Redis, not Graphiti directly), stamping `deployment_id` / `trust_domain` in provenance. That is the ADR-065 promotion story. Do not bolt Redis onto `memory.hydrate`.

---

**Do not do**

- Turn Redis on inside this campaign or SessionStart.
- Import `RedisActiveStore` from app code.
- Treat `L9_MEMORY_ENABLED` as the active-memory flag (it is canonical memory).
- Point this at C1 `l9-redis` or any shared instance without the ACL + deployment hash.
- Expect MCP `memory.*` to grow Redis tools. That would mix planes.

**Honest status:** you can use everything you have today as a **library** in a consumer, with Redis constructed internally the same way tests construct in-memory. You cannot claim “fully activated as designed” until the factory, settings, and live Redis conformance exist. That is a small, bounded follow-on in this repo — not a new product and not a move-out.

If you want that factory + settings + Redis conformance fixture built, switch to Agent mode and say so. Keep it out of the PE campaign.
