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

**Host rule:** This is the **Task-specific lane brief**, not the child system prompt. CTO renders `cto_mode.py child-prompt` from `$HOME/.cursor-governance` whose HEAD equals `origin/main`. The first child action is the rendered prompt's first action, including `/coding-agent` ACTIVE, never edits before that. All status is reported in the child transcript or Cursor Task result with CTO-STATUS / CTO-QUESTION / CTO-BLOCKER. No cross-session tool calls, no child merges, no child integration test. If no operator-scoped producer contract exists, return `CTO-STATUS: BLOCKED_INTERFACE` and do not open a compiler PR. That status is complete for this lane.

**Publication:** From the compiler checkout run `PR_REMEDIATE=0 PR_BASE="origin/main" make -C "$HOME/.cursor-governance" pr WS="<this checkout>"` only when a compiler change is actually required. Leave `PR_STACK` empty. Then write `CTO-STATUS: stood-down`. Do not remediate, watch CI, or merge. The CTO remediates a red check inside this write set, runs integration tests, and merges this PR with the other in-scope PRs after those tests pass. A `make pr` rewrite outside this write set is named in `CTO-STATUS` and left uncommitted. No raw `git push` and no `gh pr create`.
