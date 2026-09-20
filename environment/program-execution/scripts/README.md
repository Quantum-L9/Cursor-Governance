# Scripts

**Path:** `environment/program-execution/scripts` | **Tier:** discovered

## Purpose

Program Execution adapter scripts package.



## Components

### `BlueprintTreeError`

The blueprint tree holds something an inventory cannot honestly digest.

- File: `environment/program-execution/scripts/blueprint_ops.py` (L29–30)
- Methods: _none_

### `CampaignInputKind`

No description

- File: `environment/program-execution/scripts/campaign_input.py` (L53–61)
- Methods: _none_

### `Classification`

No description

- File: `environment/program-execution/scripts/campaign_input.py` (L87–123)
- Methods: `supported`, `route`, `to_dict`

### `CampaignInputRejected`

A terminal, self-explaining refusal. Nothing has executed when it raises.

- File: `environment/program-execution/scripts/campaign_input.py` (L126–183)
- Methods: `to_dict`, `render`

### `CopyError`

No description

- File: `environment/program-execution/scripts/campaign_pr_copy.py` (L22–23)
- Methods: _none_

### `ArchitectureCompileError`

Terminal, self-explaining. Nothing has executed when this raises.

- File: `environment/program-execution/scripts/compile_architecture_intent.py` (L71–108)
- Methods: `to_dict`, `render`

### `CompileError`

No description

- File: `environment/program-execution/scripts/compile_campaign_source.py` (L119–120)
- Methods: _none_

### `StackProofError`

No description

- File: `environment/program-execution/scripts/context7_stack_proof.py` (L76–79)
- Methods: _none_

### `Condition`

One gate condition and why it did or did not hold.

- File: `environment/program-execution/scripts/gate_s0_baseline.py` (L61–85)
- Methods: `to_dict`

### `LaunchabilityError`

Raised when a campaign cannot be launched and inference cannot save it.

- File: `environment/program-execution/scripts/launchability.py` (L57–58)
- Methods: _none_

### `Decision`

Whether a stage may be skipped, and the reason either way.

- File: `environment/program-execution/scripts/pe_prepare_state.py` (L95–108)
- Methods: `as_detail`

### `StageRun`

The live handle a stage body uses to see and set its own result.

- File: `environment/program-execution/scripts/pe_prepare_state.py` (L112–121)
- Methods: `reused`

## Functions

- `def accept_blueprint(blueprint) -> dict[str, Any]`
- `def main(argv) -> int`
- `def command_validate(args) -> int`
- `def command_probe(args) -> int`
- `def command_route(args) -> int`
- `def command_dispatch(args) -> int`
- `def command_lifecycle(args, operation) -> int`
- `def build_parser() -> argparse.ArgumentParser`
- `def apply(repository_root) -> list[str]`
- `def main() -> int`
- `def tree_files(root) -> list[Path]` — Every regular file under `root`, refusing any symlink on the way.
- `def load_yaml(path) -> Any`
- `def load_json(path) -> Any`
- `def dump_yaml(path, data) -> None`
- `def load_validator() -> Any` — Load the canonical Blueprint validator module (cached by module name).
- `def validate_blueprint(root, mode) -> list[str]` — Run the canonical Blueprint validator; returns [] on PASS.
- `def scan_placeholders(root) -> list[str]` — Mirror the validator's placeholder scan (same patterns, same file classes).
- `def write_manifest(root, compiled_from) -> None` — Canonical Blueprint MANIFEST.yaml generator (digest of every tree file).
- `def patch_phase0_operator_name(root, owner) -> bool` — Fill PHASE0_USER_CONFIG.operator_ack.name when it is the template placeholder.
- `def lock_exists_for_blueprint(root) -> bool` — True when an existing program-lock binds this blueprint root.

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `adapters.common.errors`, `adapters.common.models`, `argparse`, `ast`, `blueprint_ops`, `campaign_exec`, `collections.abc`, `compiler.architecture_coverage`, `compiler.architecture_extractor`, `compiler.architecture_intent`, `compiler.architecture_target`, `compiler.architecture_to_campaign`, `concurrent.futures`, `contextlib`, `dataclasses`, `datetime`, `enum`, `generate_manifest`, `hashlib`, `importlib.util`, `inspect`, `io`, `json`

<!-- l9-module-readme: generated-from-ast -->
