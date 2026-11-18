```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/l9-ci-core
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/Cursor-Governance
    - https://github.com/Quantum-L9/l9-ci-sdk
  unlisted_repositories: no_access
```
# Lane A — Core execution tier owner

**Exclusive writable files:** `Repo.mk`; `tests/repo_execution/test_core_self_hosting.py`; `AGENTS.md`; `docs/repository-execution-runtime.md` **all in this same PR**. Core policy `repository-execution-evidence` expressly requires the changed test and both docs whenever `Repo.mk` changes; do not delegate those companion edits to D.

## Objective

Replace the **Core-local** `repo-test` complete discovery with a meaningful, explicit, deterministic PR-critical subset. Keep the four ABI leaves .PHONY and executable; do not touch `Makefile`, `.l9/repo-workflow.json`, or central action. Add a Core-local `test-deep` target in the existing `Repo.mk` that invokes the full unchanged discoverable suite. Preserve non-test V1 compatibility assertions, and revise the affected `test_core_self_hosting.py` parity assertion to distinguish new PR and deep behavior.

Critical fast coverage includes CI required contexts, source validation, registry and admission, SDK compatibility, merge/authorization protections and prior false-green regressions. Consume CTO's frozen per-job critical-test census. If it is missing, return CTO-QUESTION before writing a selector; do not infer test speed or skip failures. Fail on empty or missing suite. Include Core's existing test-collectability witness and high-impact false-green cases in one PR-blocking job; CTO decides exact nonduplicate allocation with B. Report exact selected modules, discovered case counts and walltime.

**Mandatory companion docs:** update `AGENTS.md` and `docs/repository-execution-runtime.md` in your same PR. Preserve historical §29; correct stale instructions that still imply `MANIFEST.sha256` is a required tracked ledger, because executable manifest verification is now opt-in and that ledger is retired. Do not add a new manifest.

## Handoff to CTO

Push own PR A against frozen main; do not merge. Provide changed-file census, target selection evidence, `repo-test` fast and `test-deep` full dry-run/live results as available, parity tests, current head and clear `CTO-STATUS`. B depends on the published branch head before it can claim readiness. A's original self-CI Unit tests job may still run the full suite until B changes it; do not claim a speed-up from A's PR in isolation.

## Mandatory protocol

You are one registered `/lcto` fixed-pool coding-agent child, NOT the CTO. Your real launch **system prompt** is the unchanged `cto_mode.py child-prompt` rendered by CTO; this brief is only your task. Enable `/coding-agent` MODE and report ACTIVE JSON in `CTO-STATUS:` before modifying code. Report questions/blockers/status only in your own transcript with `CTO-QUESTION:`, `CTO-BLOCKER:`, `CTO-STATUS:`. Never message another session/operator, coordinate another lane, test combined integration, change scope or merge. Publish via the current sanctioned PR path, then own review/CI remediation on your exact branch until ready-to-merge. Read all current projection views and file owners; pin baseline revision before editing.

No edits outside your writable path whitelist. Read-only repository access never permits edits. If missing authority, shared path ownership or a new required file emerges, stop the affected change and raise a `CTO-QUESTION` rather than taking the file.
