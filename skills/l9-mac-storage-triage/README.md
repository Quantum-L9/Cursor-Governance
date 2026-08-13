# l9-mac-storage-triage

Diagnose-first macOS disk triage. Control plane: [SKILL.md](SKILL.md).

After diagnose, open the human table:

[handoffs/current/FINDINGS.txt](handoffs/current/FINDINGS.txt)

Repair uses the JSON twin:

[handoffs/current/findings.json](handoffs/current/findings.json)

```bash
./bin/mac-storage-triage run diagnose    # read-only; refreshes both files
./bin/mac-storage-triage run repair      # plan allowlisted noise; HITL before apply
./bin/mac-storage-triage run autonomy    # diagnose then purge allowlisted noise
```

Repair and autonomy delete only stale package caches, unused Docker artifacts, and Trash.

What was actually deleted on a host: [references/deletion-log.md](references/deletion-log.md).

Tests: `./tests/run.sh`
