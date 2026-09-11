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


def test_fact_is_one_pickup_handoff_with_evidence() -> None:
    fact = hook.format_fact(_summary(), remediates=True)
    assert fact is not None
    assert fact.startswith("PICKUP: PR Quantum-L9/Cursor-Governance#542 published.")
    assert "url=https://github.com/Quantum-L9/Cursor-Governance/pull/542" in fact
    assert "head=fix/cursor-execution-velocity" in fact
    assert "sha=deadbeefcafe" in fact
    assert "files=3 +40/-2" in fact
    assert "paths: ops/autonomy/kernel_gate.py AGENTS.md" in fact


def test_remediation_enabled_may_describe_the_sanctioned_continuation() -> None:
    on = hook.format_fact(_summary(), remediates=True)
    assert on is not None
    assert "next=/l9-pr-remediation Converge" in on
    assert "open_prs=0" in on
    assert "ceremony already requested a remediator spawn." in on


def test_pr_remediate_zero_writes_no_remediation_or_merge_instruction() -> None:
    """The authority boundary, asserted on the durable payload itself.

    A publish-only run (`PR_REMEDIATE=0`, the standing campaign/L4 finish)
    must not leave a fact that tells the next agent to run the remediator,
    own every open PR, or launch merge_now. Merge stays separately authorized
    (rules/48, rules/88); it is not conveyed by a handoff this hook wrote.
    """
    off = hook.format_fact(_summary(), remediates=False)
    assert off is not None
    # It still records that publication happened, with its evidence.
    assert off.startswith("PICKUP: PR Quantum-L9/Cursor-Governance#542 published.")
    assert "sha=deadbeefcafe" in off
    assert "state=published-only" in off
    # And conveys no remediation or merge authority.
    for forbidden in ("/l9-pr-remediation", "merge_now", "open_prs=0", "owns merge"):
        assert forbidden not in off, forbidden


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


CURRENT = {
    "repo": "Quantum-L9/Cursor-Governance",
    "number": 543,
    "url": "https://github.com/Quantum-L9/Cursor-Governance/pull/543",
    "head": "agent/cursor/plan-prefetch-max-vel",
    "head_sha": "f18fcf321ace40f342e9868c8e0072ad7f98d8bc",
}


def _publish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, summary_doc, **over):
    """Run one publication, returning (receipt, written_fact)."""
    monkeypatch.delenv("L9_PR_PUBLISH_MEMORY", raising=False)
    monkeypatch.setenv("L9_MEMORY_ENABLED", "1")
    (tmp_path / ".l9" / "pr").mkdir(parents=True, exist_ok=True)
    if summary_doc is not None:
        (tmp_path / hook.SUMMARY_REL).write_text(
            summary_doc if isinstance(summary_doc, str) else json.dumps(summary_doc),
            encoding="utf-8",
        )
    seen: list[list[str]] = []

    def fake(argv, *, cwd, timeout=0.0):
        seen.append(argv)
        return SimpleNamespace(returncode=0, stdout="OK", stderr="")

    monkeypatch.setattr(hook, "run_write", fake)
    current = {**CURRENT, **over}
    rc = hook.main(
        [
            "--workspace",
            str(tmp_path),
            "--gov-root",
            str(tmp_path),
            "--repo",
            str(current["repo"]),
            "--number",
            str(current["number"]),
            "--url",
            str(current["url"]),
            "--head",
            str(current["head"]),
            "--head-sha",
            str(current["head_sha"]),
        ]
    )
    assert rc == 0
    receipt = json.loads((tmp_path / hook.RECEIPT_REL).read_text(encoding="utf-8"))
    fact = seen[0][4] if seen else ""
    return receipt, fact


def test_stale_summary_from_a_previous_pr_is_discarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """PR A published, its summary survives, PR B publishes.

    The handoff must not be written under PR A's identity or idempotency key.
    """
    receipt, fact = _publish(tmp_path, monkeypatch, _summary())  # summary says #542
    assert receipt["summary_identity"]["usable"] is False
    assert "number" in receipt["summary_identity"]["mismatched"]
    assert "#543" in fact and "#542" not in fact
    assert receipt["idempotency_key"] == f"pr-publish:{CURRENT['repo']}#543@{CURRENT['head_sha']}"
    # PR A's file list must not travel with PR B either.
    assert "ops/autonomy/kernel_gate.py" not in fact


def test_stale_summary_from_another_repository_is_discarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stale = _summary(repo="Quantum-L9/SEO-Bot", number=543, head_sha=CURRENT["head_sha"])
    receipt, fact = _publish(tmp_path, monkeypatch, stale)
    assert receipt["summary_identity"]["usable"] is False
    assert "repo" in receipt["summary_identity"]["mismatched"]
    assert "Quantum-L9/SEO-Bot" not in fact


def test_same_pr_at_an_earlier_head_sha_is_discarded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stale = _summary(repo=CURRENT["repo"], number=543, head=CURRENT["head"], head_sha="0" * 40)
    receipt, fact = _publish(tmp_path, monkeypatch, stale)
    assert receipt["summary_identity"]["usable"] is False
    assert "head_sha" in receipt["summary_identity"]["mismatched"]
    assert CURRENT["head_sha"][:12] in fact


def test_matching_summary_is_used_and_marked_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = _summary(
        repo=CURRENT["repo"],
        number=543,
        head=CURRENT["head"],
        head_sha=CURRENT["head_sha"],
    )
    receipt, fact = _publish(tmp_path, monkeypatch, fresh)
    assert receipt["summary_identity"]["usable"] is True
    assert receipt["summary_identity"]["verified"] is True
    # The matching summary's evidence IS used.
    assert "paths: ops/autonomy/kernel_gate.py" in fact


def test_missing_summary_falls_back_to_current_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt, fact = _publish(tmp_path, monkeypatch, None)
    assert "#543" in fact
    assert receipt["summary_identity"]["compared"] == []
    assert receipt["summary_identity"]["verified"] is False


def test_malformed_summary_does_not_crash_the_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt, fact = _publish(tmp_path, monkeypatch, "{ this is not json")
    assert receipt["status"] == "OK"
    assert "#543" in fact


def test_non_numeric_changed_files_does_not_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`changed_files` arrives from an external receipt; it may be anything."""
    odd = _summary(
        repo=CURRENT["repo"],
        number=543,
        head=CURRENT["head"],
        head_sha=CURRENT["head_sha"],
        changed_files="many",
    )
    receipt, fact = _publish(tmp_path, monkeypatch, odd)
    assert receipt["status"] == "OK"
    assert "paths: ops/autonomy/kernel_gate.py" in fact


@pytest.mark.parametrize("value", ["many", None, "", {"n": 1}, [1], True])
def test_format_fact_survives_any_changed_files_value(value: object) -> None:
    fact = hook.format_fact(_summary(changed_files=value), remediates=True)
    assert fact is not None and "paths: " in fact


def test_duplicate_publication_is_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same PR identity twice -> same key, so memory de-duplicates it.

    Idempotency is the memory service's own mechanism (`--idempotency-key`);
    this hook must not grow a second local store or lock.
    """
    fresh = _summary(
        repo=CURRENT["repo"], number=543, head=CURRENT["head"], head_sha=CURRENT["head_sha"]
    )
    first_receipt, first_fact = _publish(tmp_path, monkeypatch, fresh)
    second_receipt, second_fact = _publish(tmp_path, monkeypatch, fresh)
    assert first_receipt["idempotency_key"] == second_receipt["idempotency_key"]
    assert first_fact == second_fact


def test_write_timeout_is_warn_not_a_hung_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess as sp

    monkeypatch.delenv("L9_PR_PUBLISH_MEMORY", raising=False)
    monkeypatch.setenv("L9_MEMORY_ENABLED", "1")

    def hang(argv, **kwargs):
        raise sp.TimeoutExpired(argv, kwargs.get("timeout") or 0.0)

    monkeypatch.setattr(sp, "run", hang)
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
            "--head-sha",
            "abc",
        ]
    )
    assert rc == 0
    receipt = json.loads((tmp_path / hook.RECEIPT_REL).read_text(encoding="utf-8"))
    assert receipt["status"] == "WARN"
    assert receipt["timed_out"] is True


def test_open_pr_after_gate_passes_current_identity() -> None:
    """Identity binding is only possible because the caller supplies it."""
    text = OPEN_PR.read_text(encoding="utf-8")
    block = text.split("pr_publish_memory_write.py", 1)[1]
    for flag in ("--repo", "--number", "--head", "--head-sha", "--pr-remediate"):
        assert flag in block, flag


def test_open_pr_after_gate_fires_the_hook_after_the_summary() -> None:
    text = OPEN_PR.read_text(encoding="utf-8")
    assert "pr_publish_memory_write.py" in text
    assert text.index("write_pr_summary.py") < text.index("pr_publish_memory_write.py")
    assert "graphiti_memory_client" not in text
