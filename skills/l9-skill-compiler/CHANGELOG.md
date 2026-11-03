<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: release
role: changelog
version: 3.9.0
status: active
-->

# Changelog

## 3.9.0 - 2026-11-02

### Removed
- v2 runtime residue left in `SKILL.md` by the 3.8.0 replacement: the five deleted policy files (`skill-families`, `runtime-routing`, `capability-closure`, `target-profiles`, `behavior-evals`) and the Skill IR, primary-family and capability-closure rules that depended on them. v3.8 replaced that runtime by design; its scripts and schemas were already gone.

### Changed
- The target-profile rule is rebound to what exists: a platform convention belongs to its adapter under `adapters/`.
- `scripts/scan_skill_topology.py` is wired into workflow step 4 and the resource map, with its input, output and decisions documented in `references/topology-scan.md`. The DAG-ownership invariant now names the step that enforces it.
- `adapters/claude-code.md` writes a tool restriction as `metadata.allowed-tools` in a governed repository, uses top-level `allowed-tools` only under the explicit `agent-skills` profile, and states that the nested key is not enforced by Claude Code.

### Added
- `validate_skill_pack.py` fails when `SKILL.md` names a backticked pack file that does not exist. A pack file is one under a conventional resource directory or any top-level directory the pack has, or a pack root release file; `file.py::symbol` is checked as `file.py`. Fenced code, paths inside a prohibition clause ("do not include ..."), globs, templates, bare directory names and paths that exist in the host repository are exempt.
- `scan_skill_topology.py` has a real `--help`, and a missing, unparseable or mis-shaped request exits `2` with the reason instead of a traceback.
- Tests: `tests/test_topology_cli.py` in the pack and `tests/ops/scripts/test_skill_compiler_resource_refs.py` in the repository.
- `references/meta-standard.md` states how `SKILL.md` names a file outside the pack: a host-repository path (`skills/l9-other/...`), `<repo>:path` for a different repository, or a `<pack>/...` template. Eight packs in this repository were rewritten to that form, and `tests/ops/scripts/test_skill_path_references.py` holds every pack to it.

### Corrected
- `MANIFEST.md`, `README.md` and `VALIDATION.md` are rebuilt from the files present and the checks actually run. The 3.8.0 `VALIDATION.md` reported a `tests/test_validators.py` run that does not exist and zero unlinked references while five listed policies were missing.

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
