# Scripts

**Path:** `skills/l9-pr-remediation/scripts` | **Kind:** subsystem

## Modules

### `codeql_fetch.py`

Fail-closed, secret-safe CodeQL code-scanning alert snapshot fetcher (stdlib only).

- `def fetch_alerts(base_url, owner, repo, ref, state, token) -> dict`
- `def latest_analysis(base_url, owner, repo, ref, token) -> dict | None`
- `def main() -> int`

### `debt_audit.py`

Deterministic, secret-safe pre-existing-debt baseline auditor (stdlib only).

- `def detect_languages(repo) -> list[str]`
- `def python_gates(repo) -> list[dict]`
- `def node_gates(repo) -> list[dict]`
- `def count_suppressions(repo, languages) -> dict[str, int]`
- `def run_gates(repo, gates) -> list[dict]`
- `def main() -> int`

Exports: `count_suppressions`, `detect_languages`, `main`, `run_gates`

### `gate_receipt.py`

Fail-closed Gate A–F latch. Stdlib only.

- `def main(argv) -> int`

### `ingest_signals.py`

Unified PR signal snapshot. Stdlib only.

- `def sonar_snapshot_binding_error(snapshot, pr) -> str | None` — Explain why a Sonar snapshot is not evidence for ``pr``; None when it binds.
- `def resolve_sonar_snapshot(cwd, fixture_dir, explicit) -> Path | None` — Attach Sonar whenever sonar-project.properties exists. --sonar stays optional.
- `def collect() -> dict[str, Any]`
- `def main(argv) -> int`

### `issue_handoff.py`

Above-paygrade issue body + optional create. Stdlib only.

- `def main(argv) -> int`

### `protocol.py`

Deterministic remediator protocol tables. Stdlib only.

- `def rest_only() -> bool` — True when this surface refuses GitHub GraphQL and REST routes must be used.
- `def strip_bot_suffix(login) -> str`
- `def reviewer_class(login) -> str`
- `def ledger_source() -> str` — Map an ingest event onto the remediation-plan source vocabulary.
- `def is_code_review_agent(login) -> bool`
- `def edit_axis(path) -> str` — Path-only edit axis. Never returns HUMAN or FALSE_POSITIVE.
- `def gate_type(text) -> str | None`
- `def ownership_hint(finding) -> str`
- _+9 more public symbol(s)_

### `reply_threads.py`

Batch reply + resolve PR review threads. Stdlib only.

- `def main(argv) -> int`

### `self_test.py`

Contract tests for l9-pr-remediation 5.5.0. Stdlib only.

- `def test_frontmatter_and_map() -> None`
- `def test_links_resolve() -> None`
- `def test_owners_exist_and_are_named() -> None`
- `def test_no_second_plane() -> None`
- `def test_verbs_and_publish() -> None`
- `def test_fleet_and_waves() -> None`
- `def test_board_and_merge() -> None`
- `def test_sonar_directive() -> None`
- _+7 more public symbol(s)_

### `semgrep_fetch.py`

Fail-closed, secret-safe Semgrep App findings snapshot fetcher (stdlib only).

- `DirectTransport` — HTTPS transport; bearer only when a token was bound in-process.
- `def build_transport(base_url, surface) -> DirectTransport` — Authenticated when an inventory token can be bound, on any surface.
- `def resolve_deployment(transport, explicit) -> str`
- `def fetch_findings(transport, slug, scope) -> dict`
- `def main() -> int`

### `sonar_fetch.py`

Fail-closed, secret-safe SonarCloud issue snapshot fetcher (stdlib only).

- `DirectTransport` — HTTPS transport; bearer only when a token was already in the environment.
- `def build_transport(base_url, surface) -> DirectTransport` — Authenticated when bind_first finds a token, on any surface.
- `def fetch_issues(transport, project, organization, scope) -> dict`
- `def fetch_rules(transport, rule_keys, organization) -> dict`
- `def main() -> int`

### `validate_plan.py`

Fail-closed remediation-plan schema check. Stdlib only.

- `def main(argv) -> int`

## Dependencies

**Internal:** `capability_bind`, `protocol`, `safe_https`, `surface_trust`

<!-- l9-readme: generated-by=l9-update-agent-docs version=2 kind=subsystem -->
