#!/usr/bin/env python3
"""Provider egress firewall for Cursor-Governance (plan §8, INV-03).

Scans production code and configuration for direct memory-provider surfaces
— Graphiti MCP tool names, provider connection variables, and the brokered
provider alias — and reports every occurrence that is not covered by an
exact, expiring, path-based allowlist entry.

Modes:

- ``warning`` (default, campaign stages C1–C10): findings are printed and the
  process exits 0, so the inventory is visible on every run without blocking.
- ``--enforce`` (stage C11+): any non-allowlisted finding, or an expired
  allowlist entry, exits 1. ``ops/config/memory-egress-allowlist.json`` also
  carries a ``mode`` field; ``--enforce`` on the command line wins.

Only ``l9-graphiti-memory`` is authorized to understand the provider dialect.

Usage:
    python3 ops/scripts/validate_memory_egress_boundary.py [--enforce] [--json] [--root PATH]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = REPO_ROOT / "ops" / "config" / "memory-egress-allowlist.json"

#: Provider surfaces production Cursor code must not carry (plan §8).
FORBIDDEN_TOKENS: tuple[str, ...] = (
    "GRAPHITI_MCP_URL",
    "GRAPHITI_MCP_TOKEN",
    "search_memory_facts",
    "search_nodes",
    "search_facts",
    "add_memory",
    "add_episode",
    "delete_episode",
    "graphiti.write_governed",
)

#: File types that are production code or configuration. Prose (.md/.mdc) is
#: out of scope: doctrine is rewritten at C12 and is not an egress path.
PRODUCTION_SUFFIXES = frozenset({".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".env"})
PRODUCTION_NAMES = frozenset({".mcp.json", ".env", "Makefile"})

#: Directories that are never production egress paths.
EXCLUDED_PREFIXES: tuple[str, ...] = (
    "tests/",
    "docs/",
    "WIP/",
    "reports/",
    "learning/",
    "releases/",
    "rules/",
    "prompts/",
    "kernels/",
    "commands/",
    "current_work/",
    "C_GOV_FILES/",
    "environment/generated/",
    "ops/generated/",
    ".cursor/",
    ".cursor-commands/",
    ".claude/",
    ".l9/",
)
EXCLUDED_PARTS = frozenset(
    {"_archived", "_archive", "archive", "archived", "fixtures", "__pycache__"}
)

_TOKEN_RE = re.compile("|".join(re.escape(token) for token in FORBIDDEN_TOKENS))


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    token: str
    allowlisted: bool
    allowlist_entry: str | None
    excerpt: str


@dataclass(frozen=True)
class AllowlistEntry:
    path: str
    reason: str
    retire_at_stage: str
    expires: str

    def matches(self, relative: str) -> bool:
        pattern = self.path
        if pattern.endswith("/**"):
            return relative.startswith(pattern[:-3] + "/")
        return fnmatch.fnmatchcase(relative, pattern)

    def expired(self, today: datetime) -> bool:
        try:
            return datetime.strptime(self.expires, "%Y-%m-%d").replace(tzinfo=UTC) < today
        except ValueError:
            return True


def load_allowlist(path: Path = ALLOWLIST_PATH) -> tuple[str, tuple[AllowlistEntry, ...]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = tuple(
        AllowlistEntry(
            path=str(item["path"]),
            reason=str(item.get("reason", "")),
            retire_at_stage=str(item.get("retire_at_stage", "")),
            expires=str(item.get("expires", "")),
        )
        for item in raw.get("entries") or []
    )
    return str(raw.get("mode", "warning")), entries


def tracked_files(root: Path) -> list[Path]:
    try:
        result = subprocess.run(  # noqa: S603 - fixed argv
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            check=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        return sorted(path for path in root.rglob("*") if path.is_file())
    return [root / item for item in result.stdout.split("\0") if item]


def is_production_path(relative: str) -> bool:
    if any(relative.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    parts = Path(relative).parts
    if any(part in EXCLUDED_PARTS for part in parts[:-1]):
        return False
    name = parts[-1]
    if name in PRODUCTION_NAMES:
        return True
    suffix = Path(name).suffix
    if suffix in PRODUCTION_SUFFIXES:
        return True
    # Extensionless executables under ops/ and hooks/ are production too.
    return suffix == "" and (relative.startswith("ops/") or "/hooks/" in relative)


def scan(
    root: Path,
    allowlist: tuple[AllowlistEntry, ...],
    *,
    today: datetime | None = None,
) -> tuple[list[Finding], list[AllowlistEntry]]:
    now = today or datetime.now(UTC)
    expired = [entry for entry in allowlist if entry.expired(now)]
    live = [entry for entry in allowlist if entry not in expired]
    findings: list[Finding] = []
    for path in tracked_files(root):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if not is_production_path(relative):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for match in _TOKEN_RE.finditer(line):
                entry = next((item for item in live if item.matches(relative)), None)
                findings.append(
                    Finding(
                        path=relative,
                        line=number,
                        token=match.group(0),
                        allowlisted=entry is not None,
                        allowlist_entry=entry.path if entry else None,
                        excerpt=line.strip()[:160],
                    )
                )
    return findings, expired


def report(
    findings: list[Finding],
    expired: list[AllowlistEntry],
    *,
    enforce: bool,
    as_json: bool,
) -> int:
    unlisted = [item for item in findings if not item.allowlisted]
    listed = [item for item in findings if item.allowlisted]
    blocking = bool(unlisted or expired)
    verdict = "FAIL" if (enforce and blocking) else ("WARN" if blocking or listed else "PASS")
    allowlisted_by_file = _by_file(listed)
    summary: dict[str, Any] = {
        "validator": "memory_egress_boundary",
        "mode": "enforce" if enforce else "warning",
        "verdict": verdict,
        "forbidden_tokens": list(FORBIDDEN_TOKENS),
        "findings_total": len(findings),
        "findings_allowlisted": len(listed),
        "findings_unlisted": len(unlisted),
        "allowlist_expired": [asdict(entry) for entry in expired],
        "unlisted": [asdict(item) for item in unlisted],
        "allowlisted_by_file": allowlisted_by_file,
    }
    if as_json:
        sys.stdout.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(
            f"memory egress boundary [{summary['mode']}]: {verdict} — "
            f"{len(findings)} provider references in production paths "
            f"({len(listed)} allowlisted for retirement, {len(unlisted)} unlisted)\n"
        )
        for path, count in sorted(allowlisted_by_file.items()):
            sys.stdout.write(f"  allowlisted  {path} ({count})\n")
        for item in unlisted:
            sys.stdout.write(
                f"  UNLISTED     {item.path}:{item.line} {item.token} — {item.excerpt}\n"
            )
        for entry in expired:
            sys.stdout.write(f"  EXPIRED      allowlist {entry.path} (expired {entry.expires})\n")
        if verdict == "WARN" and not enforce:
            sys.stdout.write(
                "  warning mode: exit 0. Stage C11 flips this validator to --enforce.\n"
            )
    return 1 if (enforce and blocking) else 0


def _by_file(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in findings:
        counts[item.path] = counts.get(item.path, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--allowlist", default=str(ALLOWLIST_PATH))
    parser.add_argument(
        "--enforce", action="store_true", help="fail on unlisted or expired findings"
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    mode, allowlist = load_allowlist(Path(args.allowlist))
    enforce = args.enforce or mode == "enforce"
    findings, expired = scan(root, allowlist)
    return report(findings, expired, enforce=enforce, as_json=args.json)


if __name__ == "__main__":
    raise SystemExit(main())
