"""Regression tests for group_resolver.resolve_group_id hardening.

Covers the fail-closed reconciliation of explicit overrides against the
computed repo match, and the segment-anchored path-hint matching that
replaced raw substring matching.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import group_resolver  # noqa: E402

_TEST_REGISTRY = {
    "workspace_group": "igor-workspace",
    "forbidden_groups": ["main", "default", "", "test"],
    "resolution": {"on_failure": "abort_write_allow_readonly"},
    "repos": {
        "ib-odoo-19": {
            "github": "cryptoxdog/IB-Odoo_19",
            "path_hints": ["IB-Odoo_19", "IB_Odoo", "plasticos_base"],
            "remote_patterns": ["*/IB-Odoo_19*"],
        },
        "cursor-governance": {
            "github": "Quantum-L9/Cursor-Governance",
            "path_hints": ["Cursor-Governance", "GlobalCommands"],
            "remote_patterns": ["*/Cursor-Governance*"],
        },
    },
}


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    monkeypatch.delenv("GRAPHITI_GROUP_ID", raising=False)
    monkeypatch.setattr(group_resolver, "load_registry", lambda: dict(_TEST_REGISTRY))
    monkeypatch.setattr(group_resolver, "_git_remote_url", lambda cwd: None)


def _set_remote(monkeypatch, url: str | None) -> None:
    monkeypatch.setattr(group_resolver, "_git_remote_url", lambda cwd: url)


def test_registry_match_by_remote(monkeypatch):
    _set_remote(monkeypatch, "git@github.com:cryptoxdog/IB-Odoo_19.git")
    result = group_resolver.resolve_group_id(Path("/tmp/anywhere"))
    assert result == {"group_id": "ib-odoo-19", "method": "registry", "readonly": False}


def test_explicit_matching_resolved_match_passes(monkeypatch):
    _set_remote(monkeypatch, "git@github.com:cryptoxdog/IB-Odoo_19.git")
    result = group_resolver.resolve_group_id(Path("/tmp/anywhere"), explicit="ib-odoo-19")
    assert result["group_id"] == "ib-odoo-19"
    assert result["method"] == "explicit_env"
    assert result["readonly"] is False


def test_explicit_contradicting_resolved_match_fails_closed(monkeypatch):
    _set_remote(monkeypatch, "git@github.com:cryptoxdog/IB-Odoo_19.git")
    result = group_resolver.resolve_group_id(Path("/tmp/anywhere"), explicit="cursor-governance")
    assert result["group_id"] is None
    assert result["readonly"] is True
    assert "contradicts" in result["error"]
    assert "ib-odoo-19" in result["error"]


def test_env_override_contradicting_resolved_match_fails_closed(monkeypatch):
    _set_remote(monkeypatch, "git@github.com:cryptoxdog/IB-Odoo_19.git")
    monkeypatch.setenv("GRAPHITI_GROUP_ID", "cursor-governance")
    result = group_resolver.resolve_group_id(Path("/tmp/anywhere"))
    assert result["group_id"] is None
    assert result["readonly"] is True
    assert "contradicts" in result["error"]


def test_explicit_with_no_repo_match_still_allowed():
    # CI runners in generic checkout dirs with GRAPHITI_GROUP_ID set on purpose.
    result = group_resolver.resolve_group_id(Path("/tmp/generic-checkout"), explicit="igorbot")
    assert result == {"group_id": "igorbot", "method": "explicit_env", "readonly": False}


def test_env_override_with_no_repo_match_still_allowed(monkeypatch):
    monkeypatch.setenv("GRAPHITI_GROUP_ID", "igorbot")
    result = group_resolver.resolve_group_id(Path("/tmp/generic-checkout"))
    assert result == {"group_id": "igorbot", "method": "GRAPHITI_GROUP_ID", "readonly": False}


def test_forbidden_explicit_rejected():
    result = group_resolver.resolve_group_id(Path("/tmp/generic-checkout"), explicit="main")
    assert result["group_id"] is None
    assert result["readonly"] is True
    assert "forbidden" in result["error"]


def test_ambiguous_match_without_explicit_stays_readonly():
    # cwd carries path segments for two different registry repos.
    result = group_resolver.resolve_group_id(Path("/Users/me/Cursor-Governance/IB_Odoo"))
    assert result["group_id"] is None
    assert result["readonly"] is True
    assert "ambiguous" in result["error"]


def test_explicit_member_of_ambiguous_set_allowed():
    result = group_resolver.resolve_group_id(
        Path("/Users/me/Cursor-Governance/IB_Odoo"), explicit="cursor-governance"
    )
    assert result["group_id"] == "cursor-governance"
    assert result["readonly"] is False


def test_explicit_outside_ambiguous_set_fails_closed():
    result = group_resolver.resolve_group_id(
        Path("/Users/me/Cursor-Governance/IB_Odoo"), explicit="igorbot"
    )
    assert result["group_id"] is None
    assert result["readonly"] is True
    assert "contradicts" in result["error"]


def test_path_hint_substring_false_positive_no_longer_matches():
    # "IB_Odoo" is a hint; it must NOT match a dir merely containing it as a
    # substring of a segment.
    result = group_resolver.resolve_group_id(Path("/Users/me/CONTRIB_Odoo_notes"))
    assert result["method"] == "fallback_readonly"
    assert result["readonly"] is True


def test_path_hint_exact_segment_match_succeeds():
    result = group_resolver.resolve_group_id(Path("/Users/me/IB_Odoo/some/subdir"))
    assert result == {"group_id": "ib-odoo-19", "method": "registry", "readonly": False}


def test_child_git_repo_does_not_collapse_to_workspace(tmp_path: Path):
    workspace = tmp_path / "home-user"
    child = workspace / "Cursor-Governance"
    child.mkdir(parents=True)
    (child / ".git").mkdir()
    result = group_resolver.resolve_group_id(workspace)
    assert result["group_id"] == "cursor-governance"
    assert result["readonly"] is False


def test_home_does_not_inherit_sibling_child_repos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_home = (tmp_path / "home-user").resolve()
    for name in ("Cursor-Governance", "Website-Bot"):
        child = fake_home / name
        child.mkdir(parents=True)
        (child / ".git").mkdir()
    monkeypatch.setattr(group_resolver.Path, "home", classmethod(lambda cls: fake_home))
    result = group_resolver.resolve_group_id(fake_home)
    assert result["group_id"] == "igor-workspace"
    assert result["method"] == "fallback_readonly"
    assert result["readonly"] is True


def test_no_match_falls_back_readonly_workspace():
    result = group_resolver.resolve_group_id(Path("/tmp/unrelated"))
    assert result["group_id"] == "igor-workspace"
    assert result["method"] == "fallback_readonly"
    assert result["readonly"] is True
