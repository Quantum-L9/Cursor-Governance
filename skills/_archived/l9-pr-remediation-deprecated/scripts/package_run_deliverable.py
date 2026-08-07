#!/usr/bin/env python3
"""Package redacted PR-remediation artifacts into a deterministic tar.gz."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

REQUIRED = ("run-report.json", "CONVERGENCE_REPORT.yaml", "PR_READY_EVIDENCE.json")
OPTIONAL = ("CYCLE_LOG.jsonl",)
ALLOWED_DIRS = ("issues", "summaries")
DENIED_NAMES = {".env", "credentials", "token", "tokens", "secrets", "secret"}
MAX_FILE_BYTES = 2_000_000
CI_PREFIX = Path("issues/ci-pipeline")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_report(root: Path) -> dict[str, Any]:
    data = json.loads((root / "run-report.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("run-report.json root must be an object")
    return data


def validate_ci_issue_files(root: Path, report: dict[str, Any]) -> None:
    signals = report.get("ci_pipeline_signals", [])
    if not isinstance(signals, list):
        raise ValueError("ci_pipeline_signals must be an array")
    expected: set[str] = set()
    fingerprints: set[str] = set()
    for raw in signals:
        if not isinstance(raw, dict):
            raise ValueError("each CI signal must be an object")
        if raw.get("classification") != "CI_PIPELINE_SIGNAL":
            raise ValueError("CI signal has invalid classification")
        if raw.get("repair_attempted") is not False:
            raise ValueError(f"CI repair attempt forbidden: {raw.get('id', '<unknown>')}")
        if raw.get("repository_files_modified") != []:
            raise ValueError(f"CI signal modified repository files: {raw.get('id', '<unknown>')}")
        fingerprint = str(raw.get("fingerprint", ""))
        if fingerprint in fingerprints:
            raise ValueError(f"duplicate CI root-cause fingerprint: {fingerprint}")
        fingerprints.add(fingerprint)
        rel = Path(str(raw.get("issue_file_path", "")))
        if rel.is_absolute() or ".." in rel.parts or rel.parts[:2] != CI_PREFIX.parts or rel.suffix.lower() != ".md":
            raise ValueError(f"unsafe CI issue path: {rel}")
        if rel.as_posix() in expected:
            raise ValueError(f"duplicate CI issue path: {rel}")
        expected.add(rel.as_posix())
        if not (root / rel).is_file():
            raise ValueError(f"missing CI issue file: {rel}")
    actual_base = root / CI_PREFIX
    actual = set()
    if actual_base.is_dir():
        actual = {p.relative_to(root).as_posix() for p in actual_base.rglob("*.md") if p.is_file()}
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"CI issue-file set mismatch; missing={missing}, extra={extra}")
    deliverable = report.get("deliverable", {})
    if deliverable.get("ci_issue_file_count") != len(expected):
        raise ValueError("deliverable.ci_issue_file_count does not match CI signals")
    if deliverable.get("contains_ci_issue_files") is not (len(expected) > 0):
        raise ValueError("deliverable.contains_ci_issue_files does not match CI signals")


def collect(root: Path) -> list[Path]:
    files: list[Path] = []
    for name in REQUIRED:
        path = root / name
        if not path.is_file():
            raise ValueError(f"missing required artifact: {name}")
        files.append(path)
    report = load_report(root)
    validate_ci_issue_files(root, report)
    for name in OPTIONAL:
        path = root / name
        if path.is_file():
            files.append(path)
    for dirname in ALLOWED_DIRS:
        base = root / dirname
        if base.is_dir():
            files.extend(p for p in base.rglob("*") if p.is_file())
    clean: list[Path] = []
    for path in sorted(set(files), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise ValueError(f"symlinks are forbidden: {path}")
        if path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError(f"artifact too large: {path}")
        lowered = {part.lower() for part in path.parts}
        if lowered & DENIED_NAMES or any(term in path.name.lower() for term in DENIED_NAMES):
            raise ValueError(f"sensitive-looking artifact forbidden: {path}")
        clean.append(path)
    return clean


def package(root: Path, output: Path) -> None:
    files = collect(root)
    manifest = {str(path.relative_to(root)): digest(path.read_bytes()) for path in files}
    manifest_bytes = (json.dumps({"schema": "l9.pr-remediation-deliverable/v2", "files": manifest}, indent=2, sort_keys=True) + "\n").encode()
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as archive:
        entries = [(Path("MANIFEST.json"), manifest_bytes)] + [(path.relative_to(root), path.read_bytes()) for path in files]
        for rel, data in sorted(entries, key=lambda item: item[0].as_posix()):
            arcname = Path("l9-pr-remediation-run") / rel
            info = tarfile.TarInfo(arcname.as_posix())
            info.size = len(data)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(data))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as compressed:
            compressed.write(raw.getvalue())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        package(Path(args.artifact_dir), Path(args.output))
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1
    print(f"PASS: wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
