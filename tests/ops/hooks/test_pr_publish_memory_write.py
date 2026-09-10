"""make pr last-step memory handoff — fact shape, fail-open, ceremony wire."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "hooks"))

import pr_publish_memory_write as hook  # noqa: E402

OPEN_PR = ROOT / "ops" / "scripts" / "open_pr_after_gate.sh"


def _summary(**overrides: object) -> dict:
    doc = {
        "schema": "l9.pr_summary.v1",
        "repo": "Quantum-L9/Cursor-Governance",
        "number": 542,
        "url": "https://github.com/Quantum-L9/Cursor-Governance/pull/542",
        "title": "Fire the tree-kernel latch on Cursor",
        "base": "main",
        "head": "fix/cursor-execution-velocity",
        "head_sha": "deadbeefcafebabe",
        "changed_files": 3,
        "additions": 40,
        "deletions": 2,
        "files": [
            {"path": "ops/autonomy/kernel_gate.py", "status": "modified"},
            {"path": "AGENTS.md", "status": "modified"},
            {"path": "ops/hooks/pr_publish_memory_write.py", "status": "added"},
        ],
    }
    doc.update(overrides)
    return doc


def test_fact_is_one_pickup_handoff_with_next_owned_action() -> None:
    fact = hook.format_fact(_summary(), remediates=False)
    assert fact is not None
    assert fact.startswith("PICKUP: PR Quantum-L9/Cursor-Governance#542 published.")
    assert "url=https://github.com/Quantum-L9/Cursor-Governance/pull/542" in fact
    assert "head=fix/cursor-execution-velocity" in fact
    assert "sha=deadbeefcafe" in fact
    assert "files=3 +40/-2" in fact
    assert "paths: ops/autonomy/kernel_gate.py AGENTS.md" in fact
    assert "next=/l9-pr-remediation Converge" in fact
    assert "open_prs=0" in fact
    assert "PR_REMEDIATE=0" in fact


def test_remediates_flag_changes_only_the_spawn_clause() -> None:
    off = hook.format_fact(_summary(), remediates=False)
    on = hook.format_fact(_summary(), remediates=True)
    assert off is not None and on is not None
    assert "ceremony already requested a remediator spawn." in on
    assert "PR_REMEDIATE=0" in off
    assert "merge_now" in on and "merge_now" in off


def test_no_identity_means_no_fact() -> None:
    assert hook.format_fact({}, remediates=False) is None
    assert hook.format_fact({}, remediates=False, fallback={"repo": "o/n"}) is None


def test_fallback_identity_when_summary_is_missing() -> None:
    fact = hook.format_fact(
        {},
        remediates=True,
        fallback={
            "repo": "o/n",
            "number": 7,
            "url": "https://example.test/7",
            "head": "feat/x",
            "head_sha": "abc1234ffff",
        },
    )
    assert fact is not None
    assert "PR o/n#7 published." in fact
    assert "url=https://example.test/7" in fact
    assert "sha=abc1234ffff" in fact


def test_path_list_is_capped() -> None:
    files = [{"path": f"f{i}.py"} for i in range(hook.MAX_PATHS + 5)]
    fact = hook.format_fact(
        _summary(changed_files=hook.MAX_PATHS + 5, files=files), remediates=True
    )
    assert fact is not None
    assert f"+{5} more" in fact
    assert "f0.py" in fact
    assert f"f{hook.MAX_PATHS}.py" not in fact


def test_write_argv_is_operator_cli_pickup_not_a_provider_client() -> None:
    argv = hook.write_argv(
        interpreter=Path("/gov/.venv/bin/python"),
        workspace=Path("/ws"),
        content="PICKUP: PR o/n#1 published.",
        key="pr-publish:o/n#1@abc",
        agent_id="cursor",
        dry_run=True,
    )
    assert argv[:6] == [
        "/gov/.venv/bin/python",
        "-m",
        "ops.memory.cli",
        "write",
        "PICKUP: PR o/n#1 published.",
        "--kind",
    ]
    assert "pickup_context" in argv
    assert "--dry-run" in argv
    assert "graphiti_memory_client" not in " ".join(argv)


def test_disabled_switch_skips_without_calling_memory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("L9_PR_PUBLISH_MEMORY", "0")
    called: list[object] = []
    monkeypatch.setattr(hook, "run_write", lambda *a, **k: called.append((a, k)))
    rc = hook.main(
        [
            "--workspace",
            str(tmp_path),
            "--gov-root",
            str(tmp_path),
            "--repo",
            "o/n",
            "--number",
            "1",
        ]
    )
    assert rc == 0
    assert called == []
    receipt = json.loads((tmp_path / hook.RECEIPT_REL).read_text(encoding="utf-8"))
    assert receipt["status"] == "SKIP"


def test_cli_failure_is_warn_and_exit_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".l9" / "pr").mkdir(parents=True)
    (tmp_path / hook.SUMMARY_REL).write_text(json.dumps(_summary()), encoding="utf-8")
    monkeypatch.delenv("L9_PR_PUBLISH_MEMORY", raising=False)
    monkeypatch.setenv("L9_MEMORY_ENABLED", "1")
    monkeypatch.setattr(
        hook,
        "run_write",
        lambda argv, cwd: SimpleNamespace(returncode=3, stdout="", stderr="unbound"),
    )
    rc = hook.main(["--workspace", str(tmp_path), "--gov-root", str(tmp_path)])
    assert rc == 0
    receipt = json.loads((tmp_path / hook.RECEIPT_REL).read_text(encoding="utf-8"))
    assert receipt["status"] == "WARN"
    assert receipt["returncode"] == 3


def test_open_pr_after_gate_fires_the_hook_after_the_summary() -> None:
    text = OPEN_PR.read_text(encoding="utf-8")
    assert "pr_publish_memory_write.py" in text
    assert text.index("write_pr_summary.py") < text.index("pr_publish_memory_write.py")
    assert "graphiti_memory_client" not in text
