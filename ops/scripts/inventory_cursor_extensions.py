#!/usr/bin/env python3
"""Read-only inventory of Cursor/VS Code extensions and likely overlap."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CATEGORIES = {
    "formatter": ("prettier", "black-formatter", "ruff"),
    "linter": ("eslint", "ruff", "pylint", "flake8"),
    "python": ("ms-python.python", "pyright", "pylance", "ruff"),
    "ai_assistant": ("copilot", "codeium", "windsurf", "tabnine", "continue", "claude", "gemini", "amazon-q"),
}


def parse_extension_line(line: str) -> tuple[str, str | None]:
    line = line.strip()
    if "@" in line:
        extension_id, version = line.rsplit("@", 1)
        return extension_id.lower(), version
    return line.lower(), None


def scan_directory(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.is_dir():
        return entries
    for child in sorted(path.iterdir(), key=lambda item: item.name.lower()):
        if not child.is_dir():
            continue
        match = re.match(r"(.+?)-(\d[^/]*)$", child.name)
        extension_id = match.group(1).lower() if match else child.name.lower()
        version = match.group(2) if match else None
        entries.append({"id": extension_id, "version": version, "source": str(path)})
    return entries


def categories(extension_id: str) -> list[str]:
    return [name for name, needles in CATEGORIES.items() if any(needle in extension_id for needle in needles)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    home = args.home.expanduser().resolve()
    output_dir = (args.output_dir or Path.cwd() / "reports").resolve()

    found: list[dict[str, Any]] = []
    cli = shutil.which("cursor")
    cli_error: str | None = None
    if cli:
        result = subprocess.run([cli, "--list-extensions", "--show-versions"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.strip():
                    extension_id, version = parse_extension_line(line)
                    found.append({"id": extension_id, "version": version, "source": "cursor-cli"})
        else:
            cli_error = result.stderr.strip() or f"cursor CLI exited {result.returncode}"

    candidates = [
        home / ".cursor/extensions",
        home / ".vscode/extensions",
        home / "Library/Application Support/Cursor/extensions",
    ]
    for candidate in candidates:
        found.extend(scan_directory(candidate))

    by_id: dict[str, dict[str, Any]] = {}
    sources: defaultdict[str, set[str]] = defaultdict(set)
    versions: defaultdict[str, set[str]] = defaultdict(set)
    for item in found:
        extension_id = item["id"]
        sources[extension_id].add(item["source"])
        if item.get("version"):
            versions[extension_id].add(item["version"])
        by_id.setdefault(extension_id, {"id": extension_id})

    extensions: list[dict[str, Any]] = []
    for extension_id in sorted(by_id):
        extensions.append(
            {
                "id": extension_id,
                "versions": sorted(versions[extension_id]),
                "sources": sorted(sources[extension_id]),
                "categories": categories(extension_id),
            }
        )

    category_members: defaultdict[str, list[str]] = defaultdict(list)
    for item in extensions:
        for category in item["categories"]:
            category_members[category].append(item["id"])
    overlaps = {name: members for name, members in category_members.items() if len(members) > 1}

    report = {
        "schema": "l9.cursor-extension-inventory/v1",
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "read_only": True,
        "cursor_cli": cli,
        "cursor_cli_error": cli_error,
        "scanned_directories": [str(path) for path in candidates],
        "extensions": extensions,
        "potential_overlaps": overlaps,
        "recommendation_policy": "Inventory only. Do not install or remove extensions automatically.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "cursor-extension-inventory.json"
    md_path = output_dir / "cursor-extension-inventory.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Cursor extension inventory",
        "",
        f"Generated: `{report['generated_utc']}`",
        "",
        "**Mode:** read-only. No installation or removal was attempted.",
        "",
        "## Installed extensions",
        "",
        "| Extension | Versions | Categories | Sources |",
        "|---|---|---|---|",
    ]
    for item in extensions:
        lines.append(
            f"| `{item['id']}` | {', '.join(item['versions']) or 'unknown'} | "
            f"{', '.join(item['categories']) or 'uncategorized'} | {', '.join(item['sources'])} |"
        )
    lines.extend(["", "## Potential overlap", ""])
    if overlaps:
        for name, members in sorted(overlaps.items()):
            lines.append(f"- **{name}:** {', '.join(f'`{member}`' for member in members)}")
    else:
        lines.append("- No category-level overlap detected from available metadata.")
    lines.extend(
        [
            "",
            "## Decision gate",
            "",
            "Review overlap manually before changing personal editor configuration.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"WROTE: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
