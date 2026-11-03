"""l9-plan-simple must validate in any repository, not only Cursor-Governance.

Regression: plan paths were recorded and resolved against the governance clone
(the scripts' own location). In a consumer repository the generator fell back
to a bare filename and the validator then reported
``G_RECEIPT_PATH: plan JSON missing``. Plans in the machine plans store broke
the same way.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FIXTURE = REPO / "skills" / "l9-plan" / "fixtures" / "plan_pass.json"
RENDERER = REPO / "skills" / "l9-plan" / "scripts" / "render_plan_pe_autonomy.py"
SCRIPTS = REPO / "skills" / "l9-plan-simple" / "scripts"
GENERATE = SCRIPTS / "generate_plan_section_receipt.py"
VALIDATE = SCRIPTS / "validate_plan_section_receipt.py"


def _run(args: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], cwd=cwd, env=env, capture_output=True, text=True, check=False
    )


def _consumer_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "consumer"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def _env(store: Path | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("L9_PLANS_STORE", None)
    if store is not None:
        env["L9_PLANS_STORE"] = str(store)
    return env


def _plan_and_receipt(cwd: Path, plan_dir: Path, env: dict[str, str]) -> Path:
    """Render, generate and return the receipt path, running from ``cwd``.

    The l9-plan renderer confines its input to the working directory, so it
    renders a working-tree copy; the plan pair then lives in ``plan_dir``.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_json = plan_dir / "plan.json"
    shutil.copyfile(FIXTURE, plan_json)
    render_src = cwd / ".l9" / "render-src.json"
    render_src.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURE, render_src)
    render = _run(
        [str(RENDERER), str(render_src), "--execute-via=cursor-build", "--workspace", "."],
        cwd,
        env,
    )
    assert render.returncode == 0, render.stderr
    plan_md = plan_dir / "demo_0123abcd.plan.md"
    plan_md.write_text(render.stdout, encoding="utf-8")
    receipt = plan_dir / "demo_0123abcd.section-receipt.json"
    gen = _run(
        [
            str(GENERATE),
            "--plan-json",
            str(plan_json),
            "--plan-md",
            str(plan_md),
            "--out",
            str(receipt),
            "--gar-invoked",
            "--gar-run-id",
            "consumer-test",
        ],
        cwd,
        env,
    )
    assert gen.returncode == 0, gen.stdout + gen.stderr
    return receipt


def test_receipt_validates_in_a_consumer_repository(tmp_path: Path) -> None:
    repo = _consumer_repo(tmp_path)
    env = _env()
    receipt = _plan_and_receipt(repo, repo / ".l9" / "plans", env)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["plan_json_path"] == ".l9/plans/plan.json"
    check = _run([str(VALIDATE), str(receipt)], repo, env)
    assert check.returncode == 0, check.stdout + check.stderr


def test_receipt_validates_from_a_consumer_subdirectory(tmp_path: Path) -> None:
    repo = _consumer_repo(tmp_path)
    env = _env()
    receipt = _plan_and_receipt(repo, repo / "docs" / "plans", env)
    sub = repo / "docs"
    check = _run([str(VALIDATE), str(receipt.relative_to(sub))], sub, env)
    assert check.returncode == 0, check.stdout + check.stderr


def test_receipt_validates_for_a_plan_in_the_plans_store(tmp_path: Path) -> None:
    repo = _consumer_repo(tmp_path)
    store = tmp_path / "plans-store"
    env = _env(store)
    receipt = _plan_and_receipt(repo, store, env)
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert Path(data["plan_json_path"]).is_absolute()
    check = _run([str(VALIDATE), str(receipt)], repo, env)
    assert check.returncode == 0, check.stdout + check.stderr
