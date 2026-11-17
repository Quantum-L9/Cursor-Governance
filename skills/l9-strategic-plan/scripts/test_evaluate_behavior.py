import hashlib
import sys
from pathlib import Path


def _load_sibling(stem: str):
    import importlib.util

    name = f"l9_strategic_plan_scripts.{stem}"
    cached = sys.modules.get(name)
    if cached is not None:
        return cached
    path = Path(__file__).resolve().parent / f"{stem}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(stem)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


evaluate = _load_sibling("evaluate_behavior").evaluate

CASES = [{"id": "X"}]


def run():
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
    print("PASS evaluator unit checks; no independent model behavior tested")


if __name__ == "__main__":
    run()
