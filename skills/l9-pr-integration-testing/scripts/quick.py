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
  no network. A PR that changes a dependency input is BLOCKED, never tested
  against that stale layer;
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
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
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


FAILURE_PARSERS = ("pytest", "unittest", "node-test")


def procedures_from_contract(
    raw: bytes, phases: list[str], timeout: int, failure_parser: str | None = None
) -> list[dict]:
    """Turn the repository's declared V2 phases into anchored test procedures.

    ``failure_parser`` names the test runner whose output the phase prints. It
    is what lets a mutation probe be judged on a candidate that is already red:
    without failure identities a pre-existing failure cannot be told apart from
    one the mutation caused.
    """
    if failure_parser is not None and failure_parser not in FAILURE_PARSERS:
        raise QuickError(f"unknown failure parser {failure_parser!r}")
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
        procedure = {
            "id": f"make-{phase}",
            "name": f"make {phase}",
            "argv": ["make", phase],
            "timeout_seconds": timeout,
            "source": {"path": CONTRACT_PATH, "sha256": digest, "anchor": anchor},
        }
        if failure_parser:
            procedure["failure_parser"] = failure_parser
        procedures.append(procedure)
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


def refuse_dependency_changes(changed_files_by_pr: dict[str, list[str]]) -> None:
    changed = dependency_changes(changed_files_by_pr)
    if changed:
        raise QuickError(
            "PR changes dependency inputs the base-SHA layer cannot represent ("
            + ", ".join(changed)
            + "); build the manifest by hand with an image provisioned from the "
            "combined revision"
        )


def summarize(evidence: Path) -> dict:
    verdict = json.loads((evidence / "integration_verdict.json").read_text())
    manifest = json.loads((evidence / "integration_manifest.json").read_text())
    findings = json.loads((evidence / "integration_findings.json").read_text())
    findings = findings if isinstance(findings, list) else findings.get("findings", [])
    states = []
    for state in manifest.get("states", []):
        tests = [t["status"] for t in state.get("tests", [])]
        merges = [m["status"] for m in state.get("merges", [])]
        skips = [t["skipped"] for t in state.get("tests", []) if t.get("skipped") is not None]
        states.append(
            {
                "name": state["name"],
                "revision": (state.get("revision") or {}).get("sha", "")[:12],
                "merges": merges,
                "tests": tests,
                "skipped": sum(skips) if skips else None,
            }
        )
    return {
        "verdict": verdict["state"],
        "execution": verdict["execution"],
        "states": states,
        "probes": [
            {"name": p.get("name"), "status": p.get("status"), "basis": p.get("basis", [])}
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
        "services": [x.get("name") for x in manifest.get("services") or []],
        "test_env_omitted": manifest.get("test_env_omitted", []),
        "service_warnings": manifest.get("service_warnings", []),
        "cleanup": manifest.get("cleanup"),
        "runner_scripts": manifest.get("runner_scripts", {}),
        "evidence": str(evidence),
    }


def render(summary: dict) -> str:
    lines = [f"PR integration: {summary['verdict']}"]
    for state in summary["states"]:
        merge = f" merge={'/'.join(state['merges'])}" if state["merges"] else ""
        tests = "/".join(state["tests"]) or "none"
        skipped = "" if state.get("skipped") is None else f" skipped={state['skipped']}"
        lines.append(f"  {state['name']:<10} {state['revision']:<12}{merge} tests={tests}{skipped}")
    if summary.get("services"):
        lines.append(f"  services: {', '.join(summary['services'])} (loopback only)")
    for warning in summary.get("service_warnings", []):
        lines.append(f"  not reproduced: {warning}")
    if summary.get("test_env_omitted"):
        lines.append("  not reproduced (CI expressions): " + ", ".join(summary["test_env_omitted"]))
    for probe in summary["probes"]:
        lines.append(f"  probe {probe['name']}: {probe['status']}")
        if probe["status"] != "KILLED":
            lines += [f"    {why}" for why in probe.get("basis", [])[:3]]
    for finding in summary["findings"]:
        lines.append(f"  [{finding['classification']} {finding['severity']}] {finding['reason']}")
    lines.append(f"  evidence: {summary['evidence']}")
    if summary["verdict"] == "INCOMPLETE_EVIDENCE" and summary["execution"].get("docker_executed"):
        lines.append(
            "  next: review the combined diff, then scripts/apply_review.py (SKILL.md step 7)"
        )
    return "\n".join(lines)


# Health flags a CI service may declare. Any other docker option (volumes,
# privileges, entrypoints, networks) changes what the sidecar is and is refused.
HEALTH_FLAGS = {
    "--health-cmd": "cmd",
    "--health-interval": "interval",
    "--health-timeout": "timeout",
    "--health-retries": "retries",
    "--health-start-period": "start_period",
}
# Non-secret run contexts a CI file may interpolate into a disposable value
# (a throwaway database password, say). Replaced by a fixed local literal.
RUN_CONTEXT = re.compile(r"\$\{\{\s*github\.(?:run_id|run_number|run_attempt)\s*\}\}")
LOCAL_RUN_VALUE = "l9local"
# Service settings an official image's entrypoint fetches from the internet at
# startup. The service still turns healthy without them (Neo4j logs "will
# continue to start"), so they are named up front rather than discovered later.
STARTUP_DOWNLOADS = {"NEO4J_PLUGINS"}


def _literal(value: object) -> str | None:
    """A committed literal with run contexts resolved; None for any other expression."""
    text = str(value).lower() if isinstance(value, bool) else str(value)
    text = RUN_CONTEXT.sub(LOCAL_RUN_VALUE, text)
    return None if "${{" in text else text


def parse_health(options: str, service: str) -> dict:
    health: dict = {}
    words = shlex.split(options or "")
    i = 0
    while i < len(words):
        flag, _, inline = words[i].partition("=")
        if flag not in HEALTH_FLAGS:
            raise QuickError(
                f"service {service} declares option {flag!r}; only health checks are supported"
            )
        if inline:
            value = inline
        elif i + 1 < len(words):
            i += 1
            value = words[i]
        else:
            raise QuickError(f"service {service} option {flag} has no value")
        key = HEALTH_FLAGS[flag]
        health[key] = int(value) if key == "retries" else value
        i += 1
    if "cmd" not in health:
        raise QuickError(
            f"service {service} declares no --health-cmd; tests would race its startup"
        )
    return health


def services_from_workflow(raw: bytes, workflow: str, job: str) -> dict:
    """The service sidecars and test environment one CI job declares.

    Service images are returned as written; the caller pins them by digest.
    Job and workflow environment travels to the tests; a value that is a
    workflow expression (a secret, a variable) is omitted and named, never
    filled in, and a service whose own environment needs one is refused.
    """
    import yaml

    try:
        document = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise QuickError(f"{workflow} is not YAML: {exc}") from exc
    jobs = (document or {}).get("jobs") or {}
    if job not in jobs:
        raise QuickError(f"{workflow} has no job {job!r} (jobs: {', '.join(sorted(jobs))})")
    definition = jobs[job] or {}
    if definition.get("container"):
        raise QuickError(f"{workflow}:{job} runs in a job container; only host jobs are supported")
    services, ports_seen = [], set()
    for name, spec in (definition.get("services") or {}).items():
        spec = spec or {}
        if not isinstance(spec, dict) or not isinstance(spec.get("image"), str):
            raise QuickError(f"service {name} has no image")
        for key in ("credentials", "volumes"):
            if spec.get(key):
                raise QuickError(f"service {name} declares {key}; not supported offline")
        image = _literal(spec["image"])
        if not image:
            raise QuickError(f"service {name} image is a workflow expression")
        env = {}
        for key, value in (spec.get("env") or {}).items():
            literal = _literal(value)
            if literal is None:
                raise QuickError(
                    f"service {name} env {key} is a workflow expression; "
                    "the service cannot be reproduced without it"
                )
            env[str(key)] = literal
        ports = []
        for mapping in spec.get("ports") or []:
            parts = str(mapping).split(":")
            if not all(part.isdigit() for part in parts) or len(parts) > 2:
                raise QuickError(f"service {name} port {mapping!r} is not HOST:CONTAINER")
            if len(parts) == 2 and parts[0] != parts[1]:
                raise QuickError(
                    f"service {name} maps host port {parts[0]} to {parts[1]}; tests here reach "
                    "services on their own port, so the mapping must be identical"
                )
            port = int(parts[-1])
            if port in ports_seen:
                raise QuickError(f"two services listen on port {port}")
            ports_seen.add(port)
            ports.append(port)
        services.append(
            {
                "name": str(name).lower().replace("_", "-"),
                "image": image,
                "env": env,
                "ports": ports,
                "health": parse_health(spec.get("options", ""), str(name)),
            }
        )
    test_env, omitted = {}, []
    for scope in ((document or {}).get("env") or {}, definition.get("env") or {}):
        for key, value in scope.items():
            literal = _literal(value)
            if literal is None:
                omitted.append(str(key))
                test_env.pop(str(key), None)
            else:
                test_env[str(key)] = literal
    warnings = [
        f"{x['name']}: {key} downloads at startup; with no network it is not loaded"
        for x in services
        for key in x["env"]
        if key in STARTUP_DOWNLOADS
    ]
    return {
        "source": {"workflow": workflow, "job": job},
        "services": services,
        "service_warnings": warnings,
        "test_env": test_env,
        "test_env_omitted": sorted(set(omitted) - set(test_env)),
    }


# --- Host side ---------------------------------------------------------------


WORKFLOW_FILE = re.compile(r"^[A-Za-z0-9_.-]+\.ya?ml$")


def ci_services(repo: str, base_sha: str, spec: str, docker_sandbox) -> dict:
    """Services from ``WORKFLOW:JOB`` at the base SHA, each image pinned by digest."""
    workflow, sep, job = spec.partition(":")
    if not sep or not job or not WORKFLOW_FILE.fullmatch(workflow):
        raise QuickError("--ci-job must be WORKFLOW:JOB, e.g. ci.yml:validate")
    raw = gh_raw(repo, f".github/workflows/{workflow}", base_sha)
    derived = services_from_workflow(raw, workflow, job)
    pins = load_service_pins()
    for service in derived["services"]:
        tag = canonical_tag(service["image"])
        pin = pins.get(tag)
        if pin is None:
            derived["service_warnings"].append(
                f"{service['name']}: {tag} is not in {SERVICE_PINS.name}; "
                "its digest was resolved from the floating tag at run time"
            )
        try:
            service["image"] = docker_sandbox.pin_image(tag, digest=pin["digest"] if pin else None)
        except docker_sandbox.SandboxError as exc:
            raise QuickError(f"service {service['name']}: {exc}") from exc
        service["pinned"] = pin is not None
    derived["service_source"] = {**derived.pop("source"), "sha": base_sha}
    return derived


SERVICE_PINS = HERE.parent / "references" / "service-images.json"
SERVICE_PINS_SCHEMA = "l9.pr-integration.service-images/v1"
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def canonical_tag(image: str) -> str:
    """A Docker Hub name as the pin file keys it: no docker.io/ or library/ prefix."""
    for prefix in ("docker.io/", "index.docker.io/"):
        if image.startswith(prefix):
            image = image[len(prefix) :]
    return image[len("library/") :] if image.startswith("library/") else image


def load_service_pins(path: Path = SERVICE_PINS) -> dict:
    """The vendored digest pins, validated. Read from this skill only, never fetched."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuickError(f"{path.name} is unreadable: {exc}") from exc
    if document.get("schema") != SERVICE_PINS_SCHEMA:
        raise QuickError(f"{path.name} must declare schema {SERVICE_PINS_SCHEMA}")
    images = document.get("images")
    if not isinstance(images, dict):
        raise QuickError(f"{path.name} has no images table")
    for tag, pin in images.items():
        if ":" not in tag or "@" in tag or canonical_tag(tag) != tag:
            raise QuickError(f"{path.name} key {tag!r} must be a bare Docker Hub name:tag")
        if not isinstance(pin, dict) or not DIGEST.fullmatch(str(pin.get("digest", ""))):
            raise QuickError(f"{path.name} pin for {tag} needs a sha256 digest")
    return images


def pr_changed_files(repo: str, number: int) -> list[str]:
    proc = subprocess.run(
        ["gh", "api", "--paginate", f"repos/{repo}/pulls/{number}/files", "--jq", ".[].filename"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode:
        raise QuickError(f"cannot list files of {repo}#{number}: {proc.stderr.strip()[-200:]}")
    return [line for line in proc.stdout.splitlines() if line]


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


# Bump when the layer recipe changes, so an image cached from an older recipe
# is never reused under the new one.
LAYER_RECIPE = "r2"
WHEELHOUSE = "/opt/l9-wheelhouse"
# pip's PEP 517 fallback for a setuptools project with no [build-system] table.
SETUPTOOLS_FALLBACK = "setuptools>=40.8.0"


def build_requirements(pyproject: str | None, has_setup_py: bool) -> list[str]:
    """The PEP 517 build requirements an isolated build will try to install.

    Tests run with no network, so ``python -m build`` (and any pip install of
    the project) can only resolve its build backend from a wheelhouse prepared
    while the image is built.
    """
    if pyproject is not None:
        try:
            table = tomllib.loads(pyproject).get("build-system", {})
        except tomllib.TOMLDecodeError as exc:
            raise QuickError(f"pyproject.toml is not valid TOML: {exc}") from exc
        requires = table.get("requires")
        if requires is not None:
            if not isinstance(requires, list) or not all(isinstance(r, str) for r in requires):
                raise QuickError("pyproject.toml [build-system].requires must be a list of strings")
            return requires
    return [SETUPTOOLS_FALLBACK] if (pyproject is not None or has_setup_py) else []


def render_dependency_dockerfile(
    image_tag: str, repo: str, base_sha: str, build_requires: list[str], *, with_ca: bool
) -> str:
    """Toolchain image + `make setup` + an offline wheelhouse for PEP 517 builds."""
    ca_mount = "--mount=type=secret,id=ca " if with_ca else ""
    ca_env = "PIP_CERT=/run/secrets/ca " if with_ca else ""
    lines = [
        f"FROM {image_tag}",
        f"RUN {ca_mount}--mount=type=bind,source=src,target=/src,rw \\",
        f"    cd /src && {ca_env}make setup",
        f"RUN mkdir -p {WHEELHOUSE}",
    ]
    if build_requires:
        lines += [
            f"RUN {ca_mount}--mount=type=bind,source=build-requirements.txt,"
            "target=/tmp/l9/build-requirements.txt \\",
            f"    {ca_env}python -m pip download --no-cache-dir --dest {WHEELHOUSE} \\",
            "    -r /tmp/l9/build-requirements.txt",
        ]
    lines += [
        # Set after `make setup`, so only the offline test run is pointed at
        # the wheelhouse. With no network the index can never answer anyway.
        f"ENV PIP_FIND_LINKS={WHEELHOUSE} PIP_NO_INDEX=1",
        f'LABEL org.l9.repo="{repo}" org.l9.base-sha="{base_sha}" '
        f'org.l9.layer-recipe="{LAYER_RECIPE}"',
    ]
    return "\n".join(lines) + "\n"


def dependency_layer(sandbox: dict, repo: str, base_sha: str) -> str:
    """Toolchain image + the repository's own `make setup`, at the base SHA."""
    safe = repo.lower().replace("/", "__")
    tag = f"l9-pr-deps/{safe}:{base_sha[:12]}-core{sandbox['core_sha'][:12]}-{LAYER_RECIPE}"
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
        # The trust bundle reaches the build only as a BuildKit secret mount; the
        # Dockerfile carries the mount flag text, never the bundle.
        ca = sandbox.get("runner_ca_bundle")
        src = ctx / "src"
        pyproject = src / "pyproject.toml"
        requires = build_requirements(
            pyproject.read_text(encoding="utf-8") if pyproject.is_file() else None,
            (src / "setup.py").is_file(),
        )
        (ctx / "build-requirements.txt").write_text("".join(f"{r}\n" for r in requires))
        (ctx / "Dockerfile").write_text(
            render_dependency_dockerfile(
                sandbox["image_tag"], repo, base_sha, requires, with_ca=bool(ca)
            )
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
    parser.add_argument(
        "--ci-job",
        metavar="WORKFLOW:JOB",
        help="run the tests beside the services this CI job declares, e.g. ci.yml:validate",
    )
    parser.add_argument(
        "--print-services",
        action="store_true",
        help="with --ci-job: print the pinned services and test env as JSON, then exit",
    )
    parser.add_argument(
        "--failure-parser",
        choices=FAILURE_PARSERS,
        help="test runner the phases print (lets probes judge an already-red candidate)",
    )
    parser.add_argument("--timeout", type=int, default=900, help="seconds per phase (max 1800)")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    parser.add_argument(
        "--image-only",
        action="store_true",
        help="build the pinned dependency image and print its id (for a hand-written manifest)",
    )
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
        # The dependency layer is built at the base SHA. A PR that changes a
        # dependency input would be tested against stale dependencies, so the
        # quick path refuses it instead of producing evidence that could be
        # promoted to INTEGRATION_READY.
        changed = {str(n): pr_changed_files(args.repo, n) for n in args.pr}
        refuse_dependency_changes(changed)
        if args.ci_job:
            # Services come from the workflow at the base SHA, like the
            # dependency layer; a PR that edits that workflow would be tested
            # beside the wrong services.
            workflow = f".github/workflows/{args.ci_job.partition(':')[0]}"
            editing = sorted(pr for pr, files in changed.items() if workflow in files)
            if editing:
                raise QuickError(
                    f"PR {', '.join(editing)} changes {workflow}; its services would be stale here"
                )
            # Before the contract, so --print-services also serves a repository
            # with no V2 contract (its services feed a hand-written manifest).
            manifest.update(ci_services(args.repo, base_sha, args.ci_job, docker_sandbox))
            if args.print_services:
                keys = (
                    "service_source",
                    "services",
                    "service_warnings",
                    "test_env",
                    "test_env_omitted",
                )
                print(json.dumps({k: manifest[k] for k in keys}, indent=2))
                return 0
        elif args.print_services:
            raise QuickError("--print-services needs --ci-job WORKFLOW:JOB")
        contract = gh_raw(args.repo, CONTRACT_PATH, base_sha)
        manifest["test_procedures"] = procedures_from_contract(
            contract, phases, args.timeout, args.failure_parser
        )
        manifest["image"] = dependency_layer(sandbox, args.repo, base_sha)
        if args.image_only:
            print(manifest["image"])
            return 0
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
    except (QuickError, OSError, subprocess.SubprocessError, KeyError, json.JSONDecodeError) as exc:
        summary = {"verdict": "BLOCKED", "reason": str(exc)}
        print(json.dumps(summary, indent=2) if args.json else f"PR integration: BLOCKED — {exc}")
        return 1
    print(json.dumps(summary, indent=2) if args.json else render(summary))
    return 0 if summary["verdict"] != "BLOCKED" else 1


if __name__ == "__main__":
    sys.exit(main())
