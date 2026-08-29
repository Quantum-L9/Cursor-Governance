"""PR_STACK=auto binds the unique chain tip before pr-check, not after it."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
LIB = SCRIPTS / "lib" / "resolve_pr_stack.sh"
GATE = SCRIPTS / "run_pr_gate.sh"
PREFLIGHT = SCRIPTS / "pr_preflight.sh"
OPEN_PR = SCRIPTS / "open_pr_after_gate.sh"
MAKEFILE = ROOT / "Makefile"


def _run(
    args: list[str], *, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    merged = {**os.environ, **(env or {})}
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        env=merged,
    )


def git_in(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    git_in(repo, "init")
    git_in(repo, "config", "user.email", "test@example.com")
    git_in(repo, "config", "user.name", "test")
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    git_in(repo, "add", "README.md")
    git_in(repo, "commit", "-m", "init")
    git_in(repo, "branch", "-M", "main")
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    git_in(repo, "update-ref", "refs/remotes/origin/main", sha)
    return repo


def _write_tip_stub(path: Path, *, tip: str, sha: str, reason: str, exit_code: int = 0) -> None:
    path.write_text(
        "\n".join(
            [
                "import sys",
                f"print('STACK_TIP={tip}')",
                f"print('STACK_TIP_SHA={sha}')",
                f"print('REASON={reason}')",
                f"raise SystemExit({exit_code})",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _apply(repo: Path, stub: Path, extra_env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    script = (
        f"source '{LIB}' && "
        f"pr_stack_apply_publish_base '{repo}' && "
        'printf "BOUND=%s\\n" "$PR_BASE"'
    )
    env = {
        "L9_STACK_TIP_RESOLVER": str(stub),
        "PR_BASE": "origin/main",
        **extra_env,
    }
    return _run(["bash", "-c", script], cwd=repo, env=env)


def test_empty_pr_stack_does_not_call_resolver(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    stub = tmp_path / "refuse.py"
    stub.write_text(
        "raise SystemExit('resolver must not run when PR_STACK is empty')\n",
        encoding="utf-8",
    )
    result = _apply(repo, stub, {"PR_STACK": ""})
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "resolver must not run" not in combined
    assert "BOUND=origin/main" in result.stdout


def test_auto_rewrites_default_main_to_unique_tip(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    git_in(repo, "update-ref", "refs/remotes/origin/feat/stack-safe-merge", sha)
    stub = tmp_path / "tip.py"
    _write_tip_stub(stub, tip="feat/stack-safe-merge", sha=sha, reason="unique_chain_tip")
    result = _apply(repo, stub, {"PR_STACK": "auto"})
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "BOUND=origin/feat/stack-safe-merge" in result.stdout
    assert "PR_STACK=auto resolved stack tip origin/feat/stack-safe-merge" in combined
    receipt = repo / ".l9" / "pr" / "stack-base.json"
    assert receipt.is_file()
    assert "origin/feat/stack-safe-merge" in receipt.read_text(encoding="utf-8")


def test_explicit_non_main_base_is_not_rewritten(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    stub = tmp_path / "refuse.py"
    stub.write_text(
        "raise SystemExit('resolver must not run for explicit PR_BASE')\n",
        encoding="utf-8",
    )
    result = _apply(
        repo,
        stub,
        {"PR_STACK": "auto", "PR_BASE": "origin/feat/already-stacked"},
    )
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "resolver must not run" not in combined
    assert "BOUND=origin/feat/already-stacked" in result.stdout


def test_siblings_fail_closed(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    stub = tmp_path / "sib.py"
    stub.write_text(
        "import sys\n"
        "print('FAIL: sibling open-PR chains target main: "
        "#10:feat/one, #11:feat/two', file=sys.stderr)\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    result = _apply(repo, stub, {"PR_STACK": "auto"})
    combined = result.stdout + result.stderr
    assert result.returncode == 2
    assert "feat/one" in combined
    assert "could not resolve a unique stack tip" in combined


def test_gh_unavailable_keeps_main(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    stub = tmp_path / "gh.py"
    stub.write_text(
        "import sys\n"
        "print('FAIL: gh CLI unavailable; refuse to guess the stack tip', file=sys.stderr)\n"
        "raise SystemExit(2)\n",
        encoding="utf-8",
    )
    result = _apply(repo, stub, {"PR_STACK": "auto"})
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "keeping PR_BASE=origin/main" in combined
    assert "BOUND=origin/main" in result.stdout


def test_receipt_reuse_skips_resolver(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    git_in(repo, "update-ref", "refs/remotes/origin/feat/stack-safe-merge", sha)
    stub = tmp_path / "tip.py"
    _write_tip_stub(stub, tip="feat/stack-safe-merge", sha=sha, reason="unique_chain_tip")
    first = _apply(repo, stub, {"PR_STACK": "auto"})
    assert first.returncode == 0, first.stdout + first.stderr
    refuse = tmp_path / "refuse.py"
    refuse.write_text(
        "raise SystemExit('resolver must not run on receipt reuse')\n",
        encoding="utf-8",
    )
    second = _apply(repo, refuse, {"PR_STACK": "auto"})
    combined = second.stdout + second.stderr
    assert second.returncode == 0, combined
    assert "resolver must not run" not in combined
    assert "reuse stack-base receipt" in combined
    assert "BOUND=origin/feat/stack-safe-merge" in second.stdout


def test_gate_resolves_stack_before_changed_files() -> None:
    gate = GATE.read_text(encoding="utf-8")
    apply_at = gate.find("pr_stack_apply_publish_base")
    digest_at = gate.find("--print-state-digest")
    changed_at = gate.find("resolve_changed_files.sh")
    assert apply_at != -1
    assert digest_at != -1
    assert changed_at != -1
    assert digest_at < apply_at < changed_at


def test_generated_heal_is_serialized_before_reader_wave() -> None:
    gate = GATE.read_text(encoding="utf-8")
    heal_at = gate.find("=== generated heal (serialized writer) ===")
    wave_at = gate.find("=== reader wave (once, parallel) ===")
    assert heal_at != -1 and wave_at != -1
    assert heal_at < wave_at
    assert "_wave_start sync " not in gate
    assert "commit the rewrite, then re-run make pr." in gate[heal_at:wave_at]
    readers = gate[gate.find("_gate_run_readers") : wave_at]
    assert "files were modified by this hook" in readers
    assert "modified-files window" in readers


def test_makefile_passes_pr_stack_into_gate_recipes() -> None:
    makefile = MAKEFILE.read_text(encoding="utf-8")
    preflight = makefile.split("pr-preflight:", 1)[1].split("\n\n", 1)[0]
    pr_check = makefile.split("pr-check:", 1)[1].split("\n\n", 1)[0]
    assert 'PR_STACK="$(PR_STACK)"' in preflight
    assert 'PR_STACK="$(PR_STACK)"' in pr_check
    precommit_repo = makefile.split("precommit-repo:", 1)[1].split("\n\n", 1)[0]
    assert 'PR_STACK="$(PR_STACK)"' in precommit_repo
    assert "pr_stack_apply_publish_base" in PREFLIGHT.read_text(encoding="utf-8")
    assert "pr_stack_apply_publish_base" in OPEN_PR.read_text(encoding="utf-8")
    assert "pr_stack_apply_publish_base" in GATE.read_text(encoding="utf-8")
    assert "pr_stack_apply_publish_base" in (
        ROOT / "ops" / "scripts" / "run_pr_precommit.sh"
    ).read_text(encoding="utf-8")
