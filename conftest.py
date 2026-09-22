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

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _git_in(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def stacked_repo(tmp_path: Path) -> Path:
    """Provide a committed feature branch for all autonomy gate tests.

    This fixture must be root-visible. The scoped publication runner selects
    test files from multiple top-level roots; keeping it in one child
    ``conftest.py`` made the fixture unavailable in that legitimate composite
    selection even though each autonomy module passed in isolation.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git_in(repo, "init")
    _git_in(repo, "config", "user.email", "test@example.com")
    _git_in(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    _git_in(repo, "add", "README.md")
    _git_in(repo, "commit", "-m", "init")
    _git_in(repo, "branch", "-M", "main")
    _git_in(repo, "checkout", "-b", "feat/l4-stack")
    (repo / "a.txt").write_text("a\n", encoding="utf-8")
    _git_in(repo, "add", "a.txt")
    _git_in(repo, "commit", "-m", "local work")
    return repo


collect_ignore = [
    "environment/program-execution/peer_execution",
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
    "skills/l9-plan/scripts/self_test.py",
    "skills/l9-code-maintenance/scripts/self_test.py",
    "skills/l9-plan-audit/scripts/self_test.py",
    "skills/l9-pipeline-audit/scripts/self_test.py",
    "skills/l9-pipeline-audit/scripts/audit_plans_self_test.py",
    "skills/l9-repo-sync/scripts/self_test.py",
    "skills/l9-update-agent-docs/scripts/self_test.py",
    "skills/l9-pr-remediation/scripts/self_test.py",
    "skills/l9-skill-compiler/scripts/self_test.py",
    "skills/l9-dag-authoring/scripts/self_test.py",
    "skills/l9-issue-remediation/scripts/self_test.py",
    "skills/l9-ynp/scripts/self_test.py",
    "skills/l9-wire-into-repo/scripts/self_test.py",
    "skills/l9-idea-execute/scripts/self_test.py",
    "skills/l9-idea-foundry/scripts/self_test.py",
    "skills/l9-plan-simple/scripts/self_test.py",
    "skills/l9-intelligence-harvest/scripts/self_test.py",
    "skills/l9-pr-digest/scripts/self_test.py",
    "skills/l9-pr-audit/scripts/self_test.py",
    "skills/l9-repo-birth/scripts/self_test.py",
    # Local PE/PR worktrees must never enter root discovery (import collisions).
    ".l9",
]
