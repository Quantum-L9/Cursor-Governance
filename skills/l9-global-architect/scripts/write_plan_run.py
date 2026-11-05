#!/usr/bin/env python3
"""Write and verify the GAR run file a simple-plan receipt must name.

Standalone GAR persistence stays optional. This writer exists so a plan
pipeline can prove the load order was hashed for that run. It does not
start orchestration and it does not change GAR's own persistence flag.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA = "l9.gar_plan_run.v1"
SKILL_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = SKILL_ROOT / "runtime" / "MANIFEST.yaml"

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"pyyaml required: {exc}") from exc


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_order_entries() -> list[dict[str, str]]:
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    order = manifest.get("load_order") if isinstance(manifest, dict) else None
    if not isinstance(order, list) or not order:
        raise ValueError(f"{MANIFEST} has no load_order")
    entries: list[dict[str, str]] = []
    for item in order:
        rel = str(item)
        path = SKILL_ROOT / rel
        if not path.is_file():
            raise ValueError(f"load_order path is not a file: {rel}")
        entries.append({"path": rel, "sha256": _sha256_bytes(path.read_bytes())})
    return entries


def load_order_digest(entries: list[dict[str, str]]) -> str:
    blob = "\n".join(f"{entry['path']} {entry['sha256']}" for entry in entries)
    return _sha256_bytes(blob.encode("utf-8"))


def planned_workspace(explicit: Path | None = None) -> Path:
    """Git root of the repository being planned.

    Evidence paths are relative to that repository, not to the governance
    clone that ships this script. An explicit path wins, then
    ``L9_PLAN_WORKSPACE`` (so a child verifier follows the pipeline's
    ``--workspace``), then the working directory. A directory inside a
    checkout resolves to that checkout's toplevel.
    """
    if explicit is None:
        raw = os.environ.get("L9_PLAN_WORKSPACE", "").strip()
        if raw:
            explicit = Path(raw)
    start = (explicit if explicit is not None else Path.cwd()).expanduser()
    try:
        start = start.resolve()
    except OSError:
        start = Path.cwd().resolve()
    probe = start if start.is_dir() else start.parent
    if explicit is not None and not probe.is_dir():
        raise ValueError(f"workspace is not a directory: {explicit}")
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=probe,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return probe
    top = proc.stdout.strip()
    if proc.returncode == 0 and top:
        return Path(top).resolve()
    return probe


def _evidence_ok(rel: str, root: Path) -> str | None:
    raw = Path(rel)
    if raw.is_absolute() or ".." in raw.parts or not rel.strip():
        return f"evidence path must be repo-relative: {rel}"
    path = (root / raw).resolve()
    repo = root.resolve()
    if path != repo and repo not in path.parents:
        return f"evidence path escapes the repository: {rel}"
    if not path.is_file():
        return f"evidence path is not a file: {rel}"
    return None


def write_run(
    dest: Path,
    *,
    governing_cause: str,
    intervention: str,
    evidence_paths: list[str],
    run_id: str,
    workspace: Path | None = None,
) -> dict[str, Any]:
    cause = governing_cause.strip()
    chosen = intervention.strip()
    if not cause or not chosen:
        raise ValueError("governing_cause and intervention are required")
    if not evidence_paths:
        raise ValueError("evidence_paths is required")
    root = planned_workspace(workspace)
    problems = [msg for rel in evidence_paths if (msg := _evidence_ok(rel, root))]
    if problems:
        raise ValueError("; ".join(problems))
    entries = load_order_entries()
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "run_id": run_id.strip() or "gar-plan-run",
        "governing_cause": cause,
        "intervention": chosen,
        "evidence_paths": list(evidence_paths),
        "load_order": entries,
        "load_order_digest": load_order_digest(entries),
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return body


def verify_run(path: Path, *, workspace: Path | None = None) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load run file: {exc}"]
    if not isinstance(data, dict):
        return ["run file root must be an object"]
    errors: list[str] = []
    if data.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}")
    if not str(data.get("governing_cause") or "").strip():
        errors.append("governing_cause is empty")
    if not str(data.get("intervention") or "").strip():
        errors.append("intervention is empty")
    evidence = data.get("evidence_paths")
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence_paths is empty")
    else:
        root = planned_workspace(workspace)
        for rel in evidence:
            problem = _evidence_ok(str(rel), root)
            if problem:
                errors.append(problem)
    try:
        live = load_order_entries()
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
        return errors
    if data.get("load_order") != live:
        errors.append("load_order does not match the current MANIFEST hash")
    if data.get("load_order_digest") != load_order_digest(live):
        errors.append("load_order_digest does not match the current MANIFEST hash")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", help="JSON object with the GAR decision fields")
    parser.add_argument("--out", help="run file to write")
    parser.add_argument("--verify", help="run file to verify")
    parser.add_argument("--run-id", default="gar-plan-run")
    parser.add_argument(
        "--workspace",
        help="repository the evidence paths are relative to (default: git root of cwd)",
    )
    args = parser.parse_args(argv)
    workspace = Path(args.workspace) if args.workspace else None
    if args.verify:
        problems = verify_run(Path(args.verify), workspace=workspace)
        if problems:
            print("FAIL: GAR run", file=sys.stderr)
            for problem in problems:
                print(f"  {problem}", file=sys.stderr)
            return 1
        print(f"PASS: {args.verify}")
        return 0
    if not args.decision or not args.out:
        print("FAIL: --decision and --out are required to write a run file", file=sys.stderr)
        return 2
    try:
        decision = json.loads(Path(args.decision).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot load decision: {exc}", file=sys.stderr)
        return 2
    if not isinstance(decision, dict):
        print("FAIL: decision root must be an object", file=sys.stderr)
        return 2
    try:
        write_run(
            Path(args.out),
            governing_cause=str(decision.get("governing_cause") or ""),
            intervention=str(decision.get("intervention") or ""),
            evidence_paths=[str(item) for item in decision.get("evidence_paths") or []],
            run_id=str(decision.get("run_id") or args.run_id),
            workspace=workspace,
        )
    except (OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
