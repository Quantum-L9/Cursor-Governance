# Repository-Root Append-Only Protection — Validation Report

Branch: `claude/cursor-governance-2y066a`
Base: `main` @ `eec93fe` (clean tree — #56/#57/#59/#60 merged, #58 closed)
Status: **local only — not merged.** This is a governance change; it requires
human CODEOWNERS approval by the repository's own `ORG_INVARIANTS.yaml`.

## Mandate

Protect every repository-root file so incoming PRs can add content but cannot
delete or overwrite existing content without a highlighted delta, a proof-carrying
justification, and owner approval — with full traceability and easy rollback.

## Design

Two enforcement layers:

1. **Mechanical (new):** `.github/workflows/root-file-protection.yml` runs
   `ops/scripts/validate_root_file_protection.py` on every PR. For each protected
   root file it diffs base→head; a removal or in-place overwrite of existing content
   **fails the gate** unless a commit message carries
   `ALLOW-ROOT-DELETION: <path> — <reason>`. Purely additive changes and new files
   pass. `regenerable` artifacts (`uv.lock`, `governance-health-report.json`,
   `.harvest_executor_state.json`) are exempt (rewritten wholesale by tooling).
2. **Human review (existing + extended):** CODEOWNERS already routes every root
   file to `@cryptoxdog` via `*`; explicit canonical-file entries were appended so
   the requirement survives a future multi-owner split. The gate mechanism itself is
   registered in `ORG_INVARIANTS.yaml` `protected_paths` so it cannot be silently
   removed.

Tier model (three tiers, documented in the config): **additive_only** (19 —
governance, legal, dependency, gate/security, environment-modifying installers);
**managed** (16 — living/operational/community docs and low-risk config; edited
freely with owner review, no marker); **regenerable** (3 — machine artifacts,
exempt). Every tier is CODEOWNERS-reviewed; the tier only decides whether the
additive gate also fires.

## Files

New: `ops/config/root-file-protection.json`,
`ops/scripts/validate_root_file_protection.py`,
`ops/scripts/test_root_file_protection.py`,
`.github/workflows/root-file-protection.yml`, this report.
Appended (additive only): `ORG_INVARIANTS.yaml` (both `protected_paths` lists),
`CODEOWNERS`, `AGENTS.md`.

## Evidence

| Command | Result |
|---|---|
| `ruff check` / `ruff format --check` (new scripts) | PASS |
| `python ops/scripts/test_root_file_protection.py` | Ran 12 tests, OK |
| Gate self-check on this PR (`validate_root_file_protection.py --base origin/main`) | PASS — all protected-file edits are additive (`-0`); recorded below |

The 12 fixture tests cover: pure addition passes; managed-tier overwrite/deletion
is exempt (no marker needed); overwrite without justification
fails; deletion without justification fails; overwrite/deletion **with** a valid
marker passes; `regenerable` wholesale rewrite is exempt; a marker for the wrong
path does not excuse; a marker without a reason is rejected; unchanged files are
not reported; an unregistered new root file **fails** the gate while a registered
one passes; and `main()` returns 0/1 correctly.

## Self-consistency

This PR only **adds** files and **appends** to `AGENTS.md`, `ORG_INVARIANTS.yaml`,
and `CODEOWNERS` (zero deleted lines on protected files), so it satisfies its own
append-only rule — the gate passes on its own diff.

## Halt

Local commits + green gates only. No merge — awaiting owner CODEOWNERS approval,
consistent with the protection this PR establishes.
