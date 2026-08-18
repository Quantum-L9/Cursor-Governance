# ADR-0023: Multi-agent main-bound execution — Git isolates writers, memory does not

## Status

Accepted (supersedes the repository-write role of the phase-lock in ADR-0002 and
ADR-0006 §1; the single-front-door decision itself stands)

## Date

2026-08-18

## Context

Memory enforcement and repository ownership had been fused. A governed write to
an authority path, a local history mutation, or a GitHub write all required a
"conflict-checked phase-lock" minted by
`environment/agents/adapters/claude-code/hooks/memory_lock.py`, and the Cursor
write gate additionally denied any GMP-shaped prompt without `gmp:phase_lock`.

Three failures follow from that design:

1. **A knowledge store was acting as a repository mutex.** A semantic conflict
   in Graphiti — evidence that some assumption is disputed — blocked unrelated
   source edits. One agent writing memory could revoke another agent's authority
   to edit code, even on files neither agent shared.
2. **The escape from that mutex was `--force`.** Because conflicts blocked
   acquisition, the lock hook offered `--force` to acquire anyway. The intended
   safety property was therefore agent-defeatable by design, while the
   *un*intended serialization was not.
3. **The real collision risks were unguarded.** Nothing required a task to start
   from the current `origin/main`, nothing refreshed main before publication, and
   the overlap gate failed *open* whenever it could not see GitHub — so the one
   moment where an autonomous agent could actually overwrite a sibling's work was
   the moment the guardrail switched itself off.

Meanwhile the properties that do prevent agents from corrupting each other —
dedicated worktrees, per-task branches, textual merge analysis, PR serialization
— were partly conventional rather than mechanical.

## Decision

Adopt the **L9 Multi-Agent Main-Bound Execution Contract**
(`rules/96-multi-agent-main-bound-execution.mdc`) and separate the authorities:

| Concern | Authority |
|---|---|
| Shared knowledge | Graphiti / canonical L9 memory |
| Repository isolation | dedicated git worktree |
| Canonical task ancestry | fetched `origin/main` |
| Publication | sanctioned `make pr` path |
| Collision detection | git diff + `merge-tree` + CI |
| Integration | PR merge into `main` |

1. **Phase-lock leaves the repository-write path.** `memory_lock.py` is deleted,
   `memory-enforcement.contract.json` moves to v2.0.0 with hydration as the only
   precondition, and the schema makes `phase_lock` an illegal value for
   `governed_writes[].requires` so it cannot be reintroduced silently.
   `memory_state.validate_requires` fails closed on any other precondition.
2. **No agent-facing force-lock exists.** Not softened — removed, along with the
   bridge's `phase_lock` / `phase_lock_satisfied` surface and the Cursor gate's
   `gmp:phase_lock` denial.
3. **Tasks are main-bound and isolated by construction.**
   `ops/scripts/agent_worktree_start.sh` fetches `origin/main`, pins the base
   SHA, branches `agent/<agent-id>/<task-id>`, creates a wired worktree, and
   records task metadata under `.l9/agent-tasks/`.
4. **Publication decides from current Git state.**
   `open_pr_after_gate.sh` fetches the base immediately before publishing, then
   runs `main_bound_check.py` (ancestry, no direct main push, PR targets main)
   and `pr_overlap_check.py` against that refreshed base.
5. **Telemetry failure denies publication.** Under autonomous publication an
   undeterminable collision state blocks the push and nothing else; an
   interactive operator still gets a WARN. `PR_OVERLAP_TELEMETRY=closed|open`
   overrides either way.

## Consequences

- Concurrent agents on different files work and publish in parallel with no
  global lock. Same-file/disjoint-hunk work is decided by `git merge-tree`, not
  by filename collision or by memory state.
- A Graphiti conflict now changes what an agent should *believe*, not what it may
  *write*. Memory writes during another agent's work are safe by construction.
- Autonomous publication is strictly more conservative than before: the gate that
  used to disable itself on network loss now blocks the push instead. Local work
  is never invalidated by a telemetry failure — only publication is.
- GMP keeps its scope discipline. The frozen edit scope is the **scope
  contract**: it says what a task may change, never who owns the repository, and
  is not represented as a lock.

## Conformance

`tests/ops/scripts/test_multi_agent_main_bound.py` proves the §21 minimum
conformance scenarios, including two agents on the same file with disjoint
hunks, conflicting hunks, memory writes during another agent's coding, absence
of the force-lock interface, shared writable worktrees, non-main ancestry,
direct main push, and undeterminable collision state.
