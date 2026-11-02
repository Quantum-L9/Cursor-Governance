<!-- L9_META
schema: 1
parent: l9-skill-compiler
layer: release
role: validation-report
version: 3.9.0
status: passed
-->

# Validation

Every row below was executed on 2026-11-02 against this pack in
`Quantum-L9/Cursor-Governance`. A check that was not run is not listed.

## Release result

- Tier: `exemplary` (both validators PASS on evidence recorded here)
- Source files: 56 (excluding Python bytecode caches)
- Runtime distribution files: 50 (`skill.zip`)
- Text lines in source files (`.md`, `.yaml`, `.py`, `.json`): 3841
- `SKILL.md` references to pack files that do not exist: 0
- Broken local markdown links: 0
- Stubs, unfinished markers, or empty files: 0

## Executed checks

| Command (from the pack root unless noted) | Result |
|---|---|
| `python scripts/validate_skill_pack.py .` | PASS (56 files); covers frontmatter contract, backticked pack-file references, markdown links, unfinished markers, empty files, script syntax |
| `python scripts/validate_exemplary_skill.py .` | PASS |
| `python scripts/validate_smart_exemplary_spec.py references/canonical-smart-exemplary-spec.yaml` | PASS |
| YAML parse of every `*.yaml` file | PASS, 11 files |
| Draft 2020-12 metaschema check of `schemas/*.yaml` | PASS, 7 gate schemas |
| Byte-compile `scripts/*.py` | PASS, 6 scripts |
| `python -m pytest tests -q` | PASS, 22 tests (`test_topology_decision.py`, `test_topology_cli.py`) |
| `pytest tests/ops/scripts/test_skill_compiler_resource_refs.py tests/ops/scripts/test_skill_compiler_frontmatter_contract.py` (repository root) | PASS, 28 tests |
| `python scripts/package_skill.py . <out>` | PASS; 50 entries, `SKILL.md` first, no wrapper directory, no `tests/` entries |
| `python scripts/scan_skill_topology.py --help` | PASS; prints usage and the request shape, exit 0 |

## Validation classes

- Structural: PASS (`validate_skill_pack.py`, YAML parse, schema metaschema check)
- Contract: PASS (frontmatter contract tests bind the validator to the install gate)
- Execution: PASS (script compile, topology CLI tests, packaging)
- Evidence: PASS (this report lists only executed commands)
- Operator: PASS (the `README.md` validate and package commands are the ones run above)
- Regression: PASS (pack and repository test suites above). Not run: comparison against the v3.2–v3.5 source archives listed in `MANIFEST.md`; those archives are not in the repository.

## Known limitations

- The backticked-path check cannot tell a pack file from an unqualified path in a different repository or another pack. Run across this repository's skills, it flags 4 packs that mention scripts in other repositories in prose (`l9-code-graph-rag-mcp`, `l9-idea-execute`, `l9-repo-birth`, `l9-repo-index`), 1 pack that names the compiler's `scripts/validate_exemplary_skill.py` without its `skills/l9-skill-compiler/` prefix (`l9-claude-coding-contract-compiler`), and 3 archived packs (`l9-idea-foundry`, `l9-pr-remediation-deprecated`, `l9-wire-skill-into-repo`). Paths that exist in the host repository are already exempt.
- Installation paths remain environment-specific and are intentionally not invented.
- Repository wiring is not performed unless a repository target is supplied.
- Target-agent tool permissions must be bound by the active platform adapter.
