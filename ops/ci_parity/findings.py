"""One finding shape for every CI-parity scanner, filtered to changed lines.

Each parser turns a tool's native output into `Finding`s with repo-relative
paths. `changed_ranges` reads `git diff -U0` so `new_findings` keeps only
findings that land on lines this change touched — the local equivalent of
CodeQL's pr-diff-range and Semgrep's baseline diff. Without that filter every
scanner reports the repository's existing debt on every run and nobody reads it.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

#: Whole-file sentinel for untracked or newly added files.
WHOLE_FILE = (1, 10**9)
SEVERITIES = ("error", "warning", "note")


@dataclass(frozen=True)
class Finding:
    tool: str
    rule: str
    severity: str
    path: str
    line: int
    message: str
    security_severity: float = 0.0
    #: Other locations of a data-flow result (source, steps). CodeQL's PR
    #: diff-informed analysis keeps a result when ANY of them is in the diff.
    related: tuple[tuple[str, int], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["related"] = [list(loc) for loc in self.related]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Finding:
        clean = dict(data)
        clean["related"] = tuple((str(p), int(n)) for p, n in clean.get("related") or ())
        return cls(**clean)

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.severity}] {self.rule} — {self.message}"


def _norm_severity(raw: object) -> str:
    text = str(raw or "").lower()
    if text in ("error", "critical", "high", "fatal"):
        return "error"
    if text in ("warning", "medium", "moderate", "warn"):
        return "warning"
    return "note"


def normalize_path(raw: str, repo_root: Path, scanned: Sequence[str] = ()) -> str:
    """Repo-relative path for a scanner-reported location."""
    text = raw.removeprefix("file://")
    path = Path(text)
    if path.is_absolute():
        try:
            return path.resolve().relative_to(repo_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
    text = path.as_posix().removeprefix("./")
    if (repo_root / text).exists():
        return text
    for candidate in scanned:
        if candidate == text or candidate.endswith("/" + text):
            return candidate
    return text


# --- parsers ---------------------------------------------------------------


def parse_sarif(
    data: dict[str, Any], tool: str, repo_root: Path, scanned: Sequence[str] = ()
) -> list[Finding]:
    out: list[Finding] = []
    for run in data.get("runs") or []:
        driver = ((run.get("tool") or {}).get("driver")) or {}
        rules = {r.get("id"): r for r in driver.get("rules") or [] if isinstance(r, dict)}
        for result in run.get("results") or []:
            rule_id = str(result.get("ruleId") or (result.get("rule") or {}).get("id") or "")
            rule = rules.get(rule_id) or {}
            level = result.get("level") or (rule.get("defaultConfiguration") or {}).get("level")
            sec = (rule.get("properties") or {}).get("security-severity")
            try:
                security = float(sec) if sec is not None else 0.0
            except (TypeError, ValueError):
                security = 0.0
            locations = result.get("locations") or []
            physical = (locations[0].get("physicalLocation") if locations else None) or {}
            flow_nodes = [
                (loc.get("location") or {}).get("physicalLocation") or {}
                for flow in result.get("codeFlows") or []
                for thread in flow.get("threadFlows") or []
                for loc in thread.get("locations") or []
            ]
            flow_nodes += [
                r.get("physicalLocation") or {} for r in result.get("relatedLocations") or []
            ]
            if not physical and flow_nodes:
                physical = flow_nodes[0]
            uri = ((physical.get("artifactLocation") or {}).get("uri")) or ""
            line = int(((physical.get("region") or {}).get("startLine")) or 1)
            related = tuple(
                (
                    normalize_path(
                        str((node.get("artifactLocation") or {}).get("uri")), repo_root, scanned
                    ),
                    int((node.get("region") or {}).get("startLine") or 1),
                )
                for node in flow_nodes
                if (node.get("artifactLocation") or {}).get("uri")
            )
            message = str((result.get("message") or {}).get("text") or rule_id).splitlines()[0]
            out.append(
                Finding(
                    tool=tool,
                    rule=rule_id,
                    severity=_norm_severity(level or "warning"),
                    path=normalize_path(uri, repo_root, scanned),
                    line=line,
                    message=message[:300],
                    security_severity=security,
                    related=related,
                )
            )
    return out


def parse_shellcheck(text: str, repo_root: Path, scanned: Sequence[str] = ()) -> list[Finding]:
    data = json.loads(text or "{}")
    comments = data.get("comments", data) if isinstance(data, dict) else data
    return [
        Finding(
            tool="shellcheck",
            rule=f"SC{c.get('code')}",
            severity=_norm_severity(c.get("level")),
            path=normalize_path(str(c.get("file") or ""), repo_root, scanned),
            line=int(c.get("line") or 1),
            message=str(c.get("message") or "")[:300],
        )
        for c in comments or []
    ]


def parse_actionlint(text: str, repo_root: Path, scanned: Sequence[str] = ()) -> list[Finding]:
    items = json.loads(text or "[]") or []
    return [
        Finding(
            tool="actionlint",
            rule=str(i.get("kind") or "actionlint"),
            severity="error",
            path=normalize_path(str(i.get("filepath") or ""), repo_root, scanned),
            line=int(i.get("line") or 1),
            message=str(i.get("message") or "")[:300],
        )
        for i in items
    ]


_YAMLLINT = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):\d+: \[(?P<sev>\w+)\] (?P<msg>.*?)(?: \((?P<rule>[\w-]+)\))?$"
)


def parse_yamllint(text: str, repo_root: Path, scanned: Sequence[str] = ()) -> list[Finding]:
    out: list[Finding] = []
    for raw in (text or "").splitlines():
        m = _YAMLLINT.match(raw.strip())
        if m:
            out.append(
                Finding(
                    tool="yamllint",
                    rule=m.group("rule") or "syntax",
                    severity=_norm_severity(m.group("sev")),
                    path=normalize_path(m.group("path"), repo_root, scanned),
                    line=int(m.group("line")),
                    message=m.group("msg")[:300],
                )
            )
    return out


def parse_ruff(text: str, repo_root: Path, scanned: Sequence[str] = ()) -> list[Finding]:
    return [
        Finding(
            tool="ruff",
            rule=str(i.get("code") or "ruff"),
            severity="warning",
            path=normalize_path(str(i.get("filename") or ""), repo_root, scanned),
            line=int((i.get("location") or {}).get("row") or 1),
            message=str(i.get("message") or "")[:300],
        )
        for i in json.loads(text or "[]") or []
    ]


def osv_vulnerabilities(data: dict[str, Any]) -> set[tuple[str, str, str]]:
    """{(lockfile, package@version, vuln id)} from `osv-scanner --format json`."""
    found: set[tuple[str, str, str]] = set()
    for result in data.get("results") or []:
        source = str((result.get("source") or {}).get("path") or "")
        for pkg in result.get("packages") or []:
            info = pkg.get("package") or {}
            ident = f"{info.get('name')}@{info.get('version')}"
            for vuln in pkg.get("vulnerabilities") or []:
                found.add((Path(source).name, ident, str(vuln.get("id"))))
    return found


# --- changed lines ---------------------------------------------------------

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(?P<start>\d+)(?:,(?P<count>\d+))? @@")


def parse_unified_diff(text: str) -> dict[str, list[tuple[int, int]]]:
    ranges: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = None if target == "/dev/null" else target.removeprefix("b/")
            if current is not None:
                ranges.setdefault(current, [])
            continue
        m = _HUNK.match(line)
        if m and current is not None:
            start = int(m.group("start"))
            count = int(m.group("count")) if m.group("count") is not None else 1
            if count > 0:
                ranges[current].append((start, start + count - 1))
    return ranges


def changed_ranges(
    repo_root: Path, base: str, head: str | None
) -> dict[str, list[tuple[int, int]]]:
    """Lines added or modified in base..head (head None = working tree vs base)."""
    args = ["git", "-C", str(repo_root), "diff", "-U0", "--no-color", "--no-ext-diff", base]
    if head:
        args.append(head)
    proc = subprocess.run(args, capture_output=True, text=True, check=True)
    ranges = parse_unified_diff(proc.stdout)
    if head is None:
        untracked = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--others", "--exclude-standard"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
        for rel in untracked:
            ranges[rel] = [WHOLE_FILE]
    return ranges


def new_findings(
    findings: Iterable[Finding], ranges: dict[str, list[tuple[int, int]]]
) -> list[Finding]:
    def touched(path: str, line: int) -> bool:
        return any(lo <= line <= hi for lo, hi in ranges.get(path) or ())

    return [
        f for f in findings if touched(f.path, f.line) or any(touched(p, n) for p, n in f.related)
    ]


def blocks(
    finding: Finding, block: Sequence[str], mapped_rules: frozenset[str] = frozenset()
) -> bool:
    """Whether a NEW finding blocks under a lane's `block` list."""
    if "error" in block and finding.severity == "error":
        return True
    if "security-high" in block and finding.security_severity >= 7.0:
        return True
    if "unmapped-rule" in block and finding.rule not in mapped_rules:
        return True
    return "new-vulnerability" in block and finding.tool == "osv-scanner"
