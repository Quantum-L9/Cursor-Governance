#!/usr/bin/env python3
"""Load and validate a repository's ``.l9/release.json`` (schema ``l9.release/v1``).

The declaration says what a repository releases and how. It never grants
publication authority: ``make release`` (``ops/scripts/l9_release.py``) still
runs every precondition and gate against the exact commit.

Usage (validator)::

    python3 ops/scripts/release_declaration.py --workspace <repo>

Exit 0: VALID, 1: INVALID, 2: ABSENT.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "ops" / "schemas" / "l9.release.v1.schema.json"
DECLARATION_RELPATH = ".l9/release.json"
SCHEMA_ID = "l9.release/v1"

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
_EXACT_TAG = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class DeclarationError(Exception):
    """The declaration or a file it names is absent, malformed, or inconsistent."""


@dataclass(frozen=True)
class Ecosystem:
    kind: str
    version_authority: str


@dataclass(frozen=True)
class Declaration:
    repository: str
    default_branch: str
    ecosystems: tuple[Ecosystem, ...]
    artifacts: tuple[str, ...]
    major_tag: str
    changelog: str
    pre_release_argv: tuple[str, ...] = field(default=())

    def artifact_names(self, version: str) -> tuple[str, ...]:
        return tuple(name.replace("{version}", version) for name in self.artifacts)


def parse_semver(text: str) -> tuple[int, int, int]:
    match = _SEMVER.match(text.strip())
    if match is None:
        raise DeclarationError(f"version {text!r} is not MAJOR.MINOR.PATCH")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def exact_tag_version(tag: str) -> tuple[int, int, int] | None:
    """Return the version an exact ``vX.Y.Z`` tag names, or None (``v4`` is not exact)."""
    match = _EXACT_TAG.match(tag)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def schema_errors(document: Any) -> list[str]:
    """Return every schema violation; empty means the document conforms."""
    import jsonschema  # locked governance venv dependency

    validator = jsonschema.Draft202012Validator(_schema())
    errors = []
    for error in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(part) for part in error.absolute_path) or "<root>"
        errors.append(f"{where}: {error.message}")
    return errors


def _relative_file(workspace: Path, relpath: str, purpose: str) -> Path:
    candidate = (workspace / relpath).resolve()
    if workspace.resolve() not in candidate.parents:
        raise DeclarationError(f"{purpose} {relpath!r} escapes the repository")
    return candidate


def load(workspace: Path) -> Declaration:
    path = workspace / DECLARATION_RELPATH
    if not path.is_file():
        raise DeclarationError(
            f"no release declaration: add {path} (schema {SCHEMA_ID}, see "
            "docs/L9_RELEASE.md and docs/examples/release/)"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DeclarationError(f"{path}: not readable JSON: {exc}") from exc
    errors = schema_errors(document)
    if errors:
        raise DeclarationError(f"{path}: does not conform to {SCHEMA_ID}: " + "; ".join(errors))
    for ecosystem in document["ecosystems"]:
        _relative_file(workspace, ecosystem["version_authority"], "version_authority")
    _relative_file(workspace, document["notes"]["changelog"], "changelog")
    kinds = [eco["kind"] for eco in document["ecosystems"]]
    if len(kinds) != len(set(kinds)):
        raise DeclarationError(f"{path}: an ecosystem kind is declared twice")
    return Declaration(
        repository=document["repository"],
        default_branch=document.get("default_branch", "main"),
        ecosystems=tuple(
            Ecosystem(kind=eco["kind"], version_authority=eco["version_authority"])
            for eco in document["ecosystems"]
        ),
        artifacts=tuple(document["artifacts"]),
        major_tag=document["major_tag"],
        changelog=document["notes"]["changelog"],
        pre_release_argv=tuple(document.get("pre_release", {}).get("argv", ())),
    )


def read_version(kind: str, text: str) -> str:
    """Read the version a version-authority file declares."""
    if kind == "python-uv":
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise DeclarationError(f"pyproject.toml is not valid TOML: {exc}") from exc
        project = data.get("project", {})
        version = project.get("version")
        if "version" in project.get("dynamic", []):
            raise DeclarationError("[project].version is dynamic; a static version is required")
    elif kind == "node-npm":
        try:
            version = json.loads(text).get("version")
        except (ValueError, AttributeError) as exc:
            raise DeclarationError(f"package.json is not a JSON object: {exc}") from exc
    else:
        raise DeclarationError(f"unknown ecosystem {kind!r}")
    if not isinstance(version, str):
        raise DeclarationError(f"{kind} version authority carries no version string")
    parse_semver(version)
    return version


def declared_version(declaration: Declaration, read_file: Any) -> str:
    """Return the one version every authority agrees on. ``read_file(relpath) -> str``."""
    versions = {
        eco.version_authority: read_version(eco.kind, read_file(eco.version_authority))
        for eco in declaration.ecosystems
    }
    distinct = set(versions.values())
    if len(distinct) != 1:
        raise DeclarationError(f"version authorities disagree: {versions}")
    return distinct.pop()


def changelog_section(text: str, version: str) -> tuple[str, str]:
    """Return (date, body) of the dated ``## X.Y.Z - YYYY-MM-DD`` section."""
    heading = re.compile(
        r"^##\s+\[?v?" + re.escape(version) + r"\]?\s+[-–—]\s+(\d{4}-\d{2}-\d{2})\s*$"
    )
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = heading.match(line)
        if match is None:
            continue
        body: list[str] = []
        for following in lines[index + 1 :]:
            if re.match(r"^##\s", following):
                break
            body.append(following)
        rendered = "\n".join(body).strip()
        if not rendered:
            raise DeclarationError(f"CHANGELOG section {version} is empty")
        return match.group(1), rendered
    raise DeclarationError(f"CHANGELOG has no dated section '## {version} - YYYY-MM-DD'")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", default=".")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace)
    if not (workspace / DECLARATION_RELPATH).is_file():
        print(f"ABSENT: {workspace / DECLARATION_RELPATH}")
        return 2
    try:
        declaration = load(workspace)
    except DeclarationError as exc:
        print(f"INVALID: {exc}")
        return 1
    print(f"VALID: {declaration.repository} ({', '.join(e.kind for e in declaration.ecosystems)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
