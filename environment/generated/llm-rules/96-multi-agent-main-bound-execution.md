---
description: Concurrent agents share memory, isolate writes in dedicated worktrees branched from fetched origin/main, and integrate through PR gates; Graphiti never gates repository mutation.
---

# L9 Multi-Agent Main-Bound Execution Contract

**Status:** Binding · **Scope:** every agent performing repository mutation.

Concurrent agents may share memory, modify the same repository, publish
independently, and integrate into `main` without overwriting each other.

## 1. Authority (never substitutable)

| Concern | Authority |
|---|---|
| Shared knowledge | Graphiti / canonical L9 memory |
| Repository isolation | dedicated git worktree |
| Canonical task ancestry | fetched `origin/main` |
| Publication | sanctioned `make pr` path |
| Collision detection | git diff + `merge-tree` + CI |
| Integration | PR merge into `main` |

**Graphiti is not repository ownership authority.** A phase-lock MUST NOT
authorize, deny, serialize, or otherwise control ordinary repository mutation.

## 2. Task start (main binding + isolation)

Ordinary mutating work begins from the **current fetched** `origin/main`:

```bash
bash ops/scripts/agent_worktree_start.sh --agent-id <id> --task-id <task>
```

The launcher fetches `origin/main`, pins the exact SHA, creates
`agent/<agent-id>/<task-id>` from it, creates a wired worktree, and records
`agent_id / task_id / branch / worktree / base_sha` under `.l9/agent-tasks/`.

MUST NOT start from another agent branch, a stale local `main`, an arbitrary
commit, an open PR branch, or another agent's worktree. Stacked/campaign
ancestry is an exception requiring `L9_TASK_BASE_AUTHORIZED=<reason>`.

One mutating agent = one dedicated worktree. Never share a writable checkout.

## 3. Shared memory

Hydrate repository-scoped memory at task start: resolve namespace → hydrate →
reason → work → write durable outcomes. The namespace represents **repository
identity**, never branch identity, and is never `main`, `master`, `default`, or
`test`.

Memory conflicts are **evidence**, not mutexes. A conflict may require resolving
an ambiguous assumption or retrieving more evidence; it MUST NOT prohibit
unrelated source mutation. One agent's memory write never revokes another
agent's repository-write authority.

## 4. Phase-lock prohibition

For ordinary repository work agents MUST NOT acquire, force, steal, override, or
synthesize a Graphiti phase-lock, and MUST NOT use `gmp:phase_lock` as
repository-write permission. **Agent-facing `--force` memory-lock functionality
MUST NOT exist.**

The only permitted memory gate shape is:

```
fresh hydration?  yes -> continue
                  no  -> hydrate, then continue
```

Never `hydration -> conflicts -> phase-lock -> edit permission`.

GMP may freeze the authorized edit scope. That construct is the **scope
contract**: it defines what the task may change, not which agent owns the
repository, and MUST NOT be represented as a Graphiti lock.

## 5. Publication

Agents MUST NOT push `main`. Task branches publish only through `make pr` →
`ops/scripts/open_pr_after_gate.sh`, which:

1. fetches `origin/main` immediately before publication;
2. runs `ops/scripts/main_bound_check.py` (ancestry, no direct main push, PR
   targets main);
3. runs `ops/scripts/pr_overlap_check.py` against the **current** base.

Same-file overlap alone is not a collision — `git merge-tree` distinguishes
disjoint hunks from a real conflict. Clean merge → allow; textual conflict →
block, then refresh from current main, resolve, test, retry. Never overwrite or
force-push another agent's work.

**Telemetry failure denies publication.** Under autonomous publication, an
undeterminable collision state (no `gh`, api failure, unresolvable repo
identity, unreadable changed files, no merge analysis) blocks the push and
nothing else — local isolated work stays valid.

## 6. Integration

`origin/main` is the sole ordinary integration SSOT and is authoritative over
local `main`, another agent's branch, and any memory statement about current
code. Development and publication are parallel; integration is serialized by PR
merge control. After integration, write a concise durable outcome
(`task_id`, `agent_id`, `branch`, `merge_sha`, decisions, residual risk).

## Enforcement invariants

`E1` dedicated worktrees · `E2` branches from fetched `origin/main` ·
`E3` no direct main push · `E4` ordinary PRs target main ·
`E5` current-main collision analysis · `E6` autonomous publication fails closed
on undeterminable collision state · `E7` phase-lock absent from repository-write
authorization · `E8` no agent-visible force-lock · `E9` repo-scoped memory
namespace · `E10` memory writes never revoke write authority · `E11` Git is
authoritative for current code state · `E12` main integration stays serialized.

Conformance suite: `tests/ops/scripts/test_multi_agent_main_bound.py`.

## Final rule

Graphiti shares knowledge. Worktrees isolate writers. Branches isolate history.
Git detects code collisions. PR gates serialize integration. `main` is canonical.

Do not introduce another global repository lock unless a separately authorized
resource exists that Git/worktree isolation cannot protect.

<!-- generated-from: rules/96-multi-agent-main-bound-execution.mdc; do-not-edit -->
