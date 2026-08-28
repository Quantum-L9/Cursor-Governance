<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: release
role: changelog
version: 3.7.0
status: active
-->

# Changelog

## 3.7.0 - 2026-08-13

### Corrected
- Runtime archives are now named exactly `skill.zip`.
- `SKILL.md` is written as the first/root ZIP member with no enclosing skill-directory wrapper.
- Packaging validates the staged runtime file set rather than source-only development artifacts.
- Root-flat skills may be packaged from arbitrary extraction-directory names; frontmatter `name` remains canonical.
- Portable structural validation no longer requires compiler-specific release documents or direct SKILL.md listing of every nested resource.
- `tests/`, cache/junk files, and unreferenced `scripts/validate_*.py` validators are excluded from normal runtime delivery.
- Runtime-referenced validators remain packaged.

### Added
- `--include-tests` and `--include-unreferenced-validators` diagnostic packaging flags.
- Regression coverage for root-flat packaging and development-artifact exclusion.

## 3.6.0 - 2026-07-27

### Restored
- Complete standalone contracts, metadata discipline, intelligence framework, and validators from v3.3.

### Adopted
- Gate schemas, scope locking, anti-drift controls, and execution-cost controls from v3.4.
- Validation evidence classes, recursive improvement, convergence analysis, and stronger build-quality doctrine from v3.5.

### Corrected
- Canonical frontmatter now uses portable top-level fields with L9 audit data nested under `metadata`.
- All references are present and linked.
- Package naming follows `l9-<skill-name>.zip`.
- Personal profile and constellation doctrine are conditional adapters, not global law.
- Exemplary claims are backed by included expertise and intelligence reports plus runnable validators.

### Removed
- Duplicate exemplary-contract alias.
- Unsupported custom top-level frontmatter keys.
- Mandatory repo wiring when no repository is in scope.
- Universal hardcoded terminology migrations unrelated to the target skill.
