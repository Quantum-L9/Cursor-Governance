# Autonomy plane

**Path:** `ops/autonomy` | **Tier:** operations

## Purpose

Enforce local-commit vs publish vs merge authority without a second scheduler.

Shared autonomy surface — L4 local gate, merge gate, and profile.

## Components

### `Outcome`

Contract ``execution_outcomes``, ordered least → most restrictive.

- File: `ops/autonomy/git_guardrails.py` (L79–88)
- Methods: `rank`

### `Effect`

Contract ``risk_dimensions.effect``.

- File: `ops/autonomy/git_guardrails.py` (L98–112)
- Methods: _none_

### `Sensitivity`

Contract ``risk_dimensions.sensitivity``.

- File: `ops/autonomy/git_guardrails.py` (L115–129)
- Methods: _none_

### `Recoverability`

Contract ``risk_dimensions.recoverability``.

- File: `ops/autonomy/git_guardrails.py` (L132–142)
- Methods: _none_

### `BlastRadius`

Contract ``risk_dimensions.blast_radius``.

- File: `ops/autonomy/git_guardrails.py` (L145–156)
- Methods: _none_

### `Purpose`

Why the agent is running the operation (contract ``diagnostic_policy``).

- File: `ops/autonomy/git_guardrails.py` (L159–163)
- Methods: _none_

### `Ownership`

Contract ``ownership`` — who a changed path belongs to.

- File: `ops/autonomy/git_guardrails.py` (L166–172)
- Methods: _none_

### `Finding`

One classified effect of one command segment.

- File: `ops/autonomy/git_guardrails.py` (L176–187)
- Methods: _none_

### `Decision`

Effective outcome for a whole (possibly compound) command.

- File: `ops/autonomy/git_guardrails.py` (L191–206)
- Methods: `needs_recovery_capture`, `deciding`

### `DirtyPath`

One path with uncommitted state, and who it belongs to.

- File: `ops/autonomy/git_guardrails.py` (L340–344)
- Methods: _none_

### `ProbeError`

A probe could not determine repository state.

- File: `ops/autonomy/git_guardrails.py` (L347–352)
- Methods: _none_

### `Probe`

Read-only view of repository state.

- File: `ops/autonomy/git_guardrails.py` (L355–383)
- Methods: `dirty_paths`, `clean_preview`, `current_branch`, `head_is_published`, `branch_has_unique_commits`, `remote_lease_known`, `can_capture_patch`

## Functions

- `def step(name, ok, detail) -> None`
- `def main() -> int`
- `def auth_path(explicit) -> Path`
- `def write_authorization() -> dict[str, Any]`
- `def default_receipt_path() -> Path`
- `def load_receipt(path) -> dict[str, Any] | None`
- `def evaluate(receipt) -> dict[str, Any]` — Classify a receipt. Never raises.
- `def active_publish_path_reason() -> str` — Return the grant reason only when a valid unexpired receipt is in force.
- `def write_receipt() -> Path`
- `def status_line() -> str`
- `def main(argv) -> int`
- `def strip_heredoc_bodies(command) -> str` — Remove heredoc bodies; keeps the line that opens the heredoc.
- `def split_segments(command) -> list[str]` — Split on ``&&`` ``||`` ``;`` ``|`` newline, honoring single/double quotes.
- `def segment_words(segment) -> list[str]` — Word-split a segment honoring quotes (no glob/expansion semantics).
- `def segment_head(segment) -> str | None` — First command word of a segment, skipping env-assignment prefixes.
- `def wrapper_subcommands(segment) -> list[str]` — Nested command strings carried by wrapper invocations (``bash -c '…'``).
- `def make_workspace_raw(segment) -> str | None` — Last ``WS=`` / ``L9_L4_WORKSPACE=`` on a make segment, or None.
- `def extract_named_roots(command) -> list[str]` — Static repo paths named by ``git -C``, make ``WS=`` / ``make -C``, or ``cd``.
- `def governance_root() -> Path`
- `def load_policy(root) -> dict[str, Any]`

## Exports

`APPLY_REL`, `APPLY_SCHEMA`, `BlastRadius`, `CONTRACT_ID`, `CONTRACT_PATH`, `CONTRACT_VERSION`, `ContractError`, `Decision`, `DirtyPath`, `Effect`, `Finding`, `GuardContext`, `GuardResult`, `HUMAN_AUTHORIZATION_ENV`, `LiveProbe`, `MEMORY_EXECUTABLES`, `OPERATOR_MODULE`, `Outcome`, `Ownership`, `OwnershipOracle` (+38 more)

## Dependencies

`__future__`, `argparse`, `collections.abc`, `command_parse`, `concurrent.futures`, `dataclasses`, `datetime`, `enum`, `execution_profile`, `first_publication_gate`, `functools`, `git_execution_exemption`, `git_guardrails`, `hashlib`, `json`, `l4_local`, `merge_gate`, `ops.autonomy`, `ops.autonomy.kernel_predicates`, `ops.autonomy.surface_detect`, `os`, `pathlib`, `re`, `shutil`

<!-- l9-module-readme: generated-from-ast -->
