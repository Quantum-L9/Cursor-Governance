---
name: precommit attribution gate fix
overview: Eliminate the "hook rewrote files and failed the gate" class of failure by making `make pr` absorb pre-commit's modified-files exit, attribute tree changes to the actual writer per hook, align the gate's dirtiness domain with pre-commit's, and serialize concurrent workspace writers behind a repo-write lock.
todos:
  - id: T0-plan-document
    content: Emit the machine PLAN_DOCUMENT JSON for this remedy and validate it with l9-plan scripts/validate_plan_document.py; project the PE+autonomy .plan.md. Create the working branch fresh from origin/main.
    status: completed
  - id: T1-lock-lib
    content: "Add ops/scripts/lib/repo_write_lock.sh (existing shell-lib convention alongside path_contracts.sh, rules_overlay.sh): acquire/release/held_by, flock with macOS atomic-mkdir fallback lifted from governance_sync.sh:44-68, lock at $HOME/.cursor/l9-repo-write.<ws-hash>.lock, ledger recording pid/cmd/ts/workspace, 300s stale break, fail-soft when unsupported. Document that this is machine-local and short-lived, distinct from the tracked long-lived .governance-build-lock kill switch - no duplicate lock policy."
    status: completed
  - id: T2-gate-holds-lock
    content: Have run_pr_gate.sh acquire the repo-write lock for its whole run (release via the existing EXIT trap) and export L9_REPO_WRITE_LOCK_OWNER=$$ so nested governance scripts identify themselves as the holder rather than self-blocking.
    status: completed
  - id: T3-reconcilers-respect-lock
    content: Make run_reconciler in ops/hooks/session_start_bootstrap.sh (line 20) wait a bounded time for the repo-write lock and otherwise skip with a note; add the same defensive check inside install_ide_profile.sh and setup_claude_code_plugins.sh for direct invocation. Keep it consistent with rules/49-shared-worktree-isolation.mdc and ops/autonomy/worktree_isolation_gate.py doctrine - the lock serializes automated reconcilers, it does not replace per-agent worktrees.
    status: completed
  - id: T4-absorb-precommit-exit
    content: "Replace the bare pre-commit call at run_pr_gate.sh line 39 with a captured-rc invocation (set +e, tee to a log) and classify the outcome by parsing pre-commit's exact 4.5.1 markers from run.py:218-228 - '- hook id: <id>', '- exit code: <n>', '- files were modified by this hook'. Modified-files-only means dirtiness, not validator failure. Genuine failures still FAIL, now naming the hook that actually returned non-zero. Retain the current abort behavior behind L9_GATE_STRICT_LEGACY=1."
    status: completed
  - id: T5-per-hook-attribution
    content: "Add ops/scripts/attribute_tree_writers.sh: on any dirtiness, re-run the same hook set one hook at a time (pre-commit run <id> --files, reusing run_pr_precommit.sh's SKIP list and changed-file list) while snapshotting git diff plus the untracked set around each hook, under the repo-write lock. Emit per-path writer attribution, classification (generated / scratch / protected / unknown), and the lock-ledger holder to stdout and a .l9/pr/gate-dirtiness.json receipt. This is the real proof of which hook wrote what - it replaces the first draft's unsound scratch-worktree replay."
    status: completed
  - id: T6-dirtiness-domain
    content: "Fix the domain mismatch: pre-commit's detector is _get_diff() = git diff --no-ext-diff --no-textconv --ignore-submodules (tracked, unstaged only; run.py:274-279), while the gate snapshots git status --porcelain (includes untracked). Make the gate track both sets explicitly so untracked-only churn is never reported as a hook modification and tracked-file edits are never missed, and state both domains in the FAIL/WARN output."
    status: completed
  - id: T7-hook-contract
    content: Add ops/config/precommit-hook-contract.json declaring every .pre-commit-config.yaml hook id as read_only or writer with allowed output prefixes, plus ops/scripts/validate_precommit_hook_contract.py that fails closed when a hook id is undeclared or drifts. Enforcement of read_only is observational via T5 attribution during real runs (a detached worktree cannot host symlinks-check, which validates live workspace wiring), not a synthetic replay.
    status: completed
  - id: T8-generated-allowlist-validator
    content: "Latent-risk hardening only, no relocation: add a validator asserting every path a forced sync_generated_artifacts.sync() reports in its wrote list is matched by is_generated_path (GENERATED_PATH_PREFIXES, sync_generated_artifacts.py:32-52), so a future generator output cannot masquerade as a non-generated autofix. This was not a cause of the observed failure - keep the diff minimal."
    status: completed
  - id: T9-tests
    content: "Add ops/scripts/test_pr_gate_attribution.py (auto-collected by the python-contract repo-root suite, which owns '.') driving the shell scripts in temp git fixtures: generated-only dirt to PASS+WARN; non-generated dirt to retry-then-FAIL naming the path; genuine validator failure naming the right hook; a writer injected during one hook's window attributed to that hook and to the lock ledger, not to symlinks-check; untracked-only churn not reported as a hook modification. Add ops/scripts/test_repo_write_lock.sh plus a Makefile repo-write-lock-test target, matching the ide-profile-test / backup-gate-test convention (TMPDIR-only writes)."
    status: completed
  - id: T10-doctrine
    content: "Append an AGENTS.md block: pre-commit's 'files were modified by this hook' names the hook's wall-clock window, not the writer (run.py:206 threads diff_before hook to hook), with the attribution command. Extend rules/48-make-pr-remediation.mdc with the gate's dirtiness semantics and rules/49-shared-worktree-isolation.mdc with the reconciler lock. Do not mint a new rule number - 47 and 49 are taken and the doctrine has existing homes. Add a learning/failures entry and write the fact to Graphiti."
    status: completed
  - id: T11-converge
    content: Exercise the new gate against temp fixtures and one throwaway clone, then run kernels/Recursive Alignment.md and kernels/Validate & Repair.md, l4_local record-kernels + authorize-release, make pr, and l9-pr-remediation to green.
    status: completed
isProject: false
---

# Remedy: pre-commit "files were modified by this hook" false failure

## Root cause

### D1 - the gate's own tolerance is dead code (primary, verified)

[ops/scripts/run_pr_gate.sh](/Users/ib-mac/Cursor-Governance/ops/scripts/run_pr_gate.sh) runs pre-commit bare under `set -euo pipefail`:

```39:50:ops/scripts/run_pr_gate.sh
bash "$SCRIPT_DIR/run_pr_precommit.sh" "$WS"

if ! git status --porcelain | diff -q "$status_before" - >/dev/null; then
  if bash "$SCRIPT_DIR/classify_generated_dirtiness.sh" "$WS" "$status_before"; then
    echo "WARN: generated artifacts updated by pre-commit — stage them with your commit:"
```

pre-commit returns non-zero for two unrelated conditions - `files_modified or bool(retcode)` (`run.py:235`). `set -e` kills the gate at line 39, so the classify/WARN-continue branch at 41-50 is unreachable on the exact condition it was written to absorb. Every other dirtiness branch in the file (lines 92-101) is reachable only because `sync_generated_artifacts.py --check` does not exit non-zero on churn.

### D2 - the message names a time window, not a writer (verified against pre-commit 4.5.1)

`_run_single_hook` compares the tracked unstaged diff before and after each hook and threads the result forward as the next hook's baseline:

```203:228:/Users/ib-mac/Library/Python/3.9/lib/python/site-packages/pre_commit/commands/run.py
        diff_after = _get_diff()

        # if the hook makes changes, fail the commit
        files_modified = diff_before != diff_after
...
        if files_modified:
            _subtle_line('- files were modified by this hook', use_color)
```

So the verdict is "the tree changed during this hook's wall-clock window", regardless of who changed it. `symlinks-check` has by far the widest window in this repo's hook set - [ops/scripts/validate_governance_symlinks.sh](/Users/ib-mac/Cursor-Governance/ops/scripts/validate_governance_symlinks.sh) delegates to `check_governance_wiring.sh`, which does a `git fetch` and a graphiti resolve - so it collects the blame. It is also provably repo-read-only: its only write is `mkdir -p "$HOME/.cursor/plans"` at line 95. Nothing in the repo declares that, so the false claim cannot be refuted mechanically and an agent burns a cycle inspecting the wrong script.

### D3 - there are real concurrent writers into the workspace

- [ops/hooks/session_start_bootstrap.sh](/Users/ib-mac/Cursor-Governance/ops/hooks/session_start_bootstrap.sh) backgrounds workspace-mutating reconcilers through one choke point, `run_reconciler` (line 20): `setup_claude_code_plugins.sh` (line 178, writes `.claude/`), `install_ide_profile.sh` (line 204, writes `.vscode/settings.json` and the AGENTS.md formatter-ownership block via `ops/scripts/adapters/agentdocs.sh`), and a cold `uv sync` (line 195). None takes a lock.
- Parallel agents or a second Cursor window on the same clone. This class is already documented doctrine: [ops/autonomy/worktree_isolation_gate.py](/Users/ib-mac/Cursor-Governance/ops/autonomy/worktree_isolation_gate.py) records the 2026-08-12 incident where a parallel agent scooped and reverted another chat's in-flight `commands/plan.md`, and `rules/49-shared-worktree-isolation.mdc` owns the policy.
- The agent's own editor/tooling writing during the gate's several-minute run.

### D4 - the gate and pre-commit measure different things

pre-commit's detector is tracked-and-unstaged only:

```274:279:/Users/ib-mac/Library/Python/3.9/lib/python/site-packages/pre_commit/commands/run.py
def _get_diff() -> bytes:
    _, out, _ = cmd_output_b(
        'git', 'diff', '--no-ext-diff', '--no-textconv', '--ignore-submodules',
        check=False,
    )
    return out
```

The gate snapshots `git status --porcelain`, which also includes untracked files. Consequences: newly created generated files (untracked) can never trigger pre-commit's message but do trip the gate's snapshot comparison, and a tracked-file edit trips both with different remedies. The two detectors must be reported separately or the diagnosis stays ambiguous.

### D5 - latent: the generated allowlist is hand-maintained

`GENERATED_PATH_PREFIXES` in [ops/scripts/sync_generated_artifacts.py](/Users/ib-mac/Cursor-Governance/ops/scripts/sync_generated_artifacts.py) (lines 32-52) is decoupled from the generators it describes, so a future generator output would classify as "non-generated autofix" and hard-fail. Not a cause of the observed failure; hardened with a validator only.

```mermaid
flowchart TD
  gate["run_pr_gate.sh snapshots git status --porcelain"] --> pc["run_pr_precommit.sh"]
  pc --> hook["symlinks-check window (widest; read-only)"]
  bg["backgrounded run_reconciler: install_ide_profile, plugins"] -.->|".vscode, AGENTS.md, .claude"| tree["working tree"]
  agents["parallel agent / second window"] -.-> tree
  hook --> tree
  tree --> verdict["pre-commit compares tracked unstaged diff -> 'files were modified by this hook' -> exit 1"]
  verdict -->|"set -e"| dead["gate aborts at line 39"]
  dead -.->|unreachable| classify["classify_generated_dirtiness.sh WARN+continue"]
```

## Corrections to the first draft of this plan (kernel pass 2)

- **Dropped as false:** "pre-commit's `staged_files_only` stash/restore mutates the tree mid-run during `make pr`." `_unstaged_changes_cleared` returns early when `git diff-index` against `git write-tree` reports no staged changes (`staged_files_only.py:57-61`), and `make pr` runs with nothing staged. The stash path is real only on the `git commit` route with partially-staged changes, where the "Stashed changes conflicted with hook auto-fixes... Rolling back fixes" branch (`staged_files_only.py:88-96`) can discard hook output. Recorded as a separate documented failure mode, not as this bug's cause.
- **Dropped as unsound:** proving read-only hooks by replaying them in a scratch worktree. `symlinks-check` validates live workspace symlink wiring and would fail in a detached worktree for reasons unrelated to writes. Replaced by observational per-hook attribution (T5).
- **Corrected:** the new rule number. `rules/47-agent-pattern-activation.mdc` and `rules/49-shared-worktree-isolation.mdc` already exist; the doctrine gets appended to `rules/48` and `rules/49` instead of minting a rule.
- **Added:** D4 domain mismatch, and parallel agents as a writer class the first draft omitted.
- **Demoted:** the generated-allowlist item from a config relocation to a validator, since no evidence ties it to the observed failure.
- **Unknown, stated rather than guessed:** who edited `rules/45-pre-action-verification.mdc` and `rules/46-kernel-pack-new-branch.mdc` in the failing run. No generator writes `rules/*.mdc` (`sync_rules` only regenerates `RULES-MANIFEST.*`; `project_llm_rules` only writes `environment/generated/llm-rules/`), so those were almost certainly authored edits, not hook output. This plan does not claim to explain them and does not revert them.

## Design

1. **One shared lock, no duplicate policy.** `ops/scripts/lib/repo_write_lock.sh` lifts the proven flock-plus-macOS-mkdir idiom from [ops/scripts/governance_sync.sh](/Users/ib-mac/Cursor-Governance/ops/scripts/governance_sync.sh) lines 44-68 and adds a ledger for attribution. It is machine-local and short-lived; the tracked `.governance-build-lock` remains an independent long-lived human kill switch.
2. **The gate holds the lock; automated reconcilers yield to it.** `run_reconciler` waits briefly, then skips fail-soft in the existing bootstrap style. This serializes automation only - per-agent worktrees remain the answer for parallel humans/agents per `rules/49`.
3. **The gate reads pre-commit's exit instead of dying on it**, separates modified-files from validator failure using the verified marker strings, and routes dirtiness through the existing classifier so the WARN-continue path finally executes.
4. **Attribution is measured, not asserted.** On dirtiness the gate re-runs hooks one at a time under the lock with per-hook tracked-diff and untracked-set snapshots, then names the writing hook or the concurrent holder. Non-generated dirt: quiesce, retry once, then FAIL naming exact paths.

## Validation

- `bash ops/scripts/run_pr_gate.sh` against temp git fixtures for each of the five scenarios in T9.
- `make repo-write-lock-test`, `make ide-profile-test`, `make backup-gate-test`.
- `python3 ops/scripts/validate_precommit_hook_contract.py`; repo-root pytest suite via `ops/scripts/run_pytest_suites.sh`.
- `make pr-check` on the real repo last, after fixtures pass.

## Safety and scope

- New branch from `origin/main`; the current checkout carries unrelated `WIP/` and PE work (`rules/46-kernel-pack-new-branch.mdc`).
- `ops/hooks/session_start_bootstrap.sh` is AGENTS.md 5.2 high-risk: the change is confined to `run_reconciler`.
- `L9_GATE_STRICT_LEGACY=1` restores today's abort behavior, so a regression cannot brick `make pr` for consumers.
- `AGENTS.md` is a protected append-only root file: append the doctrine block, delete nothing.
- New fixture tests write only under `$TMPDIR`, matching `ops/scripts/test_install_ide_profile.sh`.

## Adjacent findings, reported not fixed

- `.governance-build-lock` exists in this working tree (empty, dated 2026-08-12) and is why this session reported `backup: SKIPPED — .governance-build-lock present`. Session-end governance backup has therefore been disabled since then. Removing it is a one-line decision that belongs to the user, not to this change set.
- The `git commit` route's stash-conflict rollback (`staged_files_only.py:88-96`) can silently discard hook auto-fixes. Out of scope here; worth its own issue.

## Out of scope

Rewriting pre-commit, changing which hooks exist, reverting the `rules/45`-`rules/46` edits from the earlier PR, and relocating `GENERATED_PATH_PREFIXES`.
