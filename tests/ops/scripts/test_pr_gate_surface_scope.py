"""Regression guard: the PR gate's ssot-family branch must honour the surface gate.

`run_pr_gate.sh` documents that the Cursor DESKTOP wiring assertion has to be
gated on the surface id, because Graphiti's state directory creates
``~/.cursor`` on every surface and so "``~/.cursor`` exists" is not evidence of
a Cursor machine. That gate lived in
``should_skip_consumer_symlink_checks`` — one branch *below* the
ssot/ssot_checkout branch, which therefore short-circuited past it and ran the
full assertion. A headless adapter on an identity checkout (the governance repo
itself) then failed ``make pr`` on ``~/.cursor/hooks.json`` and its
sessionEnd / skill-router entries: artifacts the cloud installer deliberately
never creates. The result was that publication was impossible off Cursor.

These tests pin the repaired behaviour by executing the real predicate and the
real dispatch condition, not by grepping for prose:

  * a non-cursor surface scopes the check to ``--workspace``
  * a cursor surface still runs the FULL check (no coverage lost)
  * ``--workspace`` alone still carries the surface-independent checks
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
GATE = SCRIPTS / "run_pr_gate.sh"
RESOLVE = SCRIPTS / "resolve_governance_paths.sh"

# The shared predicate every Cursor-host gate now uses. One definition in
# resolve_governance_paths.sh; callers must not re-inline it.
DISPATCH = (
    f'source "{RESOLVE}" >/dev/null 2>&1; '
    "if is_cursor_host_surface; then echo full; else echo scoped; fi"
)


def _bash(script: str, env_surface: str | None) -> str:
    env = {"PATH": "/usr/bin:/bin", "HOME": "/root"}
    if env_surface is not None:
        env["L9_GOVERNANCE_SURFACE"] = env_surface
    out = subprocess.run(
        ["bash", "-c", script], capture_output=True, text=True, env=env, check=False
    )
    return out.stdout.strip()


def test_gate_script_parses() -> None:
    """A syntax error here would break every publication path."""
    proc = subprocess.run(["bash", "-n", str(GATE)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr


@pytest.mark.parametrize("surface", ["claude-code", "codex", "gemini", "manus"])
def test_headless_surfaces_scope_to_workspace(surface: str) -> None:
    """Headless adapters must not assert the Cursor desktop hook plane."""
    assert _bash(DISPATCH, surface) == "scoped"


def test_cursor_surface_keeps_full_assertion() -> None:
    """The desktop assertion must survive where it legitimately applies."""
    assert _bash(DISPATCH, "cursor") == "full"


def test_unset_surface_keeps_full_assertion() -> None:
    """Absent a declared surface, fail closed to the stricter check."""
    assert _bash(DISPATCH, None) == "full"


def test_predicate_has_exactly_one_definition() -> None:
    """A re-inlined copy is how the two branches diverged in the first place."""
    defs = [
        f
        for f in SCRIPTS.glob("*.sh")
        if re.search(r"^is_cursor_host_surface\(\)", f.read_text(encoding="utf-8"), re.M)
    ]
    assert [f.name for f in defs] == ["resolve_governance_paths.sh"]


def test_every_cursor_host_gate_uses_the_shared_predicate() -> None:
    """Both known Cursor-host assertions must be gated, not just the PR gate."""
    for name in ("run_pr_gate.sh", "validate_governance_symlinks.sh"):
        body = (SCRIPTS / name).read_text(encoding="utf-8")
        assert "is_cursor_host_surface" in body, f"{name} asserts Cursor host state ungated"


def test_ssot_branch_passes_surface_scoped_args() -> None:
    """The repaired branch must build --workspace args, not call bare.

    Structural assertion: this pins the wiring between the dispatch condition
    and the invocation. It is deliberately paired with the executable checks
    above rather than standing alone as the only evidence.
    """
    body = GATE.read_text(encoding="utf-8")
    marker = 'wiring_args=(--workspace "$WS")'
    assert marker in body, "ssot-family branch no longer scopes by surface"
    assert 'check_governance_wiring.sh" "${wiring_args[@]}"' in body
