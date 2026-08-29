<!-- --- L9_META ---
l9_schema: 1
artifact_type: documentation
component: context_memory_installation_guide
tags: [intelligence, context_memory]
retrieval: on_demand
status: retired
--- /L9_META --- -->

# Context-memory installation — retired

Do not install a LaunchAgent or hourly processor. SessionStart
(`ops/hooks/session_start_bootstrap.sh`) hydrates Graphiti. SessionEnd archives
the closed-chat document via `ops/graphiti/hydration/archive_transcript.py`.

```bash
"$HOME/.cursor-governance/.venv/bin/python" \
  "$HOME/.cursor-governance/ops/graphiti/graphiti_memory_client.py" health
```

If a leftover `com.cursor.context.processor` job is loaded, unload it — do not
re-point it at archive Python.
