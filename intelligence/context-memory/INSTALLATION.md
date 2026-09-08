<!-- --- L9_META ---
l9_schema: 1
artifact_type: documentation
component: context_memory_installation_guide
tags: [intelligence, context_memory]
retrieval: on_demand
status: retired
--- /L9_META --- -->

# Context-memory installation — retired

> **Retired 2026-09-06 (memory realignment C11, ADR-0030).** This document describes the direct Graphiti provider path that Cursor-Governance no longer has. Memory is the canonical `l9-graphite-memory` control plane (`ops/memory`, `python -m ops.memory.cli`); see `ops/memory/README.md` and `docs/MEMORY_PIPELINE_MAP.md`. Kept as an operator record of the projection deployment only.

Do not install a LaunchAgent or hourly processor. SessionStart
(`ops/hooks/session_start_bootstrap.sh`) hydrates Graphiti. SessionEnd archives
the closed-chat document via `ops/graphiti/hydration/archive_transcript.py`.

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  "$HOME/.cursor-governance/ops/graphiti/graphiti_memory_client.py" health
```

If a leftover `com.cursor.context.processor` job is loaded, unload it — do not
re-point it at archive Python.
