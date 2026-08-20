---
name: Isolate git test fixture
overview: Rebuild `make_git_fixture` to copy only the repo's tracked files instead of the live worktree, eliminating the inherited-`.git` branch collision, the 214 MB symlink traversal into the governance clone, and the global-git-config leak — then add a regression test that proves the fixture is isolated from ROOT.
todos:
  - id: branch
    content: Create a working branch from origin/main (0d28395), not from the local main at 373bb6d; decide whether the locally-modified AGENTS.md formatter block is committed or reverted so manifest verification is not tripped by unrelated churn
    status: completed
  - id: copy
    content: Replace shutil.copytree in make_git_fixture with a git ls-files -z driven copy of tracked paths (copy2 into mkdir'd parents, skip locally-deleted paths, fail clearly if ROOT is not a git repo); delete the now-dead ignore_patterns argument
    status: completed
  - id: hermetic
    content: "Harden run_git in tests/tools/test_l9_repo.py: hermetic git env via GIT_CONFIG_GLOBAL/GIT_CONFIG_SYSTEM set to os.devnull, and raise on failure with argv, exit code, fixture path, and git's stderr instead of a bare CalledProcessError"
    status: completed
  - id: guard
    content: "Add a regression test pinning fixture isolation: exactly one commit on HEAD, refs/heads == {main, feature}, refs/remotes == {origin/main}"
    status: completed
  - id: sibling
    content: "Optional consistency pass: apply the hermetic-env and stderr-surfacing changes to run_git in tests/tools/test_l9_repo_change_policy.py"
    status: completed
  - id: verify
    content: Run the full suite in the live worktree (expect 185 OK, zero errors, large runtime drop with the local feature branch still present), plus ruff check and ruff format --check; regenerate MANIFEST.sha256 for touched files; run make agent-check
    status: completed
  - id: pr
    content: Open the PR describing the root cause as worktree-copy leakage rather than only the exit-128 symptom, citing the 224 MB versus 1.1 MB and 156s versus 12s measurements
    status: completed
isProject: false
---

## Root cause

[tests/tools/test_l9_repo.py](tests/tools/test_l9_repo.py) builds every git fixture by copying the **live worktree**:

```114:132:tests/tools/test_l9_repo.py
def make_git_fixture() -> tuple[tempfile.TemporaryDirectory[str], pathlib.Path]:
    temporary = tempfile.TemporaryDirectory()
    root = pathlib.Path(temporary.name)
    shutil.copytree(
        ROOT,
        root,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "artifacts"),
    )
    initialize_target_fixture(root)
    configure_simple_commands(root)
    run_git(root, "init", "-b", "main")
```

Three independent defects follow, all from that one line:

- **`.git` is copied.** `git init -b main` on an existing `.git` is a no-op re-init, so the fixture inherits every ref, config value, hook, and worktree registration from the developer's repo. `git checkout -b feature` then fails with exit 128 when a local `feature` branch exists — the reported symptom, 14–15 tests. Worse and quieter: inherited `refs/remotes/origin/*` changes which ref `_comparison_ref` selects (it prefers `origin/<branch>` over `origin/main`), and the base commit lands on top of real history, so `rev-list --left-right --count` returns real numbers instead of a clean single-commit baseline.
- **`copytree` follows symlinks.** `.cursor-commands` is a symlink to `/Users/macm2/.cursor-governance`, excluded only via `.git/info/exclude`. Measured: the traversed tree is **224 MB** (214 MB of it the governance clone, including `ops/secrets/`) versus **1.1 MB** of tracked files. `regenerate_manifest` sha256-hashes all of it and `verify_checksum_manifest` re-hashes it, 15 fixtures per run — the measured 156s versus 12s in a clean clone, now costlier since #94 turned manifest verification on by default.
- **Global git config leaks in.** `core.excludesfile=/Users/macm2/.gitignore_global` is set on this machine and changes `git ls-files --others --exclude-standard`, which `worktree_fingerprint` hashes.

CI never sees any of it: `self-ci.yml` does a manual depth-1 fetch and `git checkout --detach FETCH_HEAD`, so there is no `refs/heads/feature`, no `origin/*` refs, and no untracked tree.

Diagnosis was slow because `run_git` uses `capture_output=True, check=True`, so `CalledProcessError` surfaces `exit status 128` with git's actual message discarded.

## Fix

**1. Copy the tracked tree, not the worktree** — [tests/tools/test_l9_repo.py](tests/tools/test_l9_repo.py)

Replace the `shutil.copytree` call with a copy driven by `git ls-files -z` run in `ROOT`: for each tracked path, `mkdir(parents=True)` the destination parent and `shutil.copy2`. Skip paths absent from the worktree (locally deleted tracked files) so the fixture reflects that state rather than crashing. `shutil.ignore_patterns` becomes dead and goes away — `git ls-files` never reports ignored or untracked paths.

This keeps tracked-file *working-tree* content, so a developer's uncommitted edits are still exercised, and it is byte-identical to today's behaviour on a clean CI checkout. Add a clear failure if `ROOT` is not a git repository, since that is now a precondition.

**2. Make the fixture's git hermetic** — `run_git`

Pass `env={**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}`. Git 2.53 is present locally; these are supported from 2.32. This closes the `core.excludesfile` leak and pre-empts a global `commit.gpgsign` or `core.hooksPath` breaking `git commit` inside the fixture.

**3. Surface git's stderr on failure** — `run_git`

Switch to `check=False` internally and, when the caller asked for `check=True`, raise with the argv, the exit code, the fixture path, and git's `stderr`. Nothing asserts `CalledProcessError` from this helper (the only reference is in `tools/l9_repo/__main__.py`, unrelated), so the raised type is free to change.

**4. Regression test that pins isolation**

Add a test asserting the fixture is a fresh repository regardless of ROOT's state, so this cannot silently return:

- `git rev-list --count HEAD` is `1` (no inherited history)
- `git for-each-ref refs/heads` is exactly `main` and `feature`
- `git for-each-ref refs/remotes` is exactly `origin/main`

These hold no matter what branches or remotes the developer has, which is the property the current fixture lacks.

**5. Secondary, droppable** — [tests/tools/test_l9_repo_change_policy.py](tests/tools/test_l9_repo_change_policy.py)

Its `init_repo` builds an empty temp dir from scratch, so it is already isolated from ROOT's refs, but its `run_git` shares the same swallowed-stderr and global-config exposure. Apply items 2 and 3 there for consistency. Cut this if you want the diff minimal.

## Validation

- `python3 -m unittest discover -s tests -p 'test_*.py'` — expect 185 tests OK with **zero** errors in the live worktree (today: 14–15 errors), and confirm the runtime drop from ~156s toward the ~12s clean-clone figure.
- Prove the original symptom is dead: with a local `feature` branch present (this checkout has one, checked out in `~/.l9/programs/pe-8c9f6de43b25/worktrees/TASK-002`), the suite must pass.
- `ruff check .`, `ruff format --check .` — both cover `tests/`. `mypy` is scoped to `.github/actions` and `tools` only, so it is unaffected.
- Regenerate the `MANIFEST.sha256` entry for every file touched. `tests/tools/test_l9_repo.py` is in the manifest, and since #94 both `make validate` and `tests/tools/test_manifest_integrity.py` enforce it.
- `make agent-check` before opening the PR, per [AGENTS.md](AGENTS.md).

## Landing preconditions

- This checkout is at `373bb6d`, behind `origin/main` at `0d28395`. Branch from `origin/main`, not from local `main`.
- `AGENTS.md` is locally modified by the session's generated formatter-ownership block, and `AGENTS.md` is a manifest entry — so `make validate` will fail locally on that file alone until it is either committed or reverted. That is a direct consequence of #94 defaulting verification on; decide which before running the gates, and keep it out of this commit either way.
