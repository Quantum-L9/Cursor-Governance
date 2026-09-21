#!/usr/bin/env python3
"""Fail closed unless every external GitHub Action is pinned to a full commit SHA.

Supply-chain hardening for .github/workflows/** (B07 / P1-08). A floating tag
(`@v4`, `@main`) is mutable: the upstream owner can move it to new code after
review. This validator requires an immutable 40-hex commit SHA for every
third-party `uses:` and fails closed on a malformed `uses:` value.

Policy
------
- Local actions (`./path`, `././...`) are exempt — they live in this repo.
- Every external action and reusable workflow MUST use a full 40-character
  commit SHA. Internal ownership does not make a mutable branch or tag
  immutable provenance.

Exit 0 = all pins compliant. Exit 1 = at least one floating/malformed ref.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / ".github" / "workflows"

USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>\S+)")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _is_local(ref: str) -> bool:
    return ref.startswith("./") or ref.startswith(".//") or ref == "."


def _check_ref(ref: str) -> str | None:
    """Return an error string if the ref is non-compliant, else None."""
    # Strip surrounding quotes a YAML author might have added.
    ref = ref.strip().strip("'\"")
    if _is_local(ref):
        return None
    if "@" not in ref:
        return f"malformed uses (no @ref): {ref!r}"
    _, gitref = ref.rsplit("@", 1)
    if not gitref:
        return f"malformed uses (empty ref): {ref!r}"
    if SHA_RE.match(gitref):
        return None
    return f"external action not pinned to a full commit SHA: {ref!r}"


def main() -> int:
    if not WORKFLOW_DIR.is_dir():
        print(f"PASS: no {WORKFLOW_DIR.relative_to(ROOT)} directory")
        return 0

    failures: list[str] = []
    checked = 0
    files = sorted(WORKFLOW_DIR.glob("*.yml")) + sorted(WORKFLOW_DIR.glob("*.yaml"))
    for wf in files:
        rel = wf.relative_to(ROOT).as_posix()
        for i, line in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            m = USES_RE.match(line)
            if not m:
                continue
            checked += 1
            err = _check_ref(m.group("ref"))
            if err:
                failures.append(f"{rel}:{i}: {err}")

    if failures:
        print("FAIL: unpinned or malformed external GitHub Action reference(s)")
        print("Pin every external action to a full 40-char commit SHA (keep a # vX comment).")
        for f in failures:
            print(f"  {f}")
        return 1

    print(f"PASS: {checked} action reference(s) across {len(files)} workflow file(s) compliant")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
