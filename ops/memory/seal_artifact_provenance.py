"""Reinstall the bound memory wheel from the lockfile hashed URL via pip.

``uv sync`` and ``uv pip install <name>==<ver>`` write no PEP 610 archive
hash. ``uv pip install URL#sha256=…`` writes ``direct_url.json`` with an
empty ``archive_info``. pip's hashed-URL install writes
``archive_info.hashes.sha256``, which is the only installer-recorded form
the binder can prove in place.

This module does not invent a digest: it refuses unless ``uv.lock`` and
``release_evidence.artifact_sha256`` agree, then asks pip to record that
hash.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
from pathlib import Path

from ops.memory.runtime_binding import BindingManifest

_DIRECT_URL = "direct_url.json"


def _dist_info_name(version: str) -> str:
    return f"l9_graphite_memory-{version}.dist-info"


def _lock_wheel(lock_path: Path, distribution: str) -> tuple[str, str]:
    data = tomllib.loads(lock_path.read_text(encoding="utf-8"))
    for package in data.get("package") or []:
        if str(package.get("name") or "") != distribution:
            continue
        wheels = package.get("wheels") or []
        if not wheels:
            raise ValueError(f"{lock_path} has no wheel for {distribution}")
        wheel = wheels[0]
        url = str(wheel.get("url") or "").strip()
        raw = str(wheel.get("hash") or "").strip()
        digest = raw.split(":", 1)[-1] if raw.startswith("sha256:") else raw
        if not url or not digest:
            raise ValueError(f"{lock_path} wheel for {distribution} is missing url/hash")
        return url, digest
    raise ValueError(f"{lock_path} does not pin {distribution}")


def _installed_direct_url(site_packages: Path, version: str) -> dict[str, object] | None:
    path = site_packages / _dist_info_name(version) / _DIRECT_URL
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _prefix(interpreter: Path) -> Path:
    """The environment prefix the interpreter serves, not the resolved binary.

    ``.venv/bin/python`` is a symlink into uv's shared CPython. ``Path.resolve``
    follows it and would look for dist-info under the toolchain, not the venv.
    """

    completed = subprocess.run(  # noqa: S603
        [str(interpreter), "-c", "import sys; print(sys.prefix)"],
        check=False,
        capture_output=True,
        text=True,
    )
    prefix = (completed.stdout or "").strip()
    if completed.returncode != 0 or not prefix:
        raise RuntimeError(f"{interpreter} did not report sys.prefix")
    return Path(prefix)


def _site_packages(interpreter: Path) -> Path:
    prefix = _prefix(interpreter)
    matches = sorted(prefix.glob("lib/python*/site-packages"))
    if not matches:
        raise FileNotFoundError(f"no site-packages under {prefix}")
    return matches[-1]


def _hash_from_direct_url(direct_url: dict[str, object]) -> str | None:
    archive = direct_url.get("archive_info")
    if not isinstance(archive, dict):
        return None
    hashes = archive.get("hashes")
    if isinstance(hashes, dict):
        digest = str(hashes.get("sha256") or "").strip()
        if digest:
            return digest
    raw = str(archive.get("hash") or "").strip()
    if raw:
        return raw.split("=", 1)[-1].strip() or None
    return None


def already_sealed(interpreter: Path, expected_sha256: str, version: str) -> bool:
    direct = _installed_direct_url(_site_packages(interpreter), version)
    if not direct:
        return False
    return _hash_from_direct_url(direct) == expected_sha256


def _ensure_pip(python: Path) -> int:
    probe = subprocess.run(  # noqa: S603
        [str(python), "-m", "pip", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return 0
    bootstrap = subprocess.run(  # noqa: S603
        [str(python), "-m", "ensurepip", "--upgrade"],
        check=False,
        capture_output=True,
        text=True,
    )
    return bootstrap.returncode


def seal(
    *,
    root: Path,
    interpreter: Path | None = None,
    check_only: bool = False,
) -> int:
    root = root.expanduser().resolve()
    manifest = BindingManifest.load(root / "ops" / "config" / "memory-binding.json")
    expected = manifest.artifact_sha256
    if not expected:
        print("seal: manifest records no artifact_sha256", file=sys.stderr)
        return 2
    url, lock_digest = _lock_wheel(root / "uv.lock", manifest.distribution)
    if lock_digest != expected:
        print(
            f"seal: uv.lock digest {lock_digest} is not release_evidence.artifact_sha256 "
            f"{expected}",
            file=sys.stderr,
        )
        return 2
    python = interpreter or (root / ".venv" / "bin" / "python")
    if not python.is_file():
        print(f"seal: interpreter missing: {python}", file=sys.stderr)
        return 2
    if already_sealed(python, expected, manifest.expected_package_version):
        print(f"seal: already exact ({expected[:12]}…)", file=sys.stderr)
        return 0
    if check_only:
        print("seal: PEP 610 archive hash is missing", file=sys.stderr)
        return 1
    if _ensure_pip(python) != 0:
        print("seal: pip is not available in the locked interpreter", file=sys.stderr)
        return 1
    hashed = f"{url}#sha256={expected}"
    cmd = [
        str(python),
        "-m",
        "pip",
        "install",
        "--no-deps",
        "--force-reinstall",
        hashed,
    ]
    try:
        completed = subprocess.run(  # noqa: S603 - argv list, never a shell string
            cmd,
            cwd=str(root),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print(f"seal: pip install failed to start: {exc}", file=sys.stderr)
        return 1
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()[:400]
        print(f"seal: pip install failed: {err}", file=sys.stderr)
        return 1
    if not already_sealed(python, expected, manifest.expected_package_version):
        print("seal: install finished but PEP 610 hash is still missing", file=sys.stderr)
        return 1
    print(f"seal: recorded PEP 610 hash {expected[:12]}…", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seal memory-wheel PEP 610 provenance")
    parser.add_argument("--root", default=".", help="governance checkout (has uv.lock)")
    parser.add_argument("--interpreter", default=None)
    parser.add_argument("--check", action="store_true", help="do not install; exit 1 if unsealed")
    args = parser.parse_args(argv)
    return seal(
        root=Path(args.root),
        interpreter=Path(args.interpreter) if args.interpreter else None,
        check_only=args.check,
    )


if __name__ == "__main__":
    raise SystemExit(main())
