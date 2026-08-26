# 🔴 URGENT — Environment Experience Improvement Pack: progress + next slice

**Assessed:** 2026-08-26, against `main` after PR #307 merged.
**Artifact (expanded, no zip):** [`environment_experience_improvement_pack_p307/`](./environment_experience_improvement_pack_p307/)
— [`PROGRESS.md`](./environment_experience_improvement_pack_p307/PROGRESS.md) is the human view,
[`progress.yaml`](./environment_experience_improvement_pack_p307/progress.yaml) the machine view,
per-record progress under each entry's `progress:` key in `improvements.yaml`.

## Status: 2 done · 9 partial · 25 not started (of 36)

### Merged
- **PR #304 + #305** — operational-parity convergence; closed **CI-007** (scoped/expiring merge
  receipts, no standing env boolean).
- **PR #306** — readiness merge-authority probe fix (in-process `merge_gate.evaluate()`).
- **PR #307** — the P0 execution slice:
  - **CI-008** — governance Makefile + pre-commit config are the environment publish authority
    regardless of the repo worked in (`l9 pr` / `make -C $GOV pr WS=$PWD`); consumer needs no `pr`
    target, no raw-push fallback. Old "ship a `pr` target into each consumer" option rejected.
  - **CI-009** — readiness proves importability before READY (`interpreter_importable_status`).
    3b/3c were already satisfied in-repo (not fabricated).
  - **CI-002** — `is_tracked()` ownership guard: bootstrap projection refuses to replace a
    git-tracked `.claude/rules` tree.

## ⏭️ NEXT SLICE (recommended, urgent) — "Ownership-aware writes"

Reuses the `is_tracked()` helper just merged; fully validatable in-repo; closes the biggest open
**P0** residual and folds in a **P1** with the same root cause.

- **CI-002 residual (P0)** — apply `is_tracked()` before the remaining projection writes
  (`claude_projection.py:422` `.mcp.json`, `reconcile_claude_l9_skills.py`,
  `reconcile_claude_commands.py`, `reconcile_claude_settings.py`) + Phase 2b (project to a
  non-owned sibling when the target is tracked). Verify the 8-fixture `git status` clean.
- **CI-003 (P1)** — Stop hook ownership-aware: stop demanding pushes of repository-owned or
  generated/untracked bootstrap artifacts (`.claude/**`, `.mcp.json`, `.l9/**`).
- **CI-031 (P3, opportunistic)** — keep tracked-path/gitignore hygiene in sync.

**Excluded from this slice:** CI-002 Phase 2c (`L9_AUTONOMY_STATE_DIR` relocation touches
`l4_local.py` + gate + `make pr` — its own change).
**Alternative slice:** toolchain — CI-009 residual (session-deps import smoke) + CI-023 + CI-018.

## Still-open P0 / high-priority (see `progress.yaml`)
- **CI-004** (P0, partial) — regenerate bootstrap receipts on lifecycle/revision changes.
- **CI-006** (P0, partial) — authority-sensitive env drift at source (flag retired; general mechanism open).
- **CI-010** (P0, partial) — broker auth/reachability diagnosability.
