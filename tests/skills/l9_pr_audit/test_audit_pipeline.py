"""l9-pr-audit end-to-end pipeline: census -> lanes -> assemble -> derive -> validate -> bundle.

Offline and synthetic. The multi-PR case is the one that used to be unrepresentable: a clean
PR audited beside a PR with a merge-blocking finding must still project as ready, because an
audit-wide FAIL domain owned by another PR's finding is not this PR's defect.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "skills/l9-pr-audit/scripts"
ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
MAIN = "a" * 40
HEAD = {1: "b" * 40, 2: "c" * 40}
REPO_NAME = "Quantum-L9/example"


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)], capture_output=True, text=True, env=ENV
    )


def snapshot(n: int, files: list[dict]) -> dict:
    return {
        "repository": REPO_NAME,
        "pr_number": n,
        "base_sha": MAIN,
        "head_sha": HEAD[n],
        "base_ref": "main",
        "base_ref_sha": MAIN,
        "head_ref": f"feature-{n}",
        "title": f"PR {n}",
        "draft": False,
        "author": "dev",
        "intent": {"source_kind": "PR_BODY", "original_pr_prompt_available": False, "pr_body": ""},
        "files": files,
        "check_runs": [{"id": n, "name": "ci", "status": "completed", "conclusion": "success"}],
        "ci_failures": [],
        "review_threads": [],
        "approvals": [],
    }


def pyfile(path: str, base: str | None, head: str) -> dict:
    return {
        "path": path,
        "previous_path": None,
        "status": "added" if base is None else "modified",
        "additions": head.count("\n"),
        "deletions": 0,
        "patch": "".join(f"+{x}\n" for x in head.splitlines()),
        "base_content": base,
        "head_content": head,
    }


def evidence(locator: str, fact: str, **extra: object) -> dict:
    return {
        "locator": locator,
        "path": "src/b.py",
        "revision": HEAD[2],
        "evidence_type": "SOURCE",
        "status": "CONFIRMED",
        "fact": fact,
        "proves": [
            "implementation_surface",
            "behavior_mismatch",
            "finding_origin",
            "merge_blocking_basis",
        ],
        **extra,
    }


def lane_pr(n: int, readiness: str, files: list[str]) -> dict:
    return {
        "pr": n,
        "head_sha": HEAD[n],
        "objective": f"objective of PR {n}",
        "objective_closure": "ACHIEVED",
        "scope_fidelity": [
            {
                "path": p,
                "disposition": "VALIDATION_REQUIRED" if p.startswith("tests/") else "REQUIRED",
                "basis": "named by the objective",
            }
            for p in files
        ],
        "ci": [],
        "review_threads": [],
        "validation_runs": [
            {
                "command": "pytest -q",
                "tested_revision": HEAD[n],
                "result": "PASS",
                "discriminates_against_base": True,
                "properties_discriminated": "new tests fail on base",
            }
        ],
        "merge_conflict_with_main": False,
        "readiness": readiness,
        "readiness_basis": "lane verdict",
    }


@pytest.fixture()
def run_dir(tmp_path: Path) -> Path:
    files = {
        1: [
            pyfile("src/a.py", "def a():\n    return 1\n", "def a():\n    return 2\n"),
            pyfile(
                "tests/test_a.py",
                None,
                "def test_a():\n    payload = {'k': 1}\n    assert payload\n",
            ),
        ],
        2: [pyfile("src/b.py", "def b():\n    return 1\n", "def b(x):\n    return x\n")],
    }
    (tmp_path / "snapshots").mkdir()
    (tmp_path / "ledgers").mkdir()
    (tmp_path / "lanes").mkdir()
    for n, fs in files.items():
        (tmp_path / "snapshots" / f"pr-{n}.json").write_text(json.dumps(snapshot(n, fs)))
        done = run(
            SCRIPTS / "build_change_ledger.py",
            "--snapshot",
            tmp_path / "snapshots" / f"pr-{n}.json",
            "--output",
            tmp_path / "ledgers" / f"pr-{n}-ledger.json",
        )
        assert done.returncode == 0, done.stderr
    (tmp_path / "frozen-pr-set.json").write_text(
        json.dumps(
            {
                "repository": REPO_NAME,
                "default_branch": "main",
                "default_branch_sha": MAIN,
                "merge_rules": {
                    "source": "repos/x/rules/branches/main",
                    "required_status_checks": ["ci"],
                    "required_workflows": [],
                    "required_approving_review_count": 0,
                    "required_review_thread_resolution": True,
                },
                "prs": [
                    {"pr": n, "head_sha": HEAD[n], "base_ref": "main", "stacked_on": None}
                    for n in files
                ],
            }
        )
    )
    binding = run(SCRIPTS / "verify_canonical_authority.py", "--mode", "admitted")
    (tmp_path / "canonical-binding.json").write_text(binding.stdout)
    ledgers = [
        a for n in files for a in ("--change-ledger", tmp_path / "ledgers" / f"pr-{n}-ledger.json")
    ]
    done = run(
        SCRIPTS / "build_audit_bundle.py",
        "--materialize-machine-rows",
        tmp_path / "machine-rows.json",
        "--authority-id",
        "AUTH-LAW",
        *ledgers,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    finding = {
        "id": "F-2-1",
        "prs": [2],
        "title": "b() changed its public signature",
        "finding_class": "CONTRACT",
        "severity": "High",
        "confidence": "Confirmed",
        "origin": "PR_INTRODUCED",
        "merge_blocking": True,
        "merge_blocking_basis": "LAW forbids public signature changes",
        "authority": "AUTH-LAW",
        "expected": "b() keeps its signature",
        "observed": "b(x) breaks every caller",
        "evidence": [evidence(f"src/b.py:1@{HEAD[2]}", "signature changed")],
        "root_cause_state": "CONFIRMED",
        "closure_condition": "b() keeps its signature",
        "implementation_surfaces": ["src/b.py"],
        "closing_validation": {"kind": "COMMAND", "procedure": "pytest -q"},
    }
    (tmp_path / "lanes" / "all.json").write_text(
        json.dumps(
            {
                "lane": "all",
                "prs": [
                    lane_pr(1, "READY", ["src/a.py", "tests/test_a.py"]),
                    lane_pr(2, "NOT_READY", ["src/b.py"]),
                ],
                "findings": [finding],
                "cross_pr": [],
                "unknowns": [],
            }
        )
    )
    (tmp_path / "judgment.json").write_text(
        json.dumps(
            {
                "audit_id": "audit.pipeline.test",
                "validation_authority": "AUTH-LAW",
                "mutation_guard": "AUTH-GUARD",
                "authorities": [
                    {
                        "authority_id": "AUTH-LAW",
                        "kind": "REPOSITORY_LAW",
                        "source": "LAW.md",
                        "scope": "public API is stable",
                        "precedence": 1,
                    },
                    {
                        "authority_id": "AUTH-GUARD",
                        "kind": "MUTATION_GUARD",
                        "source": "LAW.md#guard",
                        "scope": "who may edit",
                        "precedence": 1,
                    },
                ],
                "components": [
                    {
                        "component_id": "core",
                        "responsibilities": ["core logic"],
                        "path_prefixes": ["src/", "tests/"],
                        "authority_ids": ["AUTH-LAW"],
                    }
                ],
                "boundaries": [],
                "reconcile": {},
                "merge_order": [1, 2],
            }
        )
    )
    return tmp_path


def test_clean_pr_is_ready_beside_a_blocked_pr(run_dir: Path) -> None:
    done = run(SCRIPTS / "run_audit.py", "finalize", "--run-dir", run_dir)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    audit = json.loads((run_dir / "audit.json").read_text())
    verdicts = {v["pr_number"]: v for v in audit["per_pr_verdicts"]}
    assert verdicts[1]["merge_readiness"] == "READY"
    assert verdicts[2]["merge_readiness"] == "NOT_READY"
    assert verdicts[2]["blocking_finding_ids"] == ["F-2-1"]
    # Derive recorded the refutation of PR 2's mirrored readiness claim on a probe.
    refuted = [f for f in audit["falsification_ledger"] if f["result"] == "FALSIFIED"]
    assert refuted and all(
        e.startswith("E-DERIVED-REFUTE-") for f in refuted for e in f["evidence_ids"]
    )
    assert list((run_dir / "bundle").glob("*.zip"))


def test_added_test_file_dict_keys_are_not_symbols(run_dir: Path) -> None:
    ledger = json.loads((run_dir / "ledgers" / "pr-1-ledger.json").read_text())
    names = {s["symbol_name"] for s in ledger["changed_symbols"] if s["path"] == "tests/test_a.py"}
    assert names == {"test_a"}


def test_stale_lane_head_is_refused(run_dir: Path) -> None:
    lane = json.loads((run_dir / "lanes" / "all.json").read_text())
    lane["prs"][0]["head_sha"] = "d" * 40
    (run_dir / "lanes" / "all.json").write_text(json.dumps(lane))
    done = run(SCRIPTS / "assemble_audit.py", "--run-dir", run_dir)
    assert done.returncode == 2 and "re-run the lane" in done.stdout


def test_undispositioned_changed_file_is_refused(run_dir: Path) -> None:
    lane = json.loads((run_dir / "lanes" / "all.json").read_text())
    lane["prs"][0]["scope_fidelity"] = lane["prs"][0]["scope_fidelity"][:1]
    (run_dir / "lanes" / "all.json").write_text(json.dumps(lane))
    done = run(SCRIPTS / "assemble_audit.py", "--run-dir", run_dir)
    assert done.returncode == 2 and "tests/test_a.py" in done.stdout
