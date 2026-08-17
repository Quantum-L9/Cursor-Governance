"""Call ensure_workspace_wired.sh from Python worktree creators."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _script() -> Path | None:
    here = Path(__file__).resolve()
    candidate = here.parent / "ensure_workspace_wired.sh"
    if candidate.is_file():
        return candidate
    home = Path.home() / ".cursor-governance" / "ops" / "scripts" / "ensure_workspace_wired.sh"
    return home if home.is_file() else None


def ensure_workspace_wired(workspace: Path) -> int:
    """Wire gitignored .cursor links in *workspace*. Returns the script exit code.

    Missing script or missing directory is a no-op (0) so unit fixtures that
    never create a real folder do not fail. Production creators pass a real path.
    """
    path = Path(workspace)
    script = _script()
    if script is None or not path.is_dir():
        return 0
    env = os.environ.copy()
    env.setdefault("L9_WIRE_LINKS_ONLY", "1")
    result = subprocess.run(
        ["bash", str(script), str(path)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0 and result.stderr:
        print(result.stderr, end="")
    if result.stdout:
        print(result.stdout, end="")
    return result.returncode
