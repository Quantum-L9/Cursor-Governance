# Lesson: an integrity tool that writes the worktree is a healer, not a checker

**Date:** 2026-08-28
**Donor:** `integrity/hash-verifier.py` (default auto-repair),
`integrity/system-check.sh` (`|| true` + frozen “Verify+Repair executed”),
empty `integrity/manifest-lock.json` that stored full-file base64
**Owners today:** git + `make pr`, PE `MANIFEST.yaml` / `MANIFEST.json`
(`sha256` + `self_excluded`, no file bodies), campaign
`source-integrity-receipt.v1` (digest + bytes), `sync_generated_artifacts.py`,
`check_governance_wiring.sh` (HEAD == origin/main).

## Rule

Integrity proves a digest. It does not restore bytes from a side store.
Expose verify. Never expose restore-from-blob. A snapshot that embeds file
bodies is a secret-plane leak waiting to happen.

## Why

The Suite-6 lock claimed six leftover roots (`.cursor`, `commands`,
`pipeline`, `security`, `ops`, `intelligence`) and skipped the live SSOT
(`rules/`, `skills/`, `kernels/`, `environment/`, root law). Default verify
rewrote drift from base64. `system-check.sh` swallowed errors and stamped
Active. TODO.md / CHANGELOG then said ACTIVE, keep because the files existed.

Existence is not authority. A second content store fights tip activation and
`COMMANDS_MANIFEST.yaml` regen.

## Wrong

- `python3 integrity/hash-verifier.py` with no flags (auto-repair)
- `bash integrity/system-check.sh` (heal + `|| true`)
- Embed `b64` / full file contents in a lock committed to git
- Infer “Integrity Agent — Active” from a log substring
- Recreate `integrity/` because an old TODO said keep

## Right

- Hash-only manifests (PE already: algorithm + `self_excluded`)
- Restore via git or `governance_activate_fresh.sh`
- Report-only checks may write gitignored logs; they must not overwrite
  tracked files
- `foundation/security/_archived/signatures/*.sig.json` are basename-keyed
  hash sidecars, not signatures. Do not revive
  `governance-integrity.py`. The corpus stays under TODO C2 (cold storage),
  not a live signer.
