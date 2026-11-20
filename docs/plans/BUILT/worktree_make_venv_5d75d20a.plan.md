---
name: worktree make venv
overview: Make the sanctioned worktree creator build each new tree’s environment with
  that repo’s own `make venv` target, instead of only when `pyproject.toml` and `uv.lock`
  are both present.
todos:
- id: replace-venv-branch
  content: Replace the uv.lock / ensure_gov_python.sh branch in ops/scripts/worktree_add_wired.sh
    with make -q venv then make -C "$path" venv
  status: completed
- id: update-comments
  content: Update the uv-project-only comments in ops/scripts/agent_worktree_start.sh
    (lines 136 and 188)
  status: completed
- id: add-tests
  content: Add stub-Makefile tests in tests/ops/scripts/test_worktree_add_wired_clean.py
    for a root venv target, an included fragment, and a uv.lock tree with no venv
    target
  status: completed
isProject: false
built: true
status: built
---

# Worktree venv via `make venv`

Architecture is already settled. There is one builder, the repo’s `venv` Make target. This repo’s recipe is `venv:` in [ops/make/core.mk](ops/make/core.mk) (it runs `ensure_uv_environment.sh`). Other repos define the same target name with their own recipe. Do not add a pin-file branch, a symlink to another checkout’s `.venv`, or a call that only fires for `uv.lock`.

## Change

In [ops/scripts/worktree_add_wired.sh](ops/scripts/worktree_add_wired.sh), delete the block at lines 58–64 (the `pyproject.toml` + `uv.lock` check that calls `ensure_gov_python.sh`). After the links-only wire, probe the new tree and run its target:

```bash
# Every repo builds this tree's .venv with its own `make venv`.
# The recipe may live in an included fragment, so ask Make; do not grep
# the root Makefile and do not branch on uv.lock or requirements*.txt.
# make -q: 0 up to date, 1 would run, 2 no such target. A symlink to
# another checkout's .venv is not a substitute.
if ! command -v make >/dev/null 2>&1; then
  echo "ERROR: make is not on PATH; cannot build $path/.venv" >&2
  exit 1
fi
make_venv_rc=0
make -C "$path" -q venv >/dev/null 2>&1 || make_venv_rc=$?
if [ "$make_venv_rc" -eq 0 ] || [ "$make_venv_rc" -eq 1 ]; then
  echo "--- venv (make venv) ---"
  make -C "$path" venv
fi
```

`|| make_venv_rc=$?` is required because the script is `set -e`. Exit 2 (no target, or no Makefile) skips. Exit 0 or 1 runs `make -C "$path" venv`, and a failing recipe still aborts. Missing `make` fails closed so a worktree is not reported ready with no way to build.

`make pr` / `gov-python` keep the import proof. Worktree creation no longer calls `ensure_gov_python.sh`, which rejects any tree that is not this repo’s lock plus its import set.

## Comments

In [ops/scripts/agent_worktree_start.sh](ops/scripts/agent_worktree_start.sh), replace “uv project” / “uv projects only” at lines 136 and 188 so they say the `.venv` is materialized by `worktree_add_wired.sh` when the repo has a `venv` Make target.

Do not edit `AGENTS.md`, `session_deps_cloud.sh`, or `ensure_gov_python.sh`.

## Tests

Extend [tests/ops/scripts/test_worktree_add_wired_clean.py](tests/ops/scripts/test_worktree_add_wired_clean.py). Stub the recipe (`touch` a marker). Do not run a real install.

- Root `Makefile` with `venv:` writes a marker in the new worktree. Assert the marker exists, `.venv` is not a symlink, and stdout contains `--- venv (make venv) ---`.
- Root `Makefile` is only `include fragment.mk`, and `fragment.mk` defines `venv:`. Same assertions. This is the case a `^venv:` grep misses, and it is how this repo is built.
- `pyproject.toml` and `uv.lock` with no `venv` target: the script exits 0, stdout has no `locked venv`, and no `.venv` is created.
- The existing no-Makefile consumer test stays green (probe exits 2, docs stay clean).

## Proof

`python3 -m pytest -q tests/ops/scripts/test_worktree_add_wired_clean.py`

## Build evidence (auto)

- detected_at: `2026-11-08T21:26:29Z`
- conversation_id: `827cd55a-c16a-4326-9576-84d5e44c97fd`
- generation_id: `47695ecf-6460-49d5-986e-05fa026b69e0`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/827cd55a-c16a-4326-9576-84d5e44c97fd/827cd55a-c16a-4326-9576-84d5e44c97fd.jsonl`
- todos at build time:
- `replace-venv-branch`: completed
- `update-comments`: completed
- `add-tests`: completed
