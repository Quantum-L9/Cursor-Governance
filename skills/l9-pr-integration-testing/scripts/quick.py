#!/usr/bin/env python3
"""One-command PR integration test for hosted sessions (Claude Code Mobile first).

    python3 scripts/quick.py --repo OWNER/REPO --pr 12 [--pr 13 --order-basis ...]
                             --authority "operator request, <where and when>"

What it decides for you, and from what evidence:

* the sandbox  — the governance-owned receipt from ops/scripts/docker_sandbox.py
  (ensure runs here when no READY receipt exists, so SessionStart need not have
  finished warming it);
* the binding  — bind_github.py, unchanged;
* the tests    — only the phases the repository itself declares in
  `.l9/repo-workflow.json` (`l9.repo-execution/v2`, facade `make-v1`), anchored
  and hashed at the bound base SHA. A repository that declares no such contract
  gets BLOCKED, never a guessed command;
* the image    — the Core-locked toolchain image plus one layer holding the
  repository's own `make setup` output at the base SHA, because tests run with
  no network. A PR that changes dependency manifests is reported, not hidden;
* the runner   — the sandbox's non-root user, with the session trust bundle.

It still stops where judgment starts: the verdict stays INCOMPLETE_EVIDENCE
until an independent review is bound with apply_review.py (SKILL.md step 7).
Nothing here writes to GitHub.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOVERNANCE = HERE.parents[2]
sys.path.insert(0, str(GOVERNANCE / "ops" / "scripts"))

CONTRACT_PATH = ".l9/repo-workflow.json"
CONTRACT_SCHEMA = "l9.repo-execution/v2"
CONTRACT_FACADE = "make-v1"
DEPENDENCY_MANIFESTS = (
    "pyproject.toml",
    "uv.lock",
    "setup.py",
    "setup.cfg",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "Makefile",
    "Repo.mk",
)


RUNNER_SCRIPTS = ("integrate.py", "validate_evidence.py", "apply_review.py")


def frozen_digests(directory: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
    }


class QuickError(RuntimeError):
    """A precondition is missing; the message says which."""


def procedures_from_contract(raw: bytes, phases: list[str], timeout: int) -> list[dict]:
    """Turn the repository's declared V2 phases into anchored test procedures."""
    try:
        contract = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QuickError(f"{CONTRACT_PATH} is not JSON: {exc}") from exc
    if contract.get("schema") != CONTRACT_SCHEMA or contract.get("facade") != CONTRACT_FACADE:
        raise QuickError(
            f"{CONTRACT_PATH} must declare schema {CONTRACT_SCHEMA} with facade {CONTRACT_FACADE}"
        )
    declared = contract.get("required_phases") or []
    missing = [phase for phase in phases if phase not in declared]
    if missing:
        raise QuickError(f"{CONTRACT_PATH} does not declare phase(s) {', '.join(missing)}")
    digest = hashlib.sha256(raw).hexdigest()
    procedures = []
    for phase in phases:
        anchor = f'"{phase}"'
        if anchor.encode() not in raw:
            raise QuickError(f"{CONTRACT_PATH} lacks the literal anchor {anchor}")
        procedures.append(
            {
                "name": f"make {phase}",
                "argv": ["make", phase],
                "timeout_seconds": timeout,
                "source": {"path": CONTRACT_PATH, "sha256": digest, "anchor": anchor},
            }
        )
    return procedures


def dependency_changes(changed_files_by_pr: dict[str, list[str]]) -> list[str]:
    """Changed paths the base-SHA dependency layer cannot reflect."""
    hits = set()
    for paths in changed_files_by_pr.values():
        for path in paths:
            name = path.rsplit("/", 1)[-1]
            if name in DEPENDENCY_MANIFESTS or (
                name.startswith("requirements") and name.endswith(".txt")
            ):
                hits.add(path)
    return sorted(hits)


def summarize(evidence: Path) -> dict:
    verdict = json.loads((evidence / "integration_verdict.json").read_text())
    manifest = json.loads((evidence / "integration_manifest.json").read_text())
    findings = json.loads((evidence / "integration_findings.json").read_text())
    findings = findings if isinstance(findings, list) else findings.get("findings", [])
    states = []
    for state in manifest.get("states", []):
        tests = [t["status"] for t in state.get("tests", [])]
        merges = [m["status"] for m in state.get("merges", [])]
        states.append(
            {
                "name": state["name"],
                "revision": (state.get("revision") or {}).get("sha", "")[:12],
                "merges": merges,
                "tests": tests,
            }
        )
    return {
        "verdict": verdict["state"],
        "execution": verdict["execution"],
        "states": states,
        "probes": [
            {"name": p.get("name"), "status": p.get("status")}
            for p in manifest.get("negative_probes") or []
        ],
        "findings": [
            {
                "classification": f["classification"],
                "severity": f["severity"],
                "reason": f["reason"][:160],
            }
            for f in findings
        ],
        "cleanup": manifest.get("cleanup"),
        "runner_scripts": manifest.get("runner_scripts", {}),
        "evidence": str(evidence),
    }


def render(summary: dict, extras: list[str]) -> str:
    lines = [f"PR integration: {summary['verdict']}"]
    for state in summary["states"]:
        merge = f" merge={'/'.join(state['merges'])}" if state["merges"] else ""
        tests = "/".join(state["tests"]) or "none"
        lines.append(f"  {state['name']:<10} {state['revision']:<12}{merge} tests={tests}")
    for probe in summary["probes"]:
        lines.append(f"  probe {probe['name']}: {probe['status']}")
    for finding in summary["findings"]:
        lines.append(f"  [{finding['classification']} {finding['severity']}] {finding['reason']}")
    lines += [f"  note: {extra}" for extra in extras]
    lines.append(f"  evidence: {summary['evidence']}")
    if summary["verdict"] == "INCOMPLETE_EVIDENCE" and summary["execution"].get("docker_executed"):
        lines.append(
            "  next: review the combined diff, then scripts/apply_review.py (SKILL.md step 7)"
        )
    return "\n".join(lines)


# --- Host side ---------------------------------------------------------------


def gh_raw(repo: str, path: str, ref: str) -> bytes:
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}?ref={ref}"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode:
        raise QuickError(
            f"{repo} has no readable {path} at {ref[:12]}: {proc.stderr.strip()[-200:]}"
        )
    return base64.b64decode(json.loads(proc.stdout)["content"])


def run(args: list[str], *, timeout: int, **kwargs) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, **kwargs)
    if proc.returncode:
        raise QuickError(
            f"{' '.join(args[:3])} failed: {(proc.stderr or proc.stdout).strip()[-400:]}"
        )
    return proc


def dependency_layer(sandbox: dict, repo: str, base_sha: str) -> str:
    """Toolchain image + the repository's own `make setup`, at the base SHA."""
    safe = repo.lower().replace("/", "__")
    tag = f"l9-pr-deps/{safe}:{base_sha[:12]}-core{sandbox['core_sha'][:12]}"
    proc = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", tag], capture_output=True, text=True
    )
    if proc.returncode == 0:
        return proc.stdout.strip()
    # BuildKit resolves FROM by name, not by image ID; the local tag is the pin
    # only while it still names the exact image the sandbox receipt verified.
    current = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", sandbox["image_tag"]],
        capture_output=True,
        text=True,
    )
    if current.stdout.strip() != sandbox["image_id"]:
        raise QuickError(
            f"{sandbox['image_tag']} no longer names the verified image {sandbox['image_id']}"
        )
    with tempfile.TemporaryDirectory(prefix="l9-pr-deps-") as context:
        ctx = Path(context)
        store = ctx / "store.git"
        run(["git", "init", "--quiet", "--bare", str(store)], timeout=30)
        run(
            [
                "git",
                "--git-dir",
                str(store),
                "fetch",
                "--quiet",
                "--depth",
                "1",
                f"https://github.com/{repo}.git",
                base_sha,
            ],
            timeout=300,
        )
        (ctx / "src").mkdir()
        archive = subprocess.run(
            ["git", "--git-dir", str(store), "archive", base_sha],
            capture_output=True,
            timeout=120,
            check=True,
        )
        subprocess.run(
            ["tar", "-x", "-C", str(ctx / "src")], input=archive.stdout, check=True, timeout=120
        )
        shutil.rmtree(store)
        ca = sandbox.get("runner_ca_bundle")
        secret = "--mount=type=secret,id=ca " if ca else ""
        cert = "PIP_CERT=/run/secrets/ca " if ca else ""
        (ctx / "Dockerfile").write_text(
            f"FROM {sandbox['image_tag']}\n"
            f"RUN {secret}--mount=type=bind,source=src,target=/src,rw \\\n"
            f"    cd /src && {cert}make setup\n"
            f'LABEL org.l9.repo="{repo}" org.l9.base-sha="{base_sha}"\n'
        )
        args = ["docker", "build", "--quiet", "--tag", tag]
        if ca:
            args += ["--secret", f"id=ca,src={ca}"]
        run([*args, str(ctx)], timeout=1800)
    built = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", tag], capture_output=True, text=True
    )
    if built.returncode:
        raise QuickError(f"dependency layer {tag} was not produced")
    return built.stdout.strip()


def as_runner(sandbox: dict, argv: list[str]) -> list[str]:
    if os.geteuid() != 0:
        return argv
    return ["runuser", "-u", sandbox["runner"]["user"], "--", *argv]


def runner_env(sandbox: dict) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"GITHUB_TOKEN", "GH_TOKEN"}}
    env["HOME"] = sandbox["runner"]["home"]
    ca = sandbox.get("runner_ca_bundle")
    if ca:
        for name in (
            "GIT_SSL_CAINFO",
            "SSL_CERT_FILE",
            "REQUESTS_CA_BUNDLE",
            "CURL_CA_BUNDLE",
            "PIP_CERT",
        ):
            env[name] = ca
    return env


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="One-command disposable PR integration test.")
    parser.add_argument("--repo", required=True, help="OWNER/REPO")
    parser.add_argument(
        "--pr", type=int, action="append", required=True, help="repeat for several PRs"
    )
    parser.add_argument(
        "--authority", required=True, help="who authorized disposable testing, and where"
    )
    parser.add_argument("--phase", action="append", help="declared V2 phase to run (default: test)")
    parser.add_argument(
        "--order-basis", choices=["EXPLICIT_APPROVED", "VERIFIED_DEPENDENCY", "ORDER_PROBED"]
    )
    parser.add_argument(
        "--probes", type=Path, help="JSON list of negative probes (path/from/to/name)"
    )
    parser.add_argument("--timeout", type=int, default=900, help="seconds per phase (max 1800)")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)
    phases = args.phase or ["test"]
    try:
        import docker_sandbox

        sandbox = docker_sandbox.status()
        if sandbox.get("status") != "READY":
            sandbox = docker_sandbox.ensure("main", False)
        if sandbox.get("status") != "READY":
            raise QuickError(f"docker sandbox {sandbox.get('status')}: {sandbox.get('reason')}")
        runner = sandbox["runner"]
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        run_dir = (
            Path(runner["home"])
            / "l9-pr-runs"
            / f"{args.repo.replace('/', '__')}-{'-'.join(map(str, args.pr))}-{stamp}"
        )
        run_dir.mkdir(parents=True)
        binding = run_dir / "binding.json"
        bind = [
            sys.executable,
            str(HERE / "bind_github.py"),
            "--repo",
            args.repo,
            "--out",
            str(binding),
        ]
        for number in args.pr:
            bind += ["--pr", str(number)]
        run(bind, timeout=180)
        manifest = json.loads(binding.read_text())
        base_sha = manifest["repository"]["base_sha"]
        contract = gh_raw(args.repo, CONTRACT_PATH, base_sha)
        manifest["test_procedures"] = procedures_from_contract(contract, phases, args.timeout)
        manifest["image"] = dependency_layer(sandbox, args.repo, base_sha)
        manifest["execution_authority"] = {
            "scope": "DISPOSABLE_DOCKER_ONLY",
            "source": args.authority,
        }
        manifest["toolchain_sandbox"] = {
            "core_sha": sandbox["core_sha"],
            "image_tag": sandbox["image_tag"],
            "toolchain_lock": sandbox["toolchain_lock"],
        }
        if args.order_basis:
            manifest["order_basis"] = args.order_basis
        if args.probes:
            manifest["negative_probes"] = json.loads(args.probes.read_text())
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        # The runner cannot read a root-owned governance clone, so it executes a
        # frozen copy of the runner scripts inside its own run directory.
        frozen = run_dir / "runner-scripts"
        frozen.mkdir()
        for name in RUNNER_SCRIPTS:
            shutil.copy2(HERE / name, frozen / name)
        manifest_path.write_text(
            json.dumps({**manifest, "runner_scripts": frozen_digests(frozen)}, indent=2) + "\n"
        )
        if os.geteuid() == 0:
            for path in (
                run_dir.parent,
                run_dir,
                binding,
                manifest_path,
                frozen,
                *frozen.iterdir(),
            ):
                shutil.chown(path, runner["user"], runner["user"])
        evidence = run_dir / "evidence"
        subprocess.run(
            as_runner(
                sandbox,
                [
                    "python3",
                    str(frozen / "integrate.py"),
                    "--manifest",
                    str(manifest_path),
                    "--out",
                    str(evidence),
                ],
            ),
            env=runner_env(sandbox),
            capture_output=True,
            text=True,
            timeout=args.timeout * (len(phases) * (len(args.pr) + 3)) + 900,
        )
        if not (evidence / "integration_verdict.json").exists():
            raise QuickError(f"integrate.py produced no verdict; see {run_dir}")
        summary = summarize(evidence)
        extras = []
        changed = dependency_changes(
            json.loads((evidence / "integration_manifest.json").read_text()).get(
                "changed_files_by_pr", {}
            )
        )
        if changed:
            extras.append(
                "PR changes dependency manifests the base-SHA layer cannot reflect: "
                + ", ".join(changed)
            )
        summary["notes"] = extras
    except (QuickError, OSError, subprocess.SubprocessError, KeyError, json.JSONDecodeError) as exc:
        summary = {"verdict": "BLOCKED", "reason": str(exc)}
        print(json.dumps(summary, indent=2) if args.json else f"PR integration: BLOCKED — {exc}")
        return 1
    print(json.dumps(summary, indent=2) if args.json else render(summary, summary["notes"]))
    return 0 if summary["verdict"] != "BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
