# 🔴 URGENT — Environment Experience Improvement Pack: progress + next slice

**Assessed:** 2026-08-27, against `main@498dcaa` (post-#307-merge + 47 commits). PR #320 has since
merged as `c3ddeea` — a second live instance of CI-034 inside one hour.
**Supersedes:** the 2026-08-26 assessment, which was stamped `main@post-#307-merge` — a prose label,
not a SHA. `main` moved 47 commits underneath it and nothing marked it stale.
**Artifact (expanded, no zip):** [`environment_experience_improvement_pack_p307/`](./environment_experience_improvement_pack_p307/)
— [`PROGRESS.md`](./environment_experience_improvement_pack_p307/PROGRESS.md) is the human view,
[`progress.yaml`](./environment_experience_improvement_pack_p307/progress.yaml) the machine view,
per-record progress under each entry's `progress:` key in `improvements.yaml`.

## Status: 3 done · 15 partial · 19 not started (of 37)

Previously 2 · 9 · 25, then 3 · 14 · 19. Six records moved on re-assessment; **CI-036** was
added after a live defect, and **CI-001** advanced when its merge-verb leg was built.

### Moved on re-assessment (2026-08-27)
- **CI-026 → done** — `Quantum-L9/.github` is attached (`/home/user/.github`, in the session scope
  list). True at 78f122a already; the 08-26 pass recorded `not_started` without checking.
- **CI-001 → partial** — `5612f6b` gave `merge_gate._stacked_children` a REST transport and made the
  deny text name the blocked transport (IMP-11 + IMP-12). `gh_auth_probe.sh` (IMP-02) also predates
  the 08-26 pass. Only IMP-01 — the Anthropic session prompt — remains, and it is external.
- **CI-012 → partial** — PR #320 (merged as `c3ddeea`) makes an unevaluable `requires` precondition
  deny the capability instead of passing silently, and moves the generic adapter to the brokered front
  door. Its residuals (rule 22 vs actually-exposed servers, I-BS-12) are untouched, so it stays partial.
- **CI-017 → partial** — `7dc7e4f` moved the PE manifest from gate-time failure to commit-time heal.
- **CI-029 → partial** — `tests/corpus_fixtures.py` persists a two-root corpus builder in
  l9-constellation-topology. Not proven to be I-WT-04's builder (`build_corpus.mjs` is absent; six
  formats, not eight).
- **CI-102 → partial** — `gh api user` answers here and the stack probe answers over REST, so the
  blocked gate is unblocked — by a third route no rule or profile records.

### Residuals that closed inside an existing status
- **CI-007** — the readiness `merge_authority` probe no longer crashes; the live receipt reports
  `merge_authority_status: READY` with a correct note. (PR #306 is the fix.) The stray env var is
  now `L9_AUTONOMY_AUTONOMOUS_MERGE=false`, not `=true` — still present, so the literal `done_when`
  is unmet, but it no longer even nominally widens authority.
- **CI-015** — "read the SSOT's issues without `add_repo`" is met.
- **CI-009** — `interpreter_importable_status: READY` is live in the readiness receipt.

### Merged earlier (unchanged)
- **PR #304 + #305** — operational-parity convergence; closed **CI-007**.
- **PR #306** — readiness merge-authority probe fix (in-process `merge_gate.evaluate()`).
- **PR #307** — the P0 execution slice: **CI-008** (governance Makefile + pre-commit config are the
  publish authority regardless of the repo worked in), **CI-009** (readiness proves importability),
  **CI-002** (`is_tracked()` guard on the rule-adapter reconciler).

## ⏭️ NEXT SLICE — "Ownership-aware writes" (unchanged, now overdue)

Re-verified still unguarded at `498dcaa`. Reuses the `is_tracked()` helper already merged; fully
validatable in-repo; closes the biggest open **P0** residual and folds in a **P1** with the same
root cause.

- **CI-002 residual (P0)** — apply `is_tracked()` before the remaining projection writes
  (`claude_projection.py:422` `.mcp.json`, `reconcile_claude_l9_skills.py`,
  `reconcile_claude_commands.py`, `reconcile_claude_settings.py`) + Phase 2b (project to a
  non-owned sibling when the target is tracked). Verify the 8-fixture `git status` clean.
- **CI-003 (P1), re-scoped** — the named target `/root/.claude/stop-hook-git-check.sh` is
  harness-owned and not editable from this repo. The in-repo lever is the `.git/info/exclude` glob
  list in `ops/scripts/bootstrap_agent_environment.sh` — it already excludes `/.l9/` and `/.cursor/`
  but not `.claude/**` or `.mcp.json`, and `--exclude-standard` honours it.
- **CI-031 (P3, opportunistic)** — keep tracked-path/gitignore hygiene in sync.

**Excluded from this slice:** CI-002 Phase 2c (`L9_AUTONOMY_STATE_DIR` relocation touches
`l4_local.py` + gate + `make pr` — its own change).
**Alternative slice:** receipt integrity — CI-004's live revision disagreement plus proposed CI-034
and CI-035. Small, in-repo, and it fixes the mechanism that let this overlay go stale unnoticed.

## Proposed additions (not adopted)
- **CI-034** — bind the overlay to a governance SHA and invalidate on drift. CI-004's defect class
  applied to the pack itself.
- **CI-035** — cross-check the receipt stores against one another.
- **Progress-schema `blocked_on: external`** — CI-001/003/011/013/020 all name surfaces this org
  does not own; they inflate "not started".

## Still-open P0 / high-priority (see `progress.yaml`)
- **CI-002** (P0, partial) — four projection write sites still unguarded; Phase 2b/2c/2d unbuilt.
- **CI-004** (P0, partial) — reproducing live: `bootstrap-state.json` is pinned to
  `governance_revision c3081ee` while `gov-refresh.json` and `readiness-receipt.json` carry
  `498dcaa`. Two receipt stores disagree inside one session and nothing invalidated the stale one.
- **CI-006** (P0, partial) — general drift mechanism open; the stray var is still present, valued
  `false`.
- **CI-008** (P0, partial) — the consumer-workspace leg of the pre-commit path is scoped in-script,
  not enabled, and unverified against a real consumer checkout.
- **CI-010** (P0, partial) — broker auth/reachability; CONNECT still cannot succeed (external —
  issues #301, #302).
