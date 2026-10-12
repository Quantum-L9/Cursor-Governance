"""stack_safe_merge.py must never emit --squash for a stack parent."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HELPER = Path(__file__).resolve().parents[3] / "ops" / "autonomy" / "stack_safe_merge.py"
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "autonomy"))

from stack_safe_merge import _execute, merge_argv, select_merge_method  # noqa: E402


def _probe(tmp_path: Path, entries: dict) -> str:
    path = tmp_path / "stack-probe.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return str(path)


def _env(tmp_path: Path, entries: dict) -> dict[str, str]:
    env = {**os.environ, "L9_STACK_PROBE_FILE": _probe(tmp_path, entries)}
    return env


STACKED = {"Quantum-L9/SEO-Bot#53": {"head": "fix/parent", "children": [54]}}
LEAF = {"Quantum-L9/SEO-Bot#53": {"head": "fix/leaf", "children": []}}


def test_parent_selects_merge_commit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, STACKED))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    assert chosen["method"] == "merge"
    assert chosen["children"] == [54]
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", selection=chosen)
    assert "--merge" in argv
    assert "--squash" not in argv


def test_leaf_selects_squash(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, LEAF))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    assert chosen["method"] == "squash"
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", selection=chosen)
    assert "--squash" in argv
    assert "--merge" not in argv


def test_cli_print_parent_never_names_squash(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(HELPER), "--repo", "Quantum-L9/SEO-Bot", "--pr", "53", "--print"],
        capture_output=True,
        text=True,
        env=_env(tmp_path, STACKED),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "--merge" in proc.stdout
    assert "--squash" not in proc.stdout


def test_cli_json_leaf_is_squash(tmp_path: Path) -> None:
    proc = subprocess.run(
        [sys.executable, str(HELPER), "--repo", "Quantum-L9/SEO-Bot", "--pr", "53", "--json"],
        capture_output=True,
        text=True,
        env=_env(tmp_path, LEAF),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["method"] == "squash"
    assert "--squash" in payload["argv"]


def test_parent_omits_delete_branch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, STACKED))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", delete_branch=True, selection=chosen)
    assert "--delete-branch" not in argv
    assert chosen["children"] == [54]


def test_leaf_keeps_delete_branch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, LEAF))
    chosen = select_merge_method("Quantum-L9/SEO-Bot", "53")
    argv = merge_argv("Quantum-L9/SEO-Bot", "53", delete_branch=True, selection=chosen)
    assert "--delete-branch" in argv


def test_execute_parent_skips_delete_ref(monkeypatch) -> None:
    runs: list[list[str]] = []

    def _capture(argv: list[str]) -> int:
        runs.append(argv)
        return 0

    monkeypatch.setattr("stack_safe_merge._run", _capture)
    selection = {
        "repo": "Quantum-L9/SEO-Bot",
        "pr": 53,
        "method": "merge",
        "head": "fix/parent",
        "children": [54],
    }
    assert _execute(selection, delete_branch=True) == 0
    joined = [" ".join(argv) for argv in runs]
    assert not any("DELETE" in line and "refs/heads/" in line for line in joined)
    assert any("pulls/53/merge" in line for line in joined)


def test_execute_failed_delete_already_absent_is_note(monkeypatch, capsys) -> None:
    def _run(argv: list[str]) -> int:
        if "--method" in argv and "DELETE" in argv:
            return 1
        joined = " ".join(argv)
        if "gh api " in joined + " " and "refs/heads/" in joined and "--method" not in argv:
            return 1
        return 0

    monkeypatch.setattr("stack_safe_merge._run", _run)
    selection = {
        "repo": "Quantum-L9/SEO-Bot",
        "pr": 90,
        "method": "squash",
        "head": "agent/cursor/org-nightly-caller",
        "children": [],
    }
    assert _execute(selection, delete_branch=True) == 0
    err = capsys.readouterr().err
    assert "NOTE: merged, and branch 'agent/cursor/org-nightly-caller' is already absent" in err
    assert "WARN:" not in err


def test_execute_failed_delete_still_present_is_warn(monkeypatch, capsys) -> None:
    def _run(argv: list[str]) -> int:
        if "--method" in argv and "DELETE" in argv:
            return 1
        return 0

    monkeypatch.setattr("stack_safe_merge._run", _run)
    selection = {
        "repo": "Quantum-L9/SEO-Bot",
        "pr": 90,
        "method": "squash",
        "head": "agent/cursor/org-nightly-caller",
        "children": [],
    }
    assert _execute(selection, delete_branch=True) == 0
    err = capsys.readouterr().err
    assert "WARN: merged, but deleting branch 'agent/cursor/org-nightly-caller' failed" in err
    assert "already absent" not in err


# --- §6.2.12: --run merges only under a human grant on the live head ----------

import stack_safe_merge  # noqa: E402

SHA = "c" * 40
MOVED = "d" * 40
SLUG = "Quantum-L9/SEO-Bot"


def _grant_file(tmp_path: Path, head_sha: str = SHA, **overrides) -> Path:
    import time

    entry = {
        "repo": SLUG,
        "pr": 53,
        "head_sha": head_sha,
        "issuer": "human",
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + 600,
        "reason": "reviewed",
    }
    entry.update(overrides)
    path = tmp_path / "grants" / "merge-authorization.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"authorizations": [entry]}), encoding="utf-8")
    return path


def _merge_run(
    tmp_path: Path,
    monkeypatch,
    *,
    probe: dict,
    grant: Path | None,
    head_sha: str = SHA,
) -> tuple[int, list[list[str]]]:
    runs: list[list[str]] = []
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, probe))
    monkeypatch.delenv("L9_STACK_SAFE_MERGE_DRY_RUN", raising=False)
    monkeypatch.setattr(
        stack_safe_merge, "_account_grant_path", lambda: grant or tmp_path / "none.json"
    )
    monkeypatch.setattr(stack_safe_merge, "_run", lambda argv: runs.append(argv) or 0)
    argv = ["--repo", SLUG, "--pr", "53", "--run"]
    if head_sha:
        argv += ["--head-sha", head_sha]
    return stack_safe_merge.main(argv), runs


LEAF_AT_SHA = {f"{SLUG}#53": {"head": "fix/leaf", "children": [], "sha": SHA}}
PARENT_AT_SHA = {f"{SLUG}#53": {"head": "fix/parent", "children": [54], "sha": SHA}}


def test_run_without_grant_is_merge_pending_and_never_merges(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    code, runs = _merge_run(tmp_path, monkeypatch, probe=LEAF_AT_SHA, grant=None)
    assert code == stack_safe_merge.MERGE_PENDING_EXIT
    assert runs == []
    record = json.loads(capsys.readouterr().out)
    assert record["status"] == "MERGE_PENDING"
    assert record["head_sha"] == SHA
    assert record["grant_command"].endswith(f"--pr 53 --head-sha {SHA}")
    # AGENTS.md: manual authorize_merge.py runs use the locked governance interpreter.
    assert record["grant_command"].startswith(
        '"$HOME/.cursor-governance/.venv/bin/python" '
        '"$HOME/.cursor-governance/ops/autonomy/authorize_merge.py" '
    )  # absolute script path: the human may run it from a consumer repository


def test_run_without_named_head_is_merge_pending(tmp_path: Path, monkeypatch) -> None:
    code, runs = _merge_run(
        tmp_path, monkeypatch, probe=LEAF_AT_SHA, grant=_grant_file(tmp_path), head_sha=""
    )
    assert (code, runs) == (stack_safe_merge.MERGE_PENDING_EXIT, [])


def test_run_when_live_head_moved_is_merge_pending(tmp_path: Path, monkeypatch) -> None:
    """Grant and request name SHA; GitHub now reports MOVED. Recheck wins."""
    moved = {f"{SLUG}#53": {"head": "fix/leaf", "children": [], "sha": MOVED}}
    code, runs = _merge_run(tmp_path, monkeypatch, probe=moved, grant=_grant_file(tmp_path))
    assert (code, runs) == (stack_safe_merge.MERGE_PENDING_EXIT, [])


def test_stale_grant_for_an_older_head_is_merge_pending(tmp_path: Path, monkeypatch) -> None:
    moved = {f"{SLUG}#53": {"head": "fix/leaf", "children": [], "sha": MOVED}}
    code, runs = _merge_run(
        tmp_path, monkeypatch, probe=moved, grant=_grant_file(tmp_path), head_sha=MOVED
    )
    assert (code, runs) == (stack_safe_merge.MERGE_PENDING_EXIT, [])


def test_expired_grant_is_merge_pending(tmp_path: Path, monkeypatch) -> None:
    grant = _grant_file(tmp_path, expires_at=1)
    code, runs = _merge_run(tmp_path, monkeypatch, probe=LEAF_AT_SHA, grant=grant)
    assert (code, runs) == (stack_safe_merge.MERGE_PENDING_EXIT, [])


def test_unknown_live_head_is_merge_pending(tmp_path: Path, monkeypatch) -> None:
    code, runs = _merge_run(tmp_path, monkeypatch, probe=LEAF, grant=_grant_file(tmp_path))
    assert (code, runs) == (stack_safe_merge.MERGE_PENDING_EXIT, [])


def test_process_env_cannot_impersonate_the_human(tmp_path: Path, monkeypatch) -> None:
    """This process's environment belongs to its caller, so neither the
    breakglass nor a redirected grant file authorizes the entrypoint."""
    monkeypatch.setenv("L9_MERGE_AUTHORIZED", "agent says a human approved")
    monkeypatch.setenv("L9_MERGE_AUTHORIZATION_FILE", str(_grant_file(tmp_path)))
    code, runs = _merge_run(tmp_path, monkeypatch, probe=LEAF_AT_SHA, grant=None)
    assert (code, runs) == (stack_safe_merge.MERGE_PENDING_EXIT, [])


def test_granted_leaf_merges_squash_bound_to_head(tmp_path: Path, monkeypatch) -> None:
    code, runs = _merge_run(tmp_path, monkeypatch, probe=LEAF_AT_SHA, grant=_grant_file(tmp_path))
    assert code == 0
    rest = runs[0]
    assert "merge_method=squash" in rest and f"sha={SHA}" in rest


def test_granted_stack_parent_still_merges_with_merge_commit(tmp_path: Path, monkeypatch) -> None:
    """Authority does not relax stack safety: a parent keeps --merge, no ref delete."""
    code, runs = _merge_run(tmp_path, monkeypatch, probe=PARENT_AT_SHA, grant=_grant_file(tmp_path))
    assert code == 0
    joined = [" ".join(argv) for argv in runs]
    assert "merge_method=merge" in joined[0] and f"sha={SHA}" in joined[0]
    assert not any("squash" in line for line in joined)
    assert not any("DELETE" in line for line in joined)


def test_cli_fallback_carries_match_head_commit(tmp_path: Path, monkeypatch) -> None:
    runs: list[list[str]] = []
    monkeypatch.setattr(
        stack_safe_merge, "_run", lambda argv: runs.append(argv) or (1 if len(runs) == 1 else 0)
    )
    selection = {"repo": SLUG, "pr": 53, "method": "squash", "head": "h", "children": []}
    assert stack_safe_merge._execute(selection, delete_branch=False, head_sha=SHA) == 0
    assert runs[1][-2:] == ["--match-head-commit", SHA]


def test_json_reports_live_head_and_merge_pending(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("L9_STACK_PROBE_FILE", _probe(tmp_path, LEAF_AT_SHA))
    monkeypatch.setattr(stack_safe_merge, "_account_grant_path", lambda: tmp_path / "none.json")
    assert stack_safe_merge.main(["--repo", SLUG, "--pr", "53", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["authorization"]["status"] == "MERGE_PENDING"
    assert payload["authorization"]["head_sha"] == SHA
    assert payload["method"] == "squash"
