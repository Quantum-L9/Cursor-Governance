"""#862: make pr commits generated-heal paths instead of publishing without them.

Deterministic preparation regenerated `ops/generated/skill-registry.json`; the
publish step WARNed "non-scratch dirty paths" and pushed only committed changes,
so the PR omitted the regenerated artifact the gate had validated. The heal block
commits exactly the generated paths and leaves any other dirt for the WARN.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "ops" / "scripts" / "open_pr_after_gate.sh"


def _function(text: str, name: str) -> str:
    match = re.search(rf"^{name}\(\) \{{\n.*?^\}}\n", text, re.M | re.S)
    assert match, f"{name} not defined in open_pr_after_gate.sh"
    return match.group(0)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def test_generated_heal_is_committed_and_other_dirt_is_left(tmp_path: Path) -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    funcs = _function(text, "_meaningful_dirty") + _function(text, "_commit_generated_heal")

    repo = tmp_path / "ws"
    (repo / "ops" / "generated").mkdir(parents=True)
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "ops" / "generated" / "skill-registry.json").write_text("{}\n", encoding="utf-8")
    (repo / "notes.py").write_text("a = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")
    (repo / "ops" / "generated" / "skill-registry.json").write_text('{"v": 2}\n', encoding="utf-8")
    (repo / "notes.py").write_text("a = 2\n", encoding="utf-8")

    proc = subprocess.run(
        ["bash", "-c", f'set -u\nGOV_ROOT="{ROOT}"\n{funcs}\n_commit_generated_heal'],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "OK: committed generated heal" in proc.stdout
    status = _git(repo, "status", "--porcelain")
    assert "skill-registry.json" not in status
    assert " M notes.py" in status
    assert _git(repo, "show", "--name-only", "--format=", "HEAD").split() == [
        "ops/generated/skill-registry.json"
    ]


def test_publish_runs_the_heal_before_the_dirty_warn() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    call = text.index("_commit_generated_heal || exit 1")
    assert call < text.index("WARN: working tree has non-scratch dirty paths")
    assert call < text.index("# L4 local autonomy — no mid-execution push")
