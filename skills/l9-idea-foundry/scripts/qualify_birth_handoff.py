#!/usr/bin/env python3
"""Qualify a frozen Foundry staging repository against its live repository factory.

Foundry never authors l9.birth-payload/v1. This script invokes the factory's own
compiler, binds the observed factory contract and exact source state, and may
optionally run the factory's real local/no-remote birth engine.

BIRTH_READY is emitted here and only here: the pre-factory exact-state check
(validate_foundry_payload.py --freeze-validated) reports FREEZE_VALIDATED, and
this qualifier upgrades that state to BIRTH_READY only after the live factory
compiler returns FACTORY_COMPILE_PASS for the same source HEAD/tree.
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

from _common import tracked_tree_digest

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
SCHEMA = "l9.idea-foundry.birth-qualification/v1"
# Every subprocess is bounded so a hung git, probe, compiler, or birth engine
# fails loudly instead of stalling qualification forever.
GIT_TIMEOUT_SECONDS = 120
STEP_TIMEOUT_SECONDS = 900
LOCAL_BIRTH_TIMEOUT_SECONDS = 1800


class QualificationError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = STEP_TIMEOUT_SECONDS,
) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
    except subprocess.TimeoutExpired as exc:
        raise QualificationError(
            f"command exceeded {timeout:g}s and was terminated: {' '.join(command[:3])} ..."
        ) from exc
    return proc


def require_pass(proc: subprocess.CompletedProcess[str], label: str) -> None:
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()
        raise QualificationError(f"{label} failed ({proc.returncode}): {detail}")


def git(root: Path, *args: str) -> str:
    proc = run(["git", "-C", str(root), *args], timeout=GIT_TIMEOUT_SECONDS)
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


def _content_digest(path: Path) -> str:
    """Deterministic content digest of a file or of a directory tree.

    Directory digests cover every regular file except a `.git` store, keyed by
    POSIX-relative path, so a moved, added, removed, or edited profile file
    changes the digest.
    """
    if path.is_file():
        return sha256(path)
    if not path.is_dir():
        raise QualificationError(f"organization profile source is not a file or directory: {path}")
    h = hashlib.sha256()
    entries = sorted(
        (p for p in path.rglob("*") if p.is_file() and ".git" not in p.relative_to(path).parts),
        key=lambda p: p.relative_to(path).as_posix(),
    )
    for entry in entries:
        rel = entry.relative_to(path).as_posix().encode("utf-8")
        h.update(rel + b"\0" + sha256(entry).encode("ascii") + b"\n")
    return h.hexdigest()


def bind_org_profile(path: Path) -> dict[str, Any]:
    """Bind the exact organization-profile state consumed by a local birth.

    The profile is an input to the factory's birth engine, so its revision (when
    git-tracked) and its content digest are recorded; either drifting invalidates
    LOCAL_BIRTH_PASS evidence.
    """
    profile = path.resolve()
    binding: dict[str, Any] = {
        "path": str(profile),
        "kind": "file" if profile.is_file() else "directory",
        "content_sha256": _content_digest(profile),
        "git_revision": None,
        "git_clean": None,
    }
    probe_root = profile if profile.is_dir() else profile.parent
    inside = run(
        ["git", "-C", str(probe_root), "rev-parse", "--is-inside-work-tree"],
        timeout=GIT_TIMEOUT_SECONDS,
    )
    if inside.returncode == 0 and inside.stdout.strip() == "true":
        binding["git_revision"] = git(probe_root, "rev-parse", "HEAD")
        status = git(probe_root, "status", "--porcelain", "--untracked-files=all", "--", ".")
        binding["git_clean"] = not status.strip()
    return binding


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
        "--freeze-validated",
        "--freeze-receipt",
        str(freeze),
    ]
    validation = run(validate_cmd)
    require_pass(validation, "Foundry exact-state freeze validation")

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
    post_probe_proc = run(
        [
            PYTHON,
            str(SCRIPT_DIR / "probe_birth_factory.py"),
            str(factory),
            "--out",
            str(post_probe_path),
        ]
    )
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
    # Bind the tracked bytes themselves, not only their git object identity, so
    # revalidation can detect an uncommitted mutation of the qualified worktree.
    tracked_records, tracked_digest = tracked_tree_digest(source)
    if birth.get("schema") != "l9.birth-payload/v1":
        raise QualificationError("factory compiler emitted unexpected schema")
    if birth.get("mode") != "authoritative":
        raise QualificationError(
            f"factory classified payload as {birth.get('mode')!r}, not authoritative"
        )
    source_doc = birth.get("source") if isinstance(birth.get("source"), dict) else {}
    if source_doc.get("revision") != head or source_doc.get("tree_sha") != tree:
        raise QualificationError(
            "factory payload source revision/tree does not match frozen staging HEAD"
        )
    matched = (
        birth.get("repository_shape", {}).get("matched")
        if isinstance(birth.get("repository_shape"), dict)
        else None
    )
    required_shape = probe.get("birth_contract", {}).get("repository_shape")
    if not isinstance(matched, list) or set(matched) != set(required_shape or []):
        raise QualificationError(
            "factory compiler repository_shape does not match probed ownership contract"
        )
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
        org_profile = bind_org_profile(args.org_profile_src)
        if org_profile["git_clean"] is False:
            # Same rule as the factory probe: qualify against an exact revision,
            # otherwise the bound revision does not describe the consumed bytes.
            raise QualificationError(
                "organization profile checkout is dirty; commit or clean it before local birth"
            )
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
            org_profile["path"],
            "--no-remote",
        ]
        local = run(local_cmd, cwd=factory, timeout=LOCAL_BIRTH_TIMEOUT_SECONDS)
        log_path = out_dir / "local-birth.log"
        log_path.write_text(
            "[stdout]\n" + local.stdout + "\n[stderr]\n" + local.stderr,
            encoding="utf-8",
        )
        if local.returncode != 0 or "BIRTH: PASS" not in local.stdout:
            raise QualificationError(
                f"factory local birth did not pass (exit={local.returncode}); see {log_path}"
            )
        # The profile must not have moved while the engine consumed it.
        if bind_org_profile(args.org_profile_src) != org_profile:
            raise QualificationError("organization profile changed during local birth")
        local_birth = {
            "status": "PASS",
            "command": local_cmd,
            "org_profile": org_profile,
            "stdout_sha256": hashlib.sha256(local.stdout.encode("utf-8")).hexdigest(),
            "stderr_sha256": hashlib.sha256(local.stderr.encode("utf-8")).hexdigest(),
            "log_path": str(log_path),
        }

    if local_birth["status"] == "PASS":
        qualification_status = "LOCAL_BIRTH_PASS"
        foundry_state = "LOCAL_BIRTH_PASS"
    else:
        qualification_status = "FACTORY_COMPILE_PASS"
        foundry_state = "BIRTH_READY"
    receipt = {
        "schema": SCHEMA,
        "status": qualification_status,
        "foundry_state": foundry_state,
        "source": {
            "path": str(source),
            "revision": head,
            "tree_sha": tree,
            "tracked_file_count": len(tracked_records),
            "tracked_tree_digest": tracked_digest,
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
    parser = argparse.ArgumentParser(
        description="Qualify a frozen Foundry payload against the live repository factory."
    )
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
    print(
        "FOUNDRY_BIRTH_QUALIFICATION: PASS "
        f"status={receipt['status']} foundry_state={receipt['foundry_state']}"
    )
    print(f"receipt={receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
