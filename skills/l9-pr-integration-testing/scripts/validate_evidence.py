#!/usr/bin/env python3
"""Validate revision-bound evidence references and independently hash-seal a bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REQUIRED = (
    "integration_manifest.json",
    "integration_findings.json",
    "integration_evidence.json",
    "integration_verdict.json",
)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
STATES = {"INTEGRATION_READY", "NOT_INTEGRATION_READY", "INCOMPLETE_EVIDENCE", "BLOCKED"}


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def files_for_index(root: Path) -> dict[str, str]:
    items = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "evidence-index.json":
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
                raise ValueError("symlink or escaped file in evidence")
            items[rel] = digest(p.read_bytes())
    return items


def seal_bundle(root: Path):
    if not all((root / p).is_file() for p in REQUIRED):
        raise ValueError("cannot seal incomplete evidence")
    files = files_for_index(root)
    index = {"schema": "l9.integration.index/v1", "files_sha256": files}
    (root / "evidence-index.json").write_text(
        json.dumps(index, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    return index


def validate(root: Path) -> list[str]:
    errors = []
    data = {}
    for rel in REQUIRED:
        p = root / rel
        if not p.is_file():
            errors.append("missing " + rel)
            continue
        try:
            data[rel] = json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError):
            errors.append("invalid JSON " + rel)
    if len(data) < len(REQUIRED):
        return errors
    m, f, e, v = (data[p] for p in REQUIRED)
    for name, obj, schema in zip(
        REQUIRED,
        (m, f, e, v),
        (
            "l9.integration.manifest/v1",
            "l9.integration.findings/v1",
            "l9.integration.evidence/v1",
            "l9.integration.verdict/v1",
        ),
    ):
        if obj.get("schema") != schema:
            errors.append(f"invalid schema {name}")
    repo = m.get("repository", {})
    if not SHA40.fullmatch(repo.get("base_sha", "")):
        errors.append("missing base revision binding")
    selected = m.get("prs", [])
    if not selected or any(not SHA40.fullmatch(p.get("head_sha", "")) for p in selected):
        errors.append("missing exact PR head bindings")
    order = m.get("integration_order", [])
    if sorted(order) != sorted(p.get("number") for p in selected):
        errors.append("integration order mismatches selected PRs")
    states = m.get("states", [])
    for state in states:
        if state.get("revision") and not SHA40.fullmatch(state["revision"].get("sha", "")):
            errors.append("state lacks executable revision SHA")
        for test in state.get("tests", []):
            if test.get("status") not in {"PASS", "FAIL", "TIMEOUT"}:
                errors.append("unsupported test status")
    ids = []
    for r in e.get("records", []):
        rid = r.get("id")
        if not isinstance(rid, str):
            errors.append("evidence record has missing ID")
            continue
        ids.append(rid)
        if "log_path" in r:
            rel = r["log_path"]
            if (
                not isinstance(rel, str)
                or Path(rel).is_absolute()
                or ".." in Path(rel).parts
                or not rel.startswith("logs/")
            ):
                errors.append("invalid log locator: " + rid)
                continue
            p = root / rel
            if not p.is_file() or digest(p.read_bytes()) != r.get("log_sha256"):
                errors.append("missing/tampered execution log: " + rid)
    if len(ids) != len(set(ids)):
        errors.append("duplicate evidence IDs")
    known = set(ids)
    finding_ids = []
    for finding in f.get("findings", []):
        fid = finding.get("id")
        finding_ids.append(fid)
        if not fid or not re.fullmatch(r"F-[0-9a-f]{12}", fid):
            errors.append("unstable finding ID")
        refs = finding.get("evidence_ids", [])
        if not refs or not set(refs).issubset(known):
            errors.append(f"dangling or absent evidence in finding {fid}")
        if not finding.get("corrective_obligation"):
            errors.append(f"finding {fid} missing correction criterion")
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("duplicate finding IDs")
    if v.get("state") not in STATES:
        errors.append("unsupported readiness verdict")
    if not set(v.get("blocking_findings", [])).issubset(set(finding_ids)):
        errors.append("verdict refers to missing findings")
    status = v.get("execution", {})
    if v.get("state") == "INTEGRATION_READY":
        if m.get("execution_mode") != "DOCKER_ONLY" or not all(
            status.get(x) is True
            for x in (
                "docker_executed",
                "combined_tests_pass",
                "negative_probe_killed",
                "source_review_verified",
                "required_contracts_verified",
            )
        ):
            errors.append("ready without required Docker, review or adversarial proof")
        combined = next((s for s in states if s.get("name") == "combined"), None)
        if (
            not combined
            or not combined.get("revision")
            or not combined.get("tests")
            or any(t.get("status") != "PASS" for t in combined["tests"])
        ):
            errors.append("ready without successful combined integration tests")
        if f.get("findings"):
            blocking = [x for x in f["findings"] if x.get("severity") in ("CRITICAL", "HIGH")]
            if blocking:
                errors.append("ready despite high/critical findings")
    index_path = root / "evidence-index.json"
    if not index_path.is_file():
        errors.append("missing evidence-index.json hash seal")
    else:
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            if index.get("schema") != "l9.integration.index/v1" or index.get(
                "files_sha256"
            ) != files_for_index(root):
                errors.append("evidence index mismatch or unsealed post-hoc mutation")
        except (ValueError, OSError):
            errors.append("invalid evidence index")
    return errors


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("evidence_dir", type=Path)
    ap.add_argument(
        "--seal", action="store_true", help="hash-seal an already completed evidence bundle"
    )
    args = ap.parse_args()
    try:
        if args.seal:
            seal_bundle(args.evidence_dir)
        failures = validate(args.evidence_dir)
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    if failures:
        for e in failures:
            print("FAIL: " + e, file=sys.stderr)
        return 1
    print("PASS: exact-revision evidence references, logs, verdict and hashes verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
