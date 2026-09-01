#!/usr/bin/env python3
"""Report-only scan of installed LaunchAgents for forbidden governance roots.

FAIL when a top-level *.plist references Dropbox, Library/CloudStorage, or a
governance root other than $HOME/.cursor-governance. Never unload, bootout,
move, or delete. Missing LaunchAgents directory is a warning, not a fail.

Override the scan directory with --dir or L9_LAUNCHAGENTS_DIR (tests).
"""

from __future__ import annotations

import argparse
import os
import plistlib
from pathlib import Path

KEYS = (
    "Program",
    "ProgramArguments",
    "WorkingDirectory",
    "StandardOutPath",
    "StandardErrorPath",
)

SKIP_DIR_NAMES = {"_retired"}

FORBIDDEN_FRAGMENTS = (
    "Dropbox",
    "Library/CloudStorage",
)

GOVERNANCE_FRAGMENTS = (
    ".cursor-governance",
    "GlobalCommands",
    "Cursor Governance",
)

GOVERNANCE_LABEL_PREFIXES = (
    "com.cursor.",
    "com.tenx.",
    "com.l9.",
)


def _ssot() -> Path:
    return Path(os.path.expanduser("~/.cursor-governance")).resolve()


def _flatten(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            out.extend(_flatten(item))
        return out
    return [str(value)]


def _is_under_ssot(text: str, ssot: Path) -> bool:
    """True if the *lexical* path is under SSOT. Do not follow the leaf symlink.

    ``.venv/bin/python`` often points at a uv toolchain outside the clone;
    resolving the leaf would false-FAIL a legitimate SSOT interpreter.
    """
    raw = Path(os.path.expanduser(text))
    prefixes = {str(ssot), str(Path.home() / ".cursor-governance")}
    raw_s = str(raw)
    for prefix in prefixes:
        if raw_s == prefix or raw_s.startswith(prefix + os.sep):
            return True
    return False


def _has_governance_path_component(text: str) -> bool:
    """True when a governance fragment is a path component, not a filename substring.

    ``/tmp/com.tenx.cursor-governance.out`` contains ``.cursor-governance`` as
    a label-derived filename, not as a directory. That is not a governance root.
    """
    parts = Path(os.path.expanduser(text)).parts
    return any(fragment in parts for fragment in GOVERNANCE_FRAGMENTS)


def classify_string(text: str, ssot: Path) -> str | None:
    """Return a reason if this string violates path law, else None."""
    if not text:
        return None
    if _is_under_ssot(text, ssot):
        return None
    for fragment in FORBIDDEN_FRAGMENTS:
        if fragment in text:
            return f"forbidden fragment {fragment!r}"
    if _has_governance_path_component(text):
        return "governance root other than $HOME/.cursor-governance"
    return None


def scan_dir(launchagents: Path, ssot: Path) -> tuple[list[str], list[str]]:
    """Return (fails, warns)."""
    warns: list[str] = []
    fails: list[str] = []
    if not launchagents.exists():
        warns.append(f"LaunchAgents directory missing: {launchagents} (skip machine-plane scan)")
        return fails, warns
    if not launchagents.is_dir():
        warns.append(f"LaunchAgents path is not a directory: {launchagents}")
        return fails, warns

    for plist_path in sorted(launchagents.glob("*.plist")):
        if any(part in SKIP_DIR_NAMES for part in plist_path.parts):
            continue
        try:
            with plist_path.open("rb") as handle:
                data = plistlib.load(handle)
        except Exception as exc:  # noqa: BLE001 — report unreadable plist, do not crash the gate
            fails.append(f"{plist_path.name}: unreadable plist ({exc})")
            continue
        if not isinstance(data, dict):
            continue
        label = str(data.get("Label") or plist_path.stem)
        values: list[tuple[str, str]] = []
        for key in KEYS:
            for item in _flatten(data.get(key)):
                values.append((key, item))
        governance_related = label.startswith(GOVERNANCE_LABEL_PREFIXES) or any(
            any(fragment in item for fragment in GOVERNANCE_FRAGMENTS) for _key, item in values
        )
        if not governance_related:
            continue
        for key, item in values:
            reason = classify_string(item, ssot)
            if reason:
                fails.append(f"{label}: {key}={item} ({reason})")
    return fails, warns


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir",
        default=os.environ.get(
            "L9_LAUNCHAGENTS_DIR", str(Path.home() / "Library" / "LaunchAgents")
        ),
        help="LaunchAgents directory to scan (default: ~/Library/LaunchAgents)",
    )
    parser.add_argument(
        "--ssot",
        default=os.environ.get("L9_SSOT_ROOT", str(Path.home() / ".cursor-governance")),
        help="Allowed governance root (default: ~/.cursor-governance)",
    )
    args = parser.parse_args(argv)
    fails, warns = scan_dir(Path(args.dir), Path(os.path.expanduser(args.ssot)).resolve())
    for line in warns:
        print(f"WARN: {line}")
    if not fails and not warns:
        print("OK: no LaunchAgent references a forbidden or non-SSOT governance root")
        return 0
    if not fails:
        print("OK: LaunchAgents scan complete (warnings only)")
        return 0
    for line in fails:
        print(f"FAIL: {line}")
    print("OK: LaunchAgent scan is report-only (no unload/bootout/delete)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
