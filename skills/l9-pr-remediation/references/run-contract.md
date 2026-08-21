<!-- L9_META
l9_schema: 1
parent: l9-pr-remediation
layer: reference
role: run_contract
tags: [pr, preflight, venv, command-surface, topology, cache, makefile]
owner: igor_beylin
status: active
version: 1.2.0
updated: 2026-08-18
/L9_META -->

# Run Contract (min preflight + cache)

## Purpose

One in-run contract. Discover the expensive constraints **once**, then execute. Do not write this file into the skill pack or a generated MANIFEST.

Emit `RUN_CONTRACT` in the first Converge status. Reuse until invalidation.

## Closed preflight (required)

| Id | Check | Fail |
|----|-------|------|
| `P_cmd` | Parse Makefile PUBLIC verbs: `pr-check` (verify), `pr` (publish), `improve` (kernels). INTERNAL: `pr-preflight`, `precommit`, `precommit-repo`, `pr-full`. | If `pr` exists, raw `git push` is a skill defect. Cache `verify: make pr-check` and `publish: PR_REMEDIATE=0 make pr`. |
| `P_venv` | `.python-version`, `.venv/pyvenv.cfg` `home`, `file` + `platform.machine()` of `.venv/bin/python`, `cryptography` + `pytest` import | Arch mismatch, miniconda `home`, or import fail → set `UV_PYTHON` to uv-managed **native** CPython matching requires-python. Never `uv python find --system` (conda `base` wins). Do not loop. |
| `P_prs` | `gh pr list` + `gh pr view --json files` for each open PR | Overlap nonempty → FIRST_MERGE_GATE. Do not merge the first green PR. |
| `P_stack` | For each open PR, is `headRefName` the `baseRefName` of another open PR? | Stacked parent: squash/rebase denied. Children first, retarget, or `--merge`. |
| `P_wire` | Worktree not detached; required symlinks | Wire; `checkout -B`; do not commit wire / `AGENTS.md`. |
| `P_blockers` | Known HUMAN / CI_PIPELINE / ENVIRONMENT | Note; continue independent CODEBASE work. |
| `P_diag` | For the PR about to be edited: head SHA, `gh pr checks`, paginated `reviewThreads`, cited-file read at that SHA | Missing evidence → `Unknown`; do not edit. `disposition: fix` requires a verified root cause. |
| `P_verify` | Makefile `pr-check` + cited-path hook list | `make pr-check` is the gate. Record `Passed` / `Failed` / `Unknown`. Cited paths still get a real check. Do not replay every workflow `run:`. Do not treat local `Passed` as remote CI `Passed`. |

Stop cataloging when `RUN_CONTRACT` is filled and the next PR to edit has a finding list sufficient to patch without predictable rework.

Resume discovery when: unexpected failure, scope change, new dependency, environment drift, PR topology change, conflicting evidence.

## Command surface

This host (Cursor-Governance / Makefile capability graph):

- verify: `UV_PYTHON=<native> make pr-check`
- kernels (optional): `make improve`
- publish: `UV_PYTHON=<native> PR_REMEDIATE=0 make pr`
- merge: `ops/autonomy/stack_safe_merge.py --repo {owner}/{repo} --pr {n} --run` (method chosen in code; oldest `createdAt` first)
- interpreter: `$PWD/.venv/bin/python` (Makefile `$(PYTHON)`). Not Homebrew / system / miniconda base.
- read-only git: allowed

Forbidden after `P_cmd` succeeds on a `pr` target:

- `git push`
- `git push` with `L9_PUBLISH_PATH_OVERRIDE`
- `gh pr create` when `make pr` opens the PR
- `git add -u` / `git add -A`
- `git reset --hard`
- `make precommit` / `pre-commit run --all-files` / `pre-commit install` as the public gate
- `make pr-preflight` as a shipping command
- `make pr-check && make pr` as a second full gate on an unchanged tree

`PR_REMEDIATE=0` is mandatory so `make pr` does not spawn a poll worker. Poll workers never merge. Ignore `merge_eligible` whose SHA is older than HEAD or older than the last repo merge.

If `git push` is denied and the message names `make pr`, switch once. Do not retry `git push`.

Repos without a `pr` target: fall back to the workflow `run:` list in [fix-engine.md](fix-engine.md). Record the fallback on the plan.

Brace tokens in this file (`{owner}`, `{path}`, `{native}`) are templates. An action is executable only after those values are substituted from observed `gh`, Makefile, or `file` / `platform.machine()` output in this run.

## Venv authority

Authoritative runtime: `UV_PYTHON` = uv-managed **native** CPython matching `.python-version` / `requires-python`.

Authoritative venv after build: **worktree** `.venv` created by `uv sync` using that `UV_PYTHON`.

Discovery bias (2026-08-16 / 2026-08-18): `conda init` activates `base`. Then `uv python find 3.12 --system` returns x86_64 miniconda even when uv already has `cpython-3.12-macos-aarch64-none`. That is machine drift, not a lock-pin defect. Never use `--system` to choose `UV_PYTHON`. Prove native with `uname -m` vs `file` / `platform.machine()`.

`.cursor-commands/.venv` is not a third authority. In a wired worktree `.cursor-commands` → `$GOV_ROOT`, so `.cursor-commands/.venv` **is** `$GOV_ROOT/.venv`. If `pyvenv.cfg` `home` is miniconda / x86_64 on an arm64 Mac, reject it. The 2026-08-16 failure was Rosetta miniconda 3.12.11 + cryptography 50 (`_BIO_ADDR_free` / `_EVP_DigestSqueeze`).

`ensure_gov_python.sh` only checks `sys.prefix == .venv`. A venv whose `home` is miniconda **passes** that probe. `make pr` / `run_pytest_suites.sh` resync via `uv sync --locked --extra dev` with no `--python`. Export `UV_PYTHON` on **every** subsequent `make pr-check` / `make pr` or the SSOT `.venv` rebinds to miniconda. A pip-downgrade of cryptography will not persist.

Fingerprint: `python_path`, `version`, `arch`, `pyvenv_home`, `cryptography_import`, `pytest_import`, `UV_PYTHON`.

Invalidation: `.python-version` change, `uv.lock` change, `pyvenv.cfg` home change, import fail, arch mismatch, `UV_PYTHON` unset on a new worktree.

Repair once per invalidation. Forbidden repairs: symlink a failing SSOT venv; off-lock cryptography reinstall; treat ABI as `CODEBASE`; `uv python find --system`.

A Makefile that **hard-pins** `UV_PYTHON` to a non-native interpreter is a host defect to file, not a skill workaround loop. A Makefile that **omits** a native pin (so conda/`--system` wins) is ENVIRONMENT for this run: export `UV_PYTHON`, do not edit the Makefile from this skill.

## Worktree bootstrap

```text
git worktree add -B {branch} {path} origin/{branch}
# not detached HEAD
# setup_workspace_symlinks when the host requires it
# do not commit AGENTS.md / registry churn from wiring
# L4 begin/record/authorize after the remediation commit when the host requires L4
# export cached UV_PYTHON for every make invocation
```

Dirty `AGENTS.md` after wire is not a finding.

## PR topology

For every open PR record: number, base, head SHA, `createdAt`, `headRefName`, `baseRefName`, `files[].path`.

Edges:

- `base_dependency` / `stacked_dependency` — head of A is base of B, or B contains A's commits
- `file_overlap` — from `gh pr view --json files` (do not download full patches)
- `generated_output_overlap` — `MANIFEST.yaml`, `skill-registry.json`, `RULES-MANIFEST.*`, other generated pairs
- `merge_effect_dependency` — predicted invalidation of remaining heads

Independent = empty file overlap and not stacked.

FIRST_MERGE_GATE forbids `gh pr merge` until:

- entire open-PR inventory complete
- overlap matrix known
- stack parents known (`P_stack`)
- remediation published for the required sequence
- expected merge effect on remaining PRs known
- merge strategy selected (squash if unstacked; `--merge` or children-first if stacked)

Then MERGE_TRAIN: **oldest `createdAt` first (bottom-up)**. After each merge, do **not** `gh pr update-branch` on a child whose parent was squash-merged. Use `git rebase --onto <new-base> <old-parent-tip> <child>` when the child must move. Revalidate CI only when HEAD changed.

Forbidden: remediate A → merge A → discover B conflicts → remediate B → rerun CI → repeat.

Forbidden: squash a head that is the base of another open PR (silent delete-wins on the child).

## Companions

If the plan touches `pec/*`, `skills/*`, or `rules/*`, name the generator and include its outputs in the **same** commit.

Cursor-Governance examples:

- skill description/version → `"$PWD/.venv/bin/python" ops/scripts/sync_generated_artifacts.py` → `ops/generated/skill-registry.json` + `environment/agents/adapters/claude-code/generated/skill-registry.json`
- `environment/program-execution/**` → core + pair `MANIFEST.yaml`
- `rules/*` → `sync_generated_artifacts.py --force` for `rules/RULES-MANIFEST.*`

A companion miss is a plan-gate failure, not a remote-CI discovery.

## Fast path

- Locked plan + matching files → skip re-diagnosis; run `P_cmd`+`P_venv` if uncached; verify + publish.
- After `RUN_CONTRACT`, start the first PR that has `CODEBASE` findings. Do not wait for green-check scanner fetches.
- Parallelize independent PR worktrees after the overlap matrix. Serialize merge (oldest first).
- Native-ext import fail → stop `CODEBASE` diagnosis; `P_venv` once.
- CI green + only conversations open → reply + resolve; no new code cycle.

## RUN_CONTRACT schema

```yaml
run_contract:
  command_surface:
    verify: "make pr-check"
    publish: "PR_REMEDIATE=0 make pr"
    improve: "make improve"
    merge: "ops/autonomy/stack_safe_merge.py --repo {owner}/{repo} --pr {n} --run"
    interpreter: "{repo}/.venv/bin/python"
    readonly_git: true
  venv:
    UV_PYTHON: "{uv-managed native cpython path}"
    python: "{repo}/.venv/bin/python"
    version: "{x.y.z}"
    arch: "arm64"
    pyvenv_home: "{must not be miniconda on arm64}"
    fingerprint: "{opaque}"
  prs:
    - number: 192
      base: main
      head: "{sha}"
      createdAt: "{iso}"
      files: ["path"]
      stack_children: []
  overlap:
    - files: ["ops/generated/skill-registry.json"]
      prs: [191, 192]
      effect: "merge 191 invalidates 192 registry"
  merge_train:
    order: [191, 192]   # oldest createdAt first
    first_merge_gate: ready
    stack_safe: true
  blockers: []
  counters:
    time_to_first_useful_action: UNKNOWN
    blocked_command_attempts: 0
    environment_repair_count: 0
    ci_run_count: 0
    merge_conflict_count: 0
    repeated_command_count: 0
```

## Observability

Carry the six counters in `RUN_CONTRACT` and copy them into Final Status. No extra script. Increment `environment_repair_count` only on fingerprint invalidation. A green SHA does not increment `ci_run_count` again.
