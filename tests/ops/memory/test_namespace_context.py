"""Namespace identity is Cursor's; namespace authorization is not (INV-07/08)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ops.memory import namespace_context as nc

ROOT = Path(__file__).resolve().parents[3]


def test_this_checkout_yields_one_write_hint_and_a_read_fan_in() -> None:
    context = nc.resolve_namespace_context(ROOT)
    assert context.write_namespace_hint == "cursor-governance"
    assert context.read_namespace_hints[0] == "cursor-governance"
    assert len(context.read_namespace_hints) >= 1
    assert context.repository_identity == "Quantum-L9/Cursor-Governance"
    assert context.git_root == str(ROOT)
    assert context.as_dict()["authorization"] == "not_decided_here"


def test_explicit_override_is_a_request_not_a_grant(tmp_path: Path) -> None:
    context = nc.resolve_namespace_context(tmp_path, explicit="some-namespace")
    assert context.write_namespace_hint == "some-namespace"
    assert context.method == "explicit_request"
    assert context.explicit_request == "some-namespace"


def test_forbidden_override_yields_no_write_hint() -> None:
    context = nc.resolve_namespace_context(ROOT, explicit="main")
    assert context.write_namespace_hint is None
    assert any("forbidden" in warning for warning in context.warnings)


def test_contradicting_override_yields_no_write_hint() -> None:
    context = nc.resolve_namespace_context(ROOT, explicit="website-bot")
    assert context.write_namespace_hint is None
    assert any("contradicts" in warning for warning in context.warnings)


def test_unknown_repository_has_no_write_hint_but_may_read_workspace(tmp_path: Path) -> None:
    context = nc.resolve_namespace_context(tmp_path)
    assert context.write_namespace_hint is None
    assert context.has_write_hint is False
    assert context.warnings
    # Exactly one write namespace per mutation: none here, never a guess.
    assert "cursor-governance" not in context.read_namespace_hints


def test_repository_identity_comes_from_the_origin_remote(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "git@github.com:Quantum-L9/Website-Bot.git",
        ],
        check=True,
    )
    root, identity = nc.repository_identity_for(tmp_path)
    assert root == str(tmp_path.resolve())
    assert identity == "Quantum-L9/Website-Bot"
    context = nc.resolve_namespace_context(tmp_path)
    assert context.write_namespace_hint == "website-bot"


def test_repository_state_digest_is_head(tmp_path: Path) -> None:
    assert nc.repository_state_digest(tmp_path) is None
    head = nc.repository_state_digest(ROOT)
    assert head and len(head) == 40


# ---------------------------------------------------------------------------
# Stage C2 — namespace ownership split (plan §17, §34 "Namespace tests")
# ---------------------------------------------------------------------------


def _registry() -> dict:
    return {
        "schema_version": 3,
        "classification": "namespace_request_hints",
        "shared_read_namespaces": ["l9-workspace"],
        "workspace_group": "igor-workspace",
        "forbidden_groups": ["main", "default", "", "test"],
        "repos": {
            "cursor-governance": {
                "github": "Quantum-L9/Cursor-Governance",
                "remote_patterns": ["*/Cursor-Governance*"],
                "path_hints": ["Cursor-Governance"],
            },
            "pr-repair": {
                "github": "Quantum-L9/l9-pr-repair",
                "github_aliases": ["Quantum-L9/PR_Repair"],
                "remote_patterns": ["*/PR_Repair*", "*/l9-pr-repair*"],
                "path_hints": ["PR_Repair", "l9-pr-repair"],
            },
            "child-repo": {
                "github": "Quantum-L9/child-repo",
                "remote_patterns": ["*/child-repo*"],
                "path_hints": ["child-repo"],
            },
        },
    }


def _git_repo(path: Path, remote: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", remote], check=True)
    return path


def test_registry_is_classified_as_request_hints_not_grants() -> None:
    registry = nc.load_registry()
    assert registry["classification"] == "namespace_request_hints"
    assert nc.shared_read_namespaces(registry) == ("l9-workspace",)
    # The legacy provider group is never a canonical read request.
    assert "igor-workspace" not in nc.shared_read_namespaces(registry)


def test_single_repository_requests_its_own_namespace_plus_shared_read(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "PR_Repair", "git@github.com:Quantum-L9/PR_Repair.git")
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.method == nc.METHOD_REGISTRY
    assert context.write_namespace_hint == "pr-repair"
    assert context.read_namespace_hints == ("pr-repair", "l9-workspace")
    assert context.repository_identity == "Quantum-L9/PR_Repair"
    assert context.parent_git_root is None


def test_repository_alias_resolves_to_the_same_slug(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "renamed", "https://github.com/Quantum-L9/l9-pr-repair.git")
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.write_namespace_hint == "pr-repair"
    assert context.aliases == ("Quantum-L9/l9-pr-repair", "Quantum-L9/PR_Repair")


def test_nested_child_repository_is_its_own_identity(tmp_path: Path) -> None:
    parent = _git_repo(
        tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git"
    )
    child = _git_repo(parent / "vendor" / "child-repo", "git@github.com:Quantum-L9/child-repo.git")
    context = nc.resolve_namespace_context(child, registry=_registry(), env={})
    assert context.write_namespace_hint == "child-repo"
    assert context.git_root == str(child.resolve())
    assert context.parent_git_root == str(parent.resolve())
    assert "cursor-governance" not in context.read_namespace_hints


def test_write_namespace_is_exactly_one_while_read_may_fan_in(tmp_path: Path) -> None:
    repo = _git_repo(
        tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git"
    )
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.write_namespace_hint == "cursor-governance"
    assert len(context.read_namespace_hints) == 2
    assert set(context.read_namespace_hints) > {context.write_namespace_hint}


def test_explicit_request_is_recorded_and_forwarded_without_a_grant(tmp_path: Path) -> None:
    context = nc.resolve_namespace_context(
        tmp_path, registry=_registry(), env={nc.ENV_NAMESPACE_REQUEST: "some-namespace"}
    )
    assert context.method == nc.METHOD_EXPLICIT
    assert context.explicit_request == "some-namespace"
    assert context.write_namespace_hint == "some-namespace"
    assert context.as_dict()["authorization"] == "not_decided_here"


def test_explicit_request_contradicting_identity_is_not_forwarded_as_write(tmp_path: Path) -> None:
    repo = _git_repo(
        tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git"
    )
    context = nc.resolve_namespace_context(repo, explicit="pr-repair", registry=_registry(), env={})
    assert context.method == nc.METHOD_EXPLICIT
    assert context.write_namespace_hint is None
    assert context.explicit_request == "pr-repair"
    assert context.read_namespace_hints == ("cursor-governance", "l9-workspace")
    assert any("contradicts" in warning for warning in context.warnings)


def test_ambiguous_container_has_no_write_hint_and_names_the_candidates(tmp_path: Path) -> None:
    _git_repo(tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git")
    _git_repo(tmp_path / "PR_Repair", "git@github.com:Quantum-L9/PR_Repair.git")
    context = nc.resolve_namespace_context(tmp_path, registry=_registry(), env={})
    assert context.method == nc.METHOD_AMBIGUOUS
    assert context.write_namespace_hint is None
    assert context.candidates == ("cursor-governance", "pr-repair")
    # An ambiguous container requests no repository namespace, only the shared read.
    assert context.read_namespace_hints == ("l9-workspace",)


def test_unknown_repository_requests_only_the_shared_read(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "mystery", "git@github.com:Someone/mystery.git")
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.method == nc.METHOD_UNRESOLVED
    assert context.write_namespace_hint is None
    assert context.read_namespace_hints == ("l9-workspace",)
    assert context.repository_identity == "Someone/mystery"


def test_legacy_resolver_is_a_shim_over_the_same_matching(monkeypatch, tmp_path: Path) -> None:
    from ops.graphiti import group_resolver as legacy

    monkeypatch.setattr(legacy, "load_registry", lambda: _registry())
    repo = _git_repo(tmp_path / "PR_Repair", "git@github.com:Quantum-L9/PR_Repair.git")
    resolved = legacy.resolve_group_id(repo)
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert resolved["group_id"] == context.write_namespace_hint == "pr-repair"
    # `readonly` is identity confidence, never authorization.
    assert resolved["readonly"] is False
