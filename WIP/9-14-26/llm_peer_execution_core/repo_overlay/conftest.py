"""Root pytest configuration.

Additive collection controls kept OUT of pyproject.toml, which is a protected
file (see ORG_INVARIANTS.yaml `protected_paths` and CODEOWNERS): it is only
appended to under governed change-control, never overwritten by tooling.

Program Execution's provider and Peer Execution conformance surfaces are run by
`make program-execution-conformance` with
`PYTHONPATH=environment/program-execution`. Keep them out of root pytest
collection because peer/provider fixtures intentionally share module basenames
and import through the Program Execution subsystem root.
"""

collect_ignore = [
    "environment/program-execution/peer_execution",
    "environment/program-execution/adapters",
    "environment/program-execution/integrations",
    "environment/program-execution/conformance",
    "environment/program-execution/tests",
    ".l9",
    "skills/l9-cli-optimization/scripts/self_test.py",
    "skills/l9-repository-renovation/scripts/self_test.py",
    "skills/l9-structured-reasoning/scripts/self_test.py",
]
