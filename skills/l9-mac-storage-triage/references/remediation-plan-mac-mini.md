<!-- L9_META
l9_schema: 1
parent: l9-mac-storage-triage
layer: reference
role: current_remediation_plan
tags: [macos, storage, mac-mini, hitl]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-08-13
/L9_META -->

# Remediation plan — mac-mini — 2026-08-13

Diagnosis report: `reports/20260813T122129-mac-mini/` (gitignored). Ledger: [remediation-ledger.md](remediation-ledger.md). Guard file: `config/guarded-paths.txt`.

**Mode: applied 2026-08-13.** Original plan below is historical. What actually ran (and what was skipped) is in [deletion-log.md](deletion-log.md).

## Constraint

APFS Data is **98% full** (~12 GiB free of 460). Home is 297G of that. `/System/Volumes/VM` at 23 GiB is swap/sleepimage — a **memory** symptom of a full Data volume, not a safe delete target.

## Guard (never auto-delete)

Everything not listed in Phase A/B:

- `~/Documents`, `~/Desktop`, `~/Downloads`, `~/Library/ScreenRecordings`
- `~/Library/Application Support/**` (Claude 12.6G, Cursor, Google, Slack, Dropbox, Adobe, …)
- `~/Library/Containers`, `~/Library/Group Containers`, Mail, Messages, CloudStorage
- `/Applications`, `/Library`, `/private/var`, `/opt/homebrew` Cellar
- `~/dev`, `~/odoo`, `~/n8n-mcp`, `~/.cursor`, `~/.ssh`
- `~/miniconda3/envs` and conda **environments**
- Docker **volumes** and **running** containers
- `/System/Volumes/VM`
- tenx **scripts** and the **newest** chat_export folders (live launchd pipeline)

## Phase A — allowlisted this cycle (repair HITL)

Expected reclaim **~12.3 GiB**. Actions: `purge_stale_caches` only.

| Path | GiB | Command (via skill) |
|------|----:|---------------------|
| `~/.npm` | 3.96 | `npm cache clean --force` |
| `~/.cache/uv` | 3.36 | `uv cache clean` |
| `~/Library/Caches/Google` | 3.24 | leaf delete of Chrome disk cache only |
| `~/miniconda3/pkgs` | 1.11 | `conda clean --all --yes` (envs kept) |
| pip cache | 0.51 | `pip3 cache purge` |
| Homebrew cache | 0.20 | `rm` of `$(brew --cache)` only — **not** `brew cleanup` |

Skip: `docker_prune_unused` (0 stopped / 0 dangling), `empty_trash` (FDA Unknown).

Say **repair** to generate the hashed plan, then an explicit **yes** to apply.

## Phase B — disposable caches, extra HITL (not in current script)

Expected reclaim **~4.1 GiB** if all approved.

| Path | GiB | Guard note |
|------|----:|------------|
| `~/Library/Caches/com.spotify.client` | 2.65 | app cache only |
| `~/.cache/pre-commit` | 0.96 | regenerating |
| `~/.cache/puppeteer` | 0.53 | regenerating |

Do **not** `rm -rf ~/Library/Caches`.

## Phase C — the actual disk saver (HITL, retention — not a blind delete)

`~/.local/share/tenx/logs/chat_exports` = **109.2 GiB**, ~2804 hourly snapshot dirs from 2026-03-26 through today. Launchd is still writing a new folder every hour (`chat_export_launchd.out` touched during this diagnosis).

Proposed policy (not executed):

1. Keep the last **7 days** of `YYYY-MM-DD_HH-MM-SS` folders.
2. Delete older snapshot dirs only.
3. Leave `scripts/`, current `*.log`, and the live launchd job intact.
4. Add retention to `export_chats.sh` so this does not recur.

Expected reclaim on the order of **~100 GiB** if 7-day keep is accepted. **Requires a separate explicit yes.** This is residue of a live pipeline, not a user document tree, but it is still guarded until that yes.

## Phase D — later / pattern watch

- `~/Downloads` 13.4 GiB — human review, no auto-delete
- Screen recordings 2.8 GiB — human review
- Leftover `Miniconda3-latest-MacOSX-x86_64.sh` 0.11 GiB
- After Phase C frees Data, reboot to let VM/swap shrink (do not delete VM files)
- Grant Full Disk Access to measure Trash / Documents if those buckets matter

## Stop conditions

- No `rm` of any guarded path
- No Docker volume prune
- No Mail / CloudStorage / Application Support wipes
- No `mdutil -E`, no sudo
