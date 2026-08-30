# Deprecated Claude Environment corpus

These files are superseded by `../PLAN_DOCUMENT.claude-env-pending-fixes.v1.json`
and the Cursor Build plan projected from it.

Do not execute, admit, or `make campaign` from this archive.
Kept as provenance for the remaining-work consolidation of 2026-08-29.

## What was archived and why

| Path | Why archived |
|---|---|
| `environment_experience_improvement_pack_p307/` | Predecessor pack bound to `30c6ecd4`. Counts disagreed across stores (CI-035 shape). Superseded by the r2 pack, then by the remaining-work JSON. |
| `environment_experience_improvement_pack_p307_revised/` | r2 assessment at `59f03a5d` plus wave-1 notes for PR#360. Useful provenance; not the live queue. Several residuals have since landed or been rescoped (receipt revision-expiry, broker retirement, deps `toolchain_proven`). |
| `URGENT-environment-experience-progress.md` | 2026-08-27 overlay. Named next slice (ownership-aware writes) was invalidated by r2. |
| `8-17-25-Claude/claude-code-env-contract/` | Campaign plan for the original env-contract landing. Broker and PE-register legs are retired or parked. |
| `claude code environment/` | Duplicate setup-script snapshots. Not an execution SSOT. |
| `claude-code-mobile-environment/` | Superseded planning snapshots. Plan of record is `docs/plans/claude-code/`. The v3.1 remediation contract is provenance, not the live remaining-work queue. |

## Re-verified closures (do not re-open from archive text)

- **CI-004 revision-expiry** — `claude_bootstrap_receipt.py` treats `governance_revision` mismatch as expiry, distinct from TTL.
- **CI-009/028 applied-state** — `session_deps_cloud.sh` stamps only after `toolchain_proven`. Residual is import-smoke + non-empty stamp evidence.
- **CI-010 / OD-003 / OD-004** — capability broker retired 2026-08-29. Do not diagnose `broker.quantumaipartners.com` or provision `CLAUDE_SESSION_JWT` from this plan.
- **CI-003 / CI-036 in-repo legs** — delivered on PR#360; remaining legs are harness-owned.
- **CI-014 / CI-018 / CI-025 / CI-027 / CI-030 / CI-033 / CI-037** — closed.
- **CI-002 `is_tracked()` on four writers** — invalidated as written; those writers already compose additively.
- **CI-001 / CI-011 / CI-020 / CI-024 / CI-026 / CI-029 / CI-031 / CI-100 / CI-101 / CI-017 / CI-032** — external, needs-attachment, or other-repo. Not this checkout.

## Live remaining-work SSOT

`WIP/8-26-26-Claude Environment/PLAN_DOCUMENT.claude-env-pending-fixes.v1.json`
