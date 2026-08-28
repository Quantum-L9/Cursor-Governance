<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: release
role: changelog
version: 3.8.0
status: active
-->

# Changelog

## 3.8.0 - 2026-08-28

### Corrected
- Frontmatter contract is now the L9 native key set: `name`, `description`, `paths`, `disable-model-invocation`, `metadata`. `license` and `allowed-tools` move under `metadata:`. They were previously permitted at top level, which is why compiled packs — this one included — arrived at a governed repository needing hand repair before they could be installed.
- `references/meta-standard.md` and `references/file-contract.md` no longer show audit fields or `license` as top-level keys.
- `name` must equal the pack directory. The previous "only when the target platform requires one" carve-out did not match any discovery surface the compiler targets.

### Added
- `validate_skill_pack.py` enforces description length 150-500 with a `use when`/`use for` trigger clause, non-empty `paths`, and `disable-model-invocation: true` on archived packs.
- `--frontmatter-profile agent-skills` for packs published outside a governed repository, where top-level `license` and `allowed-tools` are valid. Never the default.
- The validator is a required gate in step 6 of the mandatory workflow rather than an optional check.

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
