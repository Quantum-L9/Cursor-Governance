"""`gh-package-deps-preflight` must judge a vendored dep as a local dep.

The hook exists to catch the PR #53 class: a `@quantum-l9/*` version that was
never published, or a lock entry whose `resolved`/`integrity` were hand-written.
Every one of those checks assumes a REGISTRY install.

A repo may instead vendor the package in-tree and declare it
`file:packages/<name>`. npm records that as `{"resolved": "packages/<name>",
"link": true}` — no tarball URL, no integrity, by construction. Judged against
the registry shape that is two findings per package, and Quantum-L9/SEO-Bot has
four such packages: eight findings, none of them real, on a `package.json` edit
that touched none of them.

What must NOT happen in fixing that is a blanket skip. A local dep is exempt
from the registry checks and subject to its own: the declaration, the lock entry
and the directory on disk have to agree, and the directory has to contain the
package it claims to. `file:packages/ghost` is still a finding.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "ops" / "scripts" / "validate_gh_package_deps.py"

VENDORED = "@quantum-l9/bot-interop"


def write_workspace(
    tmp_path: Path,
    *,
    spec: str = "file:packages/bot-interop",
    lock_entry: dict | None = None,
    vendor_dir: str | None = "packages/bot-interop",
    vendor_name: str | None = VENDORED,
) -> tuple[Path, Path]:
    package = tmp_path / "package.json"
    package.write_text(json.dumps({"name": "consumer", "dependencies": {VENDORED: spec}}))

    entry = {"resolved": "packages/bot-interop", "link": True} if lock_entry is None else lock_entry
    lock = tmp_path / "package-lock.json"
    lock.write_text(json.dumps({"packages": {f"node_modules/{VENDORED}": entry}}))

    if vendor_dir is not None:
        target = tmp_path / vendor_dir
        target.mkdir(parents=True)
        if vendor_name is not None:
            (target / "package.json").write_text(json.dumps({"name": vendor_name}))
    return package, lock


def run(package: Path, lock: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(package), str(lock), "--no-live-check"],
        capture_output=True,
        text=True,
        check=False,
    )


def test_vendored_dependency_passes(tmp_path: Path) -> None:
    """The regression: this is the SEO-Bot shape, and it was eight findings."""
    result = run(*write_workspace(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "1 vendored locally" in result.stdout
    # Specifically NOT reported under the registry shape it does not have.
    assert "hash-suffixed GitHub Packages tarball" not in result.stderr
    assert "integrity" not in result.stderr


def test_local_path_that_does_not_exist_is_a_finding(tmp_path: Path) -> None:
    """The exemption is verified, not a skip. A phantom vendor still fails."""
    result = run(*write_workspace(tmp_path, vendor_dir=None))
    assert result.returncode == 1
    assert "has no package.json" in result.stderr


def test_local_path_holding_the_wrong_package_is_a_finding(tmp_path: Path) -> None:
    result = run(*write_workspace(tmp_path, vendor_name="@quantum-l9/something-else"))
    assert result.returncode == 1
    assert "not '@quantum-l9/bot-interop'" in result.stderr


def test_lock_pointing_somewhere_else_is_a_finding(tmp_path: Path) -> None:
    """Declaration and lock must agree on WHERE the package lives."""
    result = run(
        *write_workspace(tmp_path, lock_entry={"resolved": "packages/elsewhere", "link": True})
    )
    assert result.returncode == 1
    assert "lock resolves it to" in result.stderr


def test_lock_link_without_a_local_declaration_is_a_finding(tmp_path: Path) -> None:
    """The reverse mismatch: package.json says registry, the lock says link.

    Reported as the one disagreement it is, rather than as the two symptoms
    (no tarball, no integrity) that disagreement produces.
    """
    result = run(*write_workspace(tmp_path, spec="^1.2.0"))
    assert result.returncode == 1
    assert "does not declare it with file:/link:" in result.stderr
    assert result.stderr.count("validate_gh_package_deps:") == 2  # one problem + the count line


def test_registry_dependency_is_still_judged_as_one(tmp_path: Path) -> None:
    """The check this hook was written for must be untouched."""
    package, lock = write_workspace(
        tmp_path,
        spec="^1.2.0",
        lock_entry={
            "version": "1.2.0",
            "resolved": "https://npm.pkg.github.com/download/@quantum-l9/bot-interop/1.2.0/deadbeef",
            "integrity": "sha1-nope",
        },
        vendor_dir=None,
    )
    result = run(package, lock)
    assert result.returncode == 1
    # The hash suffix is too short for TARBALL_RE, and sha1 is not sha512.
    assert "hash-suffixed GitHub Packages tarball" in result.stderr
    assert "non-sha512 integrity" in result.stderr


@pytest.mark.parametrize("prefix", ["file:", "link:"])
def test_both_local_protocols_are_recognised(tmp_path: Path, prefix: str) -> None:
    result = run(*write_workspace(tmp_path, spec=f"{prefix}packages/bot-interop"))
    assert result.returncode == 0, result.stderr
