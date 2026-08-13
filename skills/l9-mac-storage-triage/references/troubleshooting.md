<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: troubleshooting
tags: [macos, storage, spotlight, cloudstorage, env]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-08-13
/L9_META -->

# Troubleshooting

## `ncdu` stalls in Google Drive `.tmp`

Stop the scan and ensure `config/scan-excludes.txt` excludes `Library/CloudStorage`. Run a home-directory scan instead of a full Data-volume scan.

## `Operation not permitted` under CloudStorage

Grant the terminal Full Disk Access when appropriate, but do not assume that File Provider roots allow hidden files. Skip those paths.

## Spotlight state is Unknown

Do not delete `.Spotlight-V100` and do not run `mdutil -E`. Free working space, keep cloud roots excluded, use the privacy-toggle reindex procedure only as a planned extra action.

## Logical file size exceeds volume capacity

Inspect allocated blocks with `inspect-file`. Sparse disk images and VM disks can present maximum capacity rather than physical consumption.

## `.env` validation fails

Correct only the reported values. Action-specific `UNKNOWN` values must be replaced by facts confirmed during diagnosis.

## Plan digest mismatch

Regenerate the plan. This indicates the plan file or action-driving configuration changed after approval.

## Docker daemon not running

Inventory records Docker as unavailable. Omit `docker_prune_unused` from `APPROVED_ACTIONS`.
