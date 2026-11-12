---
# Hand-maintained since 2026-11-12: the projection-binding section below is written by
# hand, so the README generator must not overwrite this file.
auto_generated: false
---
# Autonomy plane

**Path:** `ops/autonomy` | **Tier:** operations

## Purpose

Enforce local-commit vs publish vs merge authority without a second scheduler.

Shared autonomy surface — L4 local gate, merge gate, and profile.

## Projection binding (how it works)

What a session reads is bound here; what it may do is not. No module below grants a
permission, and none depends on a skill.

**Default binding, automatic at SessionStart** — `host_binding.py`:

- `governance/host-bindings/<host>.yaml` holds the binding (`cursor`, `claude-code`).
- `host_binding.py` checks it with the verifiers that already exist; it adds no checking
  of its own. The operating plane
  (`l9.projection/cursor-governance-operating-plane@2`) is checked by its consumer adapter,
  `ops/scripts/operating_plane_v2_projection.py`, in admitted mode; each domain by the
  verifier its binding names.
  - It reports `BOUND` only when the operating plane is `CURRENT` and every active
    projection is `ADMITTED_AND_CURRENT`.
  - `DEGRADED` when the operating plane is bound and some active domain is not: what
    verified stays bound, each failure is named. `NOT_BOUND` when the operating plane did
    not verify: nothing is bound.
  - A conditional projection is loaded only when its condition is named with
    `--activate`; otherwise it isn't even checked.
- Both hosts' SessionStart hooks call it: Cursor renders `--format markdown`, Claude Code
  `--format line`. Fail-open: a failed, degraded or timed-out binding never stops the
  session, and is reported as exactly that, never as bound. The renderings exit 0 even if
  the module raises.
- A contract without `session_start.autobind: true` and `depends_on_skill: false` is
  rejected.

**Manual bindings, per session** — `projection_mode.py` (`ProjectionMode`), with one thin
wrapper per mode:

| Command | Wrapper | Contract | Binds |
|---|---|---|---|
| `/coding-agent` | `coding_agent_mode.py` | `governance/coding-agent-mode/MODE.yaml` | `coding-agent-execution@1` |
| `/lcto` | `cto_mode.py` | `governance/cto-mode/MODE.yaml` | technical-coordination plus seven domains |
| `/architect` | `architect_mode.py` | `governance/architect-mode/MODE.yaml` | seven architecture and strategic-planning domains |

- `on` records the request in `<workspace>/.l9/<name>-mode/session.json`, bound to the
  host session that made it; another session sees the mode `OFF`.
- A mode is `ACTIVE` only when every required projection verifies; otherwise `BLOCKED`
  with each reason, and nothing from a blocked projection is loaded. `load[].views` lists
  the files to read.
- Each projection is checked by the verifier its binding declares. A
  coding-projection binding (`governance/authority-bindings/coding-agent-execution.yaml`)
  is judged by `ops/scripts/coding_projection_status.py`: admitted only when the bundle
  verifies at `main` and its admission decision admits the exact profile digest.

Full detail: `governance/host-bindings/README.md`. Tests:
`tests/ops/autonomy/test_host_binding.py`, `test_coding_agent_mode.py`,
`test_cto_mode.py`, `test_architect_mode.py`.

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
- `def main() -> int`
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

## Exports

`ACCEPTED_SCHEMAS`, `APPLY_REL`, `APPLY_SCHEMA`, `APPLY_SCHEMA_V1`, `APPLY_SCHEMA_V2`, `BlastRadius`, `CONTRACT_ID`, `CONTRACT_PATH`, `CONTRACT_VERSION`, `ContractError`, `Decision`, `DirtyPath`, `Effect`, `Finding`, `GuardContext`, `GuardResult`, `HUMAN_AUTHORIZATION_ENV`, `LiveProbe`, `MEMORY_EXECUTABLES`, `OPERATOR_MODULE` (+58 more)

## Dependencies

`__future__`, `argparse`, `collections.abc`, `command_parse`, `concurrent.futures`, `dataclasses`, `datetime`, `enum`, `execution_profile`, `first_publication_gate`, `functools`, `git_execution_exemption`, `git_guardrails`, `hashlib`, `json`, `l4_local`, `merge_gate`, `ops.autonomy`, `ops.autonomy.kernel_predicates`, `ops.autonomy.surface_detect`, `os`, `pathlib`, `re`, `shutil`

<!-- l9-module-readme: generated-from-ast -->
