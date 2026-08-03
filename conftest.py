"""Root pytest configuration.

Additive collection controls kept OUT of pyproject.toml, which is a protected
file (see ORG_INVARIANTS.yaml `protected_paths` and CODEOWNERS): it is only
appended to under governed change-control, never overwritten by tooling.

The Program Execution adapter layer
(`environment/program-execution/{adapters,integrations,conformance,tests}`) is
unittest-based and runs via its own loader `make program-execution-conformance`
(`scripts/run_conformance.py`) with `PYTHONPATH=environment/program-execution`.
Sibling adapters intentionally ship same-named test files (`test_driver.py`,
`test_provider.py`, `test_bridge.py`) with no package `__init__.py`, which
collide under root pytest's prepend import mode; and their
`from adapters.common...` imports require the subsystem PYTHONPATH, not repo
root. Keep the whole adapter-layer test surface out of root discovery. `core/`
tests use repo-root-compatible imports and remain in the default suite.
"""

collect_ignore = [
    "environment/program-execution/adapters",
    "environment/program-execution/integrations",
    "environment/program-execution/conformance",
    "environment/program-execution/tests",
]
