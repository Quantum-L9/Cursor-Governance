#!/usr/bin/env python3
"""Pre-commit preflight: @quantum-l9 dependencies must be published and lock-true.

Catches the PR #53 failure class at author time instead of merge time: a
dependency version that was never published to GitHub Packages, or a
package-lock entry whose `resolved` URL / `integrity` were hand-written
(best-effort) rather than taken from registry metadata.

Offline-first: shape checks always run. A live registry-metadata check runs
when the secrets resolver is available; if the resolver or network fails the
live check degrades to a warning (fail-open) — shape violations still fail.

Not every `@quantum-l9/*` dependency comes from the registry. A repo may vendor
one in-tree and declare it `file:packages/<name>`, which npm records in the lock
as `{"resolved": "packages/<name>", "link": true}` with no tarball URL and no
integrity — by construction, not by omission. Judged as a registry install that
is eight findings in a repo with four such packages, none of them real. Those
deps are checked as LOCAL deps instead: the declaration, the lock entry and the
directory on disk must all agree, and its package.json must name the package it
claims to be. That is a verified exemption, not a skip — `file:packages/ghost`
pointing at nothing is still a finding, and so is a lock entry claiming a link
that the declaration does not.

Usage: python3 ops/scripts/validate_gh_package_deps.py [package.json] [package-lock.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

_OPS_LIB = Path(__file__).resolve().parent.parent / "lib"
if str(_OPS_LIB) not in sys.path:
    sys.path.insert(0, str(_OPS_LIB))

from safe_https import https_exchange  # noqa: E402

SCOPE = "@quantum-l9/"
TARBALL_RE = re.compile(r"/download/(@quantum-l9/[\w.-]+)/([\d.]+(?:-[^/]+)?)/[0-9a-f]{20,}$")

DEFAULT_PKG = "package.json"
DEFAULT_LOCK = "package-lock.json"


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def scoped_deps(package: dict[str, Any]) -> dict[str, str]:
    """{name: spec} for every @quantum-l9/* dependency across all dep kinds."""
    out: dict[str, str] = {}
    for kind in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        deps = package.get(kind) or {}
        if not isinstance(deps, dict):
            continue
        for name, spec in deps.items():
            if name.startswith(SCOPE):
                out[name] = str(spec)
    return out


def lock_entries(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    packages = lock.get("packages") or {}
    out: dict[str, dict[str, Any]] = {}
    if isinstance(packages, dict):
        for key, entry in packages.items():
            if (
                isinstance(key, str)
                and isinstance(entry, dict)
                and key.startswith("node_modules/@")
            ):
                out[key.removeprefix("node_modules/")] = entry
    return out


LOCAL_SPEC_PREFIXES = ("file:", "link:")


def local_spec_path(spec: str) -> str | None:
    """The path a `file:`/`link:` spec points at, or None when it is not one."""
    for prefix in LOCAL_SPEC_PREFIXES:
        if spec.startswith(prefix):
            return spec[len(prefix) :].strip()
    return None


def local_problems(name: str, spec_path: str, entry: dict[str, Any], root: Path) -> list[str]:
    """Verify a vendored local dependency instead of a registry one.

    Every condition here is something a registry install would have proven some
    other way: that the declaration and the lock agree on where the package
    lives, and that what lives there is the package being claimed.
    """
    problems: list[str] = []
    if entry.get("link") is not True:
        problems.append(
            f"{name}: declared as a local path ({spec_path!r}) but the lock entry is not a link"
        )
    resolved = str(entry.get("resolved") or "")
    if resolved.rstrip("/") != spec_path.rstrip("/"):
        problems.append(f"{name}: declared {spec_path!r} but the lock resolves it to {resolved!r}")
    target = (root / spec_path).resolve()
    manifest = target / "package.json"
    if not manifest.is_file():
        problems.append(f"{name}: local path {spec_path!r} has no package.json")
        return problems
    vendored = _load_json(manifest)
    if vendored is None:
        problems.append(f"{name}: local path {spec_path!r} has an unreadable package.json")
    elif vendored.get("name") != name:
        problems.append(
            f"{name}: local path {spec_path!r} contains {vendored.get('name')!r}, not {name!r}"
        )
    return problems


def shape_problems(name: str, entry: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if entry.get("link") is True:
        # The declaration says registry, the lock says local directory. Naming
        # the disagreement is more useful than reporting the two symptoms it
        # causes (no tarball URL, no integrity) as if they were separate facts.
        return [
            f"{name}: lock entry is a local link to {str(entry.get('resolved') or '')!r}, "
            "but package.json does not declare it with file:/link:"
        ]
    version = str(entry.get("version") or "")
    resolved = str(entry.get("resolved") or "")
    integrity = str(entry.get("integrity") or "")
    match = TARBALL_RE.search(resolved)
    if not match:
        problems.append(
            f"{name}: resolved URL is not a hash-suffixed GitHub Packages tarball: {resolved!r}"
        )
    else:
        resolved_name, resolved_version = match.group(1), match.group(2)
        if resolved_name != name:
            problems.append(f"{name}: resolved URL names {resolved_name!r}")
        if version and resolved_version != version:
            problems.append(
                f"{name}: resolved URL version {resolved_version!r} != lock version {version!r}"
            )
    if not integrity.startswith("sha512-"):
        problems.append(f"{name}: missing or non-sha512 integrity: {integrity!r}")
    return problems


def live_problems(name: str, version: str, integrity: str) -> list[str]:
    """Compare lock entry against live registry metadata; [] when unverifiable."""
    problems: list[str] = []
    try:
        request = urllib.request.Request(
            f"https://npm.pkg.github.com/@quantum-l9%2f{name.removeprefix(SCOPE)}",
            headers={"Accept": "application/vnd.npm.install-v1+json"},
        )
        with https_exchange(
            request,
            timeout=15,
            allowed_hosts=frozenset({"npm.pkg.github.com"}),
            label="GitHub Packages URL",
        ) as response:
            metadata = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 — offline / private-registry reachability
        print(f"validate_gh_package_deps: live check skipped for {name} ({exc})", file=sys.stderr)
        return problems
    versions = metadata.get("versions") or {}
    if version not in versions:
        problems.append(f"{name}@{version}: not published to GitHub Packages")
        return problems
    dist = (versions.get(version) or {}).get("dist") or {}
    live_integrity = str(dist.get("integrity") or "")
    if live_integrity and live_integrity != integrity:
        problems.append(
            f"{name}@{version}: lock integrity != registry integrity ({live_integrity[:24]}...)"
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package_json", nargs="?", default=DEFAULT_PKG)
    parser.add_argument("package_lock", nargs="?", default=DEFAULT_LOCK)
    parser.add_argument("--no-live-check", action="store_true")
    args = parser.parse_args()

    package = _load_json(Path(args.package_json))
    lock = _load_json(Path(args.package_lock))
    if package is None:
        print(
            f"validate_gh_package_deps: {args.package_json} unreadable; skipping", file=sys.stderr
        )
        return 0
    deps = scoped_deps(package)
    if not deps:
        return 0
    entries = lock_entries(lock or {})
    # Local specs are relative to the manifest that declares them, not to cwd.
    root = Path(args.package_json).resolve().parent

    problems: list[str] = []
    local = 0
    for name, spec in sorted(deps.items()):
        entry = entries.get(name)
        if not entry:
            problems.append(f"{name}: declared ({spec}) but missing from package-lock.json")
            continue
        spec_path = local_spec_path(spec)
        if spec_path is not None:
            local += 1
            problems.extend(local_problems(name, spec_path, entry, root))
            continue
        problems.extend(shape_problems(name, entry))
        if not args.no_live_check:
            problems.extend(
                live_problems(
                    name, str(entry.get("version") or ""), str(entry.get("integrity") or "")
                )
            )

    for problem in problems:
        print(f"validate_gh_package_deps: {problem}", file=sys.stderr)
    if problems:
        print(f"validate_gh_package_deps: {len(problems)} problem(s) found", file=sys.stderr)
        return 1
    summary = f"validate_gh_package_deps: {len(deps)} @quantum-l9 dep(s) verified"
    if local:
        summary += f" ({local} vendored locally, {len(deps) - local} from the registry)"
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
