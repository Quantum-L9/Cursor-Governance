#!/usr/bin/env python3
"""Warn at the start of a turn when a protected root file is being overwritten.

Every file at the repository root is protected (AGENTS.md
PROTECTED_ROOT_PRE_EDIT_V1, ``ops/config/root-file-protection.json``).
``AGENTS.md`` and ``Makefile`` share the same ``additive_only`` rule. An
agent may append. An overwrite is not a commit-marker or PR-template
chore: open a GitHub issue and stop.

This runs on UserPromptSubmit. It speaks only when an overwrite is
already in the tree and no marker exists yet. The always-on teacher is
``rules/00-global.mdc`` so the agent knows *before* the first edit.

  * silent when every protected-root change is additive;
  * silent once a commit carries the marker (human/ops after an issue);
  * one short paragraph: revert to additive, or open an issue. Do not
    amend or chase the PR template.

Observer class: any failure here is silent. A missing advisory must never
cost a turn. The CI gate still runs at `make pr`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

MAX_PATHS = 6


def _git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


def uncommitted_overwrites(repo: Path, protected: dict[str, str]) -> list[tuple[str, int, int]]:
    """Protected root paths whose working tree removes committed lines.

    The committed-range check cannot see an edit that has not been committed
    yet, and that is exactly the window where the warning is cheapest to act on:
    the marker can still go into the commit that carries the change.
    """
    findings: list[tuple[str, int, int]] = []
    out = _git(repo, ["diff", "HEAD", "--numstat", "--"] + sorted(protected))
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 3 or parts[0] == "-":
            continue
        added, deleted, path = parts[0], parts[1], parts[2]
        if protected.get(path) != "additive_only":
            continue
        if int(deleted) > 0:
            findings.append((path, int(added), int(deleted)))
    return findings


def advisory(repo: Path) -> str | None:
    """One paragraph when an overwrite lacks its marker, else None."""
    try:
        import validate_root_file_protection as gate
    except Exception:  # noqa: BLE001 - observer: never cost a turn
        return None
    try:
        config = gate.load_config(repo)
    except Exception:  # noqa: BLE001
        return None
    protected = {e["path"]: e["rule"] for e in config["protected_files"]}

    committed: list[tuple[str, int, int]] = []
    try:
        base = gate.merge_base(repo, "origin/main", "HEAD")
        justified = gate.collect_justified_paths(repo, base, "HEAD")
        for path, rule in protected.items():
            if rule != "additive_only" or path in justified:
                continue
            stat = gate.numstat(repo, base, "HEAD", path)
            if isinstance(stat, tuple) and stat[1] > 0:
                committed.append((path, stat[0], stat[1]))
    except Exception:  # noqa: BLE001 - no origin/main in a fresh clone, etc.
        justified = set()

    try:
        pending = [f for f in uncommitted_overwrites(repo, protected) if f[0] not in justified]
    except Exception:  # noqa: BLE001
        pending = []

    seen: dict[str, tuple[str, int, int]] = {}
    for finding in committed + pending:
        seen.setdefault(finding[0], finding)
    if not seen:
        return None

    rows = sorted(seen.values())[:MAX_PATHS]
    listed = "; ".join(f"`{p}` (+{a} -{d})" for p, a, d in rows)
    more = f" and {len(seen) - len(rows)} more" if len(seen) > len(rows) else ""
    return (
        f"Protected-root advisory: {listed}{more} — additive_only overwrite "
        "(AGENTS.md and Makefile are the same rule). STOP. Do not amend the "
        "commit and do not chase the protected-root PR template. Revert to a "
        "purely additive edit, or open a GitHub issue and wait. "
        "ALLOW-ROOT-DELETION is human/ops after that issue, not an agent first "
        "move. Authority: AGENTS.md PROTECTED_ROOT_PRE_EDIT_V1, "
        "ops/config/root-file-protection.json."
    )


def main() -> int:
    try:
        raw = sys.stdin.read()
        event = json.loads(raw) if raw.strip() else {}
        cwd = event.get("cwd") or event.get("workspace") or "."
        repo_out = _git(Path(cwd), ["rev-parse", "--show-toplevel"]).strip()
        if not repo_out:
            return 0
        message = advisory(Path(repo_out))
        if message:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": "UserPromptSubmit",
                            "additionalContext": message,
                        }
                    }
                )
            )
    except Exception:  # noqa: BLE001 - observer: never cost a turn
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
