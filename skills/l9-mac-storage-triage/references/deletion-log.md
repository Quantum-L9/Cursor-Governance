<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: deletion_record
tags: [macos, storage, deletion-log, mac-mini]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-13
/L9_META -->

# Deletion log

Append-only record of what this skill actually deleted (or refused to delete) after a dry-run. `reports/` is gitignored; this file travels with the skill to the next host.

**How to use on the next machine:** run `diagnose` first. Do not replay these paths blindly — they are host-specific. Copy the dry-run rules and the skip list.

## Rules learned 2026-08-13 (carry forward)

1. Dry-run every destructive command. Execute only after the dry-run output matches the marked folder.
2. Do **not** run `brew cleanup -s --prune=all`. It also removes `/opt/homebrew/Library/Homebrew/vendor/portable-ruby/*` (guarded Cellar/prefix). Delete only `$(brew --cache)` when that path is `$HOME/Library/Caches/Homebrew`.
3. Do **not** `rm -rf ~/miniconda3/pkgs`. `conda clean --all --dry-run` can report nothing unused — those packages belong to the live base env.
4. `npm cache clean --force` does not remove `~/.npm/_npx`. If `~/.npm` is the marked folder, delete the leftover `_npx` after a second dry-run of that leaf.
5. Never `rm -rf ~/Library/Caches`. Leaf paths only (`Google`, `pip`, `Homebrew`).
6. Never touch `~/Library/Application Support`, Downloads, ScreenRecordings, Docker volumes, or `/opt/homebrew` programs.

## Host: mac-mini — 2026-08-13

Operator: `macm2`. Skill mode: diagnose, then repair HITL, then apply. Data volume `/System/Volumes/Data`.

| When (local) | What | Path | Approx size | Command | Outcome |
|---|---|---|---:|---|---|
| morning | Leftover conda installer | `~/Miniconda3-latest-MacOSX-x86_64.sh` | 0.11 GiB | `rm` of that file only | Deleted. `~/miniconda3` kept. |
| ~15:00 | Hourly SQLite “chat_exports” stamps | `~/.local/share/tenx/logs/chat_exports/YYYY-MM-DD_*` | ~109 GiB | delete dated stamp dirs only | Deleted. Not chats — Cursor `state.vscdb` copies. Live `~/.cursor/projects/*/agent-transcripts` kept. |
| 15:35 | Duplicate jsonl mirror | `~/.local/share/tenx/logs/chat_exports` (incl. `current/`) | 19 MB | `rm -rf` that folder | Deleted after 181 jsonl were in S3 `l9-chat-transcripts-020125249784`. |
| 15:35 | Legacy sqlite/History dump | `~/Library/Application Support/Cursor/GlobalCommands/ops/logs/chat_exports` | 741 MB | `rm -rf` that folder | Deleted. 0 jsonl. Cursor Application Support otherwise kept. |
| 15:38 | npm package cache | `~/.npm` | 4.09 → 2.9 GiB then 946 MB leftover | `npm cache clean --force` then `rm -rf ~/.npm` (`_npx`) | Gone. |
| 15:38 | uv package cache | `~/.cache/uv` | 3.43 GiB | `uv cache clean --force` | Gone (3.2 GiB reported by uv). |
| 15:38 | Chrome disk cache | `~/Library/Caches/Google` | 3.27 GiB | `rm -rf` that leaf | Gone. `~/Library/Application Support/Google/Chrome` kept (~4.4 GiB). |
| 15:38 | pip package cache | `~/Library/Caches/pip` | 0.51 GiB | `pip3 cache purge` | Purged 546.3 MB / 1922 files. ~196K selfcheck residue. |
| 15:38 | Homebrew download cache | `~/Library/Caches/Homebrew` | 0.20 GiB | `rm -rf "$(brew --cache)"` after path check | Gone. `brew cleanup` **not** run. |
| 15:38 | conda pkgs (attempt) | `~/miniconda3/pkgs` | 1.11 GiB | `conda clean --all --yes` after `--dry-run` | **Kept.** Dry-run: nothing unused. Base env would break if the folder were removed. |

### Dry-run skips (not deleted)

| Path | Why |
|---|---|
| `/opt/homebrew/Library/Homebrew/vendor/portable-ruby/{3.4.8,4.0.1,4.0.5_1}` | `brew cleanup -s --prune=all -n` listed these (~104 MB). Guarded prefix. |
| `~/Library/Logs/Homebrew` | Same brew dry-run; not a marked folder. |
| `~/miniconda3/pkgs` | Live base-env packages. |
| `~/Library/Caches/com.spotify.client` | Phase B — ask first. |
| `~/.cache/pre-commit` | Phase B — ask first. |
| `~/.cache/puppeteer` | Phase B — ask first. |
| `~/Downloads` | Protected 2026-08-13. |
| `~/Library/ScreenRecordings` | Protected 2026-08-13. |
| `~/.cursor/projects/*/agent-transcripts` | Live Cursor chats. Archived to S3; still required by the UI. |
| Docker volumes / running containers | Guarded. |
| Trash | Full Disk Access unknown; `empty_trash` not selected. |

### Disk

| | Used | Free | Full |
|---|---:|---:|---:|
| Diagnose morning | ~404 GiB | ~12 GiB | 97% |
| After sqlite stamp delete | ~297 GiB | ~116 GiB | 72% |
| After Phase A caches (15:38 apply) | ~290 GiB | ~124 GiB | 71% |

Apply receipt: `purge_stale_caches` success, 2026-08-13T15:38:16–15:38:52-0400. Plan SHA `7e5dce6a129eb3b4ef78f4bac981509b9afdb68aca516c2b9501ff91e0097ef1`. Action-log free KiB 122875316 → 128888504 (~5.7 GiB in that apply; leftover `~/.npm/_npx` removed immediately after).

Chat words also copied to `s3://l9-chat-transcripts-020125249784` (`raw/` jsonl + `v1/` cleaned JSON, 181 files). That is archive, not a local delete of live transcripts.
