"""#904: the gate's locked ruff writer honours the consumer's ruff excludes.

The writer passes explicit changed paths to `ruff check --fix` and
`ruff format`. Without `--force-exclude`, ruff ignores `exclude` /
`extend-exclude` for explicitly named files, so the gate rewrote a consumer
fixture its configuration protects. A non-excluded file must still be written,
so the test also proves the writer ran.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"

FIXTURE = "import os\nx=1\n"
SOURCE = "x=1\n"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_locked_ruff_writer_leaves_excluded_fixtures_untouched(tmp_path: Path) -> None:
    repo = tmp_path / "consumer"
    (repo / "fixtures").mkdir(parents=True)
    (repo / "src").mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    (repo / "pyproject.toml").write_text(
        '[tool.ruff]\nextend-exclude = ["fixtures"]\n', encoding="utf-8"
    )
    (repo / "fixtures" / "bad.py").write_text(FIXTURE, encoding="utf-8")
    (repo / "src" / "ok.py").write_text(SOURCE, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "init")
    _git(repo, "branch", "-M", "main")

    changed = tmp_path / "changed.txt"
    changed.write_text("fixtures/bad.py\nsrc/ok.py\n", encoding="utf-8")
    observer = tmp_path / "observer.sh"
    observer.write_text("pre-commit() { return 0; }\n", encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(SCRIPTS / "run_pr_precommit.sh"), str(repo)],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
        timeout=300,
        env={
            **os.environ,
            "WS": str(repo),
            "PR_BASE": "main",
            "PR_CHANGED_FILE": str(changed),
            "PR_PRECOMMIT_STAGE": "writers",
            "PR_PRECOMMIT_DEFER_DIRTY_STOP": "1",
            "BASH_ENV": str(observer),
        },
    )
    out = proc.stdout + proc.stderr
    assert "ruff (changed): 2 file(s)" in out, out
    assert (repo / "fixtures" / "bad.py").read_text(encoding="utf-8") == FIXTURE, out
    assert (repo / "src" / "ok.py").read_text(encoding="utf-8") == "x = 1\n", out
