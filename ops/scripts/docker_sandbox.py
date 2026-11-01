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


def core_file(core_sha: str, path: str) -> str:
    body = gh_api(f"repos/{CORE_REPO}/contents/{path}?ref={core_sha}")
    return base64.b64decode(body["content"]).decode()


def daemon_up() -> bool:
    if shutil.which("docker") is None:
        return False
    return (
        run(
            ["docker", "info", "--format", "{{.ServerVersion}}"], timeout=20, check=False
        ).returncode
        == 0
    )


def start_daemon() -> None:
    if daemon_up():
        return
    if shutil.which("docker") is None or shutil.which("dockerd") is None:
        raise SandboxError("Docker is not installed (need both the docker CLI and dockerd)")
    if os.geteuid() != 0:
        raise SandboxError("no Docker daemon is running and this user cannot start one")
    log = (STATE_DIR / "dockerd.log").open("ab")
    subprocess.Popen(
        ["dockerd"], stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True
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


def pinned_base(python_version: str) -> str:
    """The base image by registry digest; pull only when no local copy has one.

    Docker Hub rate-limits even a HEAD on an already-present tag, so a warm
    rebuild must not depend on the registry answering.
    """
    ref = f"python:{python_version}-slim"
    digests = local_digests(ref)
    if not digests:
        run(["docker", "pull", "--quiet", ref], timeout=600)
        digests = local_digests(ref)
    if not digests:
        raise SandboxError(f"{ref} has no registry digest to pin")
    return digests[0]


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
            core_sha = gh_api(f"repos/{CORE_REPO}/commits/{core_ref}")["sha"]
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
