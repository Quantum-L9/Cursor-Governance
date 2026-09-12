#!/usr/bin/env python3
"""Qualify a frozen Foundry staging repository against its live repository factory.

Foundry never authors l9.birth-payload/v1. This script invokes the factory's own
compiler, binds the observed factory contract and exact source state, and may
optionally run the factory's real local/no-remote birth engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
SCHEMA = "l9.idea-foundry.birth-qualification/v1"


class QualificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    return proc


def require_pass(proc: subprocess.CompletedProcess[str], label: str) -> None:
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise QualificationError(f"{label} failed ({proc.returncode}): {detail}")


def git(root: Path, *args: str) -> str:
    proc = run(["git", "-C", str(root), *args])
    require_pass(proc, f"git {' '.join(args)}")
    return proc.stdout.strip()


def is_inside(child: Path, parent: Path) -> bool:
    child = child.resolve()
    parent = parent.resolve()
    return child == parent or parent in child.parents


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise QualificationError(f"expected JSON object: {path}")
    return data


def qualify(args: argparse.Namespace) -> dict[str, Any]:
    source = args.source.resolve()
    freeze = args.freeze_receipt.resolve()
    factory = args.repo_template_root.resolve()
    out_dir = args.out_dir.resolve()
    if is_inside(out_dir, source):
        raise QualificationError("qualification output must be outside the source tree")
    out_dir.mkdir(parents=True, exist_ok=True)

    validate_cmd = [
        PYTHON,
        str(SCRIPT_DIR / "validate_foundry_payload.py"),
        str(source),
        "--birth-ready",
        "--freeze-receipt",
        str(freeze),
    ]
    validation = run(validate_cmd)
    require_pass(validation, "Foundry birth-ready validation")

    probe_path = out_dir / "factory-probe.json"
    probe_cmd = [
        PYTHON,
        str(SCRIPT_DIR / "probe_birth_factory.py"),
        str(factory),
        "--out",
        str(probe_path),
    ]
    probe_proc = run(probe_cmd)
    require_pass(probe_proc, "factory probe")
    probe = load_json(probe_path)

    compiler = factory / "scripts/birth-runner/compile_birth_payload.py"
    contract_path = out_dir / "birth-payload.json"
    compile_cmd = [
        PYTHON,
        str(compiler),
        "--source",
        str(source),
        "--out",
        str(contract_path),
        "--require-mode",
        "authoritative",
    ]
    if args.source_repository:
        compile_cmd.extend(["--source-repository", args.source_repository])
    compiled = run(compile_cmd, cwd=factory)
    require_pass(compiled, "factory birth-payload compile")
    if not contract_path.is_file():
        raise QualificationError("factory compiler returned success without birth-payload output")
    birth = load_json(contract_path)

    # Close the probe->compile race: the exact factory contract observed before
    # compilation must still be the exact contract present after compilation.
    post_probe_path = out_dir / "factory-probe-after.json"
    post_probe_proc = run([
        PYTHON,
        str(SCRIPT_DIR / "probe_birth_factory.py"),
        str(factory),
        "--out",
        str(post_probe_path),
    ])
    require_pass(post_probe_proc, "post-compile factory probe")
    post_probe = load_json(post_probe_path)
    if post_probe.get("factory", {}).get("revision") != probe.get("factory", {}).get("revision"):
        raise QualificationError("factory revision changed during payload compilation")
    if post_probe.get("factory", {}).get("tree_sha") != probe.get("factory", {}).get("tree_sha"):
        raise QualificationError("factory tree changed during payload compilation")
    if post_probe.get("contract_files") != probe.get("contract_files"):
        raise QualificationError("factory contract files changed during payload compilation")

    head = git(source, "rev-parse", "HEAD")
    tree = git(source, "rev-parse", "HEAD^{tree}")
    if birth.get("schema") != "l9.birth-payload/v1":
        raise QualificationError("factory compiler emitted unexpected schema")
    if birth.get("mode") != "authoritative":
        raise QualificationError(f"factory classified payload as {birth.get('mode')!r}, not authoritative")
    source_doc = birth.get("source") if isinstance(birth.get("source"), dict) else {}
    if source_doc.get("revision") != head or source_doc.get("tree_sha") != tree:
        raise QualificationError("factory payload source revision/tree does not match frozen staging HEAD")
    matched = birth.get("repository_shape", {}).get("matched") if isinstance(
        birth.get("repository_shape"), dict
    ) else None
    required_shape = probe.get("birth_contract", {}).get("repository_shape")
    if not isinstance(matched, list) or set(matched) != set(required_shape or []):
        raise QualificationError("factory compiler repository_shape does not match probed ownership contract")
    manifest = birth.get("manifest_sha256")
    if not isinstance(manifest, str) or len(manifest) != 64:
        raise QualificationError("factory compiler emitted invalid manifest_sha256")

    local_birth: dict[str, Any] = {"status": "NOT_RUN"}
    if args.run_local_birth:
        missing = [
            label
            for label, value in (
                ("--repo", args.repo),
                ("--pkg", args.pkg),
                ("--desc", args.desc),
                ("--org-profile-src", args.org_profile_src),
            )
            if not value
        ]
        if missing:
            raise QualificationError("--run-local-birth requires " + ", ".join(missing))
        engine = factory / "scripts/birth-runner/new_repo.py"
        work_dir = (args.work_dir or (out_dir / "local-birth-work")).resolve()
        local_cmd = [
            PYTHON,
            str(engine),
            "--repo",
            args.repo,
            "--pkg",
            args.pkg,
            "--desc",
            args.desc,
            "--payload",
            str(source),
            "--payload-contract",
            str(contract_path),
            "--work-dir",
            str(work_dir),
            "--org-profile-src",
            str(args.org_profile_src.resolve()),
            "--no-remote",
        ]
        local = run(local_cmd, cwd=factory)
        log_path = out_dir / "local-birth.log"
        log_path.write_text(
            "[stdout]\n" + local.stdout + "\n[stderr]\n" + local.stderr,
            encoding="utf-8",
        )
        if local.returncode != 0 or "BIRTH: PASS" not in local.stdout:
            raise QualificationError(
                f"factory local birth did not pass (exit={local.returncode}); see {log_path}"
            )
        local_birth = {
            "status": "PASS",
            "command": local_cmd,
            "stdout_sha256": hashlib.sha256(local.stdout.encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(local.stderr.encode("utf-8")).hexdigest(),
            "log_path": str(log_path),
        }

    qualification_status = "LOCAL_BIRTH_PASS" if local_birth["status"] == "PASS" else "FACTORY_COMPILE_PASS"
    receipt = {
        "schema": SCHEMA,
        "status": qualification_status,
        "source": {
            "path": str(source),
            "revision": head,
            "tree_sha": tree,
            "foundry_freeze_receipt": str(freeze),
            "foundry_freeze_receipt_sha256": sha256(freeze),
        },
        "factory": {
            "path": str(factory),
            "revision": probe["factory"]["revision"],
            "tree_sha": probe["factory"]["tree_sha"],
            "role": probe["factory"]["role"],
            "probe": str(probe_path),
            "probe_sha256": sha256(probe_path),
            "contract_files": probe["contract_files"],
        },
        "compiled_birth_payload": {
            "path": str(contract_path),
            "sha256": sha256(contract_path),
            "schema": birth["schema"],
            "mode": birth["mode"],
            "manifest_sha256": birth["manifest_sha256"],
            "repository_shape": matched,
            "source_repository": source_doc.get("repository"),
        },
        "local_birth": local_birth,
        "remote_birth": {"status": "NOT_PERFORMED"},
        "deployment": {"performed": False},
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Qualify a frozen Foundry payload against the live repository factory.")
    parser.add_argument("source", type=Path)
    parser.add_argument("--freeze-receipt", required=True, type=Path)
    parser.add_argument("--repo-template-root", required=True, type=Path)
    parser.add_argument("--source-repository")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--run-local-birth", action="store_true")
    parser.add_argument("--repo")
    parser.add_argument("--pkg")
    parser.add_argument("--desc")
    parser.add_argument("--org-profile-src", type=Path)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args()
    try:
        receipt = qualify(args)
    except (QualificationError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FOUNDRY_BIRTH_QUALIFICATION: FAIL: {exc}", file=sys.stderr)
        return 1
    receipt_path = args.out_dir.resolve() / "birth-qualification-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"FOUNDRY_BIRTH_QUALIFICATION: PASS status={receipt['status']}")
    print(f"receipt={receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
