"""gh_npm.sh uses gh auth token; never NODE_AUTH_TOKEN; never prints the token."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "ops" / "secrets" / "gh_npm.sh"


def _run(args: list[str], *, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
        check=False,
    )


def test_wraps_command_with_npm_config_from_gh(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "gh").write_text("#!/bin/sh\necho ghp_testtoken_not_a_secret\n", encoding="utf-8")
    (fake_bin / "gh").chmod((fake_bin / "gh").stat().st_mode | stat.S_IXUSR)
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import os\n"
        "for key, value in os.environ.items():\n"
        "    if 'npm.pkg.github.com' in key:\n"
        "        print(value)\n"
        "        break\n",
        encoding="utf-8",
    )
    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}
    env.pop("NODE_AUTH_TOKEN", None)
    result = _run(["bash", str(SCRIPT), "python3", str(probe)], env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ghp_testtoken_not_a_secret"
    assert "ghp_testtoken_not_a_secret" not in result.stderr


def test_usage_without_args() -> None:
    result = _run(["bash", str(SCRIPT)], env=os.environ.copy())
    assert result.returncode == 2
    assert "usage:" in result.stderr
