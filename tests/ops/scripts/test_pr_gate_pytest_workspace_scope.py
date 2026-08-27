"""Regression guard: the PR gate's pytest block must be scoped to this repository.

``run_python_test_suites.py`` runs the GOVERNANCE suite registry
(``ops/config/python-contract.json``) and derives ``REPO_ROOT`` from its own
location, so it only ever describes this repository. The gate's ``--- pytest ---``
block invoked it for any workspace with a changed ``.py`` file, while
``run_pr_gate.sh`` had already ``cd``-ed into ``$WS``.

For a consumer repository the selector was therefore handed changed paths such
as ``src/<consumer_pkg>/`` and resolved them against the governance
``REPO_ROOT``, where they do not exist. The repo-root suite matched nothing and
pytest exited 4::

    [runner] scoped_pr_check paths=['src/<consumer_pkg>/...', 'tools/assurance']
    [runner] profile=local suites=4 repo_root=/root/.cursor-governance
    no tests ran in 0.06s
    [runner] END   suite=repo-root result=FAIL(exit=4)

``make pr`` then failed before any push, for every consumer repo touching a
Python file -- publication was impossible from a consumer workspace.

Every neighbouring step in the block is workspace-aware (``sync-generated-artifacts``
passes ``--root "$WS"``; the uv-lock step tests ``$WS/uv.lock``). The pytest step
was the outlier.

These tests execute the real classifier and the real dispatch condition rather
than grepping for prose:

  * a consumer workspace skips the governance registry
  * ssot and ssot_checkout still run it (no coverage lost on this repo)
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
GATE = SCRIPTS / "run_pr_gate.sh"
RESOLVE = SCRIPTS / "resolve_governance_paths.sh"


def _dispatch(workspace: Path) -> str:
    """Run the gate's real pytest-block condition against one workspace."""

    script = (
        f'source "{RESOLVE}" >/dev/null 2>&1; '
        f'k="$(classify_workspace_kind "{workspace}")"; '
        'if [ "$k" != "ssot" ] && [ "$k" != "ssot_checkout" ]; '
        "then echo skip; else echo registry; fi"
    )
    out = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home())},
        check=False,
    )
    return out.stdout.strip()


def test_gate_script_parses() -> None:
    """A syntax error here would break every publication path."""

    proc = subprocess.run(["bash", "-n", str(GATE)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr


def test_consumer_workspace_skips_the_governance_registry(tmp_path: Path) -> None:
    """The failing case: a consumer must not be gated on this repo's suites."""

    (tmp_path / "src").mkdir()
    assert _dispatch(tmp_path) == "skip"


def test_this_repository_still_runs_the_registry() -> None:
    """The repaired branch must not cost this repository its own coverage."""

    assert _dispatch(ROOT) == "registry"


def test_pytest_block_dispatches_on_workspace_kind() -> None:
    """Structural pin between the classifier and the pytest block.

    Paired with the executable checks above rather than standing alone: it
    catches a future edit that keeps the classifier call but stops guarding the
    invocation with it.
    """

    body = GATE.read_text(encoding="utf-8")
    block = body.split("--- pytest ---", 1)
    assert len(block) == 2, "pytest block marker missing from the gate"
    after = block[1].split("--- sync-generated-artifacts ---", 1)[0]
    # Match the invocation itself, not any mention: the block's own comment
    # names the script, so a bare filename search finds the prose first.
    invocation = '"$_pytest_py" "$SCRIPT_DIR/run_python_test_suites.py"'
    assert 'classify_workspace_kind "$WS"' in after, "pytest block no longer classifies $WS"
    assert invocation in after, "pytest block no longer invokes the suite runner"
    assert after.index('classify_workspace_kind "$WS"') < after.index(invocation)


@pytest.mark.parametrize("kind", ["ssot", "ssot_checkout"])
def test_registry_kinds_are_spelled_exactly(kind: str) -> None:
    """A typo in either name would silently skip this repository's suites."""

    body = GATE.read_text(encoding="utf-8")
    after = body.split("--- pytest ---", 1)[1].split("--- sync-generated-artifacts ---", 1)[0]
    assert f'"{kind}"' in after
