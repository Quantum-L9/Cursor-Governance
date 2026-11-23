"""The declared tool surface is the truth; the registry must not exceed it."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from tools.base import RuntimeContext

from tools import build_registry


@pytest.fixture
def contract(repo_root: Path) -> dict:
    path = repo_root / "environment/agents/adapters/manus/contracts/tools.v1.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture
def registry(repo_root: Path) -> dict:
    return build_registry(RuntimeContext(repo_root))


def test_every_registered_tool_is_declared(registry: dict, contract: dict) -> None:
    declared = {tool["name"] for tool in contract["tools"]}
    assert set(registry) <= declared, f"undeclared tools: {set(registry) - declared}"


def test_declared_names_are_unique(contract: dict) -> None:
    names = [tool["name"] for tool in contract["tools"]]
    assert len(names) == len(set(names))


def test_surface_is_read_only(contract: dict, registry: dict) -> None:
    assert contract["read_only_default"] is True
    for tool in contract["tools"]:
        assert tool["read_only"] is True, f"{tool['name']} claims write access"
    for name, spec in registry.items():
        assert spec.read_only is True, f"{name} is not read-only"


def test_every_declared_tool_has_an_existing_test(contract: dict, repo_root: Path) -> None:
    adapter = repo_root / "environment/agents/adapters/manus"
    for tool in contract["tools"]:
        assert (adapter / tool["test"]).is_file(), f"{tool['name']} has no test at {tool['test']}"


def test_every_registry_module_exists(contract: dict, repo_root: Path) -> None:
    adapter = repo_root / "environment/agents/adapters/manus"
    for tool in contract["tools"]:
        if tool["status"] != "registry":
            continue
        assert (adapter / tool["module"]).is_file(), (
            f"{tool['name']} module missing: {tool['module']}"
        )


def test_output_bounds_match_contract(contract: dict, registry: dict) -> None:
    for name, spec in registry.items():
        assert spec.max_output_chars <= contract["max_output_chars"], (
            f"{name} exceeds the output bound"
        )


def test_exclusions_are_documented(contract: dict) -> None:
    excluded = {item["name"] for item in contract.get("excluded", [])}
    assert {"governance_shell", "governance_secret_read"} <= excluded
