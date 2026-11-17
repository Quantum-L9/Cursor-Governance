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
# Lane B — Core own workflows / nightly scheduler

**Exclusive writable files:** `.github/workflows/self-ci.yml`; `.github/workflows/nightly-deep.yml` (new justified file); `tests/workflows/test_self_ci_gating.py`.

## Objective

Keep all existing PR-required check names and real execution. Make `Unit tests` a small meaningful nonempty fail-closed subset allocated by CTO, distinct from A's `repo-test` selection where feasible, using pinned runtime; preserve `Repository contract` as the four-phase real execution against immutable event revision. Avoid rerunning full `unittest discover` in self-ci PR jobs. Retain `tests/tools/test_check_toolchain_versions.py` or equivalent real toolchain witness in at least one required PR suite; do not replace the required Unit tests job with a no-op. Do not weaken SDK contract, security, governance or Semgrep jobs. Revise existing self-CI tests so they now require the *new* PR-fast/deep split but retain check-name uniqueness, toolchain pin and no-bypass assertions.

Create `nightly-deep.yml` with `schedule` daily (proposed 07:17 UTC) and manual dispatch, **only for Core main**, `contents: read`, fixed interpreter/tool dependencies, current-commit checkout, full `test-deep` suite fail-closed, and useful run evidence. Keep schedule separate from Core control-plane attestation. Keep full release workflow untouched.

## Dependency

Draft concurrently with A; final selector and PR readiness depend on CTO's frozen test census and A's actual fast suite. Final branch/PR is stacked on A after CTO sends `GATE` naming A's exact head. Do not make A edit your workflow files. A new scheduled workflow is not proven to fire from its PR branch: pre-merge contract proof and post-merge manual dispatch are separate evidence stages. Do not claim schedule ran from a draft PR.

## Handoff

Report PR B current head, expected check contexts, actual flow of PR vs scheduled/manual events, real YAML parsing/test results. Own CI/review remediation until ready-to-merge; no merge.

## Mandatory protocol

You are one registered `/lcto` fixed-pool coding-agent child, NOT the CTO. Your real launch **system prompt** is the unchanged `cto_mode.py child-prompt` rendered by CTO; this brief is only your task. Enable `/coding-agent` MODE and report ACTIVE JSON in `CTO-STATUS:` before modifying code. Report questions/blockers/status only in your own transcript with `CTO-QUESTION:`, `CTO-BLOCKER:`, `CTO-STATUS:`. Never message another session/operator, coordinate another lane, test combined integration, change scope or merge. Publish via the current sanctioned PR path, then own review/CI remediation on your exact branch until ready-to-merge. Read all current projection views and file owners; pin baseline revision before editing.

No edits outside your writable path whitelist. Read-only repository access never permits edits. If missing authority, shared path ownership or a new required file emerges, stop the affected change and raise a `CTO-QUESTION` rather than taking the file.
