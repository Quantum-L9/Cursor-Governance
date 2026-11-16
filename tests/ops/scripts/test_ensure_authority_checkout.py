"""The managed authority checkout makes the default projection binding repository-independent.

Regression: SessionStart reported `CANONICAL_AUTHORITY_CHECKOUT_NOT_AVAILABLE` (operating
plane NOT BOUND) in every workspace without a `.github` clone beside it, because the
authority resolver only looked inside or beside the workspace.

The provisioner's remote is a trust-boundary constant, so these tests redirect it to a local
fixture with git's own `url.<base>.insteadOf` — the checkout still records the canonical
GitHub origin the verifiers require.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "ops/scripts/ensure_authority_checkout.sh"
CANONICAL = "https://github.com/Quantum-L9/.github.git"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def upstream(tmp_path: Path) -> Path:
    src = tmp_path / "upstream"
    src.mkdir()
    _git(src, "init", "--quiet", "-b", "main")
    _git(src, "config", "user.email", "t@example.invalid")
    _git(src, "config", "user.name", "t")
    for n in range(3):
        (src / f"f{n}.txt").write_text(str(n), encoding="utf-8")
        _git(src, "add", f"f{n}.txt")
        _git(src, "commit", "--quiet", "-m", f"c{n}")
    return src


def _env(tmp_path: Path, upstream: Path, **extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("L9_AUTHORITY", "GIT_CONFIG"))}
    env.update(
        HOME=str(tmp_path / "home"),
        L9_AUTHORITY_MANAGED_ROOT=str(tmp_path / "home/.l9/authority/.github"),
        GIT_CONFIG_COUNT="1",
        GIT_CONFIG_KEY_0=f"url.{upstream.as_uri()}.insteadOf",
        GIT_CONFIG_VALUE_0=CANONICAL,
    )
    env.update(extra)
    return env


def _run(env: dict[str, str]) -> str:
    proc = subprocess.run(["bash", str(SCRIPT)], capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stderr
    lines = [ln for ln in proc.stdout.splitlines() if ln.startswith("AUTHORITY: ")]
    assert len(lines) == 1, proc.stdout
    return lines[0]


def test_provisions_a_full_checkout_on_main_then_reuses_it(tmp_path: Path, upstream: Path) -> None:
    env = _env(tmp_path, upstream)
    root = Path(env["L9_AUTHORITY_MANAGED_ROOT"])
    assert _run(env).startswith("AUTHORITY: PROVISIONED")
    assert _git(root, "remote", "get-url", "origin") == CANONICAL
    assert _git(root, "rev-parse", "--is-shallow-repository") == "false"
    assert _git(root, "symbolic-ref", "--short", "HEAD") == "main"
    assert _git(root, "rev-parse", "HEAD") == _git(upstream, "rev-parse", "HEAD")
    assert not Path(f"{root}.partial").exists()
    second = _run(env)
    assert second.startswith("AUTHORITY: READY") and "cached" in second


def test_fast_forwards_main_when_upstream_moves(tmp_path: Path, upstream: Path) -> None:
    env = _env(tmp_path, upstream, L9_AUTHORITY_FETCH_TTL_S="0")
    root = Path(env["L9_AUTHORITY_MANAGED_ROOT"])
    _run(env)
    (upstream / "new.txt").write_text("x", encoding="utf-8")
    _git(upstream, "add", "new.txt")
    _git(upstream, "commit", "--quiet", "-m", "moved")
    line = _run(env)
    assert "fetched" in line and "left as is" not in line
    assert _git(root, "rev-parse", "HEAD") == _git(upstream, "rev-parse", "HEAD")


def test_a_checkout_off_main_is_reported_never_moved(tmp_path: Path, upstream: Path) -> None:
    env = _env(tmp_path, upstream, L9_AUTHORITY_FETCH_TTL_S="0")
    root = Path(env["L9_AUTHORITY_MANAGED_ROOT"])
    _run(env)
    _git(root, "checkout", "--quiet", "-b", "operator-work")
    head = _git(root, "rev-parse", "HEAD")
    line = _run(env)
    assert "HEAD is operator-work, not main; left as is" in line
    assert _git(root, "symbolic-ref", "--short", "HEAD") == "operator-work"
    assert _git(root, "rev-parse", "HEAD") == head


def test_a_foreign_directory_is_left_untouched(tmp_path: Path, upstream: Path) -> None:
    env = _env(tmp_path, upstream)
    root = Path(env["L9_AUTHORITY_MANAGED_ROOT"])
    root.mkdir(parents=True)
    (root / "keep.txt").write_text("mine", encoding="utf-8")
    assert "UNAVAILABLE" in _run(env)
    assert (root / "keep.txt").read_text(encoding="utf-8") == "mine"
    assert not (root / ".git").exists()


def test_an_operator_authority_root_is_never_touched(tmp_path: Path, upstream: Path) -> None:
    env = _env(tmp_path, upstream, L9_AUTHORITY_ROOT=str(tmp_path / "operator"))
    assert "operator path" in _run(env)
    assert not Path(env["L9_AUTHORITY_MANAGED_ROOT"]).exists()


def test_resolver_prefers_the_managed_checkout_over_workspace_guesses(
    tmp_path: Path, upstream: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ops.scripts import coding_projection_status as cps

    managed = tmp_path / "managed/.github"
    sibling = tmp_path / "ws_parent/.github"
    for path in (managed, sibling):
        subprocess.run(["git", "clone", "--quiet", str(upstream), str(path)], check=True)
        _git(path, "remote", "set-url", "origin", CANONICAL)
    workspace = tmp_path / "ws_parent/repo"
    workspace.mkdir()
    monkeypatch.delenv("L9_AUTHORITY_ROOT", raising=False)
    monkeypatch.setenv("L9_AUTHORITY_MANAGED_ROOT", str(managed))
    root, _ = cps._authority(workspace, None)
    assert root == managed.resolve()
    # An explicit operator choice still wins over the managed checkout.
    monkeypatch.setenv("L9_AUTHORITY_ROOT", str(sibling))
    root, _ = cps._authority(workspace, None)
    assert root == sibling.resolve()
    # Without a managed checkout the workspace sibling is still found.
    monkeypatch.delenv("L9_AUTHORITY_ROOT")
    monkeypatch.setenv("L9_AUTHORITY_MANAGED_ROOT", str(tmp_path / "absent"))
    root, _ = cps._authority(workspace, None)
    assert root == sibling.resolve()


def test_both_session_start_hooks_provision_before_binding() -> None:
    cursor = (REPO / "ops/hooks/session_start_bootstrap.sh").read_text(encoding="utf-8")
    assert cursor.index("ensure_authority_checkout.sh") < cursor.index('"$HOST_BINDING_PY"')
    for rel in (
        "environment/agents/adapters/claude-code/hooks/session_start_claude_governance.sh",
        ".claude/hooks/session_start_claude_governance.sh",
    ):
        claude = (REPO / rel).read_text(encoding="utf-8")
        assert claude.index("emit_authority_checkout\n") < claude.index(
            'emit_operating_plane_projection "$PY"\n'
        )


def test_a_shallow_checkout_is_unshallowed(tmp_path: Path, upstream: Path) -> None:
    """The verifiers refuse a shallow checkout (AUTHORITY_CHECKOUT_SHALLOW)."""
    env = _env(tmp_path, upstream)
    root = Path(env["L9_AUTHORITY_MANAGED_ROOT"])
    root.parent.mkdir(parents=True)
    subprocess.run(
        ["git", "clone", "--quiet", "--depth", "1", upstream.as_uri(), str(root)], check=True
    )
    _git(root, "remote", "set-url", "origin", CANONICAL)
    assert _git(root, "rev-parse", "--is-shallow-repository") == "true"
    assert _run(env).startswith("AUTHORITY: READY")
    assert _git(root, "rev-parse", "--is-shallow-repository") == "false"


def test_a_failed_first_fetch_names_the_private_repository_causes(tmp_path: Path) -> None:
    """Quantum-L9/.github is private: an unreachable fetch must say how to fix it, not just 'offline?'."""
    env = _env(tmp_path, tmp_path / "no-such-upstream")
    line = _run(env)
    assert line.startswith("AUTHORITY: UNAVAILABLE first fetch")
    assert "no GitHub credential for the private repository" in line
    assert "not started with Quantum-L9/.github selected" in line


def test_fetches_offer_the_gh_credential_helper() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'credential.helper=!gh auth git-credential' in text
    assert text.count('git ${AUTH[@]+"${AUTH[@]}"} -C "$1" fetch') == 2
