import hashlib
import json
import os
import tempfile
from pathlib import Path

from script_loader import load_sibling

_behavior = load_sibling("evaluate_behavior")
evaluate = _behavior.evaluate
safe_path = _behavior.safe_path

CASES = [{"id": "X"}]


def test_receipt_ledger():
    assert evaluate(CASES, [])["cases"][0]["status"] == "NOT_RUN"
    r = {
        "case_id": "X",
        "actual_response": "text",
        "run_context": "isolated session",
        "observed_positive": True,
        "observed_forbidden": False,
        "reviewer_verdict": "PASS",
    }
    assert evaluate(CASES, [r])["cases"][0]["status"] == "REVIEW_REQUIRED"
    r.update(
        independent_reviewer="reviewer-1",
        evidence_refs=["response:1"],
        run_id="run1",
        skill_sha256="a" * 64,
        source_snapshot_refs=["snapshot:1"],
        reviewer_identity="reviewer",
        executor_identity="executor",
        reviewer_evidence_refs=["review:1"],
        actual_response_sha256=hashlib.sha256(b"text").hexdigest(),
        artifact_sha256_by_path={},
    )
    assert (
        evaluate(CASES, [r])["behavioral_acceptance"]
        == "RECORDED_PASS_NOT_INDEPENDENTLY_AUTHENTICATED"
    )
    missing_executor = dict(r)
    missing_executor.pop("executor_identity")
    assert evaluate(CASES, [missing_executor])["cases"][0]["status"] == "REVIEW_REQUIRED"
    same_identity = dict(r)
    same_identity["executor_identity"] = same_identity["reviewer_identity"]
    assert evaluate(CASES, [same_identity])["cases"][0]["status"] == "REVIEW_REQUIRED"
    r["actual_response_sha256"] = "b" * 64
    assert evaluate(CASES, [r])["cases"][0]["status"] == "INCOMPLETE"
    r["actual_response_sha256"] = hashlib.sha256(b"text").hexdigest()
    r["observed_forbidden"] = True
    assert evaluate(CASES, [r])["cases"][0]["status"] == "FAIL"
    try:
        evaluate(CASES, [r, r])
        raise AssertionError("duplicate accepted")
    except ValueError:
        pass


def _passing_receipt():
    response = "text"
    return {
        "case_id": "X",
        "actual_response": response,
        "run_context": "isolated session",
        "observed_positive": True,
        "observed_forbidden": False,
        "reviewer_verdict": "PASS",
        "independent_reviewer": "reviewer-1",
        "evidence_refs": ["response:1"],
        "run_id": "run1",
        "skill_sha256": "a" * 64,
        "source_snapshot_refs": ["snapshot:1"],
        "reviewer_identity": "reviewer",
        "executor_identity": "executor",
        "reviewer_evidence_refs": ["review:1"],
        "actual_response_sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
        "artifact_sha256_by_path": {},
    }


def test_cli_confines_paths_and_writes_ledger():
    previous = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as temporary:
            os.chdir(temporary)
            Path("cases.json").write_text(json.dumps(CASES))
            Path("receipts.json").write_text(json.dumps([_passing_receipt()]))
            code = _behavior.main(
                ["--cases", "cases.json", "--receipts", "receipts.json", "--out", "out.json"]
            )
            assert code == 0
            assert "RECORDED_PASS" in Path("out.json").read_text()
            try:
                safe_path("/etc/passwd")
                raise AssertionError("path outside the working directory was accepted")
            except ValueError as exc:
                assert "outside the allowed directory" in str(exc)
    finally:
        os.chdir(previous)


def test_unknown_case_and_incomplete_receipts():
    try:
        evaluate(CASES, [{"case_id": "missing"}])
        raise AssertionError("unknown case accepted")
    except ValueError as exc:
        assert "UNKNOWN_CASE" in str(exc)
    incomplete = evaluate(CASES, [{"case_id": "X"}])
    assert incomplete["cases"][0]["status"] == "INCOMPLETE"
    missing_map = _passing_receipt()
    missing_map["artifact_sha256_by_path"] = []
    assert evaluate(CASES, [missing_map])["cases"][0]["status"] == "INCOMPLETE"
    unresolved = _passing_receipt()
    unresolved["observed_positive"] = None
    unresolved["observed_forbidden"] = None
    unresolved["reviewer_verdict"] = "HOLD"
    assert evaluate(CASES, [unresolved])["cases"][0]["status"] == "REVIEW_REQUIRED"


if __name__ == "__main__":
    test_receipt_ledger()
    test_cli_confines_paths_and_writes_ledger()
    test_unknown_case_and_incomplete_receipts()
