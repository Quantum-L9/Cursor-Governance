<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: remediation_ledger
tags: [macos, storage, causes, ledger, mac-mini]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-13
/L9_META -->

# Remediation ledger

Durable tracker of disks, folders, and causes. Reports under `reports/` are gitignored; this file is the skill-local pattern log.

Update a row when a diagnosis repeats. Do not delete history; add a `Last seen` date and status change.

## Host: mac-mini (2026-08-13)

Operator evidence: Data `402–404 GiB` used / `12–14 GiB` free (`97–98%`). Home `297G`. APFS VM `23 GiB` (swap/sleep — secondary to a full Data volume).

| ID | Volume | Path | Class | GiB | Guard | Status | Cause pattern | Next step |
|---|---|---|---|---:|---|---|---|---|
| C1 | Data | `~/.local/share/tenx/logs/chat_exports` | transcript_mirror | 0 | no | closed | hourly sqlite + rolling jsonl mirror deleted 2026-08-13 after S3 archive | do not recreate hourly dumps |
| C2 | Data | `~/.npm` | disposable_cache | 0 | no | closed | npm package cache purged 2026-08-13 (incl. leftover `_npx`) | regenerates on npm install |
| C3 | Data | `~/miniconda3/pkgs` | disposable_cache | 1.11 | no | kept | `conda clean --all` dry-run: nothing unused; pkgs are live base-env packages | do not `rm -rf` pkgs |
| C4 | Data | `~/Library/Caches/pip` | disposable_cache | 0 | no | closed | pip cache purged 2026-08-13 | regenerates on pip install |
| C5 | Data | Homebrew cache | disposable_cache | 0 | no | closed | `rm` of `brew --cache` only 2026-08-13; skipped `brew cleanup` (would delete `/opt/homebrew` portable-ruby) | regenerates on brew fetch |
| C6 | Data | `~/.cache/uv` | disposable_cache | 0 | no | closed | uv cache clean --force 2026-08-13 (3.2 GiB) | regenerates on uv sync |
| C7 | Data | `~/.cache/pre-commit` | disposable_cache | 0.96 | no | candidate | pre-commit environments cache | extra HITL |
| C8 | Data | `~/.cache/puppeteer` | disposable_cache | 0.53 | no | candidate | browser download cache | extra HITL |
| C9 | Data | `~/Library/Caches/Google` | disposable_cache | 0 | no | closed | Chrome disk cache purged 2026-08-13; Application Support kept | regenerates while Chrome runs |
| C10 | Data | `~/Library/Caches/com.spotify.client` | disposable_cache | 2.65 | extra HITL | open | Spotify cache | extra HITL |
| C11 | Data | `~/Library/Application Support/Claude` | app_data | 12.57 | **YES** | guarded | live app support | never auto-delete |
| C12 | Data | `~/Library/Application Support` (rest) | app_data | ~19 | **YES** | guarded | Cursor/Google/Comet/Spotify/Slack/Dropbox/Adobe | never auto-delete |
| C13 | Data | `/Applications` | live_software | 31.33 | **YES** | guarded | installed apps | never auto-delete |
| C14 | Data | `~/Downloads` | user_data | 13.37 | **YES** | guarded | user files | review later, no auto-delete |
| C15 | Data | `~/Library/Caches` total | mixed | 9.78 | mixed | open | includes C4/C5/C9/C10 plus others | only named package caches |
| C16 | Data | `/Library` | system | 8.01 | **YES** | guarded | macOS/system | never |
| C17 | Data | `/private/var` | system | 6.52 | **YES** | guarded | system logs/vm | never without extra HITL |
| C18 | Data | `~/Library/Containers` | macos_sandbox | 3.60 | **YES** | guarded | not Docker | never |
| C19 | Data | `~/Library/ScreenRecordings` | user_media | 2.78 | **YES** | guarded | user recordings | review later |
| C20 | Data | `/opt/homebrew` | live_software | 2.55 | **YES** | guarded | Cellar; only brew *cache* is disposable | never brew uninstall via this skill |
| C21 | Data | `~/dev`, `~/odoo`, `~/n8n-mcp` | projects | 4.7 | **YES** | guarded | source trees | never |
| C22 | Data | `~/miniconda3/envs` | live_software | 0.00 | **YES** | guarded | no envs present | keep |
| C23 | Data | Docker volumes | docker_volume | 0.32 | **YES** | guarded | unused volumes | not allowlisted |
| C24 | Data | Docker containers | live_runtime | 1.18 | **YES** | guarded | 4 running; 0 stopped | no prune |
| C25 | VM | `/System/Volumes/VM` | apfs_swap | 23 | **YES** | guarded | swap/sleepimage grows when Data is full | free Data, then reboot; do not delete VM files |
| C26 | Data | `~/Documents`, `~/Desktop`, Mail, Messages | user_data | Unknown | **YES** | guarded | du denied/timeout (FDA / size) | never auto-delete |
| C27 | Data | `~/Library/CloudStorage` | cloud | skipped | **YES** | guarded | File Provider | never scan/delete |
| C28 | Data | Trash | trash | Unknown | FDA | unknown | Full Disk Access denied | skip empty_trash |
| C29 | Data | `~/Miniconda3-latest-MacOSX-x86_64.sh` | stale_installer | 0 | extra HITL | closed | leftover installer deleted 2026-08-13 | miniconda3 remains |

## Cause patterns (for later matching)

| Pattern | How it showed up | Recurrence signal |
|---------|------------------|-------------------|
| `unbounded_hourly_snapshot_exports` | tenx `chat_exports` hourly since 2026-03-26, no retention | dir count keeps rising; newest folder is today's hour |
| `package_manager_caches` | npm, pip, conda pkgs, brew, uv | sizes return after builds |
| `app_media_caches` | Google, Spotify under `Library/Caches` | regenerates while apps run |
| `full_data_inflates_vm` | Data 97%+ and VM 23 GiB | free Data first; VM is not the primary reclaim target |
| `home_is_not_the_whole_disk` | home 297G vs Data 402G | `/Applications` + `/Library` + `/private/var` explain most of the remainder |

## Status vocabulary

- `allowlisted` — repair/autonomy may delete after the mode's confirmation
- `candidate` — disposable, not yet in `purge_stale_caches`
- `extra HITL` — disposable-looking but not in the automatic allowlist
- `guarded` — never auto-delete
- `open` — diagnosed, no action taken yet
