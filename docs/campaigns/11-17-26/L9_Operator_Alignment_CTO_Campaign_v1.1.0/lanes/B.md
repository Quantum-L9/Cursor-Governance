```yaml
repository_access:
  writable:
    - https://github.com/Quantum-L9/l9-semantic-compiler-engine
  read_only:
    - https://github.com/Quantum-L9/.github
    - https://github.com/Quantum-L9/Cursor-Governance
  unlisted_repositories: no_access
```

# Lane B | Compiler producer compatibility and smallest owner-correct repair

**Objective:** Determine whether the existing compiler can project **operator-scoped** Doctrine/Intent without registering it as global `.github` law. Report exact compatibility evidence; implement the smallest compiler-owned change only when current contracts actually authorize it.

**Writable scope if needed:** Existing `src/l9_semantic_compiler/` projector/registry interface implementation directly implicated by inspected code, plus narrowly related `tests/test_projection*.py`, `tests/test_payload_validation_protocol.py`, `tests/test_composition_provenance.py`. Do not edit root compiler meaning, generated ledgers, unrelated node-build, `.github`, or Cursor.

**Entry gates:** Read current compiler `engine/registry.py#CanonicalAuthority`, `passes/projection.py`, CLI request grammar, receipt and payload validation; verify their exact pinned owner and existing supported source classes. Existing `projection-coordinates` existence is not proof an operator-owned source is accepted.

**Work:** Try actual existing producer contract first. If unsupported, give CTO a source-backed missing-contract statement before any new record/schema/API. Only when authorized scoped source semantics are established implement and test; otherwise return `CTO-BLOCKER: OPERATOR_SOURCE_CONTRACT_UNKNOWN`. Do not forge canonical source registration or invent result PASS. If a PR is needed, publish through target-verified sanctioned path and own it until ready.

**Return:** observed source/protocol, whether existing path works, accepted contract or earliest missing owner decision, native receipts if any, negative-control evidence, byte-identical replay evidence if applicable, branch/PR status.

**Host rule:** This is the **Task-specific lane brief**, not the child system prompt. CTO must use the exact child-prompt rendered by the current `ops/autonomy/cto_mode.py` and existing `/coding-agent` mode. The first child action is role registration and mode ACTIVE proof, never edits. All status is reported in the child transcript or Cursor Task result with CTO-STATUS / CTO-QUESTION / CTO-BLOCKER. No cross-session tool calls, no child merges, no child integration test, no raw publication bypass. Repository access headers express intended scope and must be enforced by host permissions to support a technical-isolation claim; headers by themselves grant nothing.

**Publication:** Only current Cursor-Governance SSOT `make pr` transport after checking its actual owner code and L4/gates at the exact checkout. The agent that publishes the PR repairs its CI/review/threads until ready to merge, then returns idle. CTO alone merges when permitted and performs combined integration. Do not invent or run unverified make targets.
