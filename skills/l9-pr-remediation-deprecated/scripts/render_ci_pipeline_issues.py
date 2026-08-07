#!/usr/bin/env python3
"""Render one downstream CI issue file per distinct pipeline root cause."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "assets" / "ci-pipeline-issue-template.md"
ALLOWED_PREFIX = Path("issues/ci-pipeline")


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("run report root must be an object")
    return data


def bullet_list(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- Unknown"


def validate_signal(signal: dict[str, Any]) -> None:
    required = (
        "id", "fingerprint", "classification", "title", "root_cause",
        "owning_surface", "affected_checks", "evidence", "source_repo",
        "source_pr", "head_sha", "blocks_pr", "repair_attempted",
        "repository_files_modified", "downstream_owner", "issue_file_path",
        "acceptance_criteria",
    )
    missing = [key for key in required if key not in signal]
    if missing:
        raise ValueError(f"CI signal missing fields: {', '.join(missing)}")
    if signal["classification"] != "CI_PIPELINE_SIGNAL":
        raise ValueError(f"{signal['id']}: classification must be CI_PIPELINE_SIGNAL")
    if signal["repair_attempted"] is not False:
        raise ValueError(f"{signal['id']}: repair_attempted must be false")
    if signal["repository_files_modified"] != []:
        raise ValueError(f"{signal['id']}: repository_files_modified must be empty")
    fingerprint = str(signal["fingerprint"])
    if not re.fullmatch(r"[0-9a-f]{64}", fingerprint):
        raise ValueError(f"{signal['id']}: fingerprint must be 64 lowercase hex characters")
    rel = Path(str(signal["issue_file_path"]))
    if rel.is_absolute() or ".." in rel.parts or rel.suffix.lower() != ".md":
        raise ValueError(f"{signal['id']}: unsafe issue_file_path")
    if rel.parts[:2] != ALLOWED_PREFIX.parts:
        raise ValueError(f"{signal['id']}: issue_file_path must be under issues/ci-pipeline")


def render(report: dict[str, Any], output_dir: Path) -> list[Path]:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    signals = report.get("ci_pipeline_signals", [])
    if not isinstance(signals, list):
        raise ValueError("ci_pipeline_signals must be an array")
    seen_fingerprints: set[str] = set()
    seen_paths: set[str] = set()
    written: list[Path] = []
    for raw in signals:
        if not isinstance(raw, dict):
            raise ValueError("each CI signal must be an object")
        validate_signal(raw)
        fingerprint = str(raw["fingerprint"])
        issue_path = str(raw["issue_file_path"])
        if fingerprint in seen_fingerprints:
            raise ValueError(f"duplicate CI root-cause fingerprint: {fingerprint}")
        if issue_path in seen_paths:
            raise ValueError(f"duplicate CI issue path: {issue_path}")
        seen_fingerprints.add(fingerprint)
        seen_paths.add(issue_path)
        replacements = {
            "{{ title }}": str(raw["title"]),
            "{{ repo }}": str(raw["source_repo"]),
            "{{ pr }}": str(raw["source_pr"]),
            "{{ fingerprint }}": fingerprint,
            "{{ head_sha }}": str(raw["head_sha"]),
            "{{ owning_surface }}": str(raw["owning_surface"]),
            "{{ blocks_pr }}": str(raw["blocks_pr"]).lower(),
            "{{ root_cause }}": str(raw["root_cause"]),
            "{{ affected_checks }}": bullet_list([str(v) for v in raw["affected_checks"]]),
            "{{ evidence }}": bullet_list([str(v) for v in raw["evidence"]]),
            "{{ reproduction }}": str(raw.get("reproduction") or "Observed in CI evidence; see affected checks and evidence above."),
            "{{ acceptance_criteria }}": bullet_list([str(v) for v in raw["acceptance_criteria"]]),
        }
        content = template
        for key, value in replacements.items():
            content = content.replace(key, value)
        if "{{" in content or "}}" in content:
            raise ValueError(f"{raw['id']}: unresolved template placeholder")
        target = output_dir / issue_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content.rstrip() + "\n", encoding="utf-8")
        written.append(target)
    return written


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-report", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        report = load(Path(args.run_report))
        written = render(report, Path(args.output_dir))
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: rendered {len(written)} CI pipeline issue file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
