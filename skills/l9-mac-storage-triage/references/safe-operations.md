<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: domain_rules
tags: [macos, storage, apfs, sparse, cloud]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
/L9_META -->

# Safe Operations

## Read-only baseline

The baseline avoids recursive size enumeration. It captures filesystem accounting, APFS inventory, local snapshots, Spotlight state, tool availability, path presence, and bounded allowlisted cache/trash sizes.

## Folder-size reality

macOS does not maintain live aggregate sizes for ordinary directories. Accurate directory sizes require traversal. Prefer one saved `ncdu` scan over repeated `du`, `find`, or Spotlight-wide queries. Noise inventory uses `du -sk` on known cache paths only.

## Sparse-file reality

Virtual disks can report huge logical sizes while occupying far fewer allocated blocks. Use:

```bash
./bin/mac-storage-triage inspect-file "/absolute/path/to/file"
```

## Cloud offload reality

Moving data into `~/Library/CloudStorage` can temporarily retain both local representations. Direct `rclone copy` streams to the provider without creating another local destination tree.

## Deletion separation

Cloud upload and local deletion are separate plans. Cache/Docker/Trash purge never shares a plan with source deletion.
