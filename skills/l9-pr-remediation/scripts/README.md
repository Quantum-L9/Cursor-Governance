# Scripts

**Path:** `skills/l9-pr-remediation/scripts` | **Tier:** discovered

## Purpose

Fail-closed, secret-safe CodeQL code-scanning alert snapshot fetcher (stdlib only).



## Components

### `DirectTransport`

HTTPS transport; bearer only when a token was bound in-process.

- File: `skills/l9-pr-remediation/scripts/semgrep_fetch.py` (L65–103)
- Methods: `authenticated`, `get`

### `DirectTransport`

HTTPS transport; bearer only when a token was already in the environment.

- File: `skills/l9-pr-remediation/scripts/sonar_fetch.py` (L68–103)
- Methods: `authenticated`, `get`

## Functions

- `def fetch_alerts(base_url, owner, repo, ref, state, token) -> dict`
- `def latest_analysis(base_url, owner, repo, ref, token) -> dict | None`
- `def main() -> int`
- `def detect_languages(repo) -> list[str]`
- `def python_gates(repo) -> list[dict]`
- `def node_gates(repo) -> list[dict]`
- `def count_suppressions(repo, languages) -> dict[str, int]`
- `def run_gates(repo, gates) -> list[dict]`
- `def main(argv) -> int`
- `def sonar_snapshot_binding_error(snapshot, pr) -> str | None` — Explain why a Sonar snapshot is not evidence for ``pr``; None when it binds.
- `def resolve_sonar_snapshot(cwd, fixture_dir, explicit) -> Path | None` — Attach Sonar whenever sonar-project.properties exists. --sonar stays optional.
- `def collect() -> dict[str, Any]`
- `def rest_only() -> bool` — True when this surface refuses GitHub GraphQL and REST routes must be used.
- `def strip_bot_suffix(login) -> str`
- `def reviewer_class(login) -> str`
- `def ledger_source() -> str` — Map an ingest event onto the remediation-plan source vocabulary.
- `def is_code_review_agent(login) -> bool`
- `def edit_axis(path) -> str` — Path-only edit axis. Never returns HUMAN or FALSE_POSITIVE.
- `def gate_type(text) -> str | None`
- `def ownership_hint(finding) -> str`

## Exports

`count_suppressions`, `detect_languages`, `main`, `run_gates`

## Dependencies

`__future__`, `argparse`, `capability_bind`, `datetime`, `json`, `os`, `pathlib`, `protocol`, `re`, `safe_https`, `shutil`, `subprocess`, `surface_trust`, `sys`, `typing`, `urllib.error`, `urllib.parse`, `urllib.request`

<!-- l9-module-readme: generated-from-ast -->
