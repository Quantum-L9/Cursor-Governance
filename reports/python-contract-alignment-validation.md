# Python Contract Alignment — Validation Report

Contract: `CURSOR-GOVERNANCE-PR-PYTEST-v1.0.0`
Branch: `claude/python-contract-alignment`
Baseline: `3c9ba5c675b91e5d1d2b20d777ff14fcb669a48c` (descendant confirmed)
Remote mutation: **prohibited** — local commits only; no push / PR / merge / tag / settings change.

This report records exact commands, exit codes, and tool-reported counts. Nothing is
marked passed without captured evidence. Final consolidated evidence is appended by
Commit 4.

---

## Baseline preflight (before any change)

All run from the repository root against the baseline tree.

| Command | Exit | Result |
|---|---|---|
| `uv sync --locked --extra dev` | 0 | environment resolved (78 packages) |
| `uv lock --check` | 0 | lockfile in sync |
| `uv run --no-build ruff check .` | 0 | All checks passed (4 pre-existing benign `# noqa` warnings in `workflows/harvest_executor.py`, unrelated) |
| `uv run --no-build ruff format --check .` | 0 | 707 files already formatted |
| `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | 0 | repo suite **77 passed, 16 subtests**; Claude autonomy **13 passed** |
| `git merge-base --is-ancestor 3c9ba5c… HEAD` | 0 | HEAD descends from baseline |

Independent confirmation that the two previously-omitted suites were already green
at baseline (halt-condition guard — nothing pre-broken is being wired in):

| Suite | Command | Exit | Result |
|---|---|---|---|
| Wave 3 | `python subagent-generated-data/tests/run_wave3_tests.py` | 0 | conformance/routing/negative/golden all OK |
| Program Execution | `validate_controller.py . --mode template` | 0 | PASS |
| Program Execution | `python -m unittest discover -s scripts/tests -p 'test_*.py'` | 0 | Ran 14 tests, OK |
| Program Execution | `run_negative_tests.py` | 0 | status PASS (controller_structure, remote_authority_denial) |

Upstream pin re-check (`Quantum-L9/l9-ci-sdk` `requirements-ci.txt` @ `a012f89`): pins
unchanged from the baseline evidence — `ruff==0.16.0`, `mypy==2.3.0`,
`types-PyYAML==6.0.12.20260724`, `types-jsonschema==4.26.0.20260518`, `pytest==9.1.1`.
`rfc3339-validator` is present upstream **for the SDK's own schema tests**; a repo-wide
scan confirms **no Cursor-Governance code path passes a `format_checker` to
`Draft202012Validator`**, so date-time format checking is never invoked here and
`rfc3339-validator` is intentionally NOT added (per contract).

---

## Commit 1 — `chore(python): lock test contract dependencies`  (`fee4b92`)

Files: `pyproject.toml`, `requirements.txt`, `uv.lock`.

Additions (exact pins, mirrored in both manifests):
`pytest-xdist==3.8.0`, `pytest-timeout==2.4.0`, `types-jsonschema==4.26.0.20260518`.

Lockfile diff (text diff of the binary-marked `uv.lock` against baseline): exactly four
new package blocks — the three direct additions plus the resolver-required transitive
`execnet==2.1.2` (dependency of pytest-xdist). **Zero** removals; **zero** version
changes to pre-existing packages.

Checkpoint:

| Command | Exit | Result |
|---|---|---|
| `uv sync --locked --extra dev` | 0 | OK |
| `uv lock --check` | 0 | OK |
| `uv run python -c "import xdist, pytest_timeout; import jsonschema"` | 0 | OK |
| `uv run python -c "import importlib.util; assert importlib.util.find_spec('jsonschema')"` | 0 | OK |
| `git diff --check` | 0 | no whitespace errors |

---

## Commit 2 — `feat(test): add canonical Python suite registry`  (`48b1a95`)

Files: `ops/config/python-contract.json` (new), `ops/scripts/run_python_test_suites.py`
(new), `ops/scripts/run_pytest_suites.sh` (reduced to wrapper), `pyproject.toml`
(topology comments + `addopts` trimmed to non-test false positives only).

Suite registry (declared once, executed in order):

| # | id | kind | isolation | profiles |
|---|---|---|---|---|
| 1 | `repo-root` | pytest | `PYTHONPATH=${REPO_ROOT}`; ignores the 3 active suites | local forwards args; ci = xdist + root coverage xml/term + `--timeout=300` + advisory `--cov-fail-under=0` |
| 2 | `claude-code-autonomy` | pytest | `PYTHONPATH=${REPO_ROOT}/environment/claude-code`; `-o addopts=` | ci = xdist + `--timeout=300`, no root coverage |
| 3 | `subagent-generated-data-wave3` | command | opaque `run_wave3_tests.py`; no pytest args appended | any nonzero fails the runner |
| 4 | `program-execution-controller` | command_sequence | fresh processes, **not** xdist | validate → unittest discover → negative tests; stop on first failure |

Coverage-move proof (no coverage lost, only relocated to fresh-process isolation):

- Baseline root pytest collected **77** tests including the 14
  `…/program-execution-controller-template/scripts/tests/test_*.py`.
- After registry: root collects **63** (the 14 controller tests are now ignored by
  root and owned by suite #4); `core/tests/test_pair_alignment.py` (3) stays in root.
- 63 (root) + 14 (controller sequence) = 77 preserved.

Checkpoint:

| Command | Exit | Result |
|---|---|---|
| `uv run --no-build ruff check ops/scripts/run_python_test_suites.py` | 0 | All checks passed |
| `uv run --no-build ruff format --check …` | 0 | already formatted |
| `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | 0 | all four suites PASS (repo-root 63, claude 13, wave3 OK, controller 14+validate+negative) |

---

## Commit 3 — `test(governance): enforce Python contract drift checks`  (pending SHA below)

Files: `ops/scripts/validate_python_contract.py` (new), `ops/scripts/test_python_contract.py`
(new), `reports/python-contract-alignment-validation.md` (this file).

The drift validator is read-only and fail-closed. It enforces the 13 substantive
checks from the mandate (structure/confinement, unique+ordered ids, ignore→single-owner,
owned-paths-exist, non-test-exclusion reasons, wrapper-has-no-topology, CI-runner-once,
no-floating-CI-installs, CI-locked-sync, dev-extra-pins, requirements-mirror,
import-map-resolves, uv.lock-present). External `uv lock --check` remains the
authoritative lock validation. The validator never edits repository files.

Checkpoint:

| Command | Exit | Result |
|---|---|---|
| `uv run --no-build ruff check …validate_python_contract.py …test_python_contract.py` | 0 | All checks passed |
| `uv run --no-build ruff format --check …` | 0 | 2 files already formatted |
| `uv run python ops/scripts/test_python_contract.py` | 0 | **Ran 23 tests, OK** |
| `uv run python ops/scripts/validate_python_contract.py` | **1** | 10/11 groups PASS; **1 FAIL: CI runner check** — expected and by-design (CI still on the pre-alignment topology; resolved in Commit 4). The failure demonstrates the fail-closed detector correctly identifying the outstanding drift. |
| `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | 0 | all four suites PASS (repo-root now **86** = 63 + 23 validator tests; claude 13) |

### Sequencing note (single, deliberate)

The fail-closed validator checks the CI workflow. A validator that enforces
`checks 7–9` cannot report green while `.github/workflows/l9-lint-test.yml` still
carries the pre-alignment topology. Per the mandate's commit plan the workflow is
rewritten in **Commit 4**, and the runner→validator wiring lands there too. Therefore:

- Every commit's **suite** checkpoint (`run_pytest_suites.sh`) is green, including Commit 3.
- Commit 3's standalone validator intentionally reports the one CI drift item — that is
  the detector working, not a regression.
- Commit 4 rewrites CI and wires the runner to consume the validator; the standalone
  validator then reports **all green**, recorded below.

Validator-logic correctness does not depend on the real repo's CI state: it is proven
green by the 23 fixture-based tests in `test_python_contract.py`, which exercise every
rejection path against temporary fixture repositories (offline, no real-tree mutation).

---

## Changed-file scope (through Commit 3)

Created: `ops/config/python-contract.json`, `ops/scripts/run_python_test_suites.py`,
`ops/scripts/validate_python_contract.py`, `ops/scripts/test_python_contract.py`,
`reports/python-contract-alignment-validation.md`.
Modified: `pyproject.toml`, `requirements.txt`, `uv.lock`,
`ops/scripts/run_pytest_suites.sh`.
Pending (Commit 4): `.github/workflows/l9-lint-test.yml`, `ops/scripts/run_python_test_suites.py`
(validator wiring), this report (final evidence).

All within the contract allowlist. No preserved runtime/governance file behavior changed.

---

## Commit 4 — `ci(test): consume the canonical locked runner`  (pending SHA below)

Files: `.github/workflows/l9-lint-test.yml` (test job rewired), `ops/scripts/run_python_test_suites.py`
(runner now calls the drift validator before any suite), `reports/python-contract-alignment-validation.md`
(this final evidence).

Workflow test job changes (lint job untouched; immutable event-revision checkout, pinned
external action SHAs, `permissions: contents: read`, concurrency, and timeouts all preserved):

- Bootstrap keeps `uv sync --locked --extra dev`.
- **Removed** the floating fallback installs (`… || pip install pytest-xdist`,
  `… || pip install pytest-timeout`) — these are now locked in the dev extra + uv.lock.
- **Replaced** the duplicated root/Claude pytest shell block (≈35 lines) with a single
  invocation: `uv run --no-build python ops/scripts/run_python_test_suites.py --profile ci`.
- Dropped the now-unused `TEST_DIR` / `COVERAGE_THRESHOLD` env vars and the obsolete
  "2 test files" comment; suite topology, coverage output, and the advisory 0% threshold
  now live in the registry's root ci profile. `SOURCE_DIR` (lint mypy) is retained.

Runner wiring: `main()` runs `validate_python_contract.py` (fail-closed) before executing
any suite, so `make test`, `make pr-full`, and CI all receive the drift gate through the
one runner. A missing validator fails closed.

CI-path proof (`--profile ci`, exactly what the workflow now runs): drift validator all
green → repo-root (xdist) **86 passed, 16 subtests**, `coverage.xml` written → claude
**13 passed** → wave3 PASS → controller sequence PASS → overall PASS, exit 0.

---

## Final validation (whole tree, post-Commit-4)

Run from the repository root in this order:

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | `uv sync --locked --extra dev` | 0 | environment resolved (82 packages) |
| 2 | `uv lock --check` | 0 | lockfile in sync |
| 3 | `uv run python ops/scripts/test_python_contract.py` | 0 | **Ran 23 tests, OK** |
| 4 | `uv run python ops/scripts/validate_python_contract.py` | 0 | **all 11 drift check groups PASS** |
| 5 | `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | 0 | validator PASS → 4 suites PASS (repo-root 86 + 16 subtests, claude 13, wave3, controller) |
| 6 | `uv run --no-build ruff check .` | 0 | All checks passed |
| 7 | `uv run --no-build ruff format --check .` | 0 | 711 files already formatted |
| 8 | `make pr-check` | 0 | **PASS** — suites green via runner; security gate pass=3 fail=0 skip=1 (bandit/semgrep/pip-audit PASS; gitleaks SKIP — brew CLI not on this sandbox PATH, non-blocking; mypy advisory) |
| 9 | `git diff --check` | 0 | no whitespace errors |
| 10 | `git status --short` | — | only tracked contract changes; no stray artifacts (ci-profile `coverage.xml`/`.coverage` removed) |

Per-suite results (both profiles): `repo-root` PASS, `claude-code-autonomy` PASS,
`subagent-generated-data-wave3` PASS, `program-execution-controller` PASS.

Drift validator: **PASS** (11/11 groups) against the aligned tree.

---

## Operator handoff

- **Branch**: `claude/python-contract-alignment` (local only; not pushed)
- **Baseline**: `3c9ba5c675b91e5d1d2b20d777ff14fcb669a48c` (HEAD descends from it)
- **Commits** (in order):
  1. `fee4b92` chore(python): lock test contract dependencies
  2. `48b1a95` feat(test): add canonical Python suite registry
  3. `d4e6126` test(governance): enforce Python contract drift checks
  4. `<commit-4>` ci(test): consume the canonical locked runner  *(this commit)*
- **Changed files (9)**: `pyproject.toml`, `requirements.txt`, `uv.lock`,
  `ops/config/python-contract.json`, `ops/scripts/run_python_test_suites.py`,
  `ops/scripts/run_pytest_suites.sh`, `ops/scripts/validate_python_contract.py`,
  `ops/scripts/test_python_contract.py`, `.github/workflows/l9-lint-test.yml`,
  plus `reports/python-contract-alignment-validation.md` (evidence).
- **Dependency diff**: +3 direct exact pins (`pytest-xdist==3.8.0`,
  `pytest-timeout==2.4.0`, `types-jsonschema==4.26.0.20260518`) mirrored in
  pyproject + requirements; uv.lock +those +transitive `execnet==2.1.2`; no other
  dependency moved. `rfc3339-validator` intentionally not added.
- **Suite registry**: 4 suites (repo-root pytest, claude-code-autonomy pytest,
  subagent-generated-data-wave3 command, program-execution-controller command_sequence).
- **Validator**: 11/11 drift check groups PASS.
- **`make pr-check`**: PASS.
- **Residual risks / UNKNOWNs**:
  - `gitleaks` is not installed in this sandbox; its security scan was SKIP (non-blocking).
    On CI/dev machines with gitleaks present it runs normally.
  - `pre-commit` was installed into the local venv only to exercise `make pr-check`; it is
    not a repo dependency and did not alter `uv.lock`, pyproject, or the worktree.
  - CI green cannot be observed locally — it is asserted by running the exact ci-profile
    command the workflow invokes. Real GitHub Actions status is confirmable only after a push.
- **Halt**: stopped after local commits + green gates. **No push, PR, merge, tag, release,
  or repository-settings change performed** (remote mutation prohibited by contract).
