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
# Lane D — Existing Core docs alignment

**Exclusive writable files:** `docs/ACTIVATION.md`; `docs/release/rulesets/README.md`. `AGENTS.md` and `docs/repository-execution-runtime.md` are **Lane A exclusive** because the `Repo.mk` change companion rule requires them in A's PR.

## Objective

Explain implemented PR Fast and Nightly Deep behavior without inventing semantic authority. Use the A-owned updates to `AGENTS.md` and `docs/repository-execution-runtime.md` as read-only inputs. Preserve the historical rationale for Core protection checks (§29) rather than falsifying history. Document nightly schedule/ref/dispatch, existing `make-v1` ABI, `repo-test` fast vs `test-deep` full in Core only, real PR check names, warnings that global downstream nightly is not implemented, and readiness/rollback. Use only actual code and live evidence; leave UNKNOWN if source is not yet implemented. No new docs unless no existing owner fits.

## Dependency

Draft concurrently; align with A/B observed exact implementation and stack on B if that is the earliest sufficient ancestor. **Do not wait for C**: C is a parallel sibling, not a prerequisite. Do not edit A-owned core docs, canonical `.github` semantics or the live ruleset payload. Own your docs PR and remediate drift/comments, no merge.

## Mandatory protocol

You are one registered `/lcto` fixed-pool coding-agent child, NOT the CTO. Your real launch **system prompt** is the unchanged `cto_mode.py child-prompt` rendered by CTO; this brief is only your task. Enable `/coding-agent` MODE and report ACTIVE JSON in `CTO-STATUS:` before modifying code. Report questions/blockers/status only in your own transcript with `CTO-QUESTION:`, `CTO-BLOCKER:`, `CTO-STATUS:`. Never message another session/operator, coordinate another lane, test combined integration, change scope or merge. Publish via the current sanctioned PR path, then own review/CI remediation on your exact branch until ready-to-merge. Read all current projection views and file owners; pin baseline revision before editing.

No edits outside your writable path whitelist. Read-only repository access never permits edits. If missing authority, shared path ownership or a new required file emerges, stop the affected change and raise a `CTO-QUESTION` rather than taking the file.
