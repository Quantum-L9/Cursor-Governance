#!/usr/bin/env python3
"""Prove every projection agrees with the governance runtime contract.

The runtime contract (ops/config/governance-runtime-contract.yaml) is the
compact SSOT for high-risk duplicated governance facts. This validator walks
each invariant's projections and fails closed on any single divergence — the
mechanical enforcement behind SP-11 / EV-X-01. It replaces "trust the prose"
with "check the prose against the contract."

Exit 0 = every projection agrees. Exit 1 = at least one divergence.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    sys.exit("PyYAML is required to validate the governance runtime contract")

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "ops/config/governance-runtime-contract.yaml"


def _check_projection(proj: dict) -> str | None:
    """Return an error string if the projection diverges, else None."""
    kind = proj.get("type")
    rel = proj.get("path")
    if not rel:
        return f"projection missing 'path': {proj!r}"
    path = ROOT / rel

    if kind == "file_exists":
        if not path.is_file():
            return f"{rel}: expected file to exist"
        return None

    if kind == "file_contains":
        pattern = proj.get("pattern")
        want_present = bool(proj.get("present", True))
        if pattern is None:
            return f"{rel}: file_contains projection missing 'pattern'"
        if not path.is_file():
            return f"{rel}: file missing (cannot check pattern {pattern!r})"
        text = path.read_text(encoding="utf-8")
        found = pattern in text
        if want_present and not found:
            return f"{rel}: expected to contain {pattern!r} but it is absent"
        if not want_present and found:
            return f"{rel}: expected NOT to contain {pattern!r} but it is present"
        return None

    return f"{rel}: unknown projection type {kind!r}"


def main() -> int:
    if not CONTRACT.is_file():
        print(f"FAIL: runtime contract missing at {CONTRACT.relative_to(ROOT)}")
        return 1

    data = yaml.safe_load(CONTRACT.read_text(encoding="utf-8")) or {}
    invariants = data.get("invariants") or []
    if not invariants:
        print("FAIL: runtime contract declares no invariants")
        return 1

    failures: list[str] = []
    checked = 0
    for inv in invariants:
        inv_id = inv.get("id", "<unnamed>")
        for proj in inv.get("projections", []):
            checked += 1
            err = _check_projection(proj)
            if err:
                failures.append(f"[{inv_id}] {err}")

    if failures:
        print("FAIL: governance runtime contract projections diverge from their sources")
        for f in failures:
            print(f"  {f}")
        return 1

    print(
        f"PASS: {len(invariants)} invariant(s), {checked} projection(s) agree with the "
        "governance runtime contract"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
