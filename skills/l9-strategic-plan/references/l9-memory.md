# L9 Graphiti Memory: strategic-planning continuity

Memory is the cross-session retrieval and evidence substrate. The user's strategic Plan remains governed by its own Plan Keeper and versioned source artifacts. `Quantum-L9/Cursor-Governance` owns this **skill source**. `Quantum-L9/.github` owns **canonical global semantics**. The Memory service owns **memory admission**, not strategic admission.

## Read path

1. If a connected, authenticated Memory MCP tool is actually available to this host, use `memory.capabilities` to establish supported operations and namespace access. If absent, do not claim live access.
2. Resolve the exact current Plan revision from its authorized source or a verified supplied plan bundle, and identify the revision/source SHA against returned records. `memory.search` or `memory.get` may locate prior planning episodes, evidence, branch decisions and source locators; graph traversal (if available) can discover related nodes but must not determine strategic priority from centrality alone.
3. Do not treat an unversioned Memory fact, Graphiti edge, learned inference or a stale plan snapshot as admitted strategy. Preserve time, actor, evidence, authority class, confidence/unknown and source coordinates.
4. Scope searches to the authorized namespace; do not assume global access. Distinguish a missing result from evidence that something does not exist.

## Write and publication path

- Proposed strategic changes, reasoning and session continuity may be **memory candidates** only when separately authorized for that actual effect. Memory `memory.ingest` / `memory.write_governed` goes through the existing `MemoryService` permission, namespace policy and admission pipeline. Do not claim the caller has grants merely because an MCP connection works.
- `TopologyPublicationAdapter` already exists at `l9_graphite_memory/ingestion/topology_publication.py`, governed by ADR-078. It accepts the versioned, integrity-bound **topology publication plan** plus matching packet. Only eligible candidates go through `MemoryService.write`; held/rejected candidates do not. The adapter is **not** a generic uploader for arbitrary Strategic Plan ZIPs. Reuse it only when real producer artifacts satisfy its contract.
- Do not implement a second Graphiti writer, a direct PostgreSQL writer, another coordinator or a new publication interface. Graphiti/Zep graph projections are rebuildable, not Strategy authority. Plan admission, approved revision creation, actual Memory admission and graph projection success are four different events.
- On cross-node transport, honor the existing Gate and Memory integration where applicable; do not bypass transport authorization just because a local adapter supports preflight or apply.

## Minimal round-trip proof after integration

A: From a source-pinned Plan revision, retrieve one known branch and a related prior decision using actual authenticated Memory tools. Preserve exact record/source locators and receipt.
B: Produce one *candidate* strategic update without Plan promotion, and, only with authorization, send that candidate through the existing Memory admission entrypoint. Preserve returned admitted/quarantined/rejected/duplicate status.
C: In a genuinely separate session, retrieve the same candidate by identity, verify provenance against the authoritative Plan revision, and confirm it was **not** silently promoted to current strategy.

Do not report A/B/C as executed until the real tool responses and independent session receipts exist. No Supabase path or fallback.

References verified at `l9-graphiti-memory@d4775a9222871143782bb2a9ddc035ef96d832a3`:
- `docs/TOPOLOGY_PUBLICATION_ADMISSION.md` and `docs/adr/ADR-078-topology-publication-admission.md`
- `src/l9_graphite_memory/ingestion/topology_publication.py`
- `src/l9_graphite_memory/mcp_tools.py`
