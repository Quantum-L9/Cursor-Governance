"""Declared expect-fail fixtures: known-bad witnesses that must fire, and only them.

A canary or parity fixture deliberately carries code a scanner must flag. The
publication gate used to have two choices for it: block (so the witness can
never be published) or be relaxed by hand (so nothing proves the scanner still
fires). This module is the third choice, owned as data.

``expect_fail_fixtures.json`` names, per consumer repository, the fixture roots
and, per file under them, the exact rule ids each scanner lane must report.
For a finding on a declared fixture path:

- a named rule that fires is ``expected``: recorded, not blocking;
- a named rule that does not fire is a FAIL (rule
  ``ci-parity/expected-finding-missing``), so a witness cannot rot silently;
- any other finding there is classified exactly as anywhere else.

Paths outside the declared roots, and repositories without an entry, are not
touched: they block exactly as before. ``run.py`` applies this to its lanes and
``ops/scripts/run_pr_security.sh`` applies it to Bandit through the CLI below,
so neither needs a suppression comment in the fixture.

Standard library only: the bash security gate calls the CLI with any python3.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "expect_fail_fixtures.json"
SCHEMA = "l9.ci-parity.expect-fail-fixtures/v1"
MISSING_RULE = "ci-parity/expected-finding-missing"


class FixtureManifestError(ValueError):
    """The manifest is malformed: fail closed, never treat it as empty."""


class FindingLike(Protocol):
    @property
    def rule(self) -> str: ...

    @property
    def path(self) -> str: ...


@dataclass(frozen=True)
class RepoFixtures:
    roots: tuple[str, ...]
    #: path -> lane (or "bandit") -> rule ids that must fire
    files: Mapping[str, Mapping[str, frozenset[str]]] = field(default_factory=dict)

    def covers(self, path: str) -> bool:
        return any(path.startswith(root) for root in self.roots)

    def expected(self, path: str, lane: str) -> frozenset[str]:
        return (self.files.get(path) or {}).get(lane, frozenset())

    def expected_paths(self, lane: str) -> list[str]:
        return sorted(p for p, lanes in self.files.items() if lanes.get(lane))


@dataclass(frozen=True)
class Registry:
    repositories: Mapping[str, RepoFixtures]

    def for_repo(self, slug: str) -> RepoFixtures | None:
        return self.repositories.get(slug.lower())


@dataclass(frozen=True)
class Verdict:
    """Findings split by the fixture contract.

    ``kept`` is classified by the caller exactly as before; ``expected`` never
    blocks; ``missing`` names (path, rule) pairs that must have fired and did not.
    """

    kept: list[Any]
    expected: list[Any]
    missing: list[tuple[str, str]]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FixtureManifestError(message)


def parse(data: Any) -> Registry:
    _require(isinstance(data, dict), "manifest must be an object")
    _require(data.get("schema") == SCHEMA, f"manifest schema must be {SCHEMA}")
    repos = data.get("repositories")
    _require(isinstance(repos, dict), "repositories must be an object")
    out: dict[str, RepoFixtures] = {}
    for slug, entry in repos.items():
        _require("/" in slug, f"repository {slug!r} must be owner/name")
        _require(isinstance(entry, dict), f"{slug}: entry must be an object")
        roots = entry.get("roots")
        _require(
            isinstance(roots, list) and bool(roots) and all(isinstance(r, str) for r in roots),
            f"{slug}: roots must be a non-empty list of paths",
        )
        for root in roots:
            _require(
                root.endswith("/") and not root.startswith("/") and ".." not in root.split("/"),
                f"{slug}: root {root!r} must be a repository-relative directory ending in /",
            )
        files = entry.get("files")
        _require(isinstance(files, dict), f"{slug}: files must be an object")
        parsed: dict[str, dict[str, frozenset[str]]] = {}
        for path, lanes in files.items():
            _require(
                any(path.startswith(root) for root in roots),
                f"{slug}: {path} is outside every declared root",
            )
            _require(isinstance(lanes, dict) and bool(lanes), f"{slug}: {path} names no lane")
            parsed[path] = {}
            for lane, rules in lanes.items():
                _require(
                    isinstance(rules, list)
                    and bool(rules)
                    and all(isinstance(r, str) and r for r in rules),
                    f"{slug}: {path} {lane}: rules must be a non-empty list of rule ids",
                )
                parsed[path][lane] = frozenset(rules)
        out[slug.lower()] = RepoFixtures(roots=tuple(roots), files=parsed)
    return Registry(repositories=out)


def load(path: Path | None = None) -> Registry:
    """Load the manifest. A missing file is an empty registry; a bad one raises."""
    path = MANIFEST if path is None else path
    if not path.is_file():
        return Registry(repositories={})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FixtureManifestError(f"{path}: {exc}") from exc
    return parse(data)


def evaluate(
    fixtures: RepoFixtures | None,
    lane: str,
    findings: Iterable[FindingLike],
    scanned: Iterable[str],
    observed: Iterable[FindingLike] = (),
) -> Verdict:
    """Split one lane's findings; ``scanned`` are the paths the lane covered.

    ``findings`` are the lane's in-scope findings (the ones it would classify).
    ``observed`` is everything the scanner reported before diff scoping, so a
    named rule that fired on an unchanged fixture line still counts as fired.
    """
    items = list(findings)
    if fixtures is None:
        return Verdict(kept=items, expected=[], missing=[])
    kept: list[Any] = []
    expected: list[Any] = []
    fired: set[tuple[str, str]] = {
        (f.path, f.rule)
        for f in observed
        if fixtures.covers(f.path) and f.rule in fixtures.expected(f.path, lane)
    }
    for finding in items:
        if fixtures.covers(finding.path) and finding.rule in fixtures.expected(finding.path, lane):
            expected.append(finding)
            fired.add((finding.path, finding.rule))
        else:
            kept.append(finding)
    covered = set(scanned)
    missing = [
        (path, rule)
        for path in fixtures.expected_paths(lane)
        if path in covered
        for rule in sorted(fixtures.expected(path, lane))
        if (path, rule) not in fired
    ]
    return Verdict(kept=kept, expected=expected, missing=missing)


def repo_slug(repo: Path) -> str:
    """owner/name from the origin URL, or ``local/<dir>`` when there is none."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    parts = proc.stdout.strip().rstrip("/").removesuffix(".git").replace(":", "/").split("/")
    if proc.returncode == 0 and len(parts) >= 2 and parts[-1] and parts[-2]:
        return f"{parts[-2]}/{parts[-1]}"
    return f"local/{repo.name}"


# --- Bandit (ops/scripts/run_pr_security.sh) --------------------------------


@dataclass(frozen=True)
class _BanditFinding:
    rule: str
    path: str
    line: int
    severity: str


def bandit_findings(report: Mapping[str, Any], repo: Path) -> list[_BanditFinding]:
    root = repo.resolve()
    out: list[_BanditFinding] = []
    for result in report.get("results") or []:
        raw = Path(str(result.get("filename") or ""))
        try:
            rel = raw.resolve().relative_to(root).as_posix() if raw.is_absolute() else raw
        except ValueError:
            rel = raw.as_posix()
        out.append(
            _BanditFinding(
                rule=str(result.get("test_id") or ""),
                path=str(rel).removeprefix("./"),
                line=int(result.get("line_number") or 0),
                severity=str(result.get("issue_severity") or ""),
            )
        )
    return out


def _cli_split(args: argparse.Namespace) -> int:
    """Print the given repo-relative paths that lie under a fixture root."""
    fixtures = load(Path(args.manifest)).for_repo(repo_slug(Path(args.repo)))
    if fixtures is not None:
        for path in args.paths:
            if fixtures.covers(path):
                print(path)
    return 0


def _cli_bandit(args: argparse.Namespace) -> int:
    """Judge a Bandit JSON report of fixture files. 0 pass, 1 fail."""
    repo = Path(args.repo)
    fixtures = load(Path(args.manifest)).for_repo(repo_slug(repo))
    report = json.loads(Path(args.report).read_text(encoding="utf-8") or "{}")
    scanned = [p.removeprefix("./") for p in args.scanned]
    verdict = evaluate(fixtures, "bandit", bandit_findings(report, repo), scanned)
    for item in verdict.expected:
        print(f"EXPECTED: {item.path}:{item.line}: {item.rule} (declared fixture)")
    for item in verdict.kept:
        print(f"BLOCK: {item.path}:{item.line}: {item.rule} [{item.severity}] (not declared)")
    for path, rule in verdict.missing:
        print(f"BLOCK: {path}: {MISSING_RULE}: declared {rule} did not fire")
    return 1 if verdict.kept or verdict.missing else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", default=str(MANIFEST))
    sub = parser.add_subparsers(dest="command", required=True)
    split = sub.add_parser("split", help="paths under a declared fixture root")
    split.add_argument("--repo", required=True)
    split.add_argument("paths", nargs="*")
    split.set_defaults(func=_cli_split)
    bandit = sub.add_parser("bandit", help="judge a Bandit JSON report of fixture files")
    bandit.add_argument("--repo", required=True)
    bandit.add_argument("--report", required=True)
    bandit.add_argument("scanned", nargs="*", help="repo-relative fixture paths scanned")
    bandit.set_defaults(func=_cli_bandit)
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except FixtureManifestError as exc:
        print(f"BLOCK: expect-fail fixture manifest is invalid: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
