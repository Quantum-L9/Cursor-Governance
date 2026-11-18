# Swarm allocation, noncollision, and PR topology

Pool: **five coding agents maximum, launched together once**. Five is a cap, not permission to force five simultaneous mutations. The fifth lane is an independent read-only challenger. Reuse idle slots for subsequent work, never launch ad-hoc helpers.

| Slot | Lane | Exclusive writable paths | Output | Dependency |
|---|---|---|---|---|
| 1 | A Core test tiers | `Repo.mk`; `tests/repo_execution/test_core_self_hosting.py`; `AGENTS.md`; `docs/repository-execution-runtime.md` | PR A | starts immediately |
| 2 | B Self-CI + nightly | `.github/workflows/self-ci.yml`; `.github/workflows/nightly-deep.yml` (new, justified); `tests/workflows/test_self_ci_gating.py` | PR B | code immediately; final PR stacks on A |
| 3 | C Independent ratchets | `tests/workflows/test_org_repository_verification.py`; `tests/workflows/test_org_runtime_contract.py` (if necessary) | PR C | code immediately; final PR stacks on earliest needed base, normally B |
| 4 | D Existing docs | `docs/ACTIVATION.md`; `docs/release/rulesets/README.md` | PR D | code immediately; stacks on B when implementation-dependent; C is not a predecessor |
| 5 | E Read-only witness | **none** | CTO transcript evidence and challenge | starts immediately; then idle |

**Critical repo-native companion rule:** Core `.l9/core-repo-policy.json` requires any `Repo.mk` change to include a changed `tests/repo_execution/` file **and** both `AGENTS.md` and `docs/repository-execution-runtime.md` in the same PR. Lane A alone owns all four. This is why Lane D must NOT touch those documents. `MANIFEST.sha256` was retired (opt-in salvage only), so no agent should reintroduce a common digest ledger.

**No two agents edit the same file.** Every lane owns one private branch/worktree and may only modify its listed files. On any discovered path conflict, CTO assigns a single owner and stacks follow-up work; agents do not both edit. Tests for one lane should live with that lane when the file is already owned there.

### Parallel coding / ordered integration

- Freeze common Core baseline HEAD before dispatch. A–D draft concurrently in independent worktrees, after CTO freezes the test allocation; do not code against invented selectors. No shared working directory and no shared branch pushes.
- Minimum dependency chain: **A → B**. C and D are independent sibling lanes unless their actual changes prove another dependency. After A pushes a tested branch, CTO gives B `GATE` with the exact parent branch/ref. B **merges** A into its branch (never rebase or force-push) before publication. C and D use B as their common predecessor if they inspect or assert the changed PR/nightly behavior; their sibling branches must remain disjoint. CTO may shorten independent edges only after proving that their tests/docs do not depend on predecessor changes.
- A later child may have draft changes before its parent pushes; it does not claim standalone ready-to-merge before its real base exists. PR bases must express dependencies, not arbitrary timing.
- Before any actual merge, CTO checks the combined tip, all changed files, recorded ready-to-merge states, and merge authorization. A stacked parent with open children is merged with a stack-safe method that preserves ancestry, not squash/rebase that destroys a child base. Retarget/recheck children when parent merges.
- A child's PR remains that child's remediation obligation until merged. If tests fail on a stacked parent, CTO returns the exact failure to the file owner; does not make downstream children quietly repair parent-owned files.

### Pre-launch allocation rules

All child briefs include repository access, a read-only authority set, exact paths, acceptance tests, no merge authority, and the actual CTO session ID. For Claude Code cloud use `cto_mode.py launch-spec` and its `source_url` of `https://github.com/Quantum-L9/.github`; primary Core and Cursor-Governance are attached in the bootstrap sitting. For Cursor use Task continuation as defined by its current mode. Child coding-agent mode must report ACTIVE before any write.

### Source-resolved repository access

Mutators: writable Core only; read-only `.github`, Cursor-Governance, l9-ci-sdk when an SDK check is needed. E may also read Gate_SDK to verify it's an application transport dependency, not a direct Core CI requirement. Changes to any read-only repo are strictly forbidden.

### Conflict matrix / integration order

| Pair | Shared write path? | Semantic dependency | Publication base |
|---|---|---|---|
| A/B | None | B uses A's fast/deep implementation | B stacks on A exact HEAD |
| B/C | None | If C tests B's new workflow, yes | C stacks on B exact HEAD; otherwise proven earliest base |
| B/D | None | D documents B's behavior | D stacks on B exact HEAD |
| C/D | None | None by default | **Siblings**, no forced C→D edge |
| E/any | None | Read-only challenge | No PR |

**Stack discipline:** a sibling merge that changes the shared base requires refreshing the other sibling's mergeability and current SHA, but not mandatory serial coding. When GitHub branch ancestry makes a parent with children unsafe to squash/rebase, CTO uses the existing stack-safe merge path only after exact authorization. Do not invent merges or rewrite history.
