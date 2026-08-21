---
name: Rewrite Zep Transport
overview: Rewrite zep_transport.py in the Quantum-L9/L9-Graphite-Memory repo against Zep Cloud's current graph.* SDK surface (replacing the fully-deprecated zep_python memory/session API), fix the pyproject dependency, and update the transport unit tests. Delivered as a PR to that standalone repo (not igorbot, not Cursor-Governance). The MemoryTransport interface stays identical so nothing else in the pack changes. No live credentials required.
todos:
  - id: rewrite-transport
    content: Rewrite zep_transport.py internals to Zep Cloud graph.* API (health/search/write/_ensure_graph/4 tool handlers), keeping the MemoryTransport interface identical
    status: pending
  - id: fix-pyproject
    content: "Correct pyproject.toml [zep] extra: zep-python>=2.0 -> zep-cloud>=2.0"
    status: pending
  - id: guard-limits
    content: "Encode Zep constraints in write(): 10k-char data guard, scalar/10-key metadata cap, limit<=50 clamp, json-vs-text detection"
    status: pending
  - id: update-tests
    content: Update tests/test_transport.py Zep mocks to client.graph.* and add guard-case tests
    status: pending
  - id: clone-repo
    content: Clone Quantum-L9/L9-Graphite-Memory, create feature branch (WIP copy is byte-identical to main, so changes apply cleanly)
    status: pending
  - id: verify
    content: py_compile + import check + pytest (mocked) green; defer live health/round-trip until ZEP_API_KEY present
    status: completed
  - id: open-pr
    content: Push feature branch and open PR to Quantum-L9/L9-Graphite-Memory (only on explicit user approval)
    status: pending
isProject: false
---

# Rewrite zep_transport.py against Zep Cloud graph.* API

## Why this is needed (verified against live docs)

The WIP transport at [zep_transport.py](/Users/macm2/igorbot-07-19-2026/igorbot/WIP-IGOR/Graphiti%20-%20Cirsor%20Governance%20copy/L9-Graphite-Memory%204/src/l9_graphite_memory/zep_transport.py) targets an SDK surface that no longer exists. Confirmed via [Zep Quick Start](https://help.getzep.com/quick-start-guide), [Graph Search reference](https://help.getzep.com/sdk-reference/graph/search), [Add Business Data](https://help.getzep.com/adding-business-data), [Get Graph Episodes](https://help.getzep.com/sdk-reference/graph/episode/get-graph-episodes), and [List All Graphs](https://help.getzep.com/sdk-reference/graph/list-all-graphs):

- Package/import is wrong: code does `from zep_python.client import Zep`; current is `pip install zep-cloud` -> `from zep_cloud.client import Zep`.
- Every call is a removed `client.memory.*` method (`list_sessions`, `search_sessions`, `add`, `get_session`, `add_session`, `get_session_messages`). The Session/Memory model was replaced by User + Thread + Graph.
- `search_scope="facts"` is not a valid value; current scopes are `edges|nodes|episodes|thread_summaries|observations|auto`.

Good news: our `group_id` namespace maps directly onto Zep's **`graph_id`** (docs explicitly separate `graph_id` from human `user_id`), so no synthetic-user hack is needed.

## Confirmed SDK mapping (this is the whole rewrite)

- health -> `client.graph.list_all(page_size=1)` (lightweight connectivity probe)
- search facts -> `client.graph.search(query=..., graph_id=group_id, scope="edges", limit=...)` -> `results.edges[]` (each is `EntityEdge` with `.fact`, `.uuid`, `.name`, `.created_at`, `.score`)
- search nodes -> same call with `scope="nodes"` -> `results.nodes[]` (`EntityNode`: `.name`, `.labels`, `.uuid`, `.created_at`)
- write/add_episode -> `client.graph.add(graph_id=group_id, type="text"|"json", data=body, created_at=..., metadata={...})` (returns the created episode)
- get_episodes -> `client.graph.episode.get_by_graph_id(graph_id=group_id, lastn=N)` -> `.episodes[]` (`GraphEpisode`: `.content`, `.uuid`, `.created_at`, `.metadata`, `.role`, `.source`)
- ensure graph exists -> `client.graph.create(graph_id=group_id, ...)` wrapped in try/except (idempotent; replaces the old `_ensure_session`)

## Constraints to encode (from docs, not guesses)

- `graph.add` has a hard 10,000-character limit on `data`. Current [episode_contract.py](/Users/macm2/igorbot-07-19-2026/igorbot/WIP-IGOR/Graphiti%20-%20Cirsor%20Governance%20copy/L9-Graphite-Memory%204/src/l9_graphite_memory/episode_contract.py) allows `MAX_BODY_CHARS = 32_000`. The transport must guard the Zep-specific 10k limit (fail clearly or truncate with a logged warning) rather than let Zep reject it. episode_contract.py is sacred/no-touch, so the guard lives in `write()`.
- Episode `metadata`: max 10 keys, scalar values only (string/number/bool). The existing `write()` kwargs filter already keeps only scalars; extend it to also cap key count.
- `search` `limit` max is 50; clamp.
- `type` should be `"json"` when body parses as JSON, else `"text"` (mirrors episode_contract's own source detection).

## Target repo and delivery

Changes land in **`Quantum-L9/L9-Graphite-Memory`** (the standalone package's own repo), NOT `igorbot` and NOT `Cursor-Governance`.

- Verified `main` already contains the full package (`src/l9_graphite_memory/zep_transport.py`, `pyproject.toml`, `tests/`); `main` is the only branch.
- The WIP scratch copy at `igorbot/WIP-IGOR/.../L9-Graphite-Memory 4/` is **byte-identical to `main`** (git blob SHAs match for `zep_transport.py` = `bdbc8ad` and `pyproject.toml` = `85fd7cf`), so a rewrite developed here applies cleanly to the real repo. But that folder has no git remote (and is gitignored inside `igorbot`), so it cannot push.

Delivery workflow:
1. Clone `Quantum-L9/L9-Graphite-Memory` to a local working dir (outside `igorbot`).
2. Create a feature branch (e.g. `feat/zep-cloud-graph-transport`).
3. Apply the three file changes below in that clone.
4. Run mocked tests locally.
5. On explicit approval only, push branch and open a PR. No commit/push happens without your say-so.

The `igorbot/WIP-IGOR/` copy stays as local reference; it is not edited as the source of truth.

## Files changed

### 1. [zep_transport.py](/Users/macm2/igorbot-07-19-2026/igorbot/WIP-IGOR/Graphiti%20-%20Cirsor%20Governance%20copy/L9-Graphite-Memory%204/src/l9_graphite_memory/zep_transport.py) (full internal rewrite)

- Swap import to `from zep_cloud.client import Zep`; update the `ImportError` install hint to `pip install l9-graphite-memory[zep]` (extra now resolves to `zep-cloud`).
- Rewrite `__init__` to construct `Zep(api_key=...)`; drop the `base_url`/`ZEP_API_URL` param unless the installed client accepts it (Zep Cloud needs no base URL). Keep `CircuitBreaker` + `RateLimiter` wiring unchanged.
- Rewrite `health`, `search`, `write`, `_ensure_graph` (renamed from `_ensure_session`), and the four private tool handlers (`_tool_search_facts`, `_tool_search_nodes`, `_tool_add_episode`, `_tool_get_episodes`) to the mapping above.
- Keep the public MemoryTransport surface byte-identical in signature: `health()`, `search(query, group_id, limit)`, `write(body, group_id, kind, **kwargs)`, `call_tool(name, arguments)`, `list_tools()`. `call_tool`'s `tool_map` keys stay the same 4 names, so [graphiti_memory_client.py](/Users/macm2/igorbot-07-19-2026/igorbot/WIP-IGOR/Graphiti%20-%20Cirsor%20Governance%20copy/L9-Graphite-Memory%204/src/l9_graphite_memory/graphiti_memory_client.py) needs no change.
- Preserve `group_id` terminology in our signatures; only the internal Zep kwarg is `graph_id`.
- Update the module docstring's stale "session_id" mapping notes to the graph_id/graph.* reality.

### 2. [pyproject.toml](/Users/macm2/igorbot-07-19-2026/igorbot/WIP-IGOR/Graphiti%20-%20Cirsor%20Governance%20copy/L9-Graphite-Memory%204/pyproject.toml)

- In the `[zep]` optional-dependency extra, replace `zep-python>=2.0` with `zep-cloud>=2.0`.

### 3. [tests/test_transport.py](/Users/macm2/igorbot-07-19-2026/igorbot/WIP-IGOR/Graphiti%20-%20Cirsor%20Governance%20copy/L9-Graphite-Memory%204/tests/test_transport.py)

- Update the Zep-path mocks from `client.memory.*` to `client.graph.*` (`list_all`, `search`, `add`, `create`, `episode.get_by_graph_id`) and assert against `results.edges`/`results.nodes`/`.episodes` shapes.
- Add a test for the 10k-char write guard and the scalar/10-key metadata cap.
- Keep all mocking; no live Zep calls (matches the pack's existing test philosophy).

## Out of scope (deliberately not touched)

- Sacred files: `episode_contract.py`, `group_resolver.py`, `graphiti_gate_lib.py`, `circuit_breaker.py`, `rate_limiter.py`, hooks, rules.
- `secrets.py` / Infisical wiring (separate track; only supplies `ZEP_API_KEY` into `os.environ`).
- The still-open packaging bug (`group_registry.yaml` not shipped beside the module) — noted, tracked separately, not part of this transport rewrite.
- No live deploy; this is code-only and testable via `pytest` with mocks before credentials arrive.

## Verification (after edits, once you approve execution)

1. `python3 -m py_compile zep_transport.py` and import check.
2. `pytest tests/test_transport.py` (mocked) green.
3. Deferred live check (needs your `ZEP_API_KEY`): `l9-memory health` -> reachable; a real `write` then `search` round-trip against a throwaway `graph_id`.

## Residual risk

- `client.graph.create` exact kwargs (`graph_id`/`name`/`description`) could not be fetched (docs page timed out); it is a well-established method but I will confirm the signature against the installed `zep-cloud` package at implementation time and adjust if needed.
