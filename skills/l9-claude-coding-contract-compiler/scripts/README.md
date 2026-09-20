# Scripts

**Path:** `skills/l9-claude-coding-contract-compiler/scripts` | **Kind:** subsystem

## Modules

### `compile_contract.py`

compile_contract.py — l9-claude-coding-contract-compiler v2.7.0

- `def load(path)`
- `def validate_command_list(commands, field)` — Validate canonical shell command strings structurally without executing target code.
- `def validate_spec(spec)` — Fail-closed canonical-spec validation. Critical execution rules do not depend on jsonschema.
- `def glob_to_re(g)`
- `def owns_path_check(in_scope_paths, owns)` — DPK doctrine: in_scope MUST be within boundaries.owns. Enforced only when owns carries
- `def dpk_readiness(cats, manifest, rollback_target, has_ai, eval_suite)`
- `def build_sections(na_map)`
- `def unique_commands(commands)` — Stable, order-preserving deduplication for canonical command projections.
- _+5 more public symbol(s)_

### `generate_claude_settings.py`

generate_claude_settings.py — l9-claude-coding-contract-compiler v2.7.0

- `def generate(contract, output_dir) -> None`
- `def main()`

### `generate_preflight.py`

generate_preflight.py — l9-claude-coding-contract-compiler v2.7.0

- `def generate(contract, output_dir) -> None`
- `def main()`

### `plan_decomposition.py`

plan_decomposition.py — l9-claude-coding-contract-compiler v2.7.0

- `def sha256(s) -> str`
- `def fits_one(m, cfg) -> tuple[bool, list[str]]`
- `def group_commits(commit_groups, source_id, total) -> list[dict]` — Convert raw commit groups -> sub-contract descriptors with stable IDs.
- `def compute_chain_digest(sub_contracts) -> str`
- `def plan(manifest, commit_groups, cfg) -> dict`
- `def main()`

### `validate_chain.py`

validate_chain.py — l9-claude-coding-contract-compiler v2.7.0

- `def sha256(s) -> str`
- `def compute_chain_digest(ids) -> str`
- `def head_commit_assertion(subject) -> str`
- `def validate_chain(contracts) -> list[str]`
- `def main()`

### `validate_contract.py`

Validate a compiled Claude coding contract against bundled JSON schemas + Claude-fit

- `def dpk_score(contract)` — Compute DPK readiness. Returns (total, band, red_line_reasons).
- `def check_read_only_authority(contract, fit)` — read_only_authority items must be {resource: str, method: GET|LIST}.
- `def check_session_budget(contract, fit)` — If session_budget present, fits_one_session must be bool; a false claim needs a reason.
- `def check_halt_codes(contract, fit)` — resume_from.if_assumption_false must be a known halt code (belt-and-braces vs the schema enum).
- `def check_handoff_seam_shape(contract, fit)` — Internal handoff tokens represent locally committed + validated predecessor state.
- `def check_git_workflow(contract, fit)`
- `def check_remote_mutation_denials(contract, fit)`
- `def run_claude_fit_checks(contract, fit)`
- _+1 more public symbol(s)_

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
