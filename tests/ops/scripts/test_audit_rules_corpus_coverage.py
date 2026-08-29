"""C3/C1 rules-corpus coverage: inverted enforcers, named population, fail-closed."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[3] / "ops" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from audit_rules_corpus import (  # noqa: E402
    ENFORCER_SET,
    build_report,
    load_manifest,
    main,
)


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _manifest(root: Path, rules: list[tuple[str, str]]) -> None:
    body = "rules:\n"
    for file_name, rule_id in rules:
        body += f"  - file: {file_name}\n    id: {rule_id}\n    activation: always\n"
    _write(root, "rules/RULES-MANIFEST.yaml", body)


def test_zero_enforcer_rule_is_listed_not_omitted(tmp_path: Path) -> None:
    """A rule referenced by no gate/hook/skill appears with an empty enforcer set."""
    _manifest(
        tmp_path,
        [
            ("10-enforced.mdc", "l9.rule.10.enforced"),
            ("99-orphan.mdc", "l9.rule.99.orphan"),
        ],
    )
    _write(tmp_path, "Makefile", "help:\n\t@echo 10-enforced\n")
    manifest, path = load_manifest(tmp_path)
    report = build_report(tmp_path, manifest, path, generated_utc="2026-08-29T00:00:00Z")
    by_id = {row["id"]: row for row in report["coverage"]["rules"]}
    assert by_id["l9.rule.99.orphan"]["enforcers"] == []
    assert by_id["l9.rule.99.orphan"]["enforcer_count"] == 0
    assert by_id["l9.rule.10.enforced"]["enforcer_count"] >= 1
    assert "Makefile" in by_id["l9.rule.10.enforced"]["enforcers"]
    assert any(item["id"] == "RCA-007" for item in report["findings"])


def test_missing_manifest_fails_closed_and_names_path(tmp_path: Path) -> None:
    """Missing source must not report a successful zero-rule analysis."""
    _write(tmp_path, "README.md", "no rules dir\n")
    rc = main(
        [
            "--root",
            str(tmp_path),
            "--json-out",
            str(tmp_path / "out.json"),
            "--md-out",
            str(tmp_path / "out.md"),
        ]
    )
    assert rc == 1
    assert not (tmp_path / "out.json").exists()


def test_missing_rules_dir_names_rules_path(tmp_path: Path) -> None:
    rc = main(["--root", str(tmp_path), "--json-out", str(tmp_path / "x.json")])
    assert rc == 1


def test_unreadable_manifest_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "rules").mkdir()
    _write(tmp_path, "rules/RULES-MANIFEST.yaml", "not: [unterminated\n")
    rc = main(
        [
            "--root",
            str(tmp_path),
            "--json-out",
            str(tmp_path / "out.json"),
            "--md-out",
            str(tmp_path / "out.md"),
        ]
    )
    assert rc == 1
    assert not (tmp_path / "out.json").exists()


def test_population_is_named_and_no_compliance_rate(tmp_path: Path) -> None:
    _manifest(tmp_path, [("00-global.mdc", "l9.rule.00.global")])
    _write(tmp_path, ".pre-commit-config.yaml", "repos: []\n")
    json_out = tmp_path / "out.json"
    rc = main(
        [
            "--root",
            str(tmp_path),
            "--json-out",
            str(json_out),
            "--md-out",
            str(tmp_path / "out.md"),
        ]
    )
    assert rc == 0
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["population"]["source"] == "rules/RULES-MANIFEST.yaml"
    assert payload["population"]["entrypoint_set"] == list(ENFORCER_SET)
    assert "generated_utc" in payload["population"]
    assert "compliance_rate" not in payload
    assert "compliance_rate" not in payload["summary"]
    assert payload["coverage"]["enforcer_set"] == list(ENFORCER_SET)
