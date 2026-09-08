# RETIRED — do not scaffold

> **Retired 2026-09-06 (memory realignment C11, ADR-0030).** This document describes the direct Graphiti provider path that Cursor-Governance no longer has. Memory is the canonical `l9-graphite-memory` control plane (`ops/memory`, `python -m ops.memory.cli`); see `ops/memory/README.md` and `docs/MEMORY_PIPELINE_MAP.md`. Kept as an operator record of the projection deployment only.

`memory-bank/` local T0 resume storage was retired 2026-08-11.

- Resume SSOT: Graphiti (`ops/graphiti/graphiti_memory_client.py` inject / PICKUP)
- PR remediation handoffs: `.l9/pr/pr-remediation-handoff.json`
- `setup_workspace_symlinks.sh` must not copy these templates into workspaces

The stub files in this directory are retained only as historical reference and
must not be reactivated as a write target.
