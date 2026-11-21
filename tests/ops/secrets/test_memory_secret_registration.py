"""Every memory-path credential is registered in the mirror and reported at SessionStart.

Lane MEM-HOOK-2: a name the memory code binds must be listed in
`ops/secrets/infisical-cursor-governance.yaml` (`root_env_keys`), and
`ops/secrets/session_start_secrets.py` must report it by name and source with
the hook carrier it resolves, never its value.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SECRETS_DIR = REPO_ROOT / "ops" / "secrets"
MEMORY_DIR = REPO_ROOT / "ops" / "memory"
for _path in (str(SECRETS_DIR), str(REPO_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import capability_bind as cb  # noqa: E402
import session_start_secrets as sss  # noqa: E402

from ops.memory import hook_carrier  # noqa: E402

#: Functions that bind an inventory name (capability_bind and the hook wrapper).
BIND_CALLS = frozenset({"bind", "bind_first", "bind_status", "bind_credential"})
SECRET = "sentinel-VALUE-must-never-appear"


def _inventory() -> dict:
    data = yaml.safe_load((SECRETS_DIR / "infisical-cursor-governance.yaml").read_text())
    assert isinstance(data, dict)
    return data


def _module_strings(tree: ast.Module) -> dict[str, tuple[str, ...]]:
    """Module-level names bound to a str or a tuple of str (incl. tuple unpacking)."""
    out: dict[str, tuple[str, ...]] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        literal: tuple[str, ...] | None = None
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            literal = (value.value,)
        elif isinstance(value, ast.Tuple) and all(
            isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts
        ):
            literal = tuple(str(e.value) for e in value.elts)  # type: ignore[attr-defined]
        elif isinstance(value, ast.Name) and value.id in out:
            literal = out[value.id]
        if literal is None:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                out[target.id] = literal
            elif isinstance(target, ast.Tuple) and len(target.elts) == len(literal):
                for element, item in zip(target.elts, literal, strict=True):
                    if isinstance(element, ast.Name):
                        out[element.id] = (item,)
    return out


def _bound_names() -> Iterator[tuple[str, str]]:
    """``(file, name)`` for every literal inventory name ops/memory passes to a bind call.

    An argument that is a parameter of the enclosing function (a pass-through
    wrapper such as ``bind_credential(name)``) is not a name; anything else
    that does not resolve to a literal fails the guard, so a new bind cannot
    hide behind an expression.
    """
    for path in sorted(MEMORY_DIR.rglob("*.py")):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        strings = _module_strings(tree)
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            # Parameters of this function and of every function or lambda nested
            # in it: a bind inside `lambda name: bind_credential(name, env)` is a
            # pass-through of the lambda's own parameter.
            params = {
                a.arg
                for scope in ast.walk(func)
                if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
                for a in [*scope.args.args, *scope.args.kwonlyargs]
            }
            for call in ast.walk(func):
                if not isinstance(call, ast.Call):
                    continue
                callee = call.func
                name = (
                    callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", "")
                )
                if name not in BIND_CALLS or not call.args:
                    continue
                arg = call.args[0]
                rel = path.relative_to(REPO_ROOT).as_posix()
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    yield rel, arg.value
                elif isinstance(arg, ast.Name) and arg.id in strings:
                    for item in strings[arg.id]:
                        yield rel, item
                elif isinstance(arg, ast.Name) and arg.id in params:
                    continue  # pass-through wrapper; its callers are checked
                else:
                    pytest.fail(f"{rel}:{call.lineno}: bind call with an unresolvable name")
        # Names reached through a wrapper: module-level tuples iterated into a bind.
        for name, items in strings.items():
            if name.endswith("CREDENTIALS"):
                for item in items:
                    yield path.relative_to(REPO_ROOT).as_posix(), item


def test_every_name_the_memory_code_binds_is_in_the_mirror() -> None:
    listed = set(_inventory()["root_env_keys"])
    found = set(_bound_names())
    names = {name for _, name in found}
    assert set(hook_carrier.HOOK_CREDENTIALS) <= names, "guard no longer sees the hook pair"
    missing = sorted(f"{rel}: {name}" for rel, name in found if name not in listed)
    assert missing == [], f"memory binds names the Infisical mirror does not list: {missing}"


def test_every_name_the_memory_code_binds_is_reported_at_session_start() -> None:
    names = {name for _, name in _bound_names()}
    assert names <= set(sss.MEMORY_BIND_NAMES)


def test_reported_memory_names_are_root_keys_never_operator_only_or_refused() -> None:
    inventory = _inventory()
    assert set(sss.MEMORY_BIND_NAMES) <= set(inventory["root_env_keys"])
    assert not set(sss.MEMORY_BIND_NAMES) & set(inventory.get("operator_only_keys") or [])
    assert not set(sss.MEMORY_BIND_NAMES) & set(cb.REFUSED_NAMES)
    assert set(hook_carrier.HOOK_CREDENTIALS) <= set(sss.MEMORY_BIND_NAMES)
    assert "L9_MEMORY_AGENT_AUTHORITY_JSON" in sss.MEMORY_BIND_NAMES  # the agent lane's door


def test_hook_principals_live_in_l9_graphite_memory_and_never_bind_here() -> None:
    refs = _inventory()["memory_prod_secret_refs"]
    assert refs["project"]["name"] == "l9-graphite-memory"
    assert refs["hook_principals"]["names"] == ["L9_MEMORY_HOOK_PRINCIPALS_JSON"]
    assert "L9_MEMORY_HOOK_PRINCIPALS_JSON" not in _inventory()["root_env_keys"]
    assert "L9_MEMORY_HOOK_PRINCIPALS_JSON" not in sss.MEMORY_BIND_NAMES


def _statuses(monkeypatch: pytest.MonkeyPatch, bound: dict[str, str]) -> None:
    def fake(name: str, *, env: object = None) -> dict[str, object]:
        source = bound.get(name)
        return {"name": name, "bound": source is not None, "source": source or "unbound"}

    monkeypatch.setattr(cb, "bind_status", fake)


@pytest.mark.parametrize(
    ("bound", "env", "carrier"),
    [
        (
            {"L9_MEMORY_HOOK_CLIENT_ID": "infisical", "L9_MEMORY_HOOK_CLIENT_SECRET": "infisical"},
            {},
            "hosted",
        ),
        ({"L9_MEMORY_HOOK_CLIENT_ID": "infisical"}, {"CLAUDE_CODE_REMOTE": "true"}, "relay"),
        ({}, {}, "local"),
        ({}, {"L9_MEMORY_HOOK_CARRIER": "bogus"}, "refused"),
        ({}, {"L9_MEMORY_HOOK_CARRIER": "relay"}, "relay"),
    ],
)
def test_memory_plane_reports_names_sources_and_the_resolved_carrier(
    monkeypatch: pytest.MonkeyPatch, bound: dict[str, str], env: dict[str, str], carrier: str
) -> None:
    _statuses(monkeypatch, bound)
    plane = sss.memory_plane(env)
    assert [b["name"] for b in plane["binds"]] == list(sss.MEMORY_BIND_NAMES)
    assert plane["carrier"] == carrier
    unbound = [n for n in sss.MEMORY_BIND_NAMES if n not in bound]
    assert len(plane["warnings"]) == len(unbound)
    for name, line in zip(unbound, plane["warnings"], strict=True):
        assert line.startswith(f"WARN: {name} unbound") and f"hook carrier: {carrier}" in line
    line = sss._memory_line(plane)
    for name in sss.MEMORY_BIND_NAMES:
        assert f"{name}={bound.get(name, 'unbound')}" in line
    assert line.endswith(f"hook_carrier={carrier}")


def test_unbound_memory_names_warn_but_never_fail_the_plane(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _statuses(monkeypatch, {})
    result = {
        "identity": {"ok": True, "code": sss.IDENTITY_OK, "source": "env", "summary": ""},
        "login": "env",
        "binds": [],
        "memory": sss.memory_plane({}),
        "authorized_names": [],
        "plane_ok": True,
        "surface_class": sss.MODEL_CONTROLLED,
        "state": sss.STATE_OK,
    }
    monkeypatch.setattr(sss, "run_plane", lambda: result)
    assert sss.main([]) == 0
    err = capsys.readouterr().err
    assert "hook_carrier=local" in err
    assert err.count("WARN: L9_MEMORY_") == len(sss.MEMORY_BIND_NAMES)
    receipt = sss.receipt_payload(result)["memory"]
    assert receipt["carrier"] == "local" and receipt["warnings"] == len(sss.MEMORY_BIND_NAMES)


def test_no_value_reaches_the_report_or_the_receipt(monkeypatch: pytest.MonkeyPatch) -> None:
    cb.reset_cache()
    cb.remember_vault_names(frozenset(sss.MEMORY_BIND_NAMES))
    try:
        env = {name: SECRET for name in sss.MEMORY_BIND_NAMES}
        plane = sss.memory_plane(env)
        assert {b["source"] for b in plane["binds"]} == {"env"}
        assert plane["carrier"] == "hosted" and plane["warnings"] == []
        rendered = sss._memory_line(plane) + repr(sss._memory_receipt(plane)) + repr(plane)
        assert SECRET not in rendered
    finally:
        cb.remember_vault_names(None)
        cb.reset_cache()
