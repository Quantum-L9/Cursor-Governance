"""The workflows.dags discovery boundary must import.

Regression for: workflows/dags/inspect_dag.py hard-imported
`tools.validation.validate_external_code`, an optional package absent from the
tree. One DAG's missing optional dependency made the whole `workflows.dags`
package unimportable, so every SessionDAG in it became unreachable — including
the discovery probe that l9-dag-authoring's REGISTER operation depends on.

The import is now soft. These tests pin both halves of that contract: the
boundary imports, AND compliance is never silently reported clean when the
validators that would have checked it are missing.
"""

from __future__ import annotations

import asyncio

import pytest


def test_the_dags_package_imports():
    """One DAG's optional dependency must not take down the whole boundary."""
    import workflows.dags  # noqa: F401


def test_registered_session_dags_are_reachable_through_the_registry():
    """Importing the package must populate the registry, not just succeed."""
    import workflows.dags  # noqa: F401
    from workflows.session.registry import get_session_dag

    for dag_id in ("dag-authoring-v1", "gmp-execution-v1", "skill-compiler-v2"):
        assert get_session_dag(dag_id) is not None, dag_id


def test_langgraph_only_modules_are_importable_even_though_unregistered():
    """inspect_dag is a LangGraph module, not a SessionDAG registration.

    That split — registered SessionDAGs alongside unregistered LangGraph
    modules in one package — is the DAG runtime taxonomy convergence tracked
    separately. What this test pins is narrower: the module must import, since
    that is what broke the boundary.
    """
    import workflows.dags

    assert hasattr(workflows.dags.inspect_dag, "compliance_node")


def test_validators_availability_is_reported_not_assumed():
    import workflows.dags

    assert isinstance(workflows.dags.inspect_dag.validators_available(), bool)


def test_missing_validators_raise_rather_than_return_no_issues():
    """An empty issue list would read downstream as 'clean'. It must raise."""
    import workflows.dags

    inspect_dag = workflows.dags.inspect_dag
    if inspect_dag.validators_available():
        pytest.skip("validators are present in this checkout; nothing to assert")
    with pytest.raises(RuntimeError, match="validators unavailable"):
        inspect_dag._run_validators_on_code("x = 1")


def test_compliance_never_reports_ok_without_validators():
    """Unchecked is not clean. The flags stay False and the gap is flagged."""
    import workflows.dags

    inspect_dag = workflows.dags.inspect_dag
    if inspect_dag.validators_available():
        pytest.skip("validators are present in this checkout; nothing to assert")

    state = inspect_dag.InspectState(target="workflows/dags/inspect_dag.py")
    result = asyncio.run(inspect_dag.compliance_node(state))

    assert result["import_ok"] is False
    assert result["adr_ok"] is False
    assert result["config_ok"] is False
    patterns = [row["pattern"] for row in result["anti_patterns"]]
    assert "validators_unavailable" in patterns
