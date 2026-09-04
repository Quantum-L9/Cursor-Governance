#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pr_digest_core import digest, validate


def fixture(**overrides):
    doc = {
        "repository": "Quantum-L9/example",
        "pr_number": 7,
        "title": "fix: narrow parser bug",
        "body": "## Non-goals\n- no provider expansion\n",
        "base_ref": "main",
        "base_sha": "a" * 40,
        "head_ref": "fix/parser",
        "head_sha": "b" * 40,
        "commits": ["b" * 40],
        "files": [
            {
                "path": "src/parser.py",
                "status": "modified",
                "additions": 4,
                "deletions": 2,
                "patch": "+def parse_fixed(x):\n+    return x\n",
            },
            {
                "path": "tests/test_parser.py",
                "status": "modified",
                "additions": 5,
                "deletions": 0,
                "patch": "+def test_parse_fixed():\n+    assert True\n",
            },
        ],
        "ci_checks": [{"name": "tests", "conclusion": "success"}],
        "intent": {
            "requested_outcome": "fix parser bug",
            "explicit_scope": ["src/parser.py", "tests/test_parser.py"],
            "explicit_non_goals": ["provider expansion"],
            "acceptance_criteria": ["regression covered"],
        },
    }
    doc.update(overrides)
    return doc


def main() -> int:
    good = digest(fixture())
    assert not validate(good), validate(good)
    assert good["decision"] == "READY_FOR_REMEDIATION", good["decision"]
    assert good["LLM_judgement_used"] is False

    ci = digest(fixture(ci_checks=[{"name": "tests", "conclusion": "failure"}]))
    assert ci["decision"] == "UNKNOWN"
    assert "CI_required_set_unavailable" in ci["unknowns"]
    ci_required = digest(
        fixture(
            ci_checks=[{"name": "tests", "conclusion": "failure"}],
            required_check_names=["tests"],
        )
    )
    assert ci_required["decision"] == "CI_OR_EXECUTION_FAILURE"

    pending = digest(fixture(ci_checks=[{"name": "tests", "conclusion": "UNKNOWN"}]))
    assert pending["decision"] == "UNKNOWN"
    assert "CI_evidence_incomplete" in pending["unknowns"]

    expanded = fixture()
    expanded["files"].append(
        {
            "path": "src/provider_adapter.py",
            "status": "added",
            "additions": 25,
            "deletions": 0,
            "patch": "+class NewProviderAdapter:\n+    pass\n",
        }
    )
    exp = digest(expanded)
    assert exp["decision"] == "UNKNOWN"
    assert any(q["code"] == "new_adapter" for q in exp["LLM_judgement_questions"])

    unknown_intent = fixture(title="", body="", intent=None)
    unknown_intent["files"].append(
        {
            "path": "src/registry.py",
            "status": "added",
            "additions": 10,
            "deletions": 0,
            "patch": "+class ProviderRegistry:\n+    pass\n",
        }
    )
    unk = digest(unknown_intent)
    assert unk["decision"] == "INTENT_UNKNOWN_REVIEW_REQUIRED"

    suppress = fixture()
    suppress["files"][0]["patch"] = "+value = unsafe()  # noqa: S307\n"
    sup = digest(suppress)
    assert any(f["code"] == "suppression_or_ignore_added" for f in sup["deterministic_findings"])
    assert sup["required_narrowing"]

    catalog = fixture(
        files=[
            {
                "path": "reports/repo-index/test_catalog.txt",
                "status": "removed",
                "additions": 0,
                "deletions": 50,
            }
        ],
        ci_checks=[{"name": "tests", "conclusion": "success"}],
    )
    cat = digest(catalog)
    assert not any(f["code"] == "deleted_test" for f in cat["deterministic_findings"])

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "digest.json"
        path.write_text(json.dumps(good), encoding="utf-8")
        assert json.loads(path.read_text())["PR_identity"]["head_sha"] == "b" * 40

    print("PASS: l9-pr-digest deterministic self-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
