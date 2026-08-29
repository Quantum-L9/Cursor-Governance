---
name: Governance Lint/Mypy Remediation
overview: No open PRs exist on Quantum-L9/Cursor-Governance overlap with this work, but the local working tree already carries unrelated uncommitted changes from an earlier session; commit those separately, then remediate the freshly re-measured 77 ruff errors and 354 mypy errors (25 files) in `$HOME/.cursor-governance`.
todos:
  - id: phase0-commit-split
    content: Split the 16 pending files into 3 commits (env pinning / docs+CI / dead-import fix) and push to Quantum-L9/Cursor-Governance
    status: cancelled
  - id: phase1-ruff-bugs
    content: "Fix 9 ruff correctness bugs: F401 x4, F841 x1, E722 x4"
    status: completed
  - id: phase2-ruff-style
    content: "Clear 68 ruff style errors: E501 x51, E402 x13, E741 x2, UP022 x2"
    status: completed
  - id: phase3-mypy-lock
    content: Add mypy as locked dev dependency + [tool.mypy] with python_version=3.12 pin; update Makefile lint target
    status: completed
  - id: phase4-guard-pattern
    content: Add _require_state() guard to the 6 sibling executors, resolving 288 union-attr errors + 14 co-located bugs
    status: in_progress
  - id: phase5-mypy-stragglers
    content: "Fix remaining ~52 mypy errors: validate_run_report.py, var-annotated x11, langgraph stub mismatches, Optional[str] guards, state.py:55, misc singles"
    status: pending
  - id: phase6-validate-close
    content: Re-run ruff+mypy to confirm zero debt, update TODO.md, re-verify governance wiring, then commit/push only on explicit request
    status: pending
isProject: false
---

## Research findings (this session)

**No open PRs.** `gh pr list --repo Quantum-L9/Cursor-Governance --state open` returns empty. The last 9 PRs (hygiene archiving, Graphiti migration, CodeQL, Copilot review, ORG_INVARIANTS canonicalization) are all merged/closed already, and local `main` is caught up (one local commit `268608b` ahead, already pushed... actually unpushed, see below).

**Working tree has 16 changed files, not 5.** All share the identical mtime `Jul 20 00:23:27`, confirming they landed together via the earlier background `governance_sync.sh` (a stash-pop after pulling PRs #3–#10), not an active concurrent process (verified: no running processes touch the repo).

- **5 files are mine (env pinning), unchanged from where I left them:** [pyproject.toml](pyproject.toml), [Makefile](Makefile), [.pre-commit-config.yaml](.pre-commit-config.yaml), [ops/hooks/session_start_bootstrap.sh](ops/hooks/session_start_bootstrap.sh), `uv.lock` (untracked). Confirmed: no `mypy` dependency added yet, no `[tool.mypy]` section yet — Phase 3 below is still needed.
- **3 files came from the earlier/other session, unrelated to my edits:** [TODO.md](TODO.md) and [CHANGELOG.md](CHANGELOG.md) already document a "mypy debt (354 errors/25 files)" section and the addition of `.github/workflows/l9-lint-test.yml` (untracked, adopted from `l9-ci-core` v2, runs `mypy .` unscoped in CI → CI will be red until fixed).
- **7 files are an unrelated, already-complete fix:** [workflows/dags/inspect_dag.py](workflows/dags/inspect_dag.py), [workflows/harvest_deploy.py](workflows/harvest_deploy.py), and 5 files under `workflows/nodes/` remove `from core.decorators import must_stay_async` + its `@must_stay_async(...)` usages. Verified `core/decorators.py` does not exist anywhere in the tree (not even archived) — this was a broken import (real `ImportError` at runtime, not just lint noise), and the fix is clean/complete (zero remaining references anywhere).

**Re-measured error counts (authoritative, superseding my earlier stale plan numbers):**

- `uv run ruff check .` → **77 errors**, exactly matching `TODO.md`'s already-tracked count: `E501`×51, `E402`×13, `E722`×4, `F401`×4, `E741`×2, `UP022`×2, `F841`×1.
- `mypy . --ignore-missing-imports --exclude '_archived|_archive|archive|archived|C_GOV_FILES|current_work'` → **354 errors in 25 files**, also matching `TODO.md` exactly. Breakdown by code: `union-attr`×295, `attr-defined`×18, `var-annotated`×11, `assignment`×7, `index`×6, `arg-type`×6, `syntax`×4, `return-value`×4, `misc`×3.
- Of the 295 `union-attr` errors, **288 sit in the same 6 sibling executor files** (`workflows/{gmp,harvest,migrate,wire,lint_fix,use_harvest}_executor.py`, 61/55/52/51/45/38 errors respectively) — all `Item "None" of "Optional[XState]" has no attribute "..."`, the exact pattern the `_require_state()` guard fixes. The remaining 7 `union-attr` are in `skills/l9-pr-remediation/scripts/validate_run_report.py`.
- **New finding:** 8 of the 18 `attr-defined` errors are `Module "datetime" has no attribute "UTC"` and 4 of the `syntax` errors are `X | Y syntax requires Python 3.10` — both classes disappear for free once `[tool.mypy] python_version = "3.12"` is set (Phase 3), since mypy currently has no version pin and is defaulting to an older stdlib target.

## Execution plan

### Phase 0 — Commit the 16 pending files as 3 separate commits (per your split-by-concern choice)
1. `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`, `ops/hooks/session_start_bootstrap.sh`, `uv.lock` → commit: environment pinning (Python 3.12 + `uv`).
2. `TODO.md`, `CHANGELOG.md`, `.github/workflows/l9-lint-test.yml` → commit: docs/CI adopted from the earlier session.
3. The 7 `workflows/*.py` files → commit: remove dead `core.decorators.must_stay_async` import/usage (fixes a real `ImportError`).
4. Push all 3 to `Quantum-L9/Cursor-Governance` `main`.

### Phase 1 — Fix 9 real ruff correctness bugs
`F401`×4 (unused imports — verify each isn't an intentional optional-import probe before removing), `F841`×1 (unused variable), `E722`×4 (bare `except:` → narrow to specific exception types per file context).

### Phase 2 — Clear 68 ruff style errors
`E501`×51 (line-too-long — wrap/reflow), `E402`×13 (import-not-at-top — usually deliberate `__future__`/sys.path patterns in these workflow files, verify before moving), `E741`×2 (ambiguous variable name), `UP022`×2 (replace-stdout-stderr). Auto-fix where `ruff check . --fix` is safe; hand-fix the rest.

### Phase 3 — Lock mypy into the environment
Add `mypy` to `pyproject.toml` `[project.optional-dependencies].dev`, re-run `uv sync --extra dev` (regenerates `uv.lock`), add:
```toml
[tool.mypy]
python_version = "3.12"
exclude = "(_archived|_archive|archive|archived|C_GOV_FILES|current_work)"
ignore_missing_imports = true
```
Update `Makefile`'s `lint` target to also run `uv run mypy .`. Re-measure — expect the 8 `datetime.UTC` + 4 `X | Y` syntax errors to disappear immediately (12 of 354 gone before touching app code).

### Phase 4 — `_require_state()` guard pattern across the 6 sibling executors
Add a private helper to each of `workflows/{gmp,harvest,migrate,wire,lint_fix,use_harvest}_executor.py`:
```python
def _require_state(self) -> XState:
    if self.state is None:
        raise RuntimeError("<Executor> used before state initialized")
    return self.state
```
Replace direct `self.state.attr` access with a local `state = self._require_state()` at the top of each method, then `state.attr`. This resolves the 288 `union-attr` errors. While in each file, also fix the smaller number of non-`union-attr` errors mypy reports there (e.g. `gmp_executor.py:588`'s list-comprehension type mismatch) — 14 total across the 6 files.

### Phase 5 — Remaining ~52 mypy stragglers
- `skills/l9-pr-remediation/scripts/validate_run_report.py` (7 `union-attr`) — same guard pattern if it has an analogous `Optional[State]` shape, else a targeted fix.
- `var-annotated`×11 — explicit `list[...]`/`dict[...]` annotations (`workflows/runner.py`×5, `workflows/dags/gmp/nodes/core.py`, `ops/scripts/tool_pattern_extractor.py`, etc.).
- `workflows/dags/inspect_dag.py` + `workflows/harvest_deploy.py` — langgraph `StateGraph`/`CompiledStateGraph`/`.ainvoke` stub mismatches; check installed `langgraph` version against what the type stubs expect before treating as app bugs.
- `workflows/nodes/validate.py` (4) + `workflows/nodes/report.py` (1) — guard unguarded `Optional[str]` before indexing/passing to `_run_shell`.
- `workflows/state.py:55` — fix the reducer function's incompatible redefinition signature.
- `workflows/dags/gmp/nodes/core.py` (6), `ops/scripts/operational-oversight.py` (2 non-syntax), `intelligence/reasoning/reasoning-snapshot-generator.py` (remaining non-syntax/non-datetime ones) — individual `assignment`/`arg-type`/`attr-defined` fixes per TODO.md's existing notes.

### Phase 6 — Validate and close the loop
Re-run `uv run ruff check .` and `uv run mypy .` (now via the locked venv), confirm 0 errors or explicitly record any accepted/deferred debt. Update `TODO.md` to reflect the resolved state. Re-run `ops/scripts/check_governance_wiring.sh` to confirm governance wiring still passes. Commit + push (only when you explicitly say so, per no-auto-push rule).
