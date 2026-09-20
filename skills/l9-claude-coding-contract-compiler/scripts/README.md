# Scripts

**Path:** `skills/l9-claude-coding-contract-compiler/scripts` | **Tier:** discovered

## Purpose

compile_contract.py — l9-claude-coding-contract-compiler v2.7.0



## Components

_No public classes in this path._

## Functions

- `def load(path)`
- `def validate_command_list(commands, field)` — Validate canonical shell command strings structurally without executing target code.
- `def validate_spec(spec)` — Fail-closed canonical-spec validation. Critical execution rules do not depend on jsonschema.
- `def glob_to_re(g)`
- `def owns_path_check(in_scope_paths, owns)` — DPK doctrine: in_scope MUST be within boundaries.owns. Enforced only when owns carries
- `def dpk_readiness(cats, manifest, rollback_target, has_ai, eval_suite)`
- `def build_sections(na_map)`
- `def unique_commands(commands)` — Stable, order-preserving deduplication for canonical command projections.
- `def branch_assertion(branch)` — Executable equality assertion. Unlike the v2.6.2 comment form, this actually fails on mismatch.
- `def commit_subject(contract_id)` — Machine-stable one-commit identity. Keep user-controlled titles out of shell assertions.
- `def head_commit_assertion(subject)`
- `def build_instance(camp, item, prev_item, idx, all_ids, prev_id, next_id, digest, commit_range, dpk_block, errors)`
- `def main(argv)`
- `def generate(contract, output_dir) -> None`
- `def main()`
- `def sha256(s) -> str`
- `def fits_one(m, cfg) -> tuple[bool, list[str]]`
- `def group_commits(commit_groups, source_id, total) -> list[dict]` — Convert raw commit groups -> sub-contract descriptors with stable IDs.
- `def compute_chain_digest(sub_contracts) -> str`
- `def plan(manifest, commit_groups, cfg) -> dict`

## Exports

_No `__all__` exports._

## Dependencies

`argparse`, `copy`, `hashlib`, `importlib.util`, `json`, `pathlib`, `re`, `shlex`, `sys`, `types`

<!-- l9-module-readme: generated-from-ast -->
