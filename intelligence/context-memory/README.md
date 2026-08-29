<!-- --- L9_META ---
l9_schema: 1
artifact_type: documentation
component: context_memory_system
tags: [intelligence, context_memory]
retrieval: on_demand
status: retired
--- /L9_META --- -->

# Context memory — retired Suite-6 path

Resume SSOT is **Graphiti**. SessionStart emits `SessionHydrationPacket` via
`ops/graphiti/hydration/compile_session_packet.py`. Closed-chat words go to S3
through `ops/graphiti/hydration/archive_transcript.py` (all-words; do not
filter). Writes use `ops/graphiti/graphiti_memory_client.py`.

Do not run hourly sqlite extractors. Do not restore Suite-6 archive Python.
Activation is SessionStart only (`AGENTS.md` §2).

Local `sessions/*.json` files here are leftover cache, not resume authority.

CLI: `ops/graphiti/graphiti_memory_client.py` (`health`, `inject`, `write`).
Skill: `l9-graphiti-memory`.
