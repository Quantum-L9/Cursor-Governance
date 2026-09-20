# Scripts

**Path:** `environment/program-execution/scripts` | **Kind:** subsystem

## Modules

### `__init__.py`

Program Execution adapter scripts package.

### `accept_blueprint.py`

Accept a compiled Blueprint — the operator's admission act.

- `def accept_blueprint(blueprint) -> dict[str, Any]`
- `def main(argv) -> int`

### `adapter_cli.py`

- `def command_validate(args) -> int`
- `def command_probe(args) -> int`
- `def command_route(args) -> int`
- `def command_dispatch(args) -> int`
- `def command_lifecycle(args, operation) -> int`
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`

### `apply_repository_alignment.py`

- `def apply(repository_root) -> list[str]`
- `def main() -> int`

### `blueprint_ops.py`

Shared admission helpers for PE blueprint tooling (compile / accept / evidence).

- `BlueprintTreeError` — The blueprint tree holds something an inventory cannot honestly digest.
- `def tree_files(root) -> list[Path]` — Every regular file under `root`, refusing any symlink on the way.
- `def load_yaml(path) -> Any`
- `def load_json(path) -> Any`
- `def dump_yaml(path, data) -> None`
- `def load_validator() -> Any` — Load the canonical Blueprint validator module (cached by module name).
- `def validate_blueprint(root, mode) -> list[str]` — Run the canonical Blueprint validator; returns [] on PASS.
- `def scan_placeholders(root) -> list[str]` — Mirror the validator's placeholder scan (same patterns, same file classes).
- _+3 more public symbol(s)_

### `campaign_exec.py`

Spawn a campaign child process.

- `def git_env() -> dict[str, str]`
- `def run_child(cmd) -> subprocess.CompletedProcess[str]`

### `campaign_input.py`

What did the operator actually hand the campaign front door?

- `CampaignInputKind`
- `Classification`
- `CampaignInputRejected` — A terminal, self-explaining refusal. Nothing has executed when it raises.
- `def route_confusion_diagnostics(text) -> tuple[str, ...]` — Warn when a non-promoted brief still carries architecture-like structure.
- `def classify(path) -> Classification` — Classify by content and schema, never by file extension alone.
- `def compile_intent_ingress(path) -> dict[str, Any]` — Classify and compile-check a program-execution.intent.v1 file.
- `def preflight(classification) -> list[str]` — Prove a direct campaign source is executable, not merely well-named.
- `def reject(classification) -> CampaignInputRejected` — Build the terminal refusal for an unsupported classification.
- _+2 more public symbol(s)_

### `campaign_pr_copy.py`

Compose campaign-specific PR title/body from immutable CAMPAIGN_SOURCE.yaml.

- `CopyError`
- `def load_yaml(path) -> Any`
- `def utc_now() -> str`
- `def branch_default_title(ref) -> str`
- `def campaign_id_from_refs() -> str`
- `def source_path_for(campaign_id) -> Path`
- `def policy_entry(campaign_id) -> dict[str, Any]`
- `def render() -> dict[str, Any]`
- _+3 more public symbol(s)_

### `collect_evidence.py`

Collect admission evidence into the Blueprint Evidence Catalog (pre-bootstrap).

- `def memory_lookup(query) -> dict[str, Any]` — Read-only Graphiti search. Fail closed. Never writes memory.
- `def collect_evidence(blueprint) -> dict[str, Any]`
- `def main(argv) -> int`

### `compile_architecture_intent.py`

Compile long-form architecture prose into an executable campaign-source.v2.

- `ArchitectureCompileError` — Terminal, self-explaining. Nothing has executed when this raises.
- `def default_cache_root() -> Path`
- `def existing_campaign_ids(repo_root) -> set[str]` — Ids that already exist — a collision check, never an admission list.
- `def compile_architecture_intent(path) -> dict[str, Any]` — Run the whole architecture route and return a receipt.
- `def build_parser() -> argparse.ArgumentParser`
- `def main(argv) -> int`

### `compile_campaign_source.py`

Compile a campaign-source.v2 seed into a Blueprint v2 pair.

- `CompileError`
- `def utc_now() -> str`
- `def validate_campaign_source(data) -> list[str]`
- `def validate_intent_provenance(src) -> list[str]` — Re-derive the architecture mapping rather than trusting the record of it.
- `def ensure_instantiated(target, src, stamp) -> None`
- `def normalize_task_validation(item, suffix) -> list[dict[str, Any]]` — The task's validation ledger, normalized once for preflight and lowering.
- `def blueprint_task_id_pattern() -> str`
- `def blueprint_gate_id_pattern() -> str`
- _+10 more public symbol(s)_

### `context7_stack_proof.py`

Runner-owned stack-doc proof for PE campaigns.

- `StackProofError`
- `def utc_now() -> str`
- `def primed_receipt_path(campaign_id, primed_dir) -> Path`
- `def seed_text(seed) -> str`
- `def infer_tools(seed) -> list[dict[str, str]]`
- `def is_pure_file_edit(seed, inferred) -> bool`
- `def require_https_url(url) -> urllib.parse.SplitResult` — Refuse file:// and every non-https scheme before urllib sees the URL.
- `def default_fetch(url, headers) -> tuple[int, str]`
- _+12 more public symbol(s)_

_+23 further module(s) in this directory._

## Dependencies

**Internal:** `adapters`, `blueprint_ops`, `campaign_exec`, `compiler`, `generate_manifest`, `launchability`, `pe_timing`, `pe_trace`, `peer_execution`, `program_policy`, `safe_https`

**External:** `jsonschema`, `yaml`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
