"""Launcher refresh precedes HOOK_PATH so tip-only SessionStart files exist."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = (
    REPO_ROOT / "environment" / "agents" / "adapters" / "claude-code" / "hooks" / "l9_hook_exec.sh"
)
TIP_HOOK = "tip_only_observer.sh"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _origin_with_tip_only_hook(tmp: Path) -> tuple[Path, str]:
    work = tmp / "origin-work"
    work.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    _git(work, "config", "user.email", "t@e")
    _git(work, "config", "user.name", "t")
    (work / "CANONICAL_LAW.md").write_text("v1\n", encoding="utf-8")
    hooks = work / "environment" / "agents" / "adapters" / "claude-code" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "existing.sh").write_text("#!/usr/bin/env bash\necho existing\n", encoding="utf-8")
    _git(work, "add", "CANONICAL_LAW.md", "environment")
    _git(work, "commit", "-qm", "base")
    old = _git(work, "rev-parse", "HEAD").stdout.strip()
    (hooks / TIP_HOOK).write_text(
        "#!/usr/bin/env bash\necho TIP_ONLY_RAN\nexit 0\n",
        encoding="utf-8",
    )
    _git(work, "add", str(hooks / TIP_HOOK))
    _git(work, "commit", "-qm", "tip-only hook")
    origin = tmp / "origin.git"
    subprocess.run(["git", "clone", "--bare", "-q", str(work), str(origin)], check=True)
    return origin, old


def _clone_at(home: Path, origin: Path, sha: str) -> Path:
    gov = home / ".cursor-governance"
    subprocess.run(["git", "clone", "-q", str(origin), str(gov)], check=True)
    _git(gov, "checkout", "-q", sha)
    return gov


def _run_launcher(home: Path, origin: Path, hook_name: str) -> subprocess.CompletedProcess[str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "CURSOR_AGENT",
            "CLAUDECODE",
            "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_SESSION_ID",
            "L9_GOVERNANCE_SURFACE",
            "L9_GOVERNANCE_DIR",
        }
    }
    env.update(
        {
            "HOME": str(home),
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "CLAUDE_CODE_REMOTE": "true",
            "L9_SURFACE_GUARD": "0",
            "L9_GOVERNANCE_REMOTE": str(origin),
            "L9_GOVERNANCE_BRANCH": "main",
        }
    )
    return subprocess.run(
        ["bash", str(LAUNCHER), "--class", "observer", hook_name],
        cwd=str(home),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def test_launcher_refresh_precedes_hook_path_resolve() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert text.index("l9_cloud_refresh_gov") < text.index("HOOK_PATH=")
    assert subprocess.run(["bash", "-n", str(LAUNCHER)]).returncode == 0


def test_tip_only_hook_is_found_after_launcher_refresh(tmp_path: Path) -> None:
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    assert not (gov / "environment/agents/adapters/claude-code/hooks" / TIP_HOOK).is_file()
    result = _run_launcher(home, origin, TIP_HOOK)
    assert result.returncode == 0, result.stderr + result.stdout
    assert "TIP_ONLY_RAN" in result.stdout
    assert "hook file absent" not in result.stderr


def test_dirty_tracked_clone_is_not_force_reset(tmp_path: Path) -> None:
    origin, old = _origin_with_tip_only_hook(tmp_path)
    home = tmp_path / "home"
    home.mkdir()
    gov = _clone_at(home, origin, old)
    (gov / "CANONICAL_LAW.md").write_text("in-flight\n", encoding="utf-8")
    result = _run_launcher(home, origin, TIP_HOOK)
    assert result.returncode == 0, result.stderr
    assert (gov / "CANONICAL_LAW.md").read_text(encoding="utf-8") == "in-flight\n"
    assert "hook file absent" in result.stderr
    assert "TIP_ONLY_RAN" not in result.stdout
    assert not (gov / "environment/agents/adapters/claude-code/hooks" / TIP_HOOK).is_file()
