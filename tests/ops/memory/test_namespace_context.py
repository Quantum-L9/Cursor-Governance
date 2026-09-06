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
