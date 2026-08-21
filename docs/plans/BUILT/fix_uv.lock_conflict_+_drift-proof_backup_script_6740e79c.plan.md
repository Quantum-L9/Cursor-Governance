---
name: Fix uv.lock conflict + drift-proof backup script
overview: Resolve the committed merge-conflict markers in pyproject.toml, Makefile, and uv.lock inside ~/.cursor-governance, then harden governance_sync.sh (primary root cause) and backup_to_github.sh (secondary safety net) so this class of failure can never again be silently written into a real commit.
todos:
  - id: fix-pyproject
    content: Resolve merge markers in pyproject.toml, keep [tool.mypy] block
    status: completed
  - id: fix-makefile
    content: Resolve merge markers in Makefile, keep mypy-inclusive lint target
    status: completed
  - id: regen-lock
    content: Regenerate uv.lock via `uv lock` from the fixed pyproject.toml
    status: completed
  - id: verify-clean
    content: Verify no conflict markers remain; uv sync / make lint / make precommit pass
    status: completed
  - id: harden-sync-stash
    content: "PRIMARY FIX: governance_sync.sh — detect stash-pop conflicts instead of silencing them to /dev/null"
    status: completed
  - id: harden-preflight
    content: Add unmerged-paths pre-flight guard to backup_to_github.sh before git add -A
    status: completed
  - id: harden-merge-abort
    content: Replace merge `|| true` with abort-and-exit-1 on conflict in backup_to_github.sh
    status: completed
  - id: harden-diff-check
    content: Add `git diff --cached --check` guard before commit in backup_to_github.sh
    status: completed
  - id: harden-lock-check
    content: Add `uv lock --check` guard before commit in backup_to_github.sh
    status: completed
  - id: pcc-merge-hook
    content: Add check-merge-conflict hook to .pre-commit-config.yaml
    status: completed
  - id: pcc-install
    content: Install pre-commit as a real git hook in ~/.cursor-governance
    status: completed
  - id: ci-lock-check
    content: Add uv lock --check step to l9-lint-test.yml
    status: completed
  - id: ci-marker-scan
    content: Add repo-wide conflict-marker scan step to l9-lint-test.yml
    status: completed
isProject: false
---

## Root cause (re-validated against actual logs — correcting the earlier draft)

All three broken files live in `~/.cursor-governance` (the repo `.cursor-commands` symlinks to), not in the igorbot repo itself. The first draft of this plan attributed the conflict to `backup_to_github.sh`'s `git merge ... || true` fallback — that theory did not survive evidence-checking. `backup.log` (122 lines, full history since 2026-06-24) contains **zero** occurrences of "CONFLICT", "rebase failed", or any merge-fallback output; every logged run shows a trivial `git rebase` ("Current branch ... is up to date") with no conflict ever surfacing through that script. The real mechanism is elsewhere:

1. **Primary cause — [ops/scripts/governance_sync.sh](/Users/macm2/.cursor-governance/ops/scripts/governance_sync.sh) line 61.** This is the session-*start* auto-sync hook. When the working tree is dirty at session start, it does:
   ```
   git stash push -q -u -m governance-autosync >/dev/null 2>&1
   git merge --ff-only --quiet "origin/$BRANCH" >/dev/null 2>&1 || true
   git stash pop -q >/dev/null 2>&1 || true   # conflict leaves stash intact for manual resolve
   ```
   `git stash pop` performs a real 3-way merge when reapplying — if the fast-forward pulled in commits that touched the same lines as the stashed local edits, the pop **writes literal `<<<<<<<`/`=======`/`>>>>>>>` markers directly into the working-tree files** and marks those paths unmerged. The comment above it ("conflict leaves stash intact for manual resolve") shows the script's author knew this could happen — but `>/dev/null 2>&1` on every step means the conflict is **100% silent**: no stderr, no log line, nothing. The script always `exit 0`s.
2. **Confirmed by exact timestamps.** `git blame` shows the marker lines in `uv.lock`/`pyproject.toml`/`Makefile` were introduced by commits `e1392ee` ("chore(governance): session-end sync 2026-07-20", 01:35:58) and `88b63fce` ("chore(governance): end-session 2026-07-20", 02:01:52) — 26 minutes apart, both on 2026-07-20 in the early-morning hours right after `6de4f8b` ("chore(env): lock Python 3.12 + uv-managed venv for governance tooling", 01:09:30). The commit messages match, verbatim, the message templates in [ops/hooks/session_end_governance_backup.sh](/Users/macm2/.cursor-governance/ops/hooks/session_end_governance_backup.sh) (`"chore(governance): session-end sync $(date +%Y-%m-%d)"`) and [end-session.yaml](/Users/macm2/.cursor-governance/end-session.yaml) (`"chore(governance): end-session $(date +%Y-%m-%d)"`) respectively — i.e. an automatic sessionEnd hook fired, then `/end-session` was run manually shortly after. Neither of those two commit events appears in `backup.log` at that timestamp with any merge/rebase output, because their job (`backup_to_github.sh`) only *commits and pushes whatever is already in the working tree* — it never diagnosed the tree was already broken.
3. **Secondary/contributing cause — [ops/scripts/backup_to_github.sh](/Users/macm2/.cursor-governance/ops/scripts/backup_to_github.sh).** Once `governance_sync.sh` silently left conflict markers sitting in the working tree, `backup_to_github.sh`'s `git add -A` (line 54) staged them as "resolved" (git has no way to know marker text isn't intentional), and `git commit -m "$MSG"` (line 64) — invoked identically by both the automatic hook and `/end-session` — baked them into real history. This script's *own* `git merge "origin/$BRANCH" -m "..." || true` fallback (line 76) is a real latent bug of the same shape (verified: `git help diff` confirms `git diff --check` explicitly warns on "conflict markers", and this fallback's `|| true` would swallow a conflict from *this* script's own merge attempt too) — it just isn't the bug that fired in this specific incident, based on the log evidence. It's still worth fixing as defense-in-depth.
4. **Nothing else in the repo would have caught either failure mode.** `.pre-commit-config.yaml` has `no-hardcoded-paths`, `symlinks-check`, and ruff hooks — none scan for conflict markers, and ruff only touches `*.py` files (never `pyproject.toml`, `Makefile`, or `uv.lock`). Confirmed `.git/hooks/pre-commit` does not exist in this repo, so pre-commit only runs via `make precommit` manually — it would never fire on either script's automated `git commit` regardless of hook content. CI ([.github/workflows/l9-lint-test.yml](/Users/macm2/.cursor-governance/.github/workflows/l9-lint-test.yml)) only runs `ruff`/`mypy`/`pytest` on `.py` files and triggers on `push: main` — reactive at best, and wouldn't catch this either.

**Related, already self-remediated (informational only — not part of this plan's scope):** the same `backup.log` shows a real Google OAuth Client ID/Secret got committed via this exact automated path on 2026-07-21 (`WIP/google_oauth_IgorBot.json`, `WIP/google_oauth_igor 2.json`, commit `54824b1`) and was only stopped by GitHub's server-side secret-scanning push protection — it never reached the remote. Verified: that commit is **not** an ancestor of current `HEAD` (dangling locally), the files are gone from the working tree, and `.gitignore` already has dated patterns (`WIP/*oauth*.json`, `WIP/*credentials*.json`, `WIP/*client_secret*.json`, added 2026-07-21) blocking recurrence. This is separate from the conflict-marker issue but is the same root pathology — blind `git add -A` with no content-aware guard before an automated commit — and is strong independent evidence for why Part B/C below matter. Flagging for your awareness; not adding remediation tasks since it's already handled.

Concretely broken conflicts to resolve (unchanged from initial diagnosis):
- [pyproject.toml lines 57-73](/Users/macm2/.cursor-governance/pyproject.toml): keep the `HEAD` side's `[tool.mypy]` block (origin/main's side is empty) — consistent with `mypy>=1.19` already being an uncontested dev dependency at line 24.
- [Makefile lines 46-57](/Users/macm2/.cursor-governance/Makefile): keep `HEAD`'s mypy-inclusive `lint:` target (matches the CI lint job step-for-step per its own comment); discard origin/main's ruff-only variant.
- `uv.lock`: do not hand-merge — regenerate from the fixed `pyproject.toml`.

## Part A — Fix the currently broken files

1. Edit [pyproject.toml](/Users/macm2/.cursor-governance/pyproject.toml): remove the `<<<<<<< HEAD` / `=======` / `>>>>>>> origin/main` marker lines (57, 72, 73), keeping the `[tool.mypy]` block between them.
2. Edit [Makefile](/Users/macm2/.cursor-governance/Makefile): remove the marker lines (46, 53, 57), keeping the `HEAD` `lint:` target (ruff check + ruff format --check + mypy).
3. Regenerate the lockfile: `cd ~/.cursor-governance && uv lock` — this rebuilds `uv.lock` cleanly against the fixed `pyproject.toml` (naturally resolving the `ast-serialize`/`mypy`/`mypy-extensions`/`librt`/`pathspec`/`resolution-markers` discrepancies without manual reconciliation). Confirmed installed `uv` is 0.11.24 and supports `uv lock --check` ("Check if the lockfile is up-to-date") for later use in Parts B/C.
4. Verify: `grep -rn '^<<<<<<<\|^=======$\|^>>>>>>>' pyproject.toml Makefile uv.lock` returns nothing; `uv sync --locked --extra dev` succeeds; `make lint` and `make precommit` pass.
5. Review diff, then commit locally in `~/.cursor-governance` (push only with your explicit go-ahead, per the repo's no-auto-push rule).

## Part B — Harden the two scripts that let this happen (root cause + contributing cause)

### B1. [governance_sync.sh](/Users/macm2/.cursor-governance/ops/scripts/governance_sync.sh) — PRIMARY fix

This is a session-start hook, explicitly designed "fail-soft" and "never destroys local edits" — the fix must preserve that intent (no hard-fail that blocks a session from starting), but must stop being **silent** about a real conflict:

1. After `git stash pop -q >/dev/null 2>&1 || true` (line 61), check the actual result instead of discarding it: test for unmerged paths (`git status --porcelain | grep -qE '^(UU|AA|DD|AU|UA|UD|DU) '`).
2. If a conflict is detected: do **not** silently continue. At minimum, write a loud, visible marker — e.g. append to a small state file (`$CLONE/.sync-conflict` or similar) and print a non-suppressed warning — so the next thing that touches this repo (a human, an agent, or `backup_to_github.sh`) can detect "there's an unresolved stash-pop conflict" and refuse to blindly commit over it. This directly closes the gap that let `backup_to_github.sh` commit broken files hours later without anyone knowing.
3. Keep the "fail-soft, never block session start" behavior — the script still `exit 0`s — but the conflict must now be *discoverable*, not merely swallowed to `/dev/null`.

### B2. [backup_to_github.sh](/Users/macm2/.cursor-governance/ops/scripts/backup_to_github.sh) — secondary safety net (defense-in-depth, independent of B1)

1. **Pre-flight guard** (before `git add -A` at line 54): check for pre-existing unmerged paths (same grep as B1, and/or check for the state file B1 writes) — if found, `exit 1` with a clear error instead of blindly staging broken files. This is the safety net that should have existed regardless of what upstream script caused the conflict.
2. **Stop swallowing this script's own merge failures** (line 76): replace `git merge "origin/$BRANCH" -m "..." || true` with a branch that, on failure, runs `git merge --abort` to restore a clean tree and then `exit 1` with a loud message — never fall through to `git push` after a failed merge. (Latent bug, not the one that fired here, but the same shape.)
3. **Conflict-marker guard before commit** (between `git add -A` and `git commit -m "$MSG"`): run `git diff --cached --check` (confirmed via `git help diff`: explicitly warns on leftover conflict markers, in addition to whitespace errors) and abort the commit if it reports anything.
4. **Lockfile-drift guard**: before committing, run `uv lock --check` against `pyproject.toml` (confirmed flag exists on the installed `uv` 0.11.24); abort if the lockfile is out of sync, rather than let a stale/inconsistent `uv.lock` get synced up to GitHub.

## Part C — Repo-wide guardrails so drift can't sneak in through any other path

1. Add the standard `check-merge-conflict` hook (from `pre-commit/pre-commit-hooks`) to [.pre-commit-config.yaml](/Users/macm2/.cursor-governance/.pre-commit-config.yaml) — catches leftover markers in any tracked file, not just the ones these two scripts touch.
2. Actually install pre-commit as a git hook in this repo (`pre-commit install`, since `.git/hooks/pre-commit` currently doesn't exist) so `make precommit`'s checks also run automatically on manual/interactive commits, not only when run by hand.
3. Add a lockfile-consistency step to [.github/workflows/l9-lint-test.yml](/Users/macm2/.cursor-governance/.github/workflows/l9-lint-test.yml)'s lint job: `uv lock --check` — a second, independent check that fires on every push to `main`, catching drift introduced through any path (not just these two scripts).
4. Add a repo-wide conflict-marker scan step to the same CI job (`pre-commit run check-merge-conflict --all-files`, or an equivalent grep) as a final safety net, since these scripts push directly to `main` with no PR/branch-protection gate — CI here is a fast-detection tripwire, not a merge blocker, so flag that limitation explicitly rather than treat it as a full fix.

## Sequencing

Part A must land first (it's the actual bug fix). Part B1 (`governance_sync.sh`) is the true root-cause fix and takes priority over B2; B2 (`backup_to_github.sh`) is an independent secondary safety net worth doing regardless. Part C is defense-in-depth for paths outside both scripts. All are independent enough to review/commit separately.
