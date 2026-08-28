#!/usr/bin/env python3
"""Warn at the start of a turn when a protected root file is being overwritten.

Every file at the repository root is protected (AGENTS.md §14,
``ops/config/root-file-protection.json``). An ``additive_only`` file may gain
lines freely; deleting or overwriting existing content needs an
``ALLOW-ROOT-DELETION: <path> — <reason>`` line in a commit message.

Nothing said so until `make pr` — the last step of a session's work. On
2026-08-28 a single rewritten line in ``pyproject.toml`` was discovered there,
an hour after the edit, and cost an amend and a second gate run. The rule was
not missing: AGENTS.md §14 states it exactly. AGENTS.md is 28 KB and did not
reach the model's context, which is the failure ``CLAUDE.md`` opens by
describing — authority in force and invisible at the same time.

A document that must be read before the mistake cannot prevent it. This runs on
UserPromptSubmit, reuses ``ops/scripts/validate_root_file_protection.py`` rather
than restating its rule, and speaks only when there is something to say:

  * silent when every protected-root change is additive;
  * silent once a commit carries the marker (the advisory clears itself);
  * one short paragraph naming the path, the counts, and the exact remedy
    otherwise.

It never blocks. An edit to a protected root file is legitimate work; only an
unjustified overwrite reaching a PR is not.

Observer class: any failure here is silent. A missing advisory must never cost a
turn, and the real gate still runs at `make pr` and in CI.
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
        f"Protected-root advisory: {listed}{more} — additive_only root file(s) with "
        "removed/overwritten lines and no ALLOW-ROOT-DELETION marker. `make pr` will "
        "block on this. Either rewrite the change to be purely additive, or put "
        "`ALLOW-ROOT-DELETION: <path> — <reason with proof of necessity>` in a commit "
        "message on this branch (any commit in the range counts, so amending HEAD "
        "works). The PR body also needs the protected-root template; `make pr` injects "
        "it. Authority: AGENTS.md §14, ops/config/root-file-protection.json."
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
