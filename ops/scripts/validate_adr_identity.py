#!/usr/bin/env python3
"""Fail closed when two decisions share an ADR number, and keep the index honest.

``docs/decisions/README.md`` is the generated identity manifest. A
``docs/decisions/`` pointer and an ``environment/contracts/execution/adr/``
body may share a number only when the filename slug is the same decision.
Anything else is a collision. The check also requires each heading number to
match its filename, and the generated index to match the files on disk.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCAN_DIRS = (
    Path("docs/decisions"),
    Path("docs/adr"),
    Path("environment/contracts/execution/adr"),
)
FILENAME = re.compile(r"^ADR-(?P<number>\d{3,})-(?P<slug>.+)\.md$")
H1 = re.compile(r"^#\s+ADR-(?P<number>\d+):\s+(?P<title>\S.*?)\s*$", re.MULTILINE)
H2 = re.compile(r"^##\s+(?P<heading>.+?)\s*#*\s*$", re.MULTILINE)
BOLD_STATUS = re.compile(r"^\s*-?\s*\*\*Status:\*\*\s*(.+?)\s*$", re.MULTILINE)
LIST_STATUS = re.compile(r"^\s*\*\s+Status:\s*(.+?)\s*$", re.MULTILINE)
INDEX_BEGIN = "<!-- BEGIN L9 ADR INDEX (generated — do not edit) -->"
INDEX_END = "<!-- END L9 ADR INDEX -->"
POINTER_MARK = "Org catalog pointer only."
README_REL = Path("docs/decisions/README.md")


@dataclass
class Record:
    number: str
    slug: str
    path: str
    title: str
    status: str
    pointer: bool
    findings: list[str] = field(default_factory=list)


def _section(text: str, name: str) -> str | None:
    matches = list(H2.finditer(text))
    wanted = name.casefold()
    for index, match in enumerate(matches):
        if match.group("heading").strip().casefold() != wanted:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        return body or None
    return None


def _status(text: str, *, pointer: bool) -> str:
    if pointer:
        return "Pointer"
    body = _section(text, "Status")
    if body:
        first = body.split("\n\n", 1)[0]
        return " ".join(first.split())
    bold = BOLD_STATUS.search(text)
    if bold:
        return " ".join(bold.group(1).split())
    listed = LIST_STATUS.search(text)
    if listed:
        return " ".join(listed.group(1).split())
    return "Unknown"


def _load(root: Path, path: Path) -> Record | None:
    match = FILENAME.fullmatch(path.name)
    if match is None:
        return None
    text = path.read_text(encoding="utf-8")
    number = f"{int(match.group('number')):04d}"
    rel = path.relative_to(root).as_posix()
    heading = H1.search(text)
    findings: list[str] = []
    title = ""
    if heading is None:
        findings.append(f"{rel}: missing '# ADR-{number}: …' heading")
    elif int(heading.group("number")) != int(number):
        findings.append(
            f"{rel}: heading ADR-{heading.group('number')} does not match filename ADR-{number}"
        )
        title = heading.group("title")
    else:
        title = heading.group("title")
    pointer = POINTER_MARK in text
    return Record(
        number=number,
        slug=match.group("slug"),
        path=rel,
        title=title,
        status=_status(text, pointer=pointer),
        pointer=pointer,
        findings=findings,
    )


def collect(root: Path) -> list[Record]:
    records: list[Record] = []
    for directory in SCAN_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.glob("ADR-*.md")):
            if not path.is_file():
                continue
            record = _load(root, path)
            if record is not None:
                records.append(record)
    return records


def identity_findings(records: list[Record]) -> list[str]:
    findings = [item for record in records for item in record.findings]
    grouped: dict[str, list[Record]] = {}
    for record in records:
        grouped.setdefault(record.number, []).append(record)
    for number, rows in sorted(grouped.items(), key=lambda item: int(item[0])):
        bodies = [row for row in rows if not row.pointer]
        if len(bodies) > 1:
            paths = ", ".join(row.path for row in bodies)
            findings.append(f"ADR-{number} has more than one full body: {paths}")
        slugs = {row.slug for row in rows}
        if len(slugs) <= 1:
            continue
        paths = ", ".join(row.path for row in rows)
        findings.append(f"ADR-{number} names more than one decision: {paths}")
    return findings


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _canonical(rows: list[Record]) -> Record:
    bodies = [row for row in rows if not row.pointer]
    return bodies[0] if bodies else rows[0]


def render_readme(records: list[Record]) -> str:
    grouped: dict[str, list[Record]] = {}
    for record in records:
        grouped.setdefault(record.number, []).append(record)
    lines = [
        "# Architecture Decision Records",
        "",
        "This directory is the repository's record of durable architecture decisions.",
        "Each ADR file is the record. This index is generated from those files by",
        "`ops/scripts/validate_adr_identity.py`. One number is one decision. A",
        "`docs/decisions/` pointer and an `environment/contracts/execution/adr/` body",
        "may share a number only when the filename slug is the same decision.",
        "",
        INDEX_BEGIN,
        "",
        "| Number | Status | Title | Record |",
        "|---|---|---|---|",
    ]
    for number in sorted(grouped, key=int):
        rows = sorted(grouped[number], key=lambda row: row.path)
        source = _canonical(rows)
        paths = "<br>".join(f"`{row.path}`" for row in rows)
        lines.append(f"| ADR-{number} | {_cell(source.status)} | {_cell(source.title)} | {paths} |")
    lines.extend(
        [
            "",
            INDEX_END,
            "",
            "The next number is one greater than the highest number in this index.",
            "Unassigned integers below that highest number stay unused.",
            "Superseding a decision adds a later ADR that links to the record it replaces.",
            "Prior records stay on disk.",
            "",
        ]
    )
    return "\n".join(lines)


def check(root: Path) -> list[str]:
    records = collect(root)
    findings = identity_findings(records)
    readme = root / README_REL
    expected = render_readme(records)
    if not readme.is_file():
        findings.append(f"{README_REL.as_posix()}: missing generated index")
    elif readme.read_text(encoding="utf-8") != expected:
        findings.append(f"{README_REL.as_posix()}: generated index is stale; re-run --write")
    return findings


def write_readme(root: Path) -> None:
    records = collect(root)
    path = root / README_REL
    path.write_text(render_readme(records), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--write",
        action="store_true",
        help="regenerate docs/decisions/README.md from the ADR files",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.write:
        write_readme(root)
    findings = check(root)
    if findings:
        print("ADR identity: FAIL", file=sys.stderr)
        for finding in findings:
            print(f"  {finding}", file=sys.stderr)
        return 1
    print(f"ADR identity: PASS ({len(collect(root))} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
