#!/usr/bin/env python3
"""Revision-bound, fail-closed Docker integration runner. No upstream mutations."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Sibling modules (validate_evidence) resolve even under `python -I`.
sys.path.insert(0, str(Path(__file__).resolve().parent))

HEX40 = re.compile(r"^[0-9a-f]{40}$")
IMAGE = re.compile(r"^(?:sha256:[0-9a-f]{64}|[a-zA-Z0-9][a-zA-Z0-9_./:-]*@sha256:[0-9a-f]{64})$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SAFE_REF = re.compile(r"^[A-Za-z0-9_./-]+$")
CATEGORIES = {"PYTHON", "NODE", "ODOO", "CONTAINER", "DATABASE"}
SERVICE_NAME = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
DURATION = re.compile(r"^([0-9]{1,4})(ms|s|m)$")
# What an official database image's entrypoint needs to drop from root to its
# service user. Nothing here reaches the network: services share a namespace
# whose only interface is loopback.
SERVICE_CAPS = ("CHOWN", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID")


class SafetyError(RuntimeError):
    """Critical metadata/authority/infra failure; no speculative workaround."""


def now():
    return datetime.now(UTC).isoformat()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def assert_sha(value, label):
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        raise SafetyError(f"{label} must be an immutable lowercase Git commit SHA")


def bounded_relative(path: str) -> bool:
    p = Path(path)
    return (
        bool(path)
        and not p.is_absolute()
        and ".." not in p.parts
        and ".git" not in p.parts
        and not any(x in path for x in ("\\", "\x00"))
    )


def validate_env(env, where: str) -> dict:
    """Literal, committed configuration only: no expressions, no NULs."""
    if env is None:
        return {}
    if not isinstance(env, dict):
        raise SafetyError(f"{where} must be an object of strings")
    for key, value in env.items():
        if not isinstance(key, str) or not ENV_KEY.fullmatch(key):
            raise SafetyError(f"{where} has an invalid variable name {key!r}")
        if not isinstance(value, str) or "\x00" in value or "\n" in value:
            raise SafetyError(f"{where}.{key} must be a single-line string")
        if "${{" in value:
            raise SafetyError(f"{where}.{key} is a workflow expression, not a literal value")
    return env


def duration_seconds(value: str) -> float:
    match = DURATION.fullmatch(value)
    if not match:
        raise SafetyError(f"health duration {value!r} must look like 500ms, 10s or 1m")
    number, unit = int(match.group(1)), match.group(2)
    return number / 1000 if unit == "ms" else number * 60 if unit == "m" else float(number)


def validate_services(services) -> list:
    """Service sidecars: digest-pinned, health-checked, on one loopback namespace."""
    if services is None:
        return []
    if not isinstance(services, list) or len(services) > 6:
        raise SafetyError("services must be a list of at most 6 sidecars")
    names, ports = set(), set()
    for service in services:
        if not isinstance(service, dict):
            raise SafetyError("each service must be an object")
        name = service.get("name", "")
        if not SERVICE_NAME.fullmatch(name) or name in names:
            raise SafetyError(f"service name {name!r} must be unique, lowercase and short")
        names.add(name)
        if not isinstance(service.get("image"), str) or not IMAGE.fullmatch(service["image"]):
            raise SafetyError(f"service {name} image must be pinned by sha256 digest")
        validate_env(service.get("env"), f"services.{name}.env")
        health = service.get("health")
        if not isinstance(health, dict):
            raise SafetyError(
                f"service {name} needs a health check: tests must not race its startup"
            )
        cmd = health.get("cmd")
        if not isinstance(cmd, str) or not cmd.strip() or "\x00" in cmd or "\n" in cmd:
            raise SafetyError(f"service {name} health.cmd must be a single-line command")
        for key in ("interval", "timeout", "start_period"):
            if key in health:
                duration_seconds(health[key])
        retries = health.get("retries", 3)
        if not isinstance(retries, int) or not 1 <= retries <= 100:
            raise SafetyError(f"service {name} health.retries must be 1-100")
        for port in service.get("ports", []):
            if not isinstance(port, int) or not 0 < port < 65536:
                raise SafetyError(f"service {name} port {port!r} invalid")
            if port in ports:
                raise SafetyError(
                    f"two services listen on port {port}; one loopback namespace cannot hold both"
                )
            ports.add(port)
    return services


def health_deadline(health: dict) -> float:
    """How long Docker itself would take to call the service unhealthy, plus slack."""
    interval = duration_seconds(health.get("interval", "30s"))
    timeout = duration_seconds(health.get("timeout", "30s"))
    start = duration_seconds(health.get("start_period", "0s"))
    return min(600.0, start + (interval + timeout) * (health.get("retries", 3) + 1) + 30)


def validate_plan(m: dict):
    if not isinstance(m, dict):
        raise SafetyError("manifest must be an object")
    repo = m.get("repository", {})
    if not REPO.fullmatch(repo.get("full_name", "")):
        raise SafetyError("repository.full_name must be owner/name")
    target = repo.get("url", "")
    if target != f"https://github.com/{repo['full_name']}.git":
        if not m.get("fixture_only") or not Path(target).is_absolute():
            raise SafetyError("repository.url must be canonical GitHub HTTPS URL")
    assert_sha(repo.get("base_sha"), "repository.base_sha")
    if not SAFE_REF.fullmatch(repo.get("base_ref", "")) or repo["base_ref"].startswith("-"):
        raise SafetyError("repository.base_ref invalid")
    prs = m.get("prs")
    if not isinstance(prs, list) or not prs or len(prs) > 8:
        raise SafetyError("prs must have 1-8 selected pull requests")
    ids = set()
    heads = set()
    for pr in prs:
        n = pr.get("number")
        if not isinstance(n, int) or n <= 0 or n in ids:
            raise SafetyError("PR IDs must be distinct positive integers")
        ids.add(n)
        assert_sha(pr.get("head_sha"), f"PR {n} head")
        if pr["head_sha"] in heads:
            raise SafetyError("multiple PR identifiers point to one head; disclose duplication")
        heads.add(pr["head_sha"])
        source = pr.get("fetch_url", "")
        if source != target and (not m.get("fixture_only") or not Path(source).is_absolute()):
            raise SafetyError(f"PR {n} must use verified target PR fetch endpoint")
        ref = pr.get("fetch_ref", "")
        if not SAFE_REF.fullmatch(ref) or ref.startswith("-"):
            raise SafetyError(f"PR {n} fetch ref invalid")
        if not m.get("fixture_only") and ref != f"refs/pull/{n}/head":
            raise SafetyError(f"PR {n} must bind to refs/pull/{n}/head")
        if pr.get("base_ref") != repo["base_ref"]:
            raise SafetyError(f"PR {n} targets a different base; stacked/base resolution required")
    order = m.get("integration_order", [])
    if sorted(order) != sorted(ids):
        raise SafetyError("integration_order must enumerate each selected PR exactly once")
    if len(prs) > 1 and m.get("order_basis") not in {
        "EXPLICIT_APPROVED",
        "VERIFIED_DEPENDENCY",
        "ORDER_PROBED",
    }:
        raise SafetyError("multi-PR integration requires justified order_basis")
    if m.get("network", "none") != "none":
        raise SafetyError(
            "network access requires a separately reviewed runner, not this safe profile"
        )
    if not isinstance(m.get("image"), str) or not IMAGE.fullmatch(m.get("image")):
        raise SafetyError("locally available Docker image must be pinned by sha256 digest")
    tests = m.get("test_procedures", [])
    if not isinstance(tests, list) or not tests:
        raise SafetyError("at least one verified test procedure is required")
    procedure_ids = [p.get("id") for p in tests if isinstance(p, dict)]
    if any(not isinstance(i, str) or not i for i in procedure_ids) or len(
        set(procedure_ids)
    ) != len(tests):
        raise SafetyError("every test procedure needs a unique nonempty id")
    for p in tests:
        argv = p.get("argv")
        if (
            not isinstance(argv, list)
            or not argv
            or any(not isinstance(s, str) or not s or "\x00" in s for s in argv)
        ):
            raise SafetyError("test procedures must be nonempty argv arrays (no shell)")
        if argv[0] in {"sh", "bash", "dash", "zsh", "cmd", "powershell", "sudo", "env"}:
            raise SafetyError("shell, sudo and env wrappers are not approved test commands")
        origin = p.get("source", {})
        if (
            not bounded_relative(origin.get("path", ""))
            or not re.fullmatch(r"[0-9a-f]{64}", origin.get("sha256", ""))
            or not isinstance(origin.get("anchor"), str)
        ):
            raise SafetyError("every test command needs verified baseline file path + sha256")
        if p.get("timeout_seconds", 300) > 1800 or p.get("timeout_seconds", 300) < 1:
            raise SafetyError("timeout must be 1-1800 seconds")
    authority = m.get("execution_authority", {})
    if authority.get("scope") != "DISPOSABLE_DOCKER_ONLY" or not authority.get("source"):
        raise SafetyError("explicit verified disposable execution authority source required")
    for probe in m.get("negative_probes", []):
        if not bounded_relative(probe.get("path", "")):
            raise SafetyError("probe path must remain inside disposable worktree")
        if (
            not isinstance(probe.get("from"), str)
            or not probe["from"]
            or not isinstance(probe.get("to"), str)
        ):
            raise SafetyError("probe requires exact nonempty from and to text")
        if probe["from"] == probe["to"] or len(probe["from"]) > 8000 or len(probe["to"]) > 8000:
            raise SafetyError("probe must materially change bounded exact text")
    validate_services(m.get("services"))
    validate_env(m.get("test_env"), "test_env")
    if m.get("fixture_only"):
        raise SafetyError("fixture_only input cannot be run through production CLI")
    return True


# Markers of a failure in the runtime or transport, not in binding or authority.
# A TLS or network error on `git fetch` says nothing about who may run what.
ENVIRONMENT_MARKERS = (
    "docker_unavailable",
    "container",
    "image",
    "disposable baseline checkout failed",
    "unable to access",
    "ssl",
    "certificate",
    "could not resolve host",
    "failed to connect",
    "connection timed out",
    "connection refused",
    "network is unreachable",
)


def blocker_kind(reason: str) -> str:
    lowered = reason.lower()
    return (
        "ENVIRONMENT" if any(marker in lowered for marker in ENVIRONMENT_MARKERS) else "AUTHORITY"
    )


def git_env():
    e = dict(os.environ)
    for key in list(e):
        if key.startswith("GIT_CONFIG_") or key == "GIT_SSH_COMMAND":
            e.pop(key, None)
    e.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_LFS_SKIP_SMUDGE": "1",
        }
    )
    return e


def git(args: list[str], cwd: Path | None = None, timeout=120, check=True):
    cmd = ["git", "-c", "core.hooksPath=/dev/null", *args]
    p = subprocess.run(cmd, cwd=cwd, env=git_env(), text=True, capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise SafetyError(f"Git failed ({p.returncode}): {p.stderr[-700:]}")
    return p


def local_bind_git_objects(m: dict, workdir: Path):
    """Fetch immutable objects only. Test code/merges execute in Docker, not on host."""
    store = workdir / "objects.git"
    git(["init", "--bare", str(store)])
    remote = m["repository"]["url"]
    git(
        ["--git-dir", str(store), "fetch", "--no-tags", remote, m["repository"]["base_ref"]],
        timeout=300,
    )
    actual = git(["--git-dir", str(store), "rev-parse", "FETCH_HEAD"]).stdout.strip()
    if actual != m["repository"]["base_sha"]:
        raise SafetyError(
            "target base branch moved since binding: expected SHA differs from fetched SHA"
        )
    git(
        [
            "--git-dir",
            str(store),
            "update-ref",
            "refs/heads/l9-baseline",
            m["repository"]["base_sha"],
        ]
    )
    for pr in m["prs"]:
        git(
            ["--git-dir", str(store), "fetch", "--no-tags", pr["fetch_url"], pr["fetch_ref"]],
            timeout=300,
        )
        actual = git(["--git-dir", str(store), "rev-parse", "FETCH_HEAD"]).stdout.strip()
        if actual != pr["head_sha"]:
            raise SafetyError(
                f"PR #{pr['number']} moved since binding: expected SHA differs from fetched SHA"
            )
        git(
            [
                "--git-dir",
                str(store),
                "update-ref",
                f"refs/heads/l9-pr-{pr['number']}",
                pr["head_sha"],
            ]
        )
    return store


def git_blob(store: Path, revision: str, path: str) -> bytes:
    raw = subprocess.run(
        ["git", "--git-dir", str(store), "show", f"{revision}:{path}"],
        capture_output=True,
        env=git_env(),
        timeout=60,
    )
    if raw.returncode:
        raise SafetyError(f"source authority file {path} missing at baseline {revision}")
    return raw.stdout


def verify_commands(m, store):
    base = m["repository"]["base_sha"]
    for procedure in m["test_procedures"]:
        s = procedure["source"]
        actual = sha(git_blob(store, base, s["path"]))
        if actual != s["sha256"]:
            raise SafetyError(
                f"test procedure source {s['path']} does not match pinned trusted baseline"
            )
        if not s.get("anchor") or s["anchor"].encode() not in git_blob(store, base, s["path"]):
            raise SafetyError(
                f"test command lacks verifiable invocation anchor in trusted file {s['path']}"
            )


def detect_adapters(files: list[str]) -> list[str]:
    names = set(files)
    types = set()
    if any(
        x in names for x in ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")
    ) or any(x.endswith(".py") for x in names):
        types.add("PYTHON")
    if "package.json" in names or any(x.endswith((".ts", ".tsx", ".js")) for x in names):
        types.add("NODE")
    if any(
        x.endswith(("/__manifest__.py", "/__openerp__.py"))
        or x in ("__manifest__.py", "__openerp__.py")
        for x in names
    ):
        types.add("ODOO")
    if any(x.endswith("Dockerfile") or x in ("compose.yaml", "docker-compose.yml") for x in names):
        types.add("CONTAINER")
    if any("migrations/" in x or x.endswith("schema.sql") for x in names):
        types.add("DATABASE")
    return sorted(types)


def changed_files(store, base, head):
    p = git(["--git-dir", str(store), "diff", "--name-only", f"{base}...{head}"])
    return [v for v in p.stdout.splitlines() if v]


def list_tree(store, base):
    return git(["--git-dir", str(store), "ls-tree", "-r", "--name-only", base]).stdout.splitlines()


def adapter_census(store, m):
    """Adapters across every tree the run tests, not only the base.

    A PR that adds an Odoo manifest or a migration must trip the
    stateful-adapter guard in apply_review.py as well.
    """
    files = set(list_tree(store, m["repository"]["base_sha"]))
    for pr in m["prs"]:
        files.update(list_tree(store, pr["head_sha"]))
    return detect_adapters(sorted(files))


def detect_overlap(store, m):
    per_pr = {
        str(p["number"]): changed_files(store, m["repository"]["base_sha"], p["head_sha"])
        for p in m["prs"]
    }
    index = {}
    for pid, files in per_pr.items():
        for f in files:
            index.setdefault(f, []).append(pid)
    return per_pr, [{"path": f, "prs": pids} for f, pids in sorted(index.items()) if len(pids) > 1]


def dependency_order(store, m):
    heads = {p["number"]: p["head_sha"] for p in m["prs"]}
    order = m["integration_order"]
    deps = []
    for a in order:
        for b in order:
            if a == b:
                continue
            p = git(
                ["--git-dir", str(store), "merge-base", "--is-ancestor", heads[a], heads[b]],
                check=False,
            )
            if p.returncode == 0:
                deps.append({"ancestor_pr": a, "descendant_pr": b})
                if order.index(a) > order.index(b):
                    raise SafetyError(
                        f"dependency order contradicts Git ancestry: PR {a} must precede {b}"
                    )
            elif p.returncode != 1:
                raise SafetyError("could not establish merge ancestry")
    if m.get("order_basis") == "VERIFIED_DEPENDENCY" and len(order) > 1 and not deps:
        raise SafetyError("order_basis claimed dependency but no ancestor relationship verified")
    return deps


def inspect_weak_tests(store, heads, per_pr):
    """Only triage signals, never proof of a defect or absence of one."""
    cues = []
    for prnum, paths in per_pr.items():
        head = heads[int(prnum)]
        for path in paths:
            if not (path.startswith("test") or "/test" in path or path.endswith(".spec.js")):
                continue
            try:
                b = git_blob(store, head, path)
            except SafetyError:
                continue
            body = b.decode("utf-8", "replace")
            for needle, label in (
                ("assert True", "constant_true_assertion"),
                ("@pytest.mark.skip", "skipped_test"),
                ("@pytest.mark.xfail", "expected_failure"),
                ("assert 1 == 1", "tautological_assertion"),
                ("expect(true).toBe(true)", "tautological_assertion"),
            ):
                if needle in body:
                    cues.append(
                        {
                            "pr": int(prnum),
                            "path": path,
                            "signal": label,
                            "status": "REVIEW_REQUIRED_NOT_CONFIRMED",
                        }
                    )
    return cues


class DockerSandbox:
    """Allowlisted docker run flags only; no networks, host socket, root or privilege."""

    def __init__(self, image, run_id, uid=None, gid=None, services=(), test_env=None):
        if not IMAGE.fullmatch(image):
            raise SafetyError("image digest not pinned")
        self.image = image
        self.services = list(services)
        self.test_env = dict(test_env or {})
        self.run_id = run_id
        self.uid = os.getuid() if uid is None else uid
        self.gid = os.getgid() if gid is None else gid
        if self.uid == 0:
            raise SafetyError(
                "DOCKER_UNAVAILABLE: root host UID requires a verified nonroot workspace policy"
            )
        self.call_number = 0

    def preflight(self):
        if shutil.which("docker") is None:
            raise SafetyError("DOCKER_UNAVAILABLE: Docker CLI not installed")
        provenance = {}
        for name, args in (
            ("docker_server", ["docker", "info", "--format", "{{.ServerVersion}}"]),
            ("image_id", ["docker", "image", "inspect", "--format", "{{.Id}}", self.image]),
        ):
            p = subprocess.run(args, capture_output=True, text=True, timeout=20)
            if p.returncode:
                raise SafetyError(
                    "DOCKER_UNAVAILABLE: Docker daemon or pinned local image unavailable: "
                    + p.stderr[-300:]
                )
            provenance[name] = p.stdout.strip()
        for service in self.services:
            p = subprocess.run(
                ["docker", "image", "inspect", "--format", "{{.Id}}", service["image"]],
                capture_output=True,
                text=True,
                timeout=20,
            )
            if p.returncode:
                raise SafetyError(
                    f"DOCKER_UNAVAILABLE: pinned service image for {service['name']} is not local"
                )
            provenance[f"service_image:{service['name']}"] = p.stdout.strip()
        return provenance

    def command(
        self,
        case_dir: Path,
        argv: list[str],
        seconds=300,
        isolate_git=False,
        network="none",
        env=None,
    ):
        self.call_number += 1
        name = f"l9-pr-{self.run_id}-{self.call_number}"
        if not argv or any(not isinstance(s, str) or "\x00" in s for s in argv):
            raise SafetyError("container command requires clean argv")
        if network != "none" and not re.fullmatch(r"container:l9-pr-[a-z0-9-]+-net-\d+", network):
            raise SafetyError("a command may only join this run's own loopback namespace")
        args = [
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--name",
            name,
            "--network",
            network,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "128",
            "--memory",
            "1024m",
            "--cpus",
            "2",
            "--ulimit",
            "nofile=1024:1024",
            "--user",
            f"{self.uid}:{self.gid}",
            "--workdir",
            "/workspace",
            "--mount",
            f"type=bind,src={case_dir.resolve()},dst=/workspace",
            # Docker mounts a --tmpfs noexec unless told otherwise, which fails
            # every test that runs a stub binary from a temp directory. exec here
            # grants nothing new: /workspace is already writable and executable.
            "--tmpfs",
            "/tmp:rw,exec,nosuid,nodev,size=128m",
            "-e",
            "HOME=/tmp",
            "-e",
            "GIT_TERMINAL_PROMPT=0",
            "-e",
            "PYTHONDONTWRITEBYTECODE=1",
            *(item for key, value in (env or {}).items() for item in ("-e", f"{key}={value}")),
            # The runner's own Git steps ignore global/system config and pin the
            # commit date. Test procedures must not inherit that: a suite that
            # writes $HOME/.gitconfig (url.insteadOf, identity) would otherwise
            # run differently here than in its own CI.
            *(
                [
                    "-e",
                    "GIT_CONFIG_GLOBAL=/dev/null",
                    "-e",
                    "GIT_CONFIG_NOSYSTEM=1",
                    "-e",
                    "GIT_COMMITTER_DATE=2000-01-01T00:00:00+00:00",
                    # Both dates, or a merge commit's SHA changes on every run
                    # and the same candidate gets a different revision id.
                    "-e",
                    "GIT_AUTHOR_DATE=2000-01-01T00:00:00+00:00",
                ]
                if isolate_git
                else []
            ),
            "--entrypoint",
            argv[0],
            self.image,
            *argv[1:],
        ]
        started = time.monotonic()
        try:
            p = subprocess.run(
                args, capture_output=True, text=True, errors="replace", timeout=seconds
            )
            stdout = (p.stdout or "")[-200000:]
            stderr = (p.stderr or "")[-100000:]
            return {
                "returncode": p.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "timed_out": False,
            }
        except subprocess.TimeoutExpired:
            # Docker client timeout can leave a daemon-side container; remove by exact name.
            subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=20)
            return {
                "returncode": None,
                "stdout": "",
                "stderr": "container command timed out; daemon-side cleanup requested",
                "elapsed_ms": int((time.monotonic() - started) * 1000),
                "timed_out": True,
            }

    @contextlib.contextmanager
    def services_up(self, writer, case):
        """Start this case's sidecars in a fresh network-less namespace.

        A holder container owns a namespace whose only interface is loopback.
        Services and the test container join it, so tests reach them on
        localhost exactly as a CI job does, and nothing has a route out. Every
        case gets fresh services: no state crosses from one candidate to the next.
        """
        if not self.services:
            yield "none"
            return
        self.call_number += 1
        holder = f"l9-pr-{self.run_id}-net-{self.call_number}"
        started = []
        try:
            self._docker_run_detached(
                [
                    "--name",
                    holder,
                    "--network",
                    "none",
                    # Joined containers take this hostname. Under --network none
                    # a container's own hostname does not resolve, and a server
                    # that looks itself up (Neo4j's JVM does) refuses to start;
                    # "localhost" resolves through the namespace's own hosts file.
                    "--hostname",
                    "localhost",
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "--pids-limit",
                    "8",
                    "--memory",
                    "32m",
                    "--user",
                    f"{self.uid}:{self.gid}",
                    "--entrypoint",
                    "sleep",
                    self.image,
                    "infinity",
                ]
            )
            started.append(holder)
            for service in self.services:
                name = f"{holder}-{service['name']}"
                health = service["health"]
                args = [
                    "--name",
                    name,
                    "--network",
                    f"container:{holder}",
                    "--cap-drop",
                    "ALL",
                    *(item for cap in SERVICE_CAPS for item in ("--cap-add", cap)),
                    "--security-opt",
                    "no-new-privileges",
                    "--pids-limit",
                    "256",
                    "--memory",
                    "1024m",
                    "--cpus",
                    "1",
                    "--health-cmd",
                    health["cmd"],
                    "--health-retries",
                    str(health.get("retries", 3)),
                ]
                for key in ("interval", "timeout", "start_period"):
                    if key in health:
                        args += [f"--health-{key.replace('_', '-')}", health[key]]
                for key, value in (service.get("env") or {}).items():
                    args += ["-e", f"{key}={value}"]
                self._docker_run_detached([*args, service["image"]])
                started.append(name)
            ready = {}
            for service in self.services:
                name = f"{holder}-{service['name']}"
                ready[service["name"]] = self._await_healthy(
                    name, service["name"], health_deadline(service["health"])
                )
            writer.record(
                case,
                "SERVICES",
                "HEALTHY",
                {
                    "namespace": "loopback-only",
                    "services": [
                        {"name": s["name"], "image": s["image"], "ready_ms": ready[s["name"]]}
                        for s in self.services
                    ],
                },
            )
            yield f"container:{holder}"
        finally:
            # Each service's own log travels with the evidence: a service can be
            # healthy yet degraded (a plugin it could not download), and that
            # must be attributable rather than read as a defect in the PR.
            for name in started[1:]:
                logs = subprocess.run(
                    ["docker", "logs", "--tail", "200", name],
                    capture_output=True,
                    text=True,
                    errors="replace",
                    timeout=30,
                )
                writer.record(
                    case,
                    "SERVICE_LOG",
                    "CAPTURED" if logs.returncode == 0 else "UNAVAILABLE",
                    {"container": name},
                    log=(logs.stdout or "") + (logs.stderr or ""),
                )
            for name in reversed(started):
                subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=60)

    def _docker_run_detached(self, args):
        p = subprocess.run(
            ["docker", "run", "-d", "--pull", "never", *args],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if p.returncode:
            raise SafetyError(
                "service container failed to start: " + (p.stderr or p.stdout).strip()[-300:]
            )

    def _await_healthy(self, container, label, deadline_seconds):
        started = time.monotonic()
        state = ""
        while time.monotonic() - started < deadline_seconds:
            p = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}",
                    container,
                ],
                capture_output=True,
                text=True,
                timeout=20,
            )
            state = p.stdout.strip()
            if state == "running healthy":
                return int((time.monotonic() - started) * 1000)
            if p.returncode or not state.startswith(("running", "created")) or "unhealthy" in state:
                break
            time.sleep(0.5)
        logs = subprocess.run(
            ["docker", "logs", "--tail", "40", container],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=20,
        )
        tail = ((logs.stdout or "") + (logs.stderr or "")).strip()[-600:]
        raise SafetyError(
            f"service container {label} did not become healthy ({state or 'gone'}); "
            f"it has no network, so an image that downloads at startup cannot run here. "
            f"log tail: {tail}"
        )


class EvidenceWriter:
    def __init__(self, output: Path):
        self.output = output
        (output / "logs").mkdir(parents=True, exist_ok=True)
        self.records = []
        self.findings = []
        self.seen_findings = set()

    def record(self, subject, kind, status, details=None, log=None):
        idx = len(self.records) + 1
        rid = f"E{idx:05d}"
        record = {
            "id": rid,
            "subject": subject,
            "kind": kind,
            "status": status,
            "details": details or {},
        }
        if log is not None:
            rel = f"logs/{rid}.txt"
            (self.output / rel).write_text(log, encoding="utf-8")
            record["log_path"] = rel
            record["log_sha256"] = sha((self.output / rel).read_bytes())
        self.records.append(record)
        return rid

    def finding(
        self,
        category,
        severity,
        reason,
        evidence_ids,
        scope="combined",
        root_cause="UNKNOWN",
        action="Reproduce and correct the authoritative owner",
    ):
        identity = f"{category}|{scope}|{reason}"
        fid = "F-" + sha(identity.encode())[:12]
        if fid in self.seen_findings:
            return fid
        self.seen_findings.add(fid)
        self.findings.append(
            {
                "id": fid,
                "classification": category,
                "severity": severity,
                "reason": reason,
                "scope": scope,
                "evidence_ids": list(evidence_ids),
                "root_cause": root_cause,
                "corrective_obligation": action,
            }
        )
        return fid

    def log_command(self, subject, kind, argv, result):
        body = (
            f"$ argv: {json.dumps(argv)}\nreturncode={result['returncode']} elapsed_ms={result['elapsed_ms']} timed_out={result['timed_out']}\n"
            + result["stdout"]
            + "\nSTDERR:\n"
            + result["stderr"]
        )
        return self.record(
            subject,
            kind,
            "TIMEOUT" if result["timed_out"] else "PASS" if result["returncode"] == 0 else "FAIL",
            {
                "argv": argv,
                "returncode": result["returncode"],
                "elapsed_ms": result["elapsed_ms"],
                "timed_out": result["timed_out"],
            },
            log=body,
        )


def docker_git(sandbox: DockerSandbox, path: Path, args, seconds=90):
    argv = [
        "git",
        "-c",
        "safe.directory=/workspace",
        "-c",
        "core.hooksPath=/dev/null",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "user.name=L9 Test",
        "-c",
        "user.email=integration@example.invalid",
        *args,
    ]
    return argv, sandbox.command(path, argv, seconds, isolate_git=True)


def prepare_case(store, name, workdir, sandbox, writer, base_sha, heads):
    path = workdir / name
    git(["clone", "--no-checkout", str(store), str(path)], timeout=120)
    argv, result = docker_git(sandbox, path, ["checkout", "--detach", base_sha])
    writer.log_command(name, "CHECKOUT", argv, result)
    if result["returncode"] != 0:
        raise SafetyError(f"disposable baseline checkout failed for {name}")
    merge_records = []
    for pr in heads:
        argv, result = docker_git(sandbox, path, ["merge", "--no-ff", "--no-edit", pr["head_sha"]])
        eid = writer.log_command(name, "MERGE", argv, result)
        merge_records.append(
            {
                "pr": pr["number"],
                "evidence_id": eid,
                "status": "PASS" if result["returncode"] == 0 else "CONFLICT",
            }
        )
        if result["returncode"] != 0:
            return path, merge_records, None
    argv, rev = docker_git(sandbox, path, ["rev-parse", "HEAD"])
    eid = writer.log_command(name, "REVISION", argv, rev)
    if rev["returncode"] != 0 or not HEX40.fullmatch(rev["stdout"].strip()):
        raise SafetyError("could not determine combined synthetic revision")
    return path, merge_records, {"sha": rev["stdout"].strip(), "evidence_id": eid}


def tests_case(sandbox, path, name, tests, writer):
    results = []
    with sandbox.services_up(writer, name) as network:
        for p in tests:
            result = sandbox.command(
                path,
                p["argv"],
                int(p.get("timeout_seconds", 300)),
                network=network,
                env=sandbox.test_env,
            )
            eid = writer.log_command(name, "TEST", p["argv"], result)
            body = result["stdout"] + "\n" + result["stderr"]
            parser = p.get("failure_parser", "")
            results.append(
                {
                    "evidence_id": eid,
                    "status": "TIMEOUT"
                    if result["timed_out"]
                    else "PASS"
                    if result["returncode"] == 0
                    else "FAIL",
                    "procedure": p["id"],
                    "returncode": result["returncode"],
                    "failure_ids": parse_failure_ids(body, parser),
                    "skipped": parse_skipped(body, parser),
                }
            )
    return results


def parse_skipped(body: str, parser: str):
    """Skipped-test count from a known runner's summary; None when unknown.

    A skip is not a pass: a suite that skips its database tests reports green
    while proving nothing about them, so the count travels with the result.
    """
    patterns = {
        "pytest": r"\b(\d+) skipped\b",
        "unittest": r"\bskipped=(\d+)\b",
        "node-test": r"(?m)^# skip (\d+)$",
    }
    if parser not in patterns:
        return None
    found = re.findall(patterns[parser], body)
    return sum(int(n) for n in found) if found else 0


def parse_failure_ids(body: str, parser: str):
    """Known parsers only; unknown shapes must not invent test identities."""
    if parser == "pytest":
        return sorted(set(re.findall(r"(?m)^FAILED\s+(\S+)", body)))
    if parser == "unittest":
        return sorted(set(re.findall(r"(?m)^(?:FAIL|ERROR): (.+)$", body)))
    if parser == "node-test":
        return sorted(set(re.findall(r"(?m)^not ok \d+ - (.+)$", body)))
    return None


def judge_probe(reference, mutated):
    """Decide whether a mutation was caught, relative to the unmutated candidate.

    A failure only counts as catching the mutation when it is a failure the
    unmutated candidate did not already have: a passing procedure that now
    fails, or an already-failing procedure that gains failure identities it did
    not have before. Anything that cannot be told apart from the pre-existing
    failure is INCONCLUSIVE, never KILLED.
    """
    before = {r["procedure"]: r for r in reference}
    caught, unjudged = [], []
    for result in mutated:
        pid = result["procedure"]
        ref = before.get(pid)
        if result["status"] == "TIMEOUT":
            unjudged.append(f"{pid}: timed out under the mutation")
        elif ref is None:
            unjudged.append(f"{pid}: no unmutated result to compare against")
        elif ref["status"] == "PASS":
            if result["status"] == "FAIL":
                caught.append(f"{pid}: passed unmutated, fails under the mutation")
        elif ref["status"] == "TIMEOUT":
            unjudged.append(f"{pid}: timed out on the unmutated candidate")
        elif result["status"] == "PASS":
            continue
        elif ref.get("failure_ids") is None or result.get("failure_ids") is None:
            unjudged.append(
                f"{pid}: already failing unmutated and has no failure parser, "
                "so a failure under the mutation cannot be told apart"
            )
        elif not result["failure_ids"]:
            unjudged.append(f"{pid}: failure under the mutation named no test identities")
        else:
            new = sorted(set(result["failure_ids"]) - set(ref["failure_ids"]))
            if new:
                caught.append(f"{pid}: new failures {', '.join(new[:5])}")
    if caught:
        return "KILLED", caught
    if unjudged:
        return "INCONCLUSIVE", unjudged
    return "SURVIVED", ["no procedure gained a failure under the mutation"]


def negative_probe(sandbox, path, index, p, tests, writer, workdir, reference):
    proof = workdir / f"mutation-{index}"
    # Source mutation never touches authoritative case; only a disposable copy.
    shutil.copytree(path, proof, symlinks=True)
    # A copied Python .pyc can validate by timestamp+size against changed source
    # and suppress a legitimate mutant. Prevent this false green in probe copies.
    for cachedir in proof.rglob("__pycache__"):
        if cachedir.is_dir() and not cachedir.is_symlink():
            shutil.rmtree(cachedir)
    for pyc in proof.rglob("*.pyc"):
        if pyc.is_file() and not pyc.is_symlink():
            pyc.unlink()
    raw_target = proof / p["path"]
    target = raw_target.resolve()
    if (
        raw_target.is_symlink()
        or not target.is_relative_to(proof.resolve())
        or not target.is_file()
    ):
        raise SafetyError("mutation target escaped disposable copy or is not regular file")
    raw = target.read_text(encoding="utf-8")
    if raw.count(p["from"]) != 1:
        raise SafetyError("mutation target must match exactly once; no guessed replacement")
    target.write_text(raw.replace(p["from"], p["to"], 1), encoding="utf-8")
    results = tests_case(sandbox, proof, f"fault-probe-{index}", tests, writer)
    status, basis = judge_probe(reference, results)
    return {
        "index": index,
        "path": p["path"],
        "name": p.get("name", f"probe-{index}"),
        "from_sha256": sha(p["from"].encode()),
        "to_sha256": sha(p["to"].encode()),
        "status": status,
        "basis": basis,
        "test_evidence_ids": [x["evidence_id"] for x in results],
    }


def verdict_for(execution, findings, m):
    if any(f["classification"] == "ENVIRONMENT" for f in findings):
        return "BLOCKED"
    if any(
        f["severity"] in ("CRITICAL", "HIGH")
        and f["classification"]
        in {
            "INTEGRATION_ONLY",
            "PR_DEFECT",
            "REGRESSION",
            "FALSE_GREEN",
            "MERGE_CONFLICT",
            "ORDER_SENSITIVITY",
        }
        for f in findings
    ):
        return "NOT_INTEGRATION_READY"
    if (
        execution.get("docker_executed") is not True
        or execution.get("combined_tests_pass") is not True
    ):
        return "INCOMPLETE_EVIDENCE"
    if not execution.get("negative_probe_killed") or not execution.get("source_review_verified"):
        return "INCOMPLETE_EVIDENCE"
    if not execution.get("required_contracts_verified"):
        return "INCOMPLETE_EVIDENCE"
    if any(f["classification"] in {"UNVERIFIED", "AUTHORITY"} for f in findings):
        return "INCOMPLETE_EVIDENCE"
    return "INTEGRATION_READY"


def write_bundle(out, m, manifest, writer, execution):
    state = verdict_for(execution, writer.findings, m)
    summary = {
        "schema": "l9.integration.verdict/v1",
        "state": state,
        "revision_bound": True,
        "readiness_scope": "disposable Git/Docker integration only; not production readiness or merge authorization",
        "blocking_findings": [
            f["id"] for f in writer.findings if f["severity"] in ("CRITICAL", "HIGH")
        ],
        "unverified": [
            f["reason"]
            for f in writer.findings
            if f["classification"] in {"UNVERIFIED", "AUTHORITY", "ENVIRONMENT"}
        ],
        "execution": execution,
        "generated_at": now(),
    }
    docs = {
        "integration_manifest.json": manifest,
        "integration_findings.json": {
            "schema": "l9.integration.findings/v1",
            "findings": writer.findings,
        },
        "integration_evidence.json": {
            "schema": "l9.integration.evidence/v1",
            "records": writer.records,
        },
        "integration_verdict.json": summary,
    }
    for name, body in docs.items():
        (out / name).write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def run(m: dict, out: Path):
    """Real runtime, Docker required. No mocked or host-only runtime fallback."""
    if out.exists() and any(out.iterdir()):
        raise SafetyError(f"output must be empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    writer = EvidenceWriter(out)
    stamp = now()
    run_id = uuid.uuid4().hex[:10]
    manifest = {
        "schema": "l9.integration.manifest/v1",
        "repository": m.get("repository", {}),
        "prs": m.get("prs", []),
        "integration_order": m.get("integration_order", []),
        "order_basis": m.get("order_basis", "UNKNOWN"),
        "docker_image": m.get("image", "UNKNOWN"),
        "network": "none",
        # Sidecars share a loopback-only namespace with the tests; "network"
        # stays none because nothing in the run has a route out.
        "services": [
            {"name": x.get("name"), "image": x.get("image")} for x in m.get("services") or []
        ],
        "service_source": m.get("service_source"),
        "test_env_keys": sorted(m.get("test_env") or {}),
        "test_env_omitted": m.get("test_env_omitted", []),
        "service_warnings": m.get("service_warnings", []),
        "run_id": run_id,
        "started_at": stamp,
        "states": [],
        "cleanup": "NOT_STARTED",
        "execution_mode": "DOCKER_ONLY",
    }
    execution = {
        "docker_executed": False,
        "combined_tests_pass": False,
        "negative_probe_killed": False,
        "source_review_verified": False,
        "required_contracts_verified": False,
    }
    work_path = None
    try:
        validate_plan(m)
        sandbox = DockerSandbox(
            m["image"], run_id, services=m.get("services") or [], test_env=m.get("test_env")
        )
        manifest["docker_provenance"] = sandbox.preflight()
        with tempfile.TemporaryDirectory(prefix="l9-pr-integration-") as tmp:
            work = Path(tmp)
            work_path = work
            try:
                store = local_bind_git_objects(m, work)
                verify_commands(m, store)
                per_pr, overlap = detect_overlap(store, m)
                deps = dependency_order(store, m)
                manifest["adapters_detected"] = adapter_census(store, m)
                manifest["dependencies"] = deps
                manifest["changed_files_by_pr"] = per_pr
                manifest["overlaps"] = overlap
                for x in overlap:
                    writer.record(x["path"], "OVERLAP_CANDIDATE", "REVIEW_REQUIRED", x)
                for sig in inspect_weak_tests(
                    store, {p["number"]: p["head_sha"] for p in m["prs"]}, per_pr
                ):
                    writer.record(sig["path"], "TEST_QUALITY_SIGNAL", "REVIEW_REQUIRED", sig)
                # Source review runs after the candidate has an actual combined SHA.
                # Never trust a pre-execution PASS claim against an unseen synthetic merge.
                eid = writer.record(
                    "source audit",
                    "UNCERTAINTY",
                    "UNVERIFIED",
                    {
                        "reason": "independent source review must be bound after combined revision exists"
                    },
                )
                writer.finding(
                    "UNVERIFIED",
                    "MEDIUM",
                    "Independent exact-revision adversarial source review not yet attached",
                    [eid],
                )
                eid = writer.record(
                    "authority",
                    "UNCERTAINTY",
                    "UNVERIFIED",
                    {
                        "reason": "independent contract closure must be verified against combined candidate"
                    },
                )
                writer.finding(
                    "UNVERIFIED",
                    "MEDIUM",
                    "Applicable domain obligation closure not yet reviewed",
                    [eid],
                )
                ordered = [
                    next(p for p in m["prs"] if p["number"] == pid)
                    for pid in m["integration_order"]
                ]
                phases = (
                    [("baseline", [])]
                    + [(f"pr-{p['number']}", [p]) for p in ordered]
                    + [("combined", ordered)]
                )
                statuses = {}
                combined_path = None
                combined_tests = []
                for name, heads in phases:
                    case, merges, rev = prepare_case(
                        store, name, work, sandbox, writer, m["repository"]["base_sha"], heads
                    )
                    row = {"name": name, "merges": merges, "revision": rev}
                    if rev is None:
                        statuses[name] = "CONFLICT"
                        eid = merges[-1]["evidence_id"]
                        writer.finding(
                            "MERGE_CONFLICT",
                            "HIGH",
                            f"Textual merge conflict in {name}",
                            [eid],
                            scope=name,
                            action="Resolve conflict by updating authoritative PR; rerun exact-bound simulation",
                        )
                    else:
                        tests = tests_case(sandbox, case, name, m["test_procedures"], writer)
                        row["tests"] = tests
                        statuses[name] = (
                            "PASS" if all(t["status"] == "PASS" for t in tests) else "FAIL"
                        )
                        if name == "combined":
                            combined_path = case
                            combined_tests = tests
                        execution["docker_executed"] = True
                    manifest["states"].append(row)
                if combined_path:
                    diff = git(
                        [
                            "-C",
                            str(combined_path),
                            "diff",
                            "--no-ext-diff",
                            "--binary",
                            m["repository"]["base_sha"] + "..HEAD",
                        ],
                        timeout=150,
                    )
                    if len(diff.stdout.encode("utf-8", "replace")) > 2_000_000:
                        eid = writer.record(
                            "combined source",
                            "SOURCE_DIFF",
                            "TRUNCATED",
                            {
                                "reason": "diff exceeds 2MB evidence cap; inspect exact repository checkout for full review"
                            },
                            log=diff.stdout[:2_000_000],
                        )
                        writer.finding(
                            "UNVERIFIED",
                            "MEDIUM",
                            "Combined diff truncated; independent source review must inspect full checkout",
                            [eid],
                        )
                    else:
                        writer.record(
                            "combined source",
                            "SOURCE_DIFF",
                            "CAPTURED",
                            {
                                "baseline": m["repository"]["base_sha"],
                                "integrated": next(
                                    (
                                        c["revision"]["sha"]
                                        for c in manifest["states"]
                                        if c["name"] == "combined" and c.get("revision")
                                    ),
                                    None,
                                ),
                            },
                            log=diff.stdout,
                        )
                if statuses.get("combined") == "PASS":
                    execution["combined_tests_pass"] = True
                if statuses.get("baseline") == "PASS" and statuses.get("combined") == "FAIL":
                    individually = [statuses[f"pr-{p['number']}"] for p in ordered]
                    evs = [
                        t["evidence_id"]
                        for c in manifest["states"]
                        if c["name"] == "combined"
                        for t in c.get("tests", [])
                        if t["status"] != "PASS"
                    ]
                    label = (
                        "INTEGRATION_ONLY"
                        if len(ordered) > 1 and all(s == "PASS" for s in individually)
                        else "REGRESSION"
                    )
                    writer.finding(
                        label,
                        "HIGH",
                        "Combined candidate introduced failure relative to passing baseline",
                        evs,
                        root_cause="UNKNOWN",
                        action="Trace failing test through combined producer-consumer paths; add regression witness",
                    )
                elif statuses.get("baseline") == "FAIL" and statuses.get("combined") == "FAIL":
                    base_tests = next(
                        (c.get("tests", []) for c in manifest["states"] if c["name"] == "baseline"),
                        [],
                    )
                    merged_tests = next(
                        (c.get("tests", []) for c in manifest["states"] if c["name"] == "combined"),
                        [],
                    )
                    if (
                        base_tests
                        and len(base_tests) == len(merged_tests)
                        and all(
                            a["failure_ids"] is not None
                            and b["failure_ids"] is not None
                            and (a["status"] == "PASS" or a["failure_ids"])
                            and (b["status"] == "PASS" or b["failure_ids"])
                            for a, b in zip(base_tests, merged_tests)
                        )
                    ):
                        introduced = sorted(
                            {
                                x
                                for a, b in zip(base_tests, merged_tests)
                                for x in set(b["failure_ids"]) - set(a["failure_ids"])
                            }
                        )
                        eid = writer.record(
                            "baseline differential",
                            "FAILURE_IDENTITIES",
                            "OBSERVED",
                            {
                                "introduced_ids": introduced,
                                "baseline_ids": [t["failure_ids"] for t in base_tests],
                                "combined_ids": [t["failure_ids"] for t in merged_tests],
                            },
                        )
                        if introduced:
                            writer.finding(
                                "REGRESSION",
                                "HIGH",
                                "New test failure identity appeared against red baseline: "
                                + ", ".join(introduced),
                                [eid],
                                action="Repair introduced regression without hiding pre-existing baseline failures",
                            )
                        else:
                            writer.finding(
                                "UNVERIFIED",
                                "MEDIUM",
                                "Pre-existing baseline failures remain; required disposition and passing witness are absent",
                                [eid],
                                action="Disposition existing failures and reverify integration obligations",
                            )
                    else:
                        eid = writer.record(
                            "baseline differential",
                            "UNCERTAINTY",
                            "UNKNOWN",
                            {
                                "reason": "baseline and combined failing; missing verified failure identity comparison"
                            },
                        )
                        writer.finding(
                            "UNVERIFIED",
                            "HIGH",
                            "Baseline-failing and combined-failing test attribution unresolved",
                            [eid],
                            action="Compare verified failure identities",
                        )
                elif statuses.get("combined") == "FAIL":
                    eid = writer.record(
                        "combined",
                        "UNCERTAINTY",
                        "UNKNOWN",
                        {"reason": "not attributable without clean baseline and individual tests"},
                    )
                    writer.finding(
                        "UNVERIFIED",
                        "HIGH",
                        "Combined failure could not be assigned to a proven cause",
                        [eid],
                    )
                if len(ordered) == 2 and not deps:
                    alt_path, alt_merges, alt_rev = prepare_case(
                        store,
                        "order-reversed",
                        work,
                        sandbox,
                        writer,
                        m["repository"]["base_sha"],
                        list(reversed(ordered)),
                    )
                    alt_record = {
                        "name": "order-reversed",
                        "merges": alt_merges,
                        "revision": alt_rev,
                    }
                    if alt_rev is None:
                        eid = alt_merges[-1]["evidence_id"]
                        writer.finding(
                            "ORDER_SENSITIVITY",
                            "HIGH",
                            "Reverse integration order produces a Git conflict",
                            [eid],
                            scope="order-reversed",
                        )
                    else:
                        alt_tests = tests_case(
                            sandbox, alt_path, "order-reversed", m["test_procedures"], writer
                        )
                        alt_record["tests"] = alt_tests
                        if (
                            any(t["status"] != "PASS" for t in alt_tests)
                            and statuses.get("combined") == "PASS"
                        ):
                            writer.finding(
                                "ORDER_SENSITIVITY",
                                "HIGH",
                                "Reverse integration order fails while forward integration passes",
                                [t["evidence_id"] for t in alt_tests if t["status"] != "PASS"],
                            )
                        argv, tree_b = docker_git(sandbox, alt_path, ["rev-parse", "HEAD^{tree}"])
                        writer.log_command("order-reversed", "TREE", argv, tree_b)
                        argv, tree_a = (
                            docker_git(sandbox, combined_path, ["rev-parse", "HEAD^{tree}"])
                            if combined_path
                            else (None, None)
                        )
                        if tree_a:
                            writer.log_command("combined", "TREE", argv, tree_a)
                        if (
                            tree_a
                            and tree_a["returncode"] == 0
                            and tree_b["returncode"] == 0
                            and tree_a["stdout"].strip() != tree_b["stdout"].strip()
                        ):
                            eid = writer.record(
                                "ordering",
                                "TREE_COMPARISON",
                                "DIFFERENT",
                                {
                                    "forward_tree": tree_a["stdout"].strip(),
                                    "reverse_tree": tree_b["stdout"].strip(),
                                },
                            )
                            writer.finding(
                                "ORDER_SENSITIVITY",
                                "HIGH",
                                "Reverse integration produces different source tree",
                                [eid],
                                action="Resolve justified integration sequence and add order-specific proof",
                            )
                    manifest["states"].append(alt_record)
                probe_results = []
                requested = m.get("negative_probes", [])
                if requested and not combined_path:
                    eid = writer.record(
                        "negative probes",
                        "PROBE_SKIPPED",
                        "NOT_RUN",
                        {"reason": "no combined candidate to mutate", "requested": len(requested)},
                    )
                    writer.finding(
                        "UNVERIFIED",
                        "MEDIUM",
                        "Mutation probes not run: the combined candidate did not merge",
                        [eid],
                        action="Resolve the merge conflict, then rerun the probes",
                    )
                if combined_path:
                    for i, probe in enumerate(requested, 1):
                        result = negative_probe(
                            sandbox,
                            combined_path,
                            i,
                            probe,
                            m["test_procedures"],
                            writer,
                            work,
                            combined_tests,
                        )
                        probe_results.append(result)
                        if result["status"] == "SURVIVED":
                            writer.finding(
                                "FALSE_GREEN",
                                "HIGH",
                                f"Known negative case {result['name']} survived tests",
                                result["test_evidence_ids"],
                                root_cause="CONFIRMED_FOR_PROBE",
                                action="Strengthen assertions against verified expected behavior; kill mutant",
                            )
                        if result["status"] == "INCONCLUSIVE":
                            writer.finding(
                                "UNVERIFIED",
                                "MEDIUM",
                                f"Mutation probe {result['name']} inconclusive: "
                                + "; ".join(result["basis"]),
                                result["test_evidence_ids"],
                                action="Declare a failure_parser for the procedure, or fix the "
                                "pre-existing failure, so the probe can be judged",
                            )
                manifest["negative_probes"] = probe_results
                execution["negative_probe_killed"] = bool(probe_results) and all(
                    p["status"] == "KILLED" for p in probe_results
                )
            finally:
                pass
    except (SafetyError, OSError, subprocess.TimeoutExpired) as exc:
        reason = str(exc)
        kind = blocker_kind(reason)
        eid = writer.record("execution blocker", "BLOCKER", "BLOCKED", {"error": reason})
        writer.finding(
            kind,
            "HIGH",
            reason,
            [eid],
            action="Resolve exact missing environment/binding/authority before executing",
        )
    manifest["completed_at"] = now()
    manifest["cleanup"] = (
        "NO_DISPOSABLE_WORKSPACE_CREATED"
        if work_path is None
        else "REMOVED"
        if not work_path.exists()
        else "RESIDUAL_WORKSPACE_BLOCKER"
    )
    if manifest["cleanup"] == "RESIDUAL_WORKSPACE_BLOCKER":
        eid = writer.record(
            "cleanup",
            "BLOCKER",
            "BLOCKED",
            {"reason": "disposable workspace remains; operator cleanup required"},
        )
        writer.finding("ENVIRONMENT", "HIGH", "Unremoved disposable workspace", [eid])
    verdict = write_bundle(out, m, manifest, writer, execution)
    from validate_evidence import seal_bundle

    seal_bundle(out)
    return verdict


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    try:
        plan = json.loads(args.manifest.read_text(encoding="utf-8"))
        verdict = run(plan, args.out)
    except (ValueError, OSError, SafetyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"state": verdict["state"], "output": str(args.out)}, sort_keys=True))
    return 0 if verdict["state"] == "INTEGRATION_READY" else 1


if __name__ == "__main__":
    sys.exit(main())
