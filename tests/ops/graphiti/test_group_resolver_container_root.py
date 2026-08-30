"""Group resolution at a multi-repository container root.

A cloud session is rooted at a container holding several repositories, so this
is the common shape, not an edge case. Refusing to pick is correct — a group_id
is repository identity, and collapsing several repositories onto one namespace
is the failure the guard exists to prevent. What was wrong was the remedy: the
error said "set GRAPHITI_GROUP_ID", which reads as an account-level pin, and the
environment contract forbids exactly that for the same reason.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "graphiti"))

import group_resolver as gr  # noqa: E402


def _registry(monkeypatch, groups: dict[str, list[str]]) -> None:
    payload = {
        "schema_version": 2,
        "repos": {
            name: {"path_hints": hints, "remote_patterns": []} for name, hints in groups.items()
        },
        "workspace_group": "igor-workspace",
        "forbidden_groups": ["main", "default", "", "test"],
        "resolution": {"on_failure": "abort_write_allow_readonly"},
    }
    monkeypatch.setattr(gr, "load_registry", lambda: payload)
    # Path hints are the match axis under test; a real remote would add a second.
    monkeypatch.setattr(gr, "_git_remote_url", lambda _cwd: "")


def _container(tmp_path: Path, names: list[str]) -> Path:
    for name in names:
        (tmp_path / name / ".git").mkdir(parents=True)
    return tmp_path


def test_container_root_names_the_situation_and_the_real_remedies(tmp_path, monkeypatch) -> None:
    _registry(monkeypatch, {"repo-a": ["repo-a"], "repo-b": ["repo-b"]})
    root = _container(tmp_path, ["repo-a", "repo-b"])

    result = gr.resolve_group_id(root)

    assert result["group_id"] is None
    assert result["readonly"] is True
    assert result["container_root"] is True
    assert sorted(result["candidates"]) == ["repo-a", "repo-b"]
    error = result["error"]
    assert "container root" in error
    # The two legitimate remedies are named, and the forbidden one is refused.
    assert "--group-id" in error
    assert "Do not pin GRAPHITI_GROUP_ID" in error


def test_single_repository_still_resolves_cleanly(tmp_path, monkeypatch) -> None:
    """The container-root branch must not disturb the ordinary case."""
    _registry(monkeypatch, {"repo-a": ["repo-a"], "repo-b": ["repo-b"]})
    root = _container(tmp_path, ["repo-a", "repo-b"])

    result = gr.resolve_group_id(root / "repo-a")

    assert result["group_id"] == "repo-a"
    assert result["readonly"] is False
