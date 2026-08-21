---
name: Zizmor Workflow Hardening
overview: "Remediate all 103 zizmor findings (58 High, 24 Medium, 18 Low, 3 Informational) across the 7 GitHub Actions workflow files in `Gate_SDK`, via one PR containing 5 logically-separated commits: SHA-pin every unpinned action, add `persist-credentials: false` to remaining checkout steps, add minimal explicit `permissions:` blocks (workflow- and job-scoped), remove cache-poisoning-prone caching from tag-triggered release workflows, and harden two template-injection sites in `release-publish.yml`."
todos:
  - id: commit1
    content: Pin all 51 unpinned action call sites to resolved commit SHAs across all 7 workflow files (checkout, setup-python, upload-artifact, download-artifact, trufflehog->v3.95.9, pypi-publish, gh-release)
    status: completed
  - id: commit2
    content: "Add persist-credentials: false to the 18 remaining checkout steps (merge into 2 existing with: blocks, add new with: block to 16 others)"
    status: completed
  - id: commit3
    content: "Add explicit contents: read permissions to ci.yml/pre-commit-ci.yml/nightly.yml/coverage.yml/integration.yml; restructure release-publish.yml workflow-level write/id-token into job-scoped permissions on publish and gh-release only"
    status: completed
  - id: commit4
    content: "Remove cache: pip from setup-python steps in the 4 release-publish.yml jobs and the 1 release.yml job (cache-poisoning fix)"
    status: completed
  - id: commit5
    content: "Harden the 2 template-injection sites in release-publish.yml (verify-tag version check, SBOM filename) via step-level env: indirection"
    status: completed
  - id: validate
    content: YAML-validate all 7 files, re-run zizmor locally expecting 0 findings, run pre-commit hooks on changed files
    status: completed
  - id: pr-and-dispatch
    content: "Push branch, open PR, confirm ci/pre-commit-ci/coverage/integration pass automatically, then manually workflow_dispatch nightly.yml, release.yml, and release-publish.yml (dry_run: true) to validate the non-PR-triggered workflows"
    status: completed
isProject: false
---

## Scope

All 7 workflow files, all 103 findings, delivered as **one PR** (`fix/zizmor-workflow-hardening` branch off `main`) with 5 commits. `softprops/action-gh-release` replacement (the one `superfluous-actions` finding) is pinned only — replacement deferred to a separate follow-up per your decision.

## Commit 1 — Pin all unpinned actions to commit SHA (51 findings, `unpinned-uses`)

Master SHA table (resolved via GitHub API against the tag/branch currently referenced):

| Action | Current ref | Pinned SHA | Sites | Files |
|---|---|---|---|---|
| `actions/checkout` | `v7` | `9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0` | 18 | [pre-commit-ci.yml](.github/workflows/pre-commit-ci.yml) (3), [coverage.yml](.github/workflows/coverage.yml) (1), [integration.yml](.github/workflows/integration.yml) (1), [nightly.yml](.github/workflows/nightly.yml) (6), [release.yml](.github/workflows/release.yml) (1), [release-publish.yml](.github/workflows/release-publish.yml) (6) |
| `actions/setup-python` | `v6` | `ece7cb06caefa5fff74198d8649806c4678c61a1` | 21 | ci.yml (6, already `checkout`-pinned there — only `setup-python` remains), pre-commit-ci.yml (3), coverage.yml (1), integration.yml (1), nightly.yml (5), release.yml (1), release-publish.yml (4) |
| `actions/upload-artifact` | `v7` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | 6 | ci.yml (1), coverage.yml (1), nightly.yml (1), release.yml (1), release-publish.yml (2) |
| `actions/download-artifact` | `v8` | `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` | 3 | release-publish.yml (3) |
| `trufflesecurity/trufflehog` | `@main` (mutable branch) | switch to tag `v3.95.9` → `27b0417c16317ca9a472a9a8092acce143b49c55` | 1 | ci.yml:208 |
| `pypa/gh-action-pypi-publish` | `release/v1` (mutable branch) | `ba38be9e461d3875417946c167d0b5f3d385a247` | 1 | release-publish.yml:255 |
| `softprops/action-gh-release` | `v3` | `3d0d9888cb7fd7b750713d6e236d1fcb99157228` | 1 | release-publish.yml:291 |

`actions/cache@55cc834...` in pre-commit-ci.yml is already pinned — no change.

Every pin gets a trailing `# vX` comment (matches existing style, e.g. `actions/checkout@9c091bb... # v7`) so Dependabot's `github-actions` ecosystem config (already present in [.github/dependabot.yml](.github/dependabot.yml)) continues to bump these correctly going forward.

## Commit 2 — `persist-credentials: false` on all remaining checkout steps (18 findings, `artipacked`, Low)

18 sites across pre-commit-ci.yml (3), coverage.yml (1), integration.yml (1), nightly.yml (6), release.yml (1), release-publish.yml (6). `ci.yml` already has this on all 7 of its checkout steps — no change needed there.

Two sites already have a `with:` block (merge into it, don't duplicate):
- `pre-commit-ci.yml:84` (`pre-commit-run` job) — already has `fetch-depth: 0`
- `release-publish.yml:274` (`gh-release` job) — already has `fetch-depth: 0`

The remaining 16 sites get a new `with:\n  persist-credentials: false` block added.

## Commit 3 — Explicit minimal `permissions:` (26 findings, `excessive-permissions`)

Add `permissions:\n  contents: read` at the workflow level (no job in these files pushes, comments, or creates releases — verified via grep for `git push|git commit|gh release|contents: write|id-token`, zero matches):
- [ci.yml](.github/workflows/ci.yml)
- [pre-commit-ci.yml](.github/workflows/pre-commit-ci.yml)
- [nightly.yml](.github/workflows/nightly.yml)
- [coverage.yml](.github/workflows/coverage.yml)
- [integration.yml](.github/workflows/integration.yml)

`release.yml` already has `permissions:\n  contents: read` — no change (this is why it has zero `excessive-permissions` findings today).

**release-publish.yml** (the 2 High findings — `contents: write` and `id-token: write` declared at the workflow level, applying to all 7 jobs when only 2 need them):
- Change workflow-level block (lines 37-39) from `contents: write` + `id-token: write` to just `contents: read`.
- Add job-level `permissions:\n      id-token: write` to the `publish` job only (needs OIDC for PyPI Trusted Publisher — no `contents` write needed, it only downloads an artifact and calls the publish action).
- Add job-level `permissions:\n      contents: write` to the `gh-release` job only (needs write to create the GitHub Release and attach assets).
- All other jobs (`verify-tag`, `quality-gate`, `dep-audit`, `build`, `sbom`) inherit the new `contents: read` default — correct, since none of them write anything.

## Commit 4 — Remove `cache: pip` from tag-triggered release workflows (5 findings, `cache-poisoning`, High)

Zizmor flags built-in dependency caching in workflows triggered by tag-push because a cache poisoned by an earlier (e.g. PR) run could be consumed by the release build. Scope is precisely the two tag-triggered files — `ci.yml`/`pre-commit-ci.yml`/`nightly.yml`/`coverage.yml`/`integration.yml` trigger on branches/schedule/PR, not tags, so they are correctly unaffected and keep their caching:

- **release-publish.yml**: remove the `cache: pip` line from the `actions/setup-python` step in `quality-gate` (~line 103), `dep-audit` (~line 147), `build` (~line 180), `sbom` (~line 215). Keep `python-version` line.
- **release.yml**: remove `cache: "pip"` from the single `actions/setup-python` step (~line 26).

Minor, acceptable perf cost (slightly slower installs) confined to the rarely-run release path.

## Commit 5 — Template-injection hardening in release-publish.yml (2 findings, Informational)

Both sites embed a `${{ }}` expression directly into a `run:` shell script body. Fix: move the expression into a step-level `env:` block and reference it as a shell variable instead (GitHub Actions treats `env:` values as literal strings, not shell-parsed — eliminates injection risk even though these particular values are low-risk today).

1. **`verify-tag` job, "Verify version matches pyproject.toml" step** (lines 69-88): replace inline `TAG_VERSION="${{ steps.extract.outputs.version }}"` with a step `env: TAG_VERSION: ${{ steps.extract.outputs.version }}`, reference `$TAG_VERSION` in the script.
2. **`sbom` job, "Generate SBOM" step** (lines 223-227): replace inline `--output-file sbom-${{ needs.verify-tag.outputs.version }}.cdx.json` with a step `env: RELEASE_VERSION: ${{ needs.verify-tag.outputs.version }}`, reference `--output-file sbom-${RELEASE_VERSION}.cdx.json`.

## Out of scope (explicitly not touched)

- The pre-existing `coverage.yml` bug (`needs: [quality]` references a job that doesn't exist in that file) — unrelated to zizmor, functional bug, separate fix.
- Replacing `softprops/action-gh-release` with native `gh release create` — deferred per your decision; only pinned in Commit 1.
- Adding zizmor as a new permanent CI gate to prevent regression — worth proposing separately, not bundled into this remediation.

## Validation (before opening PR, and again in PR)

1. `python -c "import yaml; yaml.safe_load(open(f))"` for all 7 changed files.
2. Re-run `zizmor .github/workflows/` locally — expect 0 findings.
3. Run relevant `pre-commit` hooks (`check-yaml`, etc.) against the changed files.
4. Push branch, open PR — `ci.yml`, `pre-commit-ci.yml`, `coverage.yml`, `integration.yml` all trigger automatically on `pull_request`; confirm all green.
5. `nightly.yml` and `release.yml`/`release-publish.yml` don't auto-trigger on PR. Manually trigger via `workflow_dispatch` from the PR branch to validate the SHA-pinned actions and restructured permissions actually work at runtime:
   - `nightly.yml` — full dispatch (schedule-only otherwise).
   - `release.yml` — full dispatch (build + upload-artifact only, non-destructive).
   - `release-publish.yml` — dispatch with `dry_run: true` (already a supported input) to exercise `verify-tag → quality-gate → dep-audit → build → sbom` end-to-end while `publish`/`gh-release` skip safely.
6. Confirm no new CodeRabbit findings on the PR before merge.
