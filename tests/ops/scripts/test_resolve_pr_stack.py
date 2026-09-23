"""PR_STACK=auto binds the unique chain tip before the direct gate, not after it."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "ops" / "scripts"
LIB = SCRIPTS / "lib" / "resolve_pr_stack.sh"
GATE = SCRIPTS / "run_pr_gate.sh"
PREFLIGHT = SCRIPTS / "pr_preflight.sh"
OPEN_PR = SCRIPTS / "open_pr_after_gate.sh"
PUBLISH = ROOT / "ops" / "make" / "publish.mk"
QUALITY = ROOT / "ops" / "make" / "quality.mk"


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


def _write_tip_stub(
    path: Path, *, tip: str, sha: str, reason: str, exit_code: int = 0, chain: str = ""
) -> None:
    lines = [
        "import sys",
        f"print('STACK_TIP={tip}')",
        f"print('STACK_TIP_SHA={sha}')",
        f"print('REASON={reason}')",
    ]
    if chain:
        lines.append(f"print('STACK_CHAIN={chain}')")
    lines += [f"raise SystemExit({exit_code})", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


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


def test_receipt_records_the_whole_chain_not_only_the_tip(tmp_path: Path) -> None:
    """compose_pr_body.py excludes every chain head from a child's story.

    A stack parent cut before its own base was refreshed lends the child
    commits that are not the child's (PR #602's title). The tip alone cannot
    say which those are; the receipt has to carry the heads above it.
    """
    repo = _init_repo(tmp_path)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    git_in(repo, "update-ref", "refs/remotes/origin/feat/c", sha)
    stub = tmp_path / "tip.py"
    _write_tip_stub(
        stub, tip="feat/c", sha=sha, reason="unique_chain_tip", chain="feat/a feat/b feat/c"
    )
    result = _apply(repo, stub, {"PR_STACK": "auto"})
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    receipt = json.loads((repo / ".l9" / "pr" / "stack-base.json").read_text(encoding="utf-8"))
    assert receipt["chain"] == ["feat/a", "feat/b", "feat/c"]
    # No origin remote here: fetching the parents fails quietly and never gates.
    assert "BOUND=origin/feat/c" in result.stdout


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
    heal_block = gate[heal_at:wave_at]
    assert "commit the rewrite, then re-run make pr." in heal_block
    assert "_gate_run_projection_heal" in heal_block
    fn_at = gate.find("_gate_run_projection_heal() {")
    assert fn_at != -1 and fn_at < heal_at
    heal_fn = gate[fn_at:heal_at]
    assert "--quiet --no-receipt" in heal_fn
    assert "--check --quiet --no-receipt" not in heal_fn
    readers = gate[gate.find("_gate_run_readers") : wave_at]
    assert "files were modified by this hook" in readers
    assert "modified-files window" in readers


def test_makefile_passes_pr_stack_into_gate_recipes() -> None:
    publish = PUBLISH.read_text(encoding="utf-8")
    preflight = publish.split("pr-preflight:", 1)[1].split("\n\n", 1)[0]
    pr = publish.split("pr:", 1)[1].split("\n\n", 1)[0]
    assert 'PR_STACK="$(PR_STACK)"' in preflight
    assert 'PR_STACK="$(PR_STACK)"' in pr
    quality = QUALITY.read_text(encoding="utf-8")
    precommit_repo = quality.split("precommit-repo:", 1)[1].split("\n\n", 1)[0]
    # The quality recipe stays byte-identical; the simply-expanded export
    # remains in the publication fragment for GNU Make 3.81.
    assert 'PR_BASE="$(PR_BASE)"' in precommit_repo
    assert "bash ops/scripts/run_pr_precommit.sh" in precommit_repo
    assert "precommit-repo: export PR_STACK := $(PR_STACK)" in publish
    assert "precommit-repo: export PR_STACK = $(PR_STACK)" not in publish
    assert "pr_stack_apply_publish_base" in PREFLIGHT.read_text(encoding="utf-8")
    assert "pr_stack_apply_publish_base" in OPEN_PR.read_text(encoding="utf-8")
    assert "pr_stack_apply_publish_base" in GATE.read_text(encoding="utf-8")
    precommit = (ROOT / "ops" / "scripts" / "run_pr_precommit.sh").read_text(encoding="utf-8")
    assert "pr_stack_apply_publish_base" in precommit
    rem_at = precommit.find("L9_REMEDIATOR")
    apply_at = precommit.find("pr_stack_apply_publish_base")
    assert rem_at != -1
    assert rem_at < apply_at
    assert 'elif [[ -z "${PR_CHANGED_FILE:-}"' in precommit


def test_l9_remediator_skips_stack_tip_rewrite() -> None:
    precommit = (ROOT / "ops" / "scripts" / "run_pr_precommit.sh").read_text(encoding="utf-8")
    skip = precommit[
        precommit.find("_REMEDIATOR=") : precommit.find('elif [[ -z "${PR_CHANGED_FILE:-}"')
    ]
    assert "pr_stack_apply_publish_base" not in skip
    assert "PR_BASE=" in skip


def _apple_make() -> Path | None:
    make = Path("/usr/bin/make")
    if not make.is_file():
        return None
    ver = subprocess.run([str(make), "--version"], capture_output=True, text=True, check=False)
    if "GNU Make 3.81" not in (ver.stdout or ""):
        return None
    return make


def test_apple_make_381_snapshots_pr_stack_with_simply_expanded_export(
    tmp_path: Path,
) -> None:
    make = _apple_make()
    if make is None:
        pytest.skip("Apple /usr/bin/make 3.81 is not this host's make")
    probe = tmp_path / "t.mk"
    probe.write_text(
        "PR_STACK ?= auto\n"
        ".PHONY: precommit-repo\n"
        "precommit-repo: export PR_STACK := $(PR_STACK)\n"
        "precommit-repo:\n"
        "\t@echo env=$$PR_STACK\n",
        encoding="utf-8",
    )
    default = _run([str(make), "-f", str(probe), "precommit-repo"], cwd=tmp_path)
    assert default.returncode == 0, default.stderr
    assert "env=auto" in default.stdout
    empty = _run([str(make), "-f", str(probe), "precommit-repo", "PR_STACK="], cwd=tmp_path)
    assert empty.returncode == 0, empty.stderr
    assert empty.stdout.strip() == "env="
    custom = _run(
        [str(make), "-f", str(probe), "precommit-repo", "PR_STACK=custom"],
        cwd=tmp_path,
    )
    assert custom.returncode == 0, custom.stderr
    assert "env=custom" in custom.stdout


def test_apple_make_381_rejects_recursive_pr_stack_export(tmp_path: Path) -> None:
    make = _apple_make()
    if make is None:
        pytest.skip("Apple /usr/bin/make 3.81 is not this host's make")
    probe = tmp_path / "t.mk"
    probe.write_text(
        "PR_STACK ?= auto\n"
        ".PHONY: precommit-repo\n"
        "precommit-repo: export PR_STACK = $(PR_STACK)\n"
        "precommit-repo:\n"
        "\t@echo env=$$PR_STACK\n",
        encoding="utf-8",
    )
    result = _run([str(make), "-f", str(probe), "precommit-repo"], cwd=tmp_path)
    assert result.returncode != 0
    assert "Recursive variable" in (result.stderr or result.stdout)
