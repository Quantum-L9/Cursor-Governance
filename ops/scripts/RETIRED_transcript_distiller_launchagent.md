# Retired: `com.l9.transcript-distiller` LaunchAgent

**Status:** retired 2026-08-12  
**Replacement:** SessionEnd → S3 redacted job enqueue → GitHub Actions `memory-distill.yml` → Graphiti

## Why

The 5am Mac LaunchAgent pointed at Dropbox paths, expected flat `*.txt` transcripts
(Cursor writes nested `.jsonl`), and targeted the deprecated C1 `save_memory` sink.
It was unloaded on this machine and never produced reliable Graphiti ingest.

## One-time unload (operator)

```bash
launchctl bootout "gui/$(id -u)/com.l9.transcript-distiller" 2>/dev/null || true
rm -f ~/Library/LaunchAgents/com.l9.transcript-distiller.plist
```

## Local operator CLI (same worker as GHA)

```bash
export MEMORY_DISTILL_S3_BUCKET=<bucket>
export GRAPHITI_MCP_URL=https://memory.quantumaipartners.com/graphiti/mcp
export GRAPHITI_MCP_TOKEN=<token>
# OPENAI_API_KEY or AWS creds for SM l9/OPENAI_API_KEY
python3 -m ops.graphiti.distill_queue.worker --max-jobs 20
# or:
bash ops/scripts/run_distiller.sh
```

Do **not** reintroduce Dropbox SSOT or a C1 MCP primary sink.
