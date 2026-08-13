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
    # Owned Claude autonomy suite (python-contract.json claude-code-autonomy).
    "environment/agents/adapters/claude-code/autonomy",
    "environment/program-execution/adapters",
    "environment/program-execution/integrations",
    "environment/program-execution/conformance",
    "environment/program-execution/tests",
    # Local runtime / nested worktrees — never root-suite collection targets.
    ".l9",
    # Skill self-check scripts share basename `self_test.py` and collide under
    # pytest prepend import mode. They are invoked by skill tooling, not root CI.
    "skills/l9-cli-optimization/scripts/self_test.py",
    "skills/l9-repository-renovation/scripts/self_test.py",
    "skills/l9-structured-reasoning/scripts/self_test.py",
]
