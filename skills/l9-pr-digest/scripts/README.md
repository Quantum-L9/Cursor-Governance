# Scripts

**Path:** `skills/l9-pr-digest/scripts` | **Kind:** subsystem

## Modules

### `pr_digest.py`

CLI for the deterministic, read-only L9 pre-remediation PR digest.

- `def parser() -> argparse.ArgumentParser`
- `def main() -> int`

### `pr_digest_core.py`

Deterministic decision engine for l9-pr-digest.

- `def digest(evidence, workspace, on_event) -> dict[str, Any]`
- `def validate(doc) -> list[str]`

### `pr_digest_render.py`

Human stream + interactive unpack for a PR digest. Same semantics as the JSON.

- `def emit_line(kind, payload) -> str`
- `def interactive_report(doc) -> str`

### `pr_evidence.py`

Evidence helpers for l9-pr-digest. Pure/read-only except subprocess collection.

- `def run(cmd, cwd, timeout) -> str`
- `def live_evidence(repo, pr_number, workspace) -> dict[str, Any]`
- `def git_patches(workspace, base, head) -> tuple[str | None, dict[str, str]]`
- `def section_line(text, names) -> str | None`
- `def non_goals(text) -> list[str]`
- `def intent_of(evidence) -> tuple[dict[str, Any], str]`
- `def tokens(text) -> set[str]`
- `def is_test(path) -> bool`
- _+4 more public symbol(s)_

### `require_digest.py`

Fail-closed check that a digest exists, is revision-bound, and (for Converge) is READY.

- `def check(doc) -> list[str]`
- `def parser() -> argparse.ArgumentParser`
- `def main() -> int`

### `self_test.py`

- `def fixture()`
- `def main() -> int`

## Dependencies

**Internal:** `pr_digest_core`, `pr_digest_render`, `pr_evidence`, `require_digest`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
