# Changelog

All notable changes to this repo are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Entries before this
file existed (2026-07-19) are not reconstructed — see `git log` for that
history instead of trusting a backfilled entry here.

## [Unreleased]

### Added
- `AGENTS.md` — activation contract for future agent sessions (§2 documents
  the real `.sh`-hook activation mechanism)
- `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `SUPPORT.md`,
  `PULL_REQUEST_TEMPLATE.md` — imported verbatim from `Quantum-L9/.github`.
  GitHub's org-default fallback is a UI/API-only pointer, not a file copy;
  these now exist locally for anyone who clones this repo offline.
- `.editorconfig`, `.gitattributes`, `pyproject.toml`, `.python-version`,
  `Makefile`, `.env.example`, `CODEOWNERS`
- `LICENSE` (MIT) — closes the `license: null` gap in the community profile
  that has no org-wide fallback (see `Quantum-L9/.github#6`)
- `.pre-commit-config.yaml` — wraps `validate_governance_no_hardcoded_paths.sh`
  and `validate_governance_symlinks.sh` as local hooks, plus ruff, so path-lint
  violations are caught pre-commit instead of only in CI

### Removed
- `start-session.yaml` (917 lines) — declarative YAML protocol that was never
  wired into any Cursor hook and had drifted from the pre-Graphiti learning
  pipeline archived in `ops/scripts/_archived/`.
  `ops/hooks/session_start_bootstrap.sh` is, and always was, the actual
  activation mechanism.

### Fixed
- `ops/scripts/resolve_governance_paths.sh` — removed the Dropbox fallback
  path entirely; `$HOME/.cursor-governance` (the GitHub clone) is now the
  sole resolvable governance root.
- `ops/scripts/backup_to_github.sh` — removed a stale `CANONICAL_LAW.md`
  copy step that, combined with the Dropbox fallback above, was reintroducing
  stale content into `main` on every session end and had caused a real merge
  conflict.
- `ops/scripts/operational-oversight.py` — fixed dangling references to
  `startup/REASONING_STACK.yaml` and `verify-startup-files.sh`, both of which
  no longer exist.
- `end-session.yaml` — `sister_file` now points at
  `ops/hooks/session_start_bootstrap.sh` instead of the deleted
  `start-session.yaml`.

## [2.0.0] - 2026-07-04

Post-Suite-6, Graphiti-native governance rewrite (per `README.md`
frontmatter). Predates this changelog — consult `git log` rather than a
backfilled entry.

## [1.x] - 2025-01-27 and earlier

Predates this changelog.
