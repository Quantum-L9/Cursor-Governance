# Python Contract Alignment — Validation Report

Contract: `CURSOR-GOVERNANCE-PR-PYTEST-v1.0.0`
Branch: `claude/python-contract-alignment`
Baseline: `3c9ba5c675b91e5d1d2b20d777ff14fcb669a48c` (local `main` HEAD at start)

All evidence below is captured from commands actually executed in this
session. Exit codes and test counts are the tools' own output, not estimates.

---

## 0. Baseline preflight (before any change)

Environment: `uv 0.8.17`; uv-managed CPython 3.12 (`.venv`); host python 3.11.

| Command | Result |
|---|---|
| `git rev-parse HEAD` | `3c9ba5c675b91e5d1d2b20d777ff14fcb669a48c` |
| `git merge-base --is-ancestor 3c9ba5c… HEAD` | exit 0 (descends from baseline) |
| `uv sync --locked --extra dev` | exit 0 |
| `uv lock --check` | exit 0 (`Resolved 78 packages`) |
| `uv run --no-build ruff check .` | exit 0 (`All checks passed!`) |
| `uv run --no-build ruff format --check .` | exit 0 (`707 files already formatted`) |
| `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | exit 0 (repo suite `77 passed, 16 subtests`; Claude suite `13 passed`) |

Baseline blob hashes matched `EVIDENCE_BASELINE.md` exactly for
`pyproject.toml`, `Makefile`, `.github/workflows/l9-lint-test.yml`,
`ops/scripts/run_pytest_suites.sh`, `requirements.txt`,
`subagent-generated-data/tests/run_wave3_tests.py`, and Program Execution
`VALIDATION.md`.

Previously-omitted suites verified GREEN independently before wiring (halt
condition guard):

- `python subagent-generated-data/tests/run_wave3_tests.py` → exit 0 (`Ran 3 tests … OK`, all four discovered suites pass).
- Program Execution documented sequence → all exit 0:
  - `validate_controller.py . --mode template` → `PASS`
  - `python -m unittest discover -s scripts/tests -p test_*.py` → `Ran 14 tests … OK`
  - `run_negative_tests.py` → `{"status": "PASS", "fixtures": [...]}`

## Upstream pin re-check (before editing)

Live `Quantum-L9/l9-ci-sdk` `requirements-ci.txt` blob is unchanged from the
baseline evidence (`c2fdb13c…`). Confirmed pins: `ruff==0.16.0`,
`mypy==2.3.0`, `types-PyYAML==6.0.12.20260724`,
`types-jsonschema==4.26.0.20260518`, `pytest==9.1.1`. No unrelated upgrade
performed. `rfc3339-validator` is **not** added: a repository-wide search for
`FormatChecker` / `format_checker` / `rfc3339` found matches only under
`.venv/`, so no Cursor-Governance code path invokes JSON Schema date-time
format checking — the brief forbids adding it without that evidence.

---

## Commit 1 — `chore(python): lock test contract dependencies`

SHA: `a48128109eedb927e421cac4a7a57e8d94961c65`
Files: `pyproject.toml`, `requirements.txt`, `uv.lock`

Dependency diff (direct):

- `[project.optional-dependencies].dev` += `pytest-xdist==3.8.0`,
  `pytest-timeout==2.4.0`, `types-jsonschema==4.26.0.20260518`.
- `requirements.txt` mirrors the same three exact pins by normalized name.
- `uv.lock` regenerated with `uv lock` (never hand-edited).

`uv.lock` delta (text diff of the `-diff` lock): added `pytest-xdist`
`3.8.0`, `pytest-timeout` `2.4.0`, `types-jsonschema` `4.26.0.20260518`, and
`execnet` `2.1.2` (pytest-xdist's required transitive dep). No package
removed; no existing package version changed. `[tool.uv] package = false`
preserved; no runtime range changed.

Checkpoint:

| Command | Result |
|---|---|
| `uv sync --locked --extra dev` | exit 0 (`Installed 4 packages`: execnet, pytest-timeout, pytest-xdist, types-jsonschema) |
| `uv lock --check` | exit 0 (`Resolved 82 packages`) |
| `uv run python -c "import xdist, pytest_timeout; import jsonschema"` | exit 0 |
| `uv run python -c "import importlib.util; assert importlib.util.find_spec('jsonschema')"` | exit 0 |
| `git diff --check` | exit 0 (clean) |

---

## Commit 2 — `feat(test): add canonical Python suite registry and runner`

SHA: `99b7b07bff8d0a20135320de9ba1c43009d9c743`
Files: `ops/config/python-contract.json`,
`ops/scripts/run_python_test_suites.py`,
`ops/scripts/run_pytest_suites.sh`, `pyproject.toml` (topology only)

### Suite registry summary

Declared once in `ops/config/python-contract.json`
(`schema_version 1.0.0`), executed in this deterministic order:

| # | id | kind | working dir | PYTHONPATH | allow_exit_5 |
|---|---|---|---|---|---|
| 1 | `repo-root` | pytest | `.` | `${REPO_ROOT}` | true |
| 2 | `claude-code-autonomy` | pytest | `.` | `environment/claude-code` | true |
| 3 | `subagent-generated-data-wave3` | command | `.` | — | false |
| 4 | `program-execution-controller` | command_sequence | `…/program-execution-controller-template` | — | false |

- `repo-root` ignores the three separately-owned active suites
  (`environment/claude-code/autonomy`, `subagent-generated-data/tests`,
  `…/program-execution-controller-template/scripts/tests`); non-test
  false-positive ignores remain in pyproject `addopts`.
- `claude-code-autonomy` targets `…/autonomy/tests` with `-o addopts=` to
  prevent package shadowing.
- `subagent-generated-data-wave3` runs `run_wave3_tests.py`; any nonzero
  fails the runner.
- `program-execution-controller` runs the documented fresh-process sequence
  and is never collected under xdist.

Pytest topology moved out of `addopts` (active-suite ignores removed; only
non-test false-positives remain). Obsolete "2 test_*.py files" comment
replaced.

Checkpoint:

| Command | Result |
|---|---|
| `uv run --no-build ruff check ops/scripts/run_python_test_suites.py` | exit 0 (`All checks passed!`) |
| `uv run --no-build ruff format --check …` | exit 0 |
| `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | exit 0; all four suites PASS |

Per-suite result (local profile via wrapper): `repo-root: PASS`,
`claude-code-autonomy: PASS`, `subagent-generated-data-wave3: PASS`,
`program-execution-controller: PASS`; `overall: PASS (exit 0)`.

---

## Commit 3 — `test(governance): enforce Python contract drift checks`

Files: `ops/scripts/validate_python_contract.py`,
`ops/scripts/test_python_contract.py`, this report.

`validate_python_contract.py` is read-only and fail-closed. It proves:
registry structure + repo-confined paths; unique/deterministic suite order;
every active-suite ignore has exactly one other registry owner; owned paths
exist; non-test exclusions carry reasons; the shell wrapper delegates and
holds no topology; CI invokes the canonical runner exactly once; CI has no
floating `pip install` of the test plugins; CI bootstraps with
`uv sync --locked --extra dev`; the dev extra pins the required test
distributions; `requirements.txt` mirrors every dev pin by normalized name;
`import_map` roots resolve to declared runtime/dev distributions; and
`uv.lock` exists (`uv lock --check` remains the authoritative freshness
check). The canonical runner calls this validator before executing any suite,
so `make test`, `make pr-full`, and CI all receive the drift gate through the
existing wrapper with no Makefile change.

Checkpoint:

| Command | Result |
|---|---|
| `uv run --no-build ruff check validate_python_contract.py test_python_contract.py` | exit 0 |
| `uv run --no-build ruff format --check …` | exit 0 |
| `uv run python ops/scripts/test_python_contract.py` | exit 0 (`Ran 21 tests … OK`) |
| `uv run python ops/scripts/validate_python_contract.py` | exit 0 (`no drift`) |
| `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | exit 0; all four suites PASS |

`test_python_contract.py` covers (network-free, temp fixtures only): valid
registry; duplicate suite id; path escape; unknown suite kind; unsupported
substitution; deterministic order; missing generated-data owner; missing
Program Execution owner; non-test exclusion without reason; unresolved
import_map; absent required dev tool; pyproject/requirements pin mismatch;
forbidden floating CI install; CI bypassing the runner; wrapper embedded
topology; missing lockfile; PYTHONPATH isolation (root vs Claude); user
pytest-arg forwarding only to allowed suites; command suite ignoring user
args; exact nonzero exit propagation; exit-5 rejected by default and accepted
only when configured.

---

## Commit 4 — `ci(test): consume the canonical locked runner`

File: `.github/workflows/l9-lint-test.yml`, plus this final evidence.

`.github/workflows/l9-lint-test.yml` test job rewired:

- Kept: immutable event-revision checkout, pinned `actions/setup-python` SHA,
  `permissions: contents: read`, concurrency group, and job timeouts.
- Kept `uv sync --locked --extra dev` as the environment bootstrap.
- Removed the fallback `python -c "import xdist" || pip install pytest-xdist`
  and `pytest-timeout` floating installs.
- Replaced the duplicated root/Claude shell orchestration with one line:
  `uv run --no-build python ops/scripts/run_python_test_suites.py --profile ci`.
- Coverage artifact generation and the advisory `--cov-fail-under=0` threshold
  are preserved through the registry's `repo-root` CI profile (verified:
  `coverage.xml` is written, `TOTAL … 33%`, job exits 0).
- Dropped now-unused `TEST_DIR` / `COVERAGE_THRESHOLD` workflow env (owned by
  the registry CI profile); `SOURCE_DIR` retained for the lint job's mypy step.
  The obsolete two-test workflow comment was removed.

---

## Final validation (whole tree, all four commits in place)

Run order and results:

| # | Command | Result |
|---|---|---|
| 1 | `uv sync --locked --extra dev` | exit 0 |
| 2 | `uv lock --check` | exit 0 |
| 3 | `uv run python ops/scripts/test_python_contract.py` | exit 0 (`Ran 21 tests … OK`) |
| 4 | `uv run python ops/scripts/validate_python_contract.py` | exit 0 (`no drift`) |
| 5 | `bash ops/scripts/run_pytest_suites.sh --tb=short -q` | exit 0 (all four suites PASS) |
| 6 | `uv run --no-build ruff check .` | exit 0 |
| 7 | `uv run --no-build ruff format --check .` | exit 0 |
| 8 | `make pr-check` | exit 0 (`RESULT: PASS — local PR gate clean`) |
| 9 | `git diff --check` | exit 0 |
| 10 | `git status --short` | only tracked in-scope changes |

CI-profile run (as GitHub Actions invokes it,
`run_python_test_suites.py --profile ci`): `repo-root` `84 passed, 16
subtests` + `coverage.xml` written; `claude-code-autonomy` `13 passed`;
`subagent-generated-data-wave3` PASS; `program-execution-controller` PASS
(`validate_controller` PASS, `unittest` `Ran 14 tests … OK`, negative tests
`status: PASS`); `overall: PASS`.

`make pr-check` detail: pre-commit changed-files gate + canonical runner all
green; security gate `pass=3 fail=0 skip=1` (bandit / semgrep / pip-audit
PASS; gitleaks SKIP — not installed on this host, advisory). mypy advisory
(unchanged policy).

### Changed-file scope proof (vs baseline `3c9ba5c…`)

```
A  ops/config/python-contract.json
A  ops/scripts/run_python_test_suites.py
A  ops/scripts/test_python_contract.py
A  ops/scripts/validate_python_contract.py
A  reports/python-contract-alignment-validation.md
M  .github/workflows/l9-lint-test.yml
M  ops/scripts/run_pytest_suites.sh
M  pyproject.toml
M  requirements.txt
M  uv.lock
```

Exactly the ten allowed paths; no preserved runtime or governance file
changed behavior.

### Behavior-preservation notes

- Root pytest count moved 77 → 84: the 14 Program Execution `scripts/tests`
  previously collected under root xdist now run through the documented
  fresh-process `program-execution-controller` sequence (validate_controller +
  unittest discover + negative tests, strictly more coverage than before), and
  the 21 new contract tests are collected at root. No test was dropped; the
  previously-omitted Wave 3 suite now runs.
- `[tool.uv] package = false`, runtime dependency ranges, the build-system
  declaration, the Makefile, and all preserved autonomy / memory /
  generated-data / Program Execution runtimes are unchanged.

### Residual risks / UNKNOWNs

- `gitleaks` and `pre-commit` are not preinstalled on this host. `pre-commit`
  was installed locally to run `make pr-check` (it passed); `gitleaks` is
  skipped and advisory — CI and a fully-provisioned developer host run it.
  Neither affects the committed change.
- Remote required-check / branch-protection contexts are repository settings
  outside the tree and were not inspected (out of scope; halt boundary).

---

## Operator handoff

Local work is complete and every gate is green. Per the contract halt
boundary, no push / PR / merge / tag / release / settings change was
performed. The operator decides whether to push and open a pull request.

