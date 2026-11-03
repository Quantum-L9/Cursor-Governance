#!/usr/bin/env python3
"""Governance-owned disposable Docker sandbox for hosted Claude Code sessions.

One owner for the environment that disposable-container skills (first among them
``skills/l9-pr-integration-testing``) need, so no skill carries its own Docker
setup:

* a running Docker daemon (started here when the session is root and has none);
* a non-root runner user in the ``docker`` group — the integration runner
  refuses to execute as UID 0;
* the session's TLS trust bundle, readable by that user, for host-side fetches;
* a toolchain image built from Quantum-L9/l9-ci-core's single version source,
  ``.github/actions/install-consumer-ci/toolchain-lock.json``, read at an exact
  Core commit. Python packages install from Core's own pin files, never from
  versions restated here, and the image is tagged with the Core SHA so a Core
  pin bump produces a new image instead of silently reusing the old one.

``ensure`` is idempotent and single-flight; on a warm sandbox it only re-resolves
the Core SHA and probes the daemon. ``status`` reads the receipt and probes
nothing remote. Neither ever pushes an image, publishes, or touches a remote.

Usage:
  python3 ops/scripts/docker_sandbox.py ensure [--core-ref main] [--with-semgrep] [--json]
  python3 ops/scripts/docker_sandbox.py status [--json]
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

CORE_REPO = "Quantum-L9/l9-ci-core"
LOCK_PATH = ".github/actions/install-consumer-ci/toolchain-lock.json"
REQUIREMENTS_PATH = ".github/actions/install-consumer-ci/requirements-consumer-ci.txt"
SEMGREP_LOCK_PATH = ".github/actions/install-semgrep/locks/semgrep-{version}.txt"

RECEIPT_SCHEMA = "l9.docker-sandbox.receipt/v1"
STATE_DIR = Path(
    os.environ.get("L9_DOCKER_SANDBOX_STATE", str(Path.home() / ".l9" / "docker-sandbox"))
)
RUNNER_USER = os.environ.get("L9_DOCKER_SANDBOX_USER", "l9sandbox")
IMAGE_REPOSITORY = "l9-ci-toolchain"

# Every lock key the image provides. Biome is excluded on purpose: it is not a
# Python distribution, and Core installs it from install-biome's own checksum
# lock. semgrep is opt-in (--with-semgrep): its hash-locked closure is large.
REQUIRED_LOCK_KEYS = ("python", "pip", "ruff", "mypy", "pytest", "pre-commit")
EXCLUDED_TOOLS = {
    "biome": "not a Python distribution; Core installs it from install-biome's checksum lock"
}

# Trust-bundle discovery order: the variables a hosted session exports for its
# TLS-intercepting proxy. Nothing is assumed about where the file lives.
CA_ENV_VARS = ("PIP_CERT", "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE")

EXACT_VERSION = re.compile(r"^\d+(?:\.\d+)+$")
PIN_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DAEMON_START_SECONDS = 45
# Pull-through mirrors tried after Docker Hub. Hosted sessions share outbound
# IPs, so anonymous Docker Hub pulls are rate-limited (HTTP 429) long before a
# single session pulls anything. mirror.gcr.io serves the official images under
# the same content digests, so a mirror changes where the bytes come from, never
# which bytes they are: the base is still pinned by digest. Comma-separated;
# set L9_DOCKER_SANDBOX_MIRRORS="" to use Docker Hub only.
DEFAULT_MIRRORS = "mirror.gcr.io"


class SandboxError(RuntimeError):
    """The sandbox cannot be made ready; the message names what is missing."""


def now() -> str:
    return datetime.now(UTC).isoformat()


# --- Core lock: pure parsing and rendering (unit-tested) ---------------------


def parse_lock(text: str) -> dict[str, str]:
    try:
        lock = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SandboxError(f"Core toolchain lock is not JSON: {exc}") from exc
    if not isinstance(lock, dict):
        raise SandboxError("Core toolchain lock must be a JSON object")
    missing = [key for key in REQUIRED_LOCK_KEYS if key not in lock]
    if missing:
        raise SandboxError(f"Core toolchain lock lacks {', '.join(missing)}")
    for key, value in lock.items():
        if not isinstance(value, str) or not EXACT_VERSION.fullmatch(value):
            raise SandboxError(f"Core toolchain lock pins {key} to {value!r}, not an exact version")
    return lock


def parse_requirements(text: str, lock: dict[str, str]) -> list[str]:
    """Return Core's pin lines, refusing any that disagree with the lock."""
    pins = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = PIN_LINE.fullmatch(line)
        if not match:
            raise SandboxError(f"Core requirements line is not an exact pin: {line!r}")
        name, version = match.group(1).lower(), match.group(2)
        if name in lock and lock[name] != version:
            raise SandboxError(
                f"Core requirements pin {name}=={version} but the lock says {lock[name]}"
            )
        pins.append(line)
    if not pins:
        raise SandboxError("Core requirements file holds no pins")
    return pins


def image_tag(core_sha: str, with_semgrep: bool) -> str:
    if not HEX40.fullmatch(core_sha):
        raise SandboxError(f"Core SHA must be 40 lowercase hex characters, got {core_sha!r}")
    return f"{IMAGE_REPOSITORY}:core-{core_sha[:12]}" + ("-semgrep" if with_semgrep else "")


def render_dockerfile(
    base_image: str, lock: dict[str, str], *, with_semgrep: bool, with_ca: bool, core_sha: str
) -> str:
    """The toolchain image. Pin files and the CA are bind-mounted, never copied in."""
    if "@sha256:" not in base_image:
        raise SandboxError("base image must be pinned by digest")
    pip_cert = "PIP_CERT=/run/secrets/ca " if with_ca else ""
    ca_mount = "--mount=type=secret,id=ca " if with_ca else ""
    lines = [
        f"FROM {base_image}",
        "RUN apt-get update \\",
        " && apt-get install -y --no-install-recommends git make \\",
        " && rm -rf /var/lib/apt/lists/*",
        f"RUN {ca_mount}--mount=type=bind,source=requirements-consumer-ci.txt,"
        "target=/tmp/l9/requirements.txt \\",
        f"    {pip_cert}python -m pip install --no-cache-dir pip=={lock['pip']} \\",
        f" && {pip_cert}python -m pip install --no-cache-dir -r /tmp/l9/requirements.txt \\",
        f"    pre-commit=={lock['pre-commit']}",
    ]
    if with_semgrep:
        lines += [
            f"RUN {ca_mount}--mount=type=bind,source=semgrep.txt,target=/tmp/l9/semgrep.txt \\",
            "    python -m venv /opt/semgrep \\",
            f" && {pip_cert}/opt/semgrep/bin/pip install --no-cache-dir \\",
            "    --only-binary :all: --require-hashes -r /tmp/l9/semgrep.txt \\",
            " && ln -s /opt/semgrep/bin/semgrep /usr/local/bin/semgrep",
        ]
    lines.append(
        f'LABEL org.l9.core-repo="{CORE_REPO}" org.l9.core-sha="{core_sha}" '
        f'org.l9.base-image="{base_image}"'
    )
    return "\n".join(lines) + "\n"


# Run inside the image with no network: report what is actually installed.
PROBE = r"""
import importlib.metadata as m, json, subprocess, sys
names = ["pip", "ruff", "mypy", "pytest", "pre-commit"]
out = {"python": sys.version.split()[0]}
for n in names:
    try:
        out[n] = m.version(n)
    except m.PackageNotFoundError:
        out[n] = None
out["git"] = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
try:
    semgrep = subprocess.run(["semgrep", "--version"], capture_output=True, text=True)
    out["semgrep"] = semgrep.stdout.strip() or None
except FileNotFoundError:
    out["semgrep"] = None
print(json.dumps(out))
"""


def verify_versions(
    observed: dict[str, str | None], lock: dict[str, str], *, with_semgrep: bool
) -> list[str]:
    """Every provided tool must report exactly the Core-locked version."""
    expected = {key: lock[key] for key in REQUIRED_LOCK_KEYS}
    if with_semgrep:
        expected["semgrep"] = lock.get("semgrep", "")
    return [
        f"{tool}: image has {observed.get(tool)!r}, Core lock pins {version!r}"
        for tool, version in expected.items()
        if observed.get(tool) != version
    ]


# --- Host side ---------------------------------------------------------------


def run(
    args: list[str], *, timeout: int = 120, check: bool = True, **kwargs
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout, **kwargs)
    if check and proc.returncode:
        raise SandboxError(
            f"{' '.join(args[:3])} failed ({proc.returncode}): "
            f"{(proc.stderr or proc.stdout)[-600:]}"
        )
    return proc


def gh_api(path: str) -> dict:
    if shutil.which("gh") is None:
        raise SandboxError("gh CLI is required to read the Core toolchain lock")
    return json.loads(run(["gh", "api", path], timeout=60).stdout)


# Some session gateways scope REST to the session's own repositories and answer
# HTTP 403 for Core, while still serving git for it. Git reads the same commit's
# bytes, so it is a transport swap, not another source (the pattern
# ops/scripts/org_dotgithub.py uses for <owner>/.github). Both failing is an error.
CORE_GIT_URL = f"https://github.com/{CORE_REPO}"
_REST_FAILURES = (SandboxError, KeyError, TypeError, json.JSONDecodeError)


def _git(*args: str) -> str:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return run(["git", *args], timeout=120, env=env).stdout


def core_commit(core_ref: str) -> str:
    """Exact Core commit for ``core_ref``: REST, then ``git ls-remote``."""
    try:
        sha = gh_api(f"repos/{CORE_REPO}/commits/{core_ref}")["sha"]
    except _REST_FAILURES as rest_error:
        if HEX40.fullmatch(core_ref):
            return core_ref
        wanted = {core_ref, f"refs/heads/{core_ref}", f"refs/tags/{core_ref}"}
        try:
            listing = _git("ls-remote", CORE_GIT_URL)
        except SandboxError as git_error:
            msg = f"{rest_error}; git transport also failed: {git_error}"
            raise SandboxError(msg) from git_error
        rows = [line.split("\t") for line in listing.splitlines()]
        sha = next((row[0] for row in rows if len(row) == 2 and row[1] in wanted), "")
        if not sha:
            msg = f"{rest_error}; git transport: {core_ref} is not a ref of {CORE_GIT_URL}"
            raise SandboxError(msg) from rest_error
    if not isinstance(sha, str) or not HEX40.fullmatch(sha):
        raise SandboxError(f"{CORE_REPO}@{core_ref} did not resolve to a commit")
    return sha


def core_file(core_sha: str, path: str) -> str:
    """``path`` at the exact Core commit: REST contents, then a shallow git fetch."""
    try:
        body = gh_api(f"repos/{CORE_REPO}/contents/{path}?ref={core_sha}")
        return base64.b64decode(body["content"]).decode()
    except _REST_FAILURES as rest_error:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                _git("init", "--bare", "-q", tmp)
                _git("-C", tmp, "fetch", "-q", "--depth=1", CORE_GIT_URL, core_sha)
                return _git("-C", tmp, "show", f"{core_sha}:{path}")
        except SandboxError as git_error:
            msg = f"{rest_error}; git transport also failed: {git_error}"
            raise SandboxError(msg) from git_error


def daemon_up() -> bool:
    if shutil.which("docker") is None:
        return False
    return (
        run(
            ["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20, check=False
        ).returncode
        == 0
    )


def registry_mirrors() -> list[str]:
    raw = os.environ.get("L9_DOCKER_SANDBOX_MIRRORS", DEFAULT_MIRRORS)
    return [host.strip() for host in raw.split(",") if host.strip()]


def dockerd_argv(mirrors: list[str]) -> list[str]:
    """dockerd as this module starts it: Docker Hub pulls fall through to the mirrors."""
    return ["dockerd", *(f"--registry-mirror=https://{host}" for host in mirrors)]


def image_refs(image: str, mirrors: list[str]) -> list[str]:
    """Where a Docker Hub image may be pulled from, in order of preference.

    Only Docker Hub names fall through to a mirror: an image already naming a
    registry host (``ghcr.io/...``) is pulled from that host alone.
    """
    first = image.split("/", 1)[0]
    if "/" in image and ("." in first or ":" in first or first == "localhost"):
        return [image]
    path = image if "/" in image else f"library/{image}"
    return [image, *(f"{host}/{path}" for host in mirrors)]


def base_refs(python_version: str, mirrors: list[str]) -> list[str]:
    """Where the official python base may be pulled from, in order of preference."""
    return image_refs(f"python:{python_version}-slim", mirrors)


def digest_for(ref: str, digests: list[str]) -> str | None:
    """The RepoDigest belonging to ``ref``'s repository, else the first one."""
    repository = ref.rsplit(":", 1)[0]
    for digest in digests:
        if digest.split("@", 1)[0] == repository:
            return digest
    return digests[0] if digests else None


def start_daemon() -> None:
    if daemon_up():
        return
    if shutil.which("docker") is None or shutil.which("dockerd") is None:
        raise SandboxError("Docker is not installed (need both the docker CLI and dockerd)")
    if os.geteuid() != 0:
        raise SandboxError("no Docker daemon is running and this user cannot start one")
    log = (STATE_DIR / "dockerd.log").open("ab")
    subprocess.Popen(
        dockerd_argv(registry_mirrors()),
        stdout=log,
        stderr=log,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.monotonic() + DAEMON_START_SECONDS
    while time.monotonic() < deadline:
        if daemon_up():
            return
        time.sleep(1)
    raise SandboxError(
        f"dockerd did not become ready within {DAEMON_START_SECONDS}s; "
        f"see {STATE_DIR / 'dockerd.log'}"
    )


def ensure_runner() -> dict:
    """The non-root identity disposable containers run as."""
    if os.geteuid() != 0:
        me = pwd.getpwuid(os.geteuid())
        return {"user": me.pw_name, "uid": me.pw_uid, "gid": me.pw_gid, "home": me.pw_dir}
    try:
        entry = pwd.getpwnam(RUNNER_USER)
    except KeyError:
        run(["useradd", "--create-home", "--groups", "docker", RUNNER_USER])
        entry = pwd.getpwnam(RUNNER_USER)
    else:
        run(["usermod", "--append", "--groups", "docker", RUNNER_USER])
    return {"user": entry.pw_name, "uid": entry.pw_uid, "gid": entry.pw_gid, "home": entry.pw_dir}


def session_ca() -> Path | None:
    for name in CA_ENV_VARS:
        value = os.environ.get(name)
        if value and Path(value).is_file():
            return Path(value)
    return None


def stage_ca(ca: Path | None, runner: dict) -> str | None:
    """Copy the trust bundle where the runner can read it; the original may be root-only."""
    if ca is None:
        return None
    if os.geteuid() != 0:
        return str(ca)
    target = Path(runner["home"]) / ".l9-sandbox-ca.crt"
    shutil.copyfile(ca, target)
    os.chown(target, runner["uid"], runner["gid"])
    target.chmod(0o644)
    return str(target)


def local_digests(ref: str) -> list[str]:
    proc = run(
        ["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", ref],
        timeout=20,
        check=False,
    )
    return json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else []


def repository_of(ref: str) -> str:
    """``ref`` without its tag or digest; a registry ``host:port`` is kept."""
    head, _, last = ref.split("@", 1)[0].rpartition("/")
    last = last.split(":", 1)[0]
    return f"{head}/{last}" if head else last


def pin_image(image: str, digest: str | None = None) -> str:
    """``image`` pinned by registry digest, pulling it if no local copy exists.

    A local copy under any known name is used first: Docker Hub rate-limits
    even a HEAD on an already-present tag, so a warm run must not depend on a
    registry answering. Otherwise Docker Hub is pulled, then each mirror; the
    first that answers wins and every failure is reported if none does.

    With ``digest`` the tag is never resolved: each registry is asked for
    exactly that content, so a moved floating tag cannot change what runs.
    """
    if digest is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise SandboxError(f"pinned digest for {image} is not sha256:<64 hex>")
    refs = image_refs(image, registry_mirrors())
    if digest is not None:
        refs = [f"{repository_of(ref)}@{digest}" for ref in refs]
        for ref in refs:
            if local_digests(ref):
                return ref
    else:
        for ref in refs:
            found = digest_for(ref, local_digests(ref))
            if found:
                return found
    failures = []
    for ref in refs:
        proc = run(["docker", "pull", "--quiet", ref], timeout=600, check=False)
        if proc.returncode == 0:
            if digest is not None:
                return ref
            found = digest_for(ref, local_digests(ref))
            if found:
                return found
            failures.append(f"{ref}: pulled but has no registry digest to pin")
            continue
        failures.append(f"{ref}: {(proc.stderr or proc.stdout).strip()[-200:]}")
    raise SandboxError(f"cannot pull {image}: " + "; ".join(failures))


def pinned_base(python_version: str) -> str:
    """The official python base, pinned by registry digest (see pin_image)."""
    return pin_image(f"python:{python_version}-slim")


def image_id(ref: str) -> str | None:
    proc = run(["docker", "image", "inspect", "--format", "{{.Id}}", ref], timeout=20, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def build_image(
    tag: str,
    core_sha: str,
    lock: dict[str, str],
    requirements: str,
    *,
    with_semgrep: bool,
    ca: Path | None,
) -> str:
    base = pinned_base(lock["python"])
    with tempfile.TemporaryDirectory(prefix="l9-sandbox-build-") as context:
        ctx = Path(context)
        (ctx / "requirements-consumer-ci.txt").write_text(requirements)
        if with_semgrep:
            if "semgrep" not in lock:
                raise SandboxError("--with-semgrep requested but the Core lock pins no semgrep")
            (ctx / "semgrep.txt").write_text(
                core_file(core_sha, SEMGREP_LOCK_PATH.format(version=lock["semgrep"]))
            )
        (ctx / "Dockerfile").write_text(
            render_dockerfile(
                base, lock, with_semgrep=with_semgrep, with_ca=ca is not None, core_sha=core_sha
            )
        )
        args = ["docker", "build", "--quiet", "--tag", tag]
        if ca is not None:
            args += ["--secret", f"id=ca,src={ca}"]
        run([*args, str(ctx)], timeout=1800)
    built = image_id(tag)
    if not built:
        raise SandboxError(f"docker build reported success but {tag} is absent")
    return built


def probe_versions(image: str) -> dict:
    proc = run(
        [
            "docker",
            "run",
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--entrypoint",
            "python",
            image,
            "-c",
            PROBE,
        ],
        timeout=120,
    )
    return json.loads(proc.stdout)


def receipt_path(with_semgrep: bool) -> Path:
    """One receipt per image variant, so a failed variant never clobbers a ready one."""
    return STATE_DIR / ("receipt-semgrep.json" if with_semgrep else "receipt.json")


def write_receipt(receipt: dict, with_semgrep: bool) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    target = receipt_path(with_semgrep)
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    tmp.replace(target)


def read_receipt(with_semgrep: bool) -> dict | None:
    try:
        return json.loads(receipt_path(with_semgrep).read_text())
    except (OSError, json.JSONDecodeError):
        return None


def ensure(core_ref: str, with_semgrep: bool) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / "lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "started_at": now(),
            "core_repo": CORE_REPO,
            "core_ref": core_ref,
        }
        try:
            core_sha = core_commit(core_ref)
            lock_text = core_file(core_sha, LOCK_PATH)
            lock = parse_lock(lock_text)
            requirements = core_file(core_sha, REQUIREMENTS_PATH)
            parse_requirements(requirements, lock)
            start_daemon()
            runner = ensure_runner()
            ca = session_ca()
            tag = image_tag(core_sha, with_semgrep)
            built = image_id(tag) or build_image(
                tag, core_sha, lock, requirements, with_semgrep=with_semgrep, ca=ca
            )
            observed = probe_versions(built)
            mismatches = verify_versions(observed, lock, with_semgrep=with_semgrep)
            if mismatches:
                raise SandboxError("image does not match the Core lock: " + "; ".join(mismatches))
            receipt.update(
                status="READY",
                core_sha=core_sha,
                toolchain_lock=lock,
                toolchain_lock_sha256=hashlib.sha256(lock_text.encode()).hexdigest(),
                image_tag=tag,
                image_id=built,
                base_image=run(
                    [
                        "docker",
                        "image",
                        "inspect",
                        "--format",
                        '{{index .Config.Labels "org.l9.base-image"}}',
                        built,
                    ]
                ).stdout.strip(),
                with_semgrep=with_semgrep,
                excluded_tools=EXCLUDED_TOOLS,
                observed_versions=observed,
                docker_server=run(
                    ["docker", "info", "--format", "{{.ServerVersion}}"]
                ).stdout.strip(),
                runner=runner,
                runner_ca_bundle=stage_ca(ca, runner),
            )
        except (
            SandboxError,
            OSError,
            subprocess.TimeoutExpired,
            KeyError,
            json.JSONDecodeError,
        ) as exc:
            receipt.update(status="FAILED", reason=str(exc))
        receipt["completed_at"] = now()
        write_receipt(receipt, with_semgrep)
        return receipt


def status(with_semgrep: bool = False) -> dict:
    receipt = read_receipt(with_semgrep)
    if receipt is None:
        return {
            "schema": RECEIPT_SCHEMA,
            "status": "ABSENT",
            "reason": f"no receipt at {receipt_path(with_semgrep)}",
        }
    if receipt.get("status") != "READY":
        return receipt
    if not daemon_up():
        return {**receipt, "status": "STALE", "reason": "Docker daemon is not running"}
    if image_id(receipt["image_tag"]) != receipt["image_id"]:
        return {
            **receipt,
            "status": "STALE",
            "reason": f"image {receipt['image_tag']} is missing or was rebuilt",
        }
    return receipt


def summarize(receipt: dict) -> str:
    if receipt.get("status") != "READY":
        return f"docker-sandbox: {receipt.get('status')} — {receipt.get('reason', 'unknown')}"
    lock = receipt["toolchain_lock"]
    tools = " ".join(f"{key}={lock[key]}" for key in REQUIRED_LOCK_KEYS)
    return (
        f"docker-sandbox: READY {receipt['image_tag']} (Core {receipt['core_sha'][:12]}; "
        f"{tools}; runner {receipt['runner']['user']})"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    ens = sub.add_parser("ensure", help="make the sandbox ready (idempotent, single-flight)")
    ens.add_argument(
        "--core-ref", default="main", help="Core ref whose toolchain lock the image follows"
    )
    ens.add_argument(
        "--with-semgrep", action="store_true", help="also install Core's hash-locked semgrep"
    )
    ens.add_argument("--json", action="store_true")
    st = sub.add_parser("status", help="report the receipt; probes the daemon and image only")
    st.add_argument("--with-semgrep", action="store_true", help="report the semgrep variant")
    st.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "ensure":
        receipt = ensure(args.core_ref, args.with_semgrep)
    else:
        receipt = status(args.with_semgrep)
    print(json.dumps(receipt, indent=2, sort_keys=True) if args.json else summarize(receipt))
    return 0 if receipt.get("status") == "READY" else 1


if __name__ == "__main__":
    sys.exit(main())
