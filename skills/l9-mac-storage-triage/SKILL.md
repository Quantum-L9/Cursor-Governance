---
name: l9-mac-storage-triage
description: "diagnose macos disk-storage pressure, then reclaim only stale caches and confirmed noise (old docker containers, package caches, trash). use when a mac is low on disk, finder or spotlight is unreliable, caches or containers are bloated, or the user asks to triage storage, free space, clean caches, or run mac-storage-triage. three modes — diagnose (read-only), repair (hitl after diagnosis), autonomy (diagnose then purge allowlisted noise without review)."
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, macos, storage, disk, caches, docker, diagnose-first]
  owner: igor_beylin
  status: active
  version: 1.1.0
  updated: 2026-08-13
---

# Mac Storage Triage

## Purpose

Diagnose macOS APFS disk pressure first, then reclaim **only** regenerating caches and confirmed noise. This skill treats "memory" as persistent disk storage. It does not tune RAM.

Default first run is **diagnose**. Repair waits for a human yes. Autonomy runs only when the user explicitly requests it after the allowlist is trusted.

## Modes

| Mode | Mutates? | Gate | What it does |
|------|----------|------|----------------|
| `diagnose` | no | none | Read-only baseline + noise inventory + summary. Stops. |
| `repair` | yes, after HITL | diagnosis receipt + plan + `APPLY_CONFIRMATION` | Plans allowlisted noise purge, **stops for human review**, applies only after yes. |
| `autonomy` | yes | diagnosis + `AUTONOMY_CONFIRMATION='I_AUTHORIZE_SAFE_NOISE_PURGE'` | Diagnose then purge the same allowlist with no extra review. |

Select mode from the user request. If unspecified, run `diagnose`. Never choose `autonomy` unless the user said autonomy / no-review / skip HITL.

Load [references/modes.md](references/modes.md) before executing.

## Core Contract

```
diagnose → inventory noise → summarize
        ↘ repair: plan allowlisted actions → HITL → apply → verify
        ↘ autonomy: plan allowlisted actions → apply → verify
```

Repair and autonomy may execute **only** `purge_stale_caches`, `docker_prune_unused`, and `empty_trash`. Mail wipe, rclone offload, verified-source delete, and Spotlight reindex stay operator-opt-in via `.env` and are **not** auto-selected. See [references/safe-noise-allowlist.md](references/safe-noise-allowlist.md).

## Authority Order

1. Current machine evidence in `reports/<id>/`
2. `handoffs/current/FINDINGS.txt` — what to show the human
3. `handoffs/current/findings.json` — what repair/autonomy consume
4. [references/diagnose-first.md](references/diagnose-first.md)
3. [references/safe-noise-allowlist.md](references/safe-noise-allowlist.md)
4. Validated `.env` + hashed plan
5. Mode confirmation values
6. `Unknown` — fail closed; do not invent paths or reclaimable sizes

## Compact Workflow

Pack root: `skills/l9-mac-storage-triage/` (this folder).

```bash
ROOT="$HOME/.cursor-governance/skills/l9-mac-storage-triage"
[ -d "$ROOT" ] || ROOT="$(pwd)/skills/l9-mac-storage-triage"
chmod +x "$ROOT/bin/mac-storage-triage" "$ROOT"/scripts/*.sh "$ROOT"/scripts/actions/*.sh "$ROOT"/scripts/lib/*.sh
"$ROOT/bin/mac-storage-triage" run diagnose
```

After diagnosis, open `handoffs/current/FINDINGS.txt` (human table). Repair reads `handoffs/current/findings.json` (machine mirror). Do not apply until the human says yes.

```bash
"$ROOT/bin/mac-storage-triage" run diagnose
open -e "$ROOT/handoffs/current/FINDINGS.txt"   # or just open the file in the editor
```

```bash
"$ROOT/bin/mac-storage-triage" run repair     # writes plan, does not apply
# HITL: show plan, wait for explicit yes
"$ROOT/bin/mac-storage-triage" apply          # only after yes + APPLY_CONFIRMATION
"$ROOT/bin/mac-storage-triage" verify
```

Autonomy (user must request it):

```bash
"$ROOT/bin/mac-storage-triage" run autonomy
```

Low-level commands remain: `diagnose`, `summarize`, `scan`, `init-env`, `validate`, `plan`, `apply`, `verify`, `status`.

## Behavior Rules

- Read-only diagnosis always precedes any write.
- Do not recurse CloudStorage / File Provider trees.
- Do not run `mdutil -E`. Do not `sudo`.
- Do not delete Documents, Downloads, project trees, Mail, Docker volumes, or `~/Library/Containers` (macOS app sandboxes).
- "Old containers" means **Docker** stopped/dangling artifacts, not macOS Library Containers.
- Sparse virtual disks: inspect allocated blocks before treating logical size as used.
- Unknown values stay `UNKNOWN`. Do not guess reclaimable GB.
- Report actual `df` numbers. Never fabricate sizes.

## Resource Map

- [references/modes.md](references/modes.md) — mode gates, confirmations, agent stop points
- [references/safe-noise-allowlist.md](references/safe-noise-allowlist.md) — what repair/autonomy may delete
- [references/diagnose-first.md](references/diagnose-first.md) — diagnose-before-write kernel
- [references/safe-operations.md](references/safe-operations.md) — APFS, sparse files, cloud offload
- [references/troubleshooting.md](references/troubleshooting.md) — scanner stalls, Spotlight, `.env`
- [references/playbook.md](references/playbook.md) — original typed playbook contract
- [references/remediation-ledger.md](references/remediation-ledger.md) — open causes, guarded folders, allowlisted next actions by host
- [references/deletion-log.md](references/deletion-log.md) — append-only record of what was actually deleted (and skipped) per host
- [handoffs/current/FINDINGS.txt](handoffs/current/FINDINGS.txt) — human table (open this)
- [handoffs/current/findings.json](handoffs/current/findings.json) — machine mirror for repair
- [handoffs/findings.schema.json](handoffs/findings.schema.json) — JSON contract
- `config/findings-catalog.json` — classification catalog (sizes filled from diagnosis)
- `bin/mac-storage-triage` — operator entrypoint
- `scripts/` — diagnose, inventory, focus layout, plan, apply, verify, actions
- `config/` — scan excludes, guarded paths, optional path lists
- `handoffs/` — report schemas

## Validation

```bash
"$ROOT/tests/run.sh"
"$ROOT/bin/mac-storage-triage" status
```

A run is complete only when:

- diagnose: `handoffs/current/FINDINGS.txt` and `findings.json` exist; no writes occurred
- repair: plan exists, HITL yes recorded, receipts exist for each applied action, verify ran
- autonomy: same receipts as repair, plus `AUTONOMY_CONFIRMATION` in `.env`

## Failure Handling

| Symptom | Action |
|---------|--------|
| Not Darwin | Stop. This skill is macOS-only. |
| Diagnosis receipt missing | Run `run diagnose`. Do not plan or apply. |
| `.env` UNKNOWN on a selected action | Drop that action; do not infer. |
| Plan/env digest mismatch | Regenerate plan. Do not apply. |
| CloudStorage / FDA permission errors | Skip that path; record Unknown. |
| Docker/conda/ncdu missing | Skip optional inventory; continue. |
| Repair without explicit yes | Stop after plan. Do not apply. |
| Autonomy without explicit user request | Run diagnose instead. |

When blocked: state the exact gap, label `Unknown`, give the smallest next command.
