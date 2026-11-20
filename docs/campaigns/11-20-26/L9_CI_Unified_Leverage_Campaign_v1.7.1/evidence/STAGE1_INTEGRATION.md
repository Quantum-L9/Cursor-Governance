# Stage 1 integration and enforcement boundary (lane I1, lane G1)

Run by the CTO session on 2026-11-20 in disposable clones. Nothing here was merged or pushed.

## Combined subject

| Owner | Pull requests | Head tested |
|---|---|---|
| `Quantum-L9/l9-ci-sdk` | #118, #119, #120 (stacked; #118 sits on the other CTO's #117) | #120 `c815c42e954ed1b65d9223580761ed5f8e193035` |
| `Quantum-L9/l9-ci-core` | #283, #286, #287 (stacked) merged locally with #285 | #287 `b284bfc7` + #285 `17e4b7aa` = local `14f540f` |

## Results

| Check | Run 1 (#287 `5b5ab0f3`) | Run 2 (#287 `b284bfc7`, after CTO REMEDIATE 283) |
|---|---|---|
| SDK `ruff check`, `ruff format --check` | PASS | unchanged head |
| SDK `mypy l9_ci` | no issues, 92 files | unchanged head |
| SDK `pytest -q` | 632 passed | unchanged head |
| Core `make validate` | PASS | PASS |
| Core `make check` (toolchain, ruff, mypy) | PASS | PASS |
| Core full suite (`unittest discover -s tests`, the `test-deep` recipe) | **1 error** (T34) | 1165 tests OK, 1 skipped |
| Core PR subset (the 22 `REPO_TEST_MODULES`) | NOT RUN | 351 tests OK, 1 skipped |
| Core main baseline, full suite | 1075 tests OK, 1 skipped | — |

T34: `tests/governance/test_ci_runtime_invariants.py` imported top-level `tools`, which `tests/tools` shadows under discovery. PR CI does not run that invocation; the nightly full suite would have gone red after merge. Repaired on #283 by lane L2 and re-verified in run 2.

## Cross-owner check: SDK inventory into Core planner

`l9-ci providers inventory --format json` from SDK #120, fed to Core's `.github/actions/plan-required-instances/plan.py` with `semgrep` required:

| Subject | Planned targets | Required count |
|---|---|---|
| mixed Python + TypeScript fixture | `semgrep:language:python`, `semgrep:language:typescript` | 2 |
| Python-only fixture | `semgrep:language:python` | 1 |
| no supported code | none | 0 |
| Core itself | `semgrep:language:python` | 1 |
| CEG, EIE, Cursor-Governance (main) | `semgrep:language:python` | 1 each |

Cursor-Governance's inventory reports `javascript` and `shell` as `unsupported` (T32, lane L1d).

Not yet proven: the aggregate on a live hosted run of the combined subject, which needs Core's SDK pin to advance after merge (`CURSOR_CANARY.md` Gate 0, `BLOCKED_ON_PROMOTION`).

## Enforcement boundary (L9-CI-CORE-006 evidence)

Read from each repository's effective branch rules. The organization ruleset listing itself is not reachable from this session (`UNKNOWN` beyond what the per-repository view shows).

| Repository | Default branch | Organization ruleset 21895545 (`org-ci.yml@refs/heads/main`, requires `Analyze (central Core)`) | Repository ruleset required checks |
|---|---|---|---|
| Cursor-Governance | main | bound | 20855699: Lint and Type Check, Test Suite, Root-file append-only gate, governance-self-check, repo-hygiene |
| l9-ci-core | main | bound | none |
| l9-ci-sdk | main | bound | 20147356: Lint, type-check, test, coverage |
| Cognitive.Engine.Graphs | main | bound | none |
| Enrichment.Inference.Engine | main | bound | none |
| .github | main | bound | none |
| cryptoxdog/IB-Odoo_19 | Staging | **not bound** | 17291607: Ruff Lint & Format, Static Analysis, Pure Python Tests, CI Gate Result |

`cryptoxdog/IB-Odoo_19` is outside the Quantum-L9 required workflow, which is the negative case `L9-CI-CORE-006` names. `.github` is bound by the live ruleset even though the committed ruleset JSON was earlier reported to exclude it; that drift is not re-checked here.
