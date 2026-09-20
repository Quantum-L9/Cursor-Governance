# Scripts

**Path:** `skills/l9-pr-digest/scripts` | **Tier:** discovered

## Purpose

CLI for the deterministic, read-only L9 pre-remediation PR digest.



## Components

_No public classes in this path._

## Functions

- `def parser() -> argparse.ArgumentParser`
- `def main() -> int`
- `def digest(evidence, workspace, on_event) -> dict[str, Any]`
- `def validate(doc) -> list[str]`
- `def emit_line(kind, payload) -> str`
- `def interactive_report(doc) -> str`
- `def run(cmd, cwd, timeout) -> str`
- `def live_evidence(repo, pr_number, workspace) -> dict[str, Any]`
- `def git_patches(workspace, base, head) -> tuple[str | None, dict[str, str]]`
- `def section_line(text, names) -> str | None`
- `def non_goals(text) -> list[str]`
- `def intent_of(evidence) -> tuple[dict[str, Any], str]`
- `def tokens(text) -> set[str]`
- `def is_test(path) -> bool`
- `def added_lines(patch) -> str`
- `def format_only(patch) -> bool`
- `def question(code, paths, text) -> dict[str, Any]`
- `def growth(kind, path) -> dict[str, Any]`
- `def check(doc) -> list[str]`
- `def fixture()`

## Exports

_No `__all__` exports._

## Dependencies

`__future__`, `argparse`, `collections.abc`, `json`, `pathlib`, `pr_digest_core`, `pr_digest_render`, `pr_evidence`, `re`, `require_digest`, `subprocess`, `sys`, `tempfile`, `typing`

<!-- l9-module-readme: generated-from-ast -->
