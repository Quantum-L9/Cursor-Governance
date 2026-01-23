Version: 1.0.0
Canonical-Source: 10X Governance Suite
Generated: 2025-10-06T17:22:56Z

# Integrity Audit — Governance Manifest & Self-Heal Layer

## Objective
Protect the 10X Governance Suite from drift, corruption, or unauthorized edits by maintaining a canonical, hash-locked manifest and an autonomous self-repair routine.

## Scope
Monitors and protects these roots (recursive):
- `/.cursor/`
- `/commands/`
- `/pipeline/`
- `/security/`
- `/ops/`
- `/intelligence/`
(Excludes `/integrity/` itself to avoid circular hashing.)

## Behavior (Option C, No Pause)
- **Snapshot Mode**: Create/refresh a full manifest with SHA-256 + Base64 content for every governed file.
- **Verify Mode**: Compare current files to the manifest and log discrepancies.
- **Repair Mode**: Autonomously restore missing/modified files from the manifest snapshot.
- **Meta-Audit**: Append an “Integrity Reflection” entry to `/intelligence/meta-audit.md`.

## Files
- `manifest-lock.json` – canonical store of file hashes and Base64 content for restoration.
- `hash-verifier.py` – builds/verifies/repairs against `manifest-lock.json`.
- `system-check.sh` – silent runner that executes verify+repair on demand or schedule.

## Logs
- `/ops/logs/integrity_report.json` – latest verification summary (timestamped).
- `/ops/logs/integrity_activity.log` – chronological activity trail.

## Usage
**Initial Snapshot (first run):**
```bash
bash integrity/system-check.sh --snapshot
```
**Verify + Repair (normal run):**
```bash
bash integrity/system-check.sh
```
