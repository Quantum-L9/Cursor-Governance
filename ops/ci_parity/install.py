#!/usr/bin/env python3
"""Install the CI-parity tools pinned in tools.yaml (hosted Claude Code).

Idempotent and single-flight: an flock on <install_root>/.install.lock
serializes the setup script and the SessionStart self-heal, and a tool already
recorded in state.json at its pinned version is skipped. Release binaries are
sha256-verified before they are made executable; a mismatch refuses and leaves
any previous install untouched. PyPI tools go through `uv tool install
<pkg>==<version>` into a private tool dir. Prints literal per-tool status only.

A tool with `track: ci_ref` installs the revision its CI file names right now
(l9-ci: the SDK revision l9-ci-core org-ci.yml provisions), read through
validate_manifest's Core reader, and records `source: ci_ref` in state.json.
When the CI file is unreadable or no longer names exactly one revision, the
reviewed hand pin in tools.yaml installs instead and a WARN line says so.

    install.py                 install every missing tool
    install.py --tool codeql   install one
    install.py --check         report; exit 1 unless every tool is OK
    install.py --from-dir DIR  use already-downloaded release assets (sha-verified)
"""

from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import manifest  # noqa: E402
import validate_manifest  # noqa: E402
from run import extract_tar_inside  # noqa: E402

DOWNLOAD_TIMEOUT = 1800


class InstallError(RuntimeError):
    """A tool could not be installed at its pinned version."""


@contextmanager
def _locked(root: Path) -> Iterator[None]:
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".install.lock").open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path, from_dir: Path | None) -> None:
    if from_dir is not None:
        candidate = from_dir / url.rsplit("/", 1)[-1]
        if candidate.is_file():
            shutil.copyfile(candidate, dest)
            return
    subprocess.run(
        [
            "curl",
            "-fsSL",
            "--retry",
            "3",
            "--max-time",
            str(DOWNLOAD_TIMEOUT),
            "-o",
            str(dest),
            url,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def _probe_version(binary: Path, tool: manifest.Tool) -> bool:
    try:
        proc = subprocess.run(
            [str(binary), *tool.version_cmd], capture_output=True, text=True, timeout=120
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return tool.expect in (proc.stdout + proc.stderr)


def _install_release(tool: manifest.Tool, target: Path, from_dir: Path | None) -> Path:
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        asset = Path(tmp) / "asset"
        _download(tool.url, asset, from_dir)
        actual = sha256_of(asset)
        if actual != tool.sha256:
            raise InstallError(
                f"{tool.name}: sha256 mismatch (refusing; previous install untouched)"
            )
        staging = Path(tmp) / "staging"
        staging.mkdir()
        if tool.method == "release_binary":
            shutil.move(str(asset), staging / tool.binary)
        else:
            with tarfile.open(asset) as archive:
                extract_tar_inside(archive, staging)
        binary = staging / tool.binary
        if not binary.is_file():
            raise InstallError(f"{tool.name}: archive lacks {tool.binary}")
        binary.chmod(0o755)
        final = target / "dist"
        if final.exists():
            shutil.rmtree(final)
        shutil.move(str(staging), final)
    return final / tool.binary


def uv_tool_spec(tool: manifest.Tool) -> str:
    """`pkg==version` from PyPI, or `git+URL@commit` for a tool pinned to a revision."""
    if tool.package.startswith("git+"):
        return f"{tool.package}@{tool.version}"
    return f"{tool.package}=={tool.version}"


def _install_uv_tool(tool: manifest.Tool, target: Path) -> Path:
    uv = shutil.which("uv")
    if uv is None:
        raise InstallError(f"{tool.name}: uv not found")
    bin_dir = target / "bin"
    env = dict(os.environ)
    env["UV_TOOL_DIR"] = str(target.parent.parent / "uv-tools")
    env["UV_TOOL_BIN_DIR"] = str(bin_dir)
    proc = subprocess.run(
        [uv, "tool", "install", "--force", uv_tool_spec(tool)],
        env=env,
        capture_output=True,
        text=True,
        timeout=DOWNLOAD_TIMEOUT,
    )
    if proc.returncode != 0:
        raise InstallError(f"{tool.name}: uv tool install failed (exit {proc.returncode})")
    return bin_dir / tool.binary


def _link(bin_dir: Path, name: str, binary: Path) -> None:
    """Expose the tool on PATH without clobbering a file we do not own."""
    bin_dir.mkdir(parents=True, exist_ok=True)
    link = bin_dir / name
    if link.is_symlink() or not link.exists():
        if link.is_symlink():
            link.unlink()
        link.symlink_to(binary)


def resolve_tracked(tool: manifest.Tool) -> tuple[str, str, str]:
    """``(version, source, warning)``: CI's revision now, else the best known one.

    When the CI file cannot answer, the revision last recorded from CI (the
    overlaid ``version``) is kept; with none recorded, the reviewed hand pin
    installs. Either way a WARN names what happened.
    """
    if not tool.track:
        return tool.version, "pin", ""
    ref = tool.ci_ref
    where = f"{ref.get('repo')}@{ref.get('ref') or 'main'}:{ref.get('path')}"
    keep = tool.version
    keep_source = "ci_ref" if tool.pinned else "pin"
    keeping = (
        f"keeping {keep} last read from CI" if tool.pinned else f"installing the hand pin {keep}"
    )
    try:
        text = validate_manifest._remote_text(ref)
    except OSError as exc:
        return keep, keep_source, f"WARN: {tool.name}: {where} unreadable ({exc}); {keeping}"
    version = manifest.tracked_version(tool, text)
    if version is None:
        return (
            keep,
            keep_source,
            f"WARN: {tool.name}: {where} no longer names exactly one revision "
            f"matching ci_ref.extract; {keeping}",
        )
    return version, "ci_ref", ""


def _installed_at(loaded: manifest.Manifest, name: str, version: str) -> bool:
    entry = loaded.read_state().get(name) or {}
    path = Path(str(entry.get("path") or ""))
    return entry.get("version") == version and path.is_file() and os.access(path, os.X_OK)


def install_tool(
    loaded: manifest.Manifest,
    name: str,
    from_dir: Path | None = None,
    *,
    version: str = "",
    source: str = "pin",
) -> str:
    """Install ``name`` at ``version`` (default: its manifest version)."""
    tool = loaded.tools[name]
    if tool.method == "venv":
        return "OK" if loaded.resolve(name) else "MISSING"
    if version and version != tool.version:
        # Keep the reviewed hand pin visible as the fallback, whatever installs.
        tool = dataclasses.replace(tool, version=version, pinned=tool.fallback_version)
    if _installed_at(loaded, name, tool.version):
        return "OK"
    target = loaded.install_root / name / tool.version
    if tool.method == "uv_tool":
        binary = _install_uv_tool(tool, target)
    else:
        binary = _install_release(tool, target, from_dir)
    if not _probe_version(binary, tool):
        raise InstallError(f"{name}: installed binary does not report {tool.expect}")
    state = loaded.read_state()
    state[name] = {"version": tool.version, "path": str(binary)}
    if tool.track:
        state[name].update(source=source, pinned=tool.fallback_version)
    tmp = loaded.state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(loaded.state_path)
    _link(loaded.bin_dir, name, binary)
    return "INSTALLED"


def check(loaded: manifest.Manifest) -> dict[str, str]:
    return {name: ("OK" if loaded.resolve(name) else "MISSING") for name in loaded.tools}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--tool", action="append", default=[])
    parser.add_argument("--from-dir", type=Path)
    args = parser.parse_args(argv)
    loaded = manifest.load()
    if args.check:
        status = check(loaded)
        for name, verdict in status.items():
            print(f"ci-parity: tool={name} version={loaded.tools[name].version} status={verdict}")
        ok = sum(1 for v in status.values() if v == "OK")
        print(f"ci-parity: {ok}/{len(status)} OK")
        return 0 if ok == len(status) else 1
    names = args.tool or list(loaded.tools)
    unknown = [n for n in names if n not in loaded.tools]
    if unknown:
        print(f"ci-parity: unknown tool(s): {', '.join(sorted(unknown))}")
        return 2
    failed = 0
    with _locked(loaded.install_root):
        for name in names:
            version, source, warning = resolve_tracked(loaded.tools[name])
            if warning:
                print(f"ci-parity: {warning}")
            try:
                verdict = install_tool(loaded, name, args.from_dir, version=version, source=source)
            except (InstallError, OSError, subprocess.SubprocessError, tarfile.TarError) as exc:
                verdict, failed = f"FAILED ({type(exc).__name__}: {exc})", failed + 1
            tracked = " source=ci_ref" if source == "ci_ref" else ""
            print(f"ci-parity: tool={name} version={version}{tracked} {verdict}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
