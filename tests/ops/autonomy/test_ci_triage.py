"""ci_triage.py: l9.ci-triage/v1 verdicts from recorded REST payloads.

Each fixture is shaped like the GitHub REST responses the tool reads
(pulls/{n}, pulls/{n}/files, commits/{sha}/check-runs,
check-runs/{id}/annotations, actions/jobs/{id}/logs). The evidence strings are
the ones observed in the Odoo pre-go-live campaign.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

import ci_triage  # noqa: E402

REPO = "acme/odoo"
PR = 42
HEAD = "a" * 40
BASE = "b" * 40

BILLING_MSG = (
    "The job was not started because recent account payments have failed or your "
    "spending limit needs to be increased. Please check the 'Billing & plans' section "
    "of your settings"
)


def _run(
    run_id: int,
    name: str,
    conclusion: str | None,
    *,
    status: str = "completed",
    output: dict[str, Any] | None = None,
    actions: bool = True,
) -> dict[str, Any]:
    return {
        "id": run_id,
        "name": name,
        "head_sha": HEAD,
        "status": status,
        "conclusion": conclusion,
        "started_at": "2026-11-22T10:00:00Z",
        "completed_at": "2026-11-22T10:05:00Z" if status == "completed" else None,
        "details_url": f"https://github.com/{REPO}/actions/runs/9/job/{run_id}",
        "app": {"id": 15368, "slug": "github-actions"} if actions else {"id": 1, "slug": "other"},
        "output": output or {"title": None, "summary": None, "text": None},
    }


def _payloads(
    runs: list[dict[str, Any]],
    *,
    files: list[str] = (),  # type: ignore[assignment]
    annotations: dict[int, list[dict[str, Any]]] | None = None,
    logs: dict[int, str] | None = None,
    base_runs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fixture: dict[str, Any] = {
        f"repos/{REPO}/pulls/{PR}": {
            "number": PR,
            "head": {"sha": HEAD, "ref": "feature"},
            "base": {"sha": BASE, "ref": "Staging"},
        },
        f"repos/{REPO}/pulls/{PR}/files?per_page=100&page=1": [{"filename": f} for f in files],
        f"repos/{REPO}/commits/{HEAD}/check-runs?per_page=100": {
            "total_count": len(runs),
            "check_runs": runs,
        },
        f"repos/{REPO}/branches/Staging": {"name": "Staging", "commit": {"sha": BASE}},
        f"repos/{REPO}/commits/{BASE}/check-runs?per_page=100": {
            "total_count": len(base_runs or []),
            "check_runs": base_runs or [],
        },
    }
    for run in runs:
        fixture[f"repos/{REPO}/check-runs/{run['id']}/annotations?per_page=100"] = (
            annotations or {}
        ).get(run["id"], [])
    for job, text in (logs or {}).items():
        fixture[f"repos/{REPO}/actions/jobs/{job}/logs"] = text
    return fixture


class Recorder:
    """fixture_fetch that also records which REST paths were read."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self.fetch = ci_triage.fixture_fetch(fixture)
        self.paths: list[str] = []

    def __call__(self, path: str) -> Any:
        self.paths.append(path)
        return self.fetch(path)


def _triage(fixture: dict[str, Any]) -> tuple[dict[str, Any], Recorder]:
    rec = Recorder(fixture)
    return ci_triage.classify(REPO, PR, fetch=rec), rec


def _only(doc: dict[str, Any]) -> dict[str, Any]:
    assert len(doc["checks"]) == 1
    return doc["checks"][0]


# --- document shape ----------------------------------------------------------


def test_document_shape_and_no_permission() -> None:
    doc, _ = _triage(_payloads([_run(1, "lint", "success")]))
    assert doc["schema"] == "l9.ci-triage/v1"
    assert doc["repo"] == REPO and doc["pr"] == PR and doc["head"] == HEAD
    assert doc["grants_permission"] is False
    check = _only(doc)
    assert set(check) == {
        "name",
        "conclusion",
        "verdict",
        "evidence",
        "failing_paths",
        "owner_hint",
    }
    assert check["verdict"] in ci_triage.VERDICTS


# --- one test per verdict ----------------------------------------------------


def test_pass() -> None:
    doc, rec = _triage(_payloads([_run(1, "lint", "success"), _run(2, "docs", "skipped")]))
    assert [c["verdict"] for c in doc["checks"]] == ["pass", "pass"]
    assert not any("annotations" in p or "/logs" in p for p in rec.paths)


def test_pending() -> None:
    doc, _ = _triage(_payloads([_run(1, "Static Analysis", None, status="in_progress")]))
    check = _only(doc)
    assert check["verdict"] == "pending"
    assert check["owner_hint"] == "unknown"


def test_billing_from_job_annotation() -> None:
    run = _run(7, "PR fast", "failure")
    fixture = _payloads(
        [run],
        annotations={
            7: [{"path": ".github", "annotation_level": "failure", "message": BILLING_MSG}]
        },
    )
    doc, rec = _triage(fixture)
    check = _only(doc)
    assert check["verdict"] == "billing"
    assert "recent account payments have failed" in check["evidence"]
    assert check["failing_paths"] == []  # ".github" is GitHub's placeholder path
    assert not any(p.endswith("/logs") for p in rec.paths), "billing needs no log read"


def test_infra_runner_lost() -> None:
    run = _run(8, "tests", "failure")
    fixture = _payloads(
        [run],
        annotations={
            8: [
                {
                    "path": ".github",
                    "annotation_level": "failure",
                    "message": "The hosted runner: GitHub Actions 12 lost communication with "
                    "the server.",
                }
            ]
        },
    )
    check = _only(_triage(fixture)[0])
    assert check["verdict"] == "infra"
    assert "lost communication with the server" in check["evidence"]


def test_infra_checkout_network_in_log() -> None:
    log = (
        "2026-11-22T10:00:01.1234567Z ##[group]Run actions/checkout@v4\n"
        "2026-11-22T10:00:09.0000000Z fatal: unable to access "
        "'https://github.com/acme/odoo/': Could not resolve host: github.com\n"
        "2026-11-22T10:00:09.1000000Z ##[error]The process '/usr/bin/git' failed "
        "with exit code 128\n"
    )
    check = _only(_triage(_payloads([_run(9, "tests", "failure")], logs={9: log}))[0])
    assert check["verdict"] == "infra"
    assert "unable to access" in check["evidence"]
    assert not check["evidence"].startswith("2026"), "log timestamps are stripped"


def test_infra_startup_failure_without_evidence() -> None:
    check = _only(_triage(_payloads([_run(10, "deploy", "startup_failure")]))[0])
    assert check["verdict"] == "infra"
    assert check["evidence"] == "conclusion startup_failure"


def test_stale_baseline_from_summary() -> None:
    output = {
        "title": "Static Analysis",
        "summary": "✅ Ruff\n❌ Audit class detectors\n"
        "stale baseline entry BAN001 addons/sale_x/models/order.py no longer occurs",
        "text": None,
    }
    check = _only(_triage(_payloads([_run(11, "Static Analysis", "failure", output=output)]))[0])
    assert check["verdict"] == "stale_baseline"
    assert "stale baseline entry" in check["evidence"]
    assert check["failing_paths"] == ["addons/sale_x/models/order.py"]


def test_gate_config_from_summary() -> None:
    output = {
        "title": "Static Analysis",
        "summary": "✅ Ruff\n❌ Audit class detectors\n2 detectors failed to load",
        "text": None,
    }
    check = _only(_triage(_payloads([_run(12, "Static Analysis", "failure", output=output)]))[0])
    assert check["verdict"] == "gate_config"
    assert "Audit class detectors" in check["evidence"]


def test_scope_unknown_named_in_log() -> None:
    log = "pr_fast: unknown path addons/new_mod/__init__.py\nProcess completed with exit code 1.\n"
    check = _only(_triage(_payloads([_run(13, "PR fast", "failure")], logs={13: log}))[0])
    assert check["verdict"] == "scope_unknown"
    assert "unknown path" in check["evidence"]


def test_scope_unknown_when_tests_pass_but_job_exits_non_zero() -> None:
    log = (
        "2026-11-22T10:01:00Z ============ 214 passed, 3 skipped in 81.2s ============\n"
        "2026-11-22T10:01:01Z ##[error]Process completed with exit code 1.\n"
    )
    check = _only(_triage(_payloads([_run(14, "PR fast", "failure")], logs={14: log}))[0])
    assert check["verdict"] == "scope_unknown"
    assert "214 passed" in check["evidence"] and "exit code 1" in check["evidence"]


def test_code_ruff_in_log_owned_by_this_pr() -> None:
    log = (
        "2026-11-22T10:00:00Z Run ruff check .\n"
        "2026-11-22T10:00:01Z addons/sale_x/models/order.py:3:1: "
        "E401 Multiple imports on one line\n"
        "2026-11-22T10:00:01Z Found 1 error.\n"
        "2026-11-22T10:00:02Z ##[error]Process completed with exit code 1.\n"
    )
    fixture = _payloads(
        [_run(15, "lint", "failure")],
        files=["addons/sale_x/models/order.py"],
        logs={15: log},
    )
    check = _only(_triage(fixture)[0])
    assert check["verdict"] == "code"
    assert "E401" in check["evidence"]
    assert check["failing_paths"] == ["addons/sale_x/models/order.py"]
    assert check["owner_hint"] == "this_pr"


def test_code_ban_rule_and_pytest_failure() -> None:
    log = (
        "BAN001 banned call in addons/sale_x/wizard/close.py:88\n"
        "FAILED addons/sale_x/tests/test_close.py::test_close_order - AssertionError\n"
        "= 1 failed, 40 passed in 9.1s =\n"
    )
    check = _only(_triage(_payloads([_run(16, "tests", "failure")], logs={16: log}))[0])
    assert check["verdict"] == "code"
    assert check["failing_paths"] == [
        "addons/sale_x/wizard/close.py",
        "addons/sale_x/tests/test_close.py",
    ]


def test_code_from_failure_annotation_with_path_skips_log() -> None:
    run = _run(17, "semgrep", "failure")
    fixture = _payloads(
        [run],
        annotations={
            17: [
                {
                    "path": "/home/runner/work/odoo/odoo/addons/sale_x/controllers/api.py",
                    "annotation_level": "failure",
                    "title": "python.lang.security.audit.eval-detected",
                    "message": "Detected the use of eval().",
                }
            ]
        },
    )
    doc, rec = _triage(fixture)
    check = _only(doc)
    assert check["verdict"] == "code"
    assert check["failing_paths"] == ["addons/sale_x/controllers/api.py"]
    assert not any(p.endswith("/logs") for p in rec.paths)


def test_unknown_when_log_names_only_an_exit_code() -> None:
    log = "Running step\n##[error]Process completed with exit code 2.\n"
    check = _only(_triage(_payloads([_run(18, "build", "failure")], logs={18: log}))[0])
    assert check["verdict"] == "unknown"
    assert "exit code 2" in check["evidence"]


def test_unknown_for_non_actions_check_without_evidence() -> None:
    check = _only(_triage(_payloads([_run(19, "external-ci", "failure", actions=False)]))[0])
    assert check["verdict"] == "unknown"


def test_unknown_when_log_read_fails() -> None:
    fixture = _payloads([_run(20, "tests", "failure")])  # no log recorded
    check = _only(_triage(fixture)[0])
    assert check["verdict"] == "unknown"
    assert "job log unavailable" in check["evidence"]


# --- owner_hint --------------------------------------------------------------


def test_owner_hint_base_when_same_check_fails_on_base_head() -> None:
    log = "lib/legacy.py:1:1: E401 Multiple imports on one line\n"
    base_run = dict(_run(99, "lint", "failure"), head_sha=BASE)
    fixture = _payloads(
        [_run(21, "lint", "failure")],
        files=["addons/sale_x/models/order.py"],
        logs={21: log},
        base_runs=[base_run],
    )
    check = _only(_triage(fixture)[0])
    assert check["verdict"] == "code"
    assert check["owner_hint"] == "base"


def test_owner_hint_unknown_when_neither_diff_nor_base() -> None:
    log = "lib/legacy.py:1:1: E401 Multiple imports on one line\n"
    base_run = dict(_run(99, "lint", "success"), head_sha=BASE)
    fixture = _payloads(
        [_run(22, "lint", "failure")], files=["README.md"], logs={22: log}, base_runs=[base_run]
    )
    assert _only(_triage(fixture)[0])["owner_hint"] == "unknown"


def test_base_head_read_lazily_only_for_failures() -> None:
    _doc, rec = _triage(_payloads([_run(1, "lint", "success")]))
    assert not any(BASE in p or "branches/" in p for p in rec.paths)


def test_latest_run_per_name_wins() -> None:
    old = dict(_run(30, "lint", "failure"), started_at="2026-11-22T09:00:00Z")
    new = dict(_run(31, "lint", "success"), started_at="2026-11-22T11:00:00Z")
    check = _only(_triage(_payloads([old, new]))[0])
    assert check["verdict"] == "pass"


def test_explicit_sha_is_classified() -> None:
    other = "c" * 40
    fixture = _payloads([])
    fixture[f"repos/{REPO}/commits/{other}/check-runs?per_page=100"] = {
        "check_runs": [_run(40, "lint", "success")]
    }
    doc = ci_triage.classify(REPO, PR, other, fetch=ci_triage.fixture_fetch(fixture))
    assert doc["head"] == other
    assert _only(doc)["verdict"] == "pass"


def test_missing_pull_request_is_an_error() -> None:
    with pytest.raises(ci_triage.TriageError):
        ci_triage.classify(REPO, PR, fetch=ci_triage.fixture_fetch({}))


# --- CLI ---------------------------------------------------------------------


def _cli(tmp_path: Path, fixture: dict[str, Any], *args: str) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    env = {**os.environ, ci_triage.FIXTURE_ENV: str(path)}
    return subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, str(ROOT / "ops" / "autonomy" / "ci_triage.py"), "classify", *args],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_cli_json(tmp_path: Path) -> None:
    fixture = _payloads(
        [_run(7, "PR fast", "failure")],
        annotations={
            7: [{"path": ".github", "annotation_level": "failure", "message": BILLING_MSG}]
        },
    )
    proc = _cli(tmp_path, fixture, "--repo", REPO, "--pr", str(PR), "--json")
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(proc.stdout)
    assert doc["grants_permission"] is False
    assert doc["checks"][0]["verdict"] == "billing"


def test_cli_text(tmp_path: Path) -> None:
    proc = _cli(tmp_path, _payloads([_run(1, "lint", "success")]), "--repo", REPO, "--pr", str(PR))
    assert proc.returncode == 0, proc.stderr
    assert "grants_permission: false" in proc.stdout
    assert "pass" in proc.stdout and "lint" in proc.stdout


def test_cli_exits_2_when_the_pr_cannot_be_read(tmp_path: Path) -> None:
    proc = _cli(tmp_path, {}, "--repo", REPO, "--pr", str(PR), "--json")
    assert proc.returncode == 2
    assert "pull request read failed" in proc.stderr
