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
# Lane C — Independent Core CI guardrails

**Exclusive writable files:** `tests/workflows/test_org_repository_verification.py`; `tests/workflows/test_org_runtime_contract.py` only, and only where a test adds nonduplicate fault detection. **Do not edit** B's `tests/workflows/test_self_ci_gating.py` or A's self-hosting parity tests.

## Objective

Investigate actual Core `run_v2` and `org-ci` behavior, then add the smallest high-value regression assertions in existing test modules: PR still enforces four phases, `pr_fast`/`merge` remain required, non-Core consumers do not silently change behavior, Core test tier does not weaken signed/immutable SDK or governance checks. Prioritize behavioral fail-known-bad/pass-known-good witnesses (direct helper execution, patched fixtures, subprocess invocations where the existing tests already support them), not merely matching YAML substrings. Static structure assertions supplement, never substitute for executable evidence when available. Do not add a second test framework. If the existing B-owned test already covers a condition adequately, report duplicate and add nothing.

## Dependency

Work concurrently. Stack on B only if the new witnesses require B's behavior; otherwise use the earliest independently proven base. Never become D's predecessor by default. A suggestion to modify the Core central action, ABI, contract schema or another owner's file is a CTO-QUESTION, not authorization.

## Handoff

If existing tests already cover the relevant failure mechanisms, report `no new test justified` and return idle rather than create filler. Report concrete failure witness, exact tests, whether checks prove the intended property, PR head and CI state. Own all remediation in scope; no merge.

## Mandatory protocol

You are one registered `/lcto` fixed-pool coding-agent child, NOT the CTO. Your real launch **system prompt** is the unchanged `cto_mode.py child-prompt` rendered by CTO; this brief is only your task. Enable `/coding-agent` MODE and report ACTIVE JSON in `CTO-STATUS:` before modifying code. Report questions/blockers/status only in your own transcript with `CTO-QUESTION:`, `CTO-BLOCKER:`, `CTO-STATUS:`. Never message another session/operator, coordinate another lane, test combined integration, change scope or merge. Publish via the current sanctioned PR path, then own review/CI remediation on your exact branch until ready-to-merge. Read all current projection views and file owners; pin baseline revision before editing.

No edits outside your writable path whitelist. Read-only repository access never permits edits. If missing authority, shared path ownership or a new required file emerges, stop the affected change and raise a `CTO-QUESTION` rather than taking the file.
