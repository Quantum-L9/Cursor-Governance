"""Finding normalization and the changed-line filter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PKG = REPO_ROOT / "ops" / "ci_parity"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

import findings as fnd  # noqa: E402

DIFF = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -10,0 +11,2 @@ def f():
+    x = 1
+    y = 2
@@ -30 +32 @@
-old
+new
diff --git a/gone.py b/gone.py
--- a/gone.py
+++ /dev/null
@@ -1,3 +0,0 @@
-x
"""


def test_unified_diff_ranges() -> None:
    assert fnd.parse_unified_diff(DIFF) == {"a.py": [(11, 12), (32, 32)]}


def _codeql_sarif(sink_line: int, source_line: int) -> dict:
    return {
        "runs": [
            {
                "tool": {
                    "driver": {
                        "rules": [
                            {
                                "id": "py/clear-text-logging-sensitive-data",
                                "properties": {"security-severity": "7.5"},
                            }
                        ]
                    }
                },
                "results": [
                    {
                        "ruleId": "py/clear-text-logging-sensitive-data",
                        "level": "error",
                        "message": {"text": "logs a secret"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "a.py"},
                                    "region": {"startLine": sink_line},
                                }
                            }
                        ],
                        "codeFlows": [
                            {
                                "threadFlows": [
                                    {
                                        "locations": [
                                            {
                                                "location": {
                                                    "physicalLocation": {
                                                        "artifactLocation": {"uri": "a.py"},
                                                        "region": {"startLine": source_line},
                                                    }
                                                }
                                            },
                                            {
                                                "location": {
                                                    "physicalLocation": {
                                                        "artifactLocation": {"uri": "a.py"},
                                                        "region": {"startLine": sink_line},
                                                    }
                                                }
                                            },
                                        ]
                                    }
                                ]
                            }
                        ],
                    }
                ],
            }
        ]
    }


def test_dataflow_result_counts_when_only_its_source_is_in_the_diff(tmp_path: Path) -> None:
    # The #659 case: the secret source changed, the print sink did not.
    found = fnd.parse_sarif(_codeql_sarif(sink_line=5, source_line=11), "codeql", tmp_path)
    ranges = fnd.parse_unified_diff(DIFF)
    kept = fnd.new_findings(found, ranges)
    assert len(kept) == 1
    assert fnd.blocks(kept[0], ("error", "security-high"))


def test_result_entirely_outside_the_diff_is_dropped(tmp_path: Path) -> None:
    found = fnd.parse_sarif(_codeql_sarif(sink_line=5, source_line=6), "codeql", tmp_path)
    assert fnd.new_findings(found, fnd.parse_unified_diff(DIFF)) == []


def test_finding_round_trips_through_a_receipt(tmp_path: Path) -> None:
    finding = fnd.parse_sarif(_codeql_sarif(5, 11), "codeql", tmp_path)[0]
    assert fnd.Finding.from_dict(json.loads(json.dumps(finding.as_dict()))) == finding


def test_block_rules() -> None:
    warn = fnd.Finding("zizmor", "r", "warning", "a", 1, "m")
    err = fnd.Finding("shellcheck", "SC1", "error", "a", 1, "m")
    assert not fnd.blocks(warn, ("error",))
    assert fnd.blocks(err, ("error",))
    assert not fnd.blocks(err, ())  # advisory lane
    mapped = fnd.Finding("semgrep-l9", "known.rule", "warning", "a", 1, "m")
    assert not fnd.blocks(mapped, ("unmapped-rule",), frozenset({"known.rule"}))
    assert fnd.blocks(mapped, ("unmapped-rule",), frozenset())


def test_native_parsers(tmp_path: Path) -> None:
    (tmp_path / "s.sh").write_text("x\n")
    sc = fnd.parse_shellcheck(
        json.dumps(
            {
                "comments": [
                    {"file": "s.sh", "line": 3, "level": "error", "code": 2086, "message": "quote"}
                ]
            }
        ),
        tmp_path,
    )
    assert sc[0].rule == "SC2086" and sc[0].severity == "error" and sc[0].path == "s.sh"
    al = fnd.parse_actionlint(
        json.dumps([{"filepath": "w.yml", "line": 7, "kind": "expression", "message": "m"}]),
        tmp_path,
    )
    assert al[0].severity == "error" and al[0].line == 7
    yl = fnd.parse_yamllint("w.yml:4:1: [error] duplication of key (key-duplicates)\n", tmp_path)
    assert yl[0].rule == "key-duplicates" and yl[0].severity == "error"
    rf = fnd.parse_ruff(
        json.dumps(
            [
                {
                    "filename": str(tmp_path / "s.sh"),
                    "code": "F401",
                    "location": {"row": 2},
                    "message": "m",
                }
            ]
        ),
        tmp_path,
    )
    assert rf[0].path == "s.sh" and rf[0].line == 2


def test_osv_vulnerabilities_are_keyed_by_lockfile_package_and_id() -> None:
    data = {
        "results": [
            {
                "source": {"path": "/x/uv.lock"},
                "packages": [
                    {
                        "package": {"name": "p", "version": "1"},
                        "vulnerabilities": [{"id": "GHSA-1"}],
                    }
                ],
            }
        ]
    }
    assert fnd.osv_vulnerabilities(data) == {("uv.lock", "p@1", "GHSA-1")}
