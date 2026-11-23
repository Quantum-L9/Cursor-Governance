#!/usr/bin/env python3
"""Tell CI trouble from code trouble on one pull request: ``l9.ci-triage/v1``.

A coordinator spent a dozen calls per red check working out whether the PR
broke something or CI did. The answers come in a few recognisable shapes:

  billing         the job never started: account payments failed or the
                  spending limit was reached (job annotation)
  infra           runner, checkout or network failures; the job never really ran
  stale_baseline  a gate failed because a baseline entry no longer occurs
  gate_config     a gate summary line names a baseline or detector set, not code
  scope_unknown   the scope gate could not place a changed path
  code            ruff / pytest / pyright / semgrep / BAN-style findings that
                  name files
  pass, pending, unknown

Evidence is read cheapest first: check-run annotations, then the check run's
own output (title, summary, text), and the job log only when neither decides.
Every verdict carries a one-line evidence quote and the failing paths it found.

``owner_hint`` says where to look: ``this_pr`` when a failing path is in the PR
diff, ``base`` when the same check fails on the base branch head, otherwise
``unknown``.

Read-only advice over REST (``gh api``), never GraphQL. It grants nothing: the
output carries ``grants_permission: false`` and decides no merge, retry or
waiver.

Usage:
  ci_triage.py classify --repo O/N --pr N [--sha S] [--json]

Offline / tests: L9_CI_TRIAGE_FIXTURE=<json file> maps each REST path (as
passed to ``gh api``) to its recorded payload; a string value is a raw log.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent.parent
for _path in (str(_HERE), str(_ROOT / "ops" / "scripts")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from merge_gate import _gh_json  # noqa: E402
from pr_board import _latest_check_runs  # noqa: E402

SCHEMA = "l9.ci-triage/v1"
FIXTURE_ENV = "L9_CI_TRIAGE_FIXTURE"
GH_TIMEOUT_SECONDS = 60
LOG_TAIL_BYTES = 400_000
EVIDENCE_MAX = 200
MAX_FILE_PAGES = 30

PASS = "pass"
PENDING = "pending"
BILLING = "billing"
INFRA = "infra"
GATE_CONFIG = "gate_config"
STALE_BASELINE = "stale_baseline"
SCOPE_UNKNOWN = "scope_unknown"
CODE = "code"
UNKNOWN = "unknown"
VERDICTS = (
    PASS,
    PENDING,
    BILLING,
    INFRA,
    GATE_CONFIG,
    STALE_BASELINE,
    SCOPE_UNKNOWN,
    CODE,
    UNKNOWN,
)

PASSING_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})
FAILING_CONCLUSIONS = frozenset(
    {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale"}
)

# Signatures, tried in this order against each evidence line (lower-cased).
# The order is the precedence: a job that never started is billing even if a
# later step would have failed on code.
_SIGNATURES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    (
        BILLING,
        (
            re.compile(r"recent account payments have failed"),
            re.compile(r"spending limit needs to be increased"),
        ),
    ),
    (
        INFRA,
        (
            re.compile(r"the runner has received a shutdown signal"),
            re.compile(r"lost communication with the server"),
            re.compile(r"no space left on device"),
            re.compile(r"could not resolve host"),
            re.compile(r"fatal: unable to access 'https?://"),
            re.compile(r"connection (?:reset|refused|timed out)"),
            re.compile(r"econnreset|etimedout|eai_again"),
            re.compile(r"\b(?:502|503|504) (?:bad gateway|service unavailable|gateway time-?out)"),
            re.compile(r"unable to find image .* locally.*(?:error|denied)"),
            re.compile(r"the hosted runner .* (?:lost|encountered an error)"),
            re.compile(r"waiting for a runner to pick up this job"),
            re.compile(r"the job was not started"),
        ),
    ),
    (STALE_BASELINE, (re.compile(r"stale baseline entry"),)),
    (
        GATE_CONFIG,
        (
            re.compile(r"(?:❌|✗|✘).*\bbaseline\b"),
            re.compile(r"(?:❌|✗|✘)\s*audit class detectors"),
            re.compile(r"(?:❌|✗|✘).*\bgate config"),
            # l9-ci-core expense guard: its static judge cannot classify the
            # repository's own Makefile / pytest invocation (CI configuration,
            # not the PR's code).
            re.compile(r"^unknown_script\b.+"),
        ),
    ),
    (
        SCOPE_UNKNOWN,
        (
            re.compile(r"scope is unknown"),
            re.compile(r"pr_fast: unknown path"),
        ),
    ),
)

_PATH = (
    r"(?P<path>(?:[\w.-]+/)*[\w.-]+\.(?:py|pyi|sh|ya?ml|json|toml|cfg|ini|md|js|ts|tsx|xml|csv))"
)
_CODE_LINES: tuple[re.Pattern[str], ...] = (
    # ruff / flake8 / BAN-style: path:line:col: CODE message
    re.compile(_PATH + r":\d+:\d+:\s*(?P<rule>[A-Z]+\d+)\b"),
    # ruff concise output without column, and semgrep-like "path:line: rule"
    re.compile(_PATH + r":\d+:\s*(?P<rule>[A-Z]+\d+)\b"),
    # Pyright output: path:line:col - error: ...
    re.compile(_PATH + r":\d+:\d+\s+-\s+error\b"),
    # pytest
    re.compile(r"\b(?:FAILED|ERROR)\s+" + _PATH + r"(?:::|\s+-)"),
    # BAN rules named after the path: "BAN001 path:line"
    re.compile(r"\b(?P<rule>BAN\d+)\b.*?" + _PATH),
)
_PYTEST_PASSED_ONLY = re.compile(r"\b\d+ passed\b(?!.*\b(?:failed|error|errors)\b)")
_EXIT_CODE = re.compile(r"process completed with exit code (\d+)")
_TIMESTAMP = re.compile(r"^\d{4}-\d\d-\d\dT[\d:.]+Z\s?")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_RUNNER_PREFIX = re.compile(r"^(?:/home/runner/work/[^/]+/[^/]+/|/github/workspace/|\./)")
_JOB_ID = re.compile(r"/job/(\d+)")
# Evidence is quoted from CI output, which can echo a credential GitHub did not
# mask. These shapes are replaced before a quote leaves the tool.
REDACTED = "[REDACTED]"
_SECRET_SHAPES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:gh[pousr]|github_pat)_[A-Za-z0-9_]{20,}"), REDACTED),
    (re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"), REDACTED),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), REDACTED),
    (re.compile(r"\beyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}"), REDACTED),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), REDACTED),
    (re.compile(r"(?i)\b(bearer|basic)\s+[\w.~+/=-]{12,}"), rf"\1 {REDACTED}"),
    (
        re.compile(
            r"(?i)\b([\w.-]*(?:token|secret|password|passwd|api[_-]?key|private[_-]?key)[\w.-]*)"
            r"(\s*[:=]\s*)(['\"]?)[^\s'\"]{4,}\3"
        ),
        rf"\1\2{REDACTED}",
    ),
    (re.compile(r"(?i)\b(https?://)[^/\s:@]+:[^/\s@]+@"), rf"\1{REDACTED}@"),
)


class TriageError(RuntimeError):
    """A REST read the triage cannot do without."""


Fetch = Callable[[str], Any]


def _gh_text(path: str) -> str:
    if not shutil.which("gh"):
        raise RuntimeError("gh not on PATH")
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["gh", "api", path],
            capture_output=True,
            text=True,
            timeout=GH_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f"gh failed: {exc}") from exc
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "gh returned non-zero").strip().splitlines()[-1][:200])
    return proc.stdout


def live_fetch(path: str) -> Any:
    """REST GET through gh api. Log paths return text, everything else JSON."""
    if path.endswith("/logs"):
        return _gh_text(path)
    return _gh_json(["api", path])


def fixture_fetch(fixture: dict[str, Any]) -> Fetch:
    def fetch(path: str) -> Any:
        if path not in fixture:
            raise RuntimeError(f"no fixture for {path}")
        return fixture[path]

    return fetch


def _clean_line(line: str) -> str:
    line = _ANSI.sub("", line.rstrip("\r"))
    line = _TIMESTAMP.sub("", line)
    for prefix in ("##[error]", "##[warning]", "##[group]", "##[endgroup]"):
        if line.startswith(prefix):
            line = line[len(prefix) :]
    return line.strip()


def redact(text: str) -> str:
    """Replace credential-shaped substrings, keeping a key name for context."""
    for pattern, replacement in _SECRET_SHAPES:
        text = pattern.sub(replacement, text)
    return text


def _quote(line: str) -> str:
    line = redact(" ".join(line.split()))
    return line if len(line) <= EVIDENCE_MAX else line[: EVIDENCE_MAX - 1] + "…"


def _normalise_path(path: str) -> str:
    return _RUNNER_PREFIX.sub("", path)


def code_paths(lines: Iterable[str]) -> tuple[list[str], str | None]:
    """Failing paths named by code-finding lines, and the first such line."""
    paths: list[str] = []
    first: str | None = None
    for line in lines:
        for pattern in _CODE_LINES:
            match = pattern.search(line)
            if match:
                path = _normalise_path(match.group("path"))
                if path not in paths:
                    paths.append(path)
                first = first or line
                break
    return paths, first


def classify_lines(lines: list[str]) -> tuple[str, str, list[str]] | None:
    """(verdict, evidence, paths) for one evidence source, or None if undecided."""
    cleaned = [c for c in (_clean_line(line) for line in lines) if c]
    for verdict, patterns in _SIGNATURES:
        for line in cleaned:
            low = line.lower()
            if any(p.search(low) for p in patterns):
                paths, _ = code_paths(cleaned)
                return verdict, _quote(line), paths
    paths, first = code_paths(cleaned)
    if first is not None:
        return CODE, _quote(first), paths
    return None


def _exit_only_verdict(lines: list[str]) -> tuple[str, str, list[str]] | None:
    """A failed job log that names no finding.

    Tests passed and nothing failed, yet the job exited non-zero: the reason
    was written somewhere other than the log (the PR-fast scope gate puts it in
    an artifact). Otherwise only the exit code is known.
    """
    cleaned = [c for c in (_clean_line(line) for line in lines) if c]
    exits = [
        line for line in cleaned if (m := _EXIT_CODE.search(line.lower())) and m.group(1) != "0"
    ]
    if not exits:
        return None
    passed = [line for line in cleaned if _PYTEST_PASSED_ONLY.search(line.lower())]
    if passed:
        return (
            SCOPE_UNKNOWN,
            _quote(f"{passed[-1]} then {exits[-1]} (reason not in the log)"),
            [],
        )
    return UNKNOWN, _quote(exits[-1]), []


def _annotation_lines(annotations: Any) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    paths: list[str] = []
    for item in annotations if isinstance(annotations, list) else []:
        if not isinstance(item, dict):
            continue
        message = str(item.get("message") or "")
        title = str(item.get("title") or "")
        path = str(item.get("path") or "")
        level = str(item.get("annotation_level") or "")
        for text in (title, *message.splitlines()):
            if text.strip():
                lines.append(text)
        # GitHub puts job-level annotations on the placeholder path ".github".
        if level == "failure" and path and path != ".github":
            normalised = _normalise_path(path)
            if normalised not in paths:
                paths.append(normalised)
    return lines, paths


def _output_lines(run: dict[str, Any]) -> list[str]:
    output = run.get("output")
    if not isinstance(output, dict):
        return []
    lines: list[str] = []
    for key in ("title", "summary", "text"):
        value = output.get(key)
        if isinstance(value, str):
            lines.extend(value.splitlines())
    return lines


def _job_id(run: dict[str, Any]) -> str | None:
    app = run.get("app")
    if not isinstance(app, dict) or app.get("slug") != "github-actions":
        return None
    match = _JOB_ID.search(str(run.get("details_url") or ""))
    if match:
        return match.group(1)
    return str(run["id"]) if run.get("id") is not None else None


def classify_run(repo: str, run: dict[str, Any], fetch: Fetch) -> dict[str, Any]:
    """Verdict, evidence and failing paths for one check run."""
    status = str(run.get("status") or "")
    conclusion = run.get("conclusion")
    if status != "completed" or not conclusion:
        return {
            "verdict": PENDING,
            "evidence": _quote(f"status {status or 'unknown'}"),
            "failing_paths": [],
        }
    conclusion = str(conclusion)
    if conclusion in PASSING_CONCLUSIONS:
        return {
            "verdict": PASS,
            "evidence": _quote(f"conclusion {conclusion}"),
            "failing_paths": [],
        }

    ann_lines: list[str] = []
    ann_paths: list[str] = []
    run_id = run.get("id")
    if run_id is not None:
        try:
            annotations = fetch(f"repos/{repo}/check-runs/{run_id}/annotations?per_page=100")
        except RuntimeError:
            annotations = []
        ann_lines, ann_paths = _annotation_lines(annotations)

    decided = classify_lines(ann_lines)
    if decided is None and ann_paths:
        first = next((line for line in ann_lines if line.strip()), "failure annotation")
        decided = (CODE, _quote(first), [])
    if decided is None:
        decided = classify_lines(_output_lines(run))
    if decided is None and conclusion in {"startup_failure", "cancelled", "timed_out"}:
        decided = (INFRA, _quote(f"conclusion {conclusion}"), [])
    if decided is None:
        job = _job_id(run)
        if job is not None:
            try:
                log = fetch(f"repos/{repo}/actions/jobs/{job}/logs")
            except RuntimeError as exc:
                log = None
                decided = (UNKNOWN, _quote(f"job log unavailable: {exc}"), [])
            if isinstance(log, str):
                lines = log[-LOG_TAIL_BYTES:].splitlines()
                decided = classify_lines(lines) or _exit_only_verdict(lines)
    if decided is None:
        decided = (UNKNOWN, _quote(f"conclusion {conclusion}; no recognised signature"), [])

    verdict, evidence, paths = decided
    merged = list(paths)
    for path in ann_paths:
        if path not in merged:
            merged.append(path)
    return {"verdict": verdict, "evidence": evidence, "failing_paths": merged}


def _pr_files(repo: str, pr: int, fetch: Fetch) -> set[str]:
    files: set[str] = set()
    for page in range(1, MAX_FILE_PAGES + 1):
        payload = fetch(f"repos/{repo}/pulls/{pr}/files?per_page=100&page={page}")
        if not isinstance(payload, list):
            break
        for item in payload:
            if isinstance(item, dict):
                for key in ("filename", "previous_filename"):
                    if item.get(key):
                        files.add(str(item[key]))
        if len(payload) < 100:
            break
    return files


def _check_runs(repo: str, sha: str, fetch: Fetch) -> list[dict[str, Any]]:
    payload = fetch(f"repos/{repo}/commits/{sha}/check-runs?per_page=100")
    runs = (payload or {}).get("check_runs") if isinstance(payload, dict) else None
    return _latest_check_runs(runs or [])


def _base_head(repo: str, pull: dict[str, Any], fetch: Fetch) -> str | None:
    raw = pull.get("base")
    base: dict[str, Any] = raw if isinstance(raw, dict) else {}
    ref = base.get("ref")
    if ref:
        try:
            branch = fetch(f"repos/{repo}/branches/{ref}")
        except RuntimeError:
            branch = None
        commit = branch.get("commit") if isinstance(branch, dict) else None
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if sha:
            return str(sha)
    sha = base.get("sha")
    return str(sha) if sha else None


def classify(
    repo: str, pr: int, sha: str | None = None, fetch: Fetch = live_fetch
) -> dict[str, Any]:
    """The ``l9.ci-triage/v1`` document for one PR."""
    try:
        pull = fetch(f"repos/{repo}/pulls/{pr}")
    except RuntimeError as exc:
        raise TriageError(f"pull request read failed: {exc}") from exc
    if not isinstance(pull, dict):
        raise TriageError("pull request read returned no object")
    head = sha or ((pull.get("head") or {}).get("sha"))
    if not head:
        raise TriageError("pull request has no head sha")
    try:
        runs = _check_runs(repo, str(head), fetch)
    except RuntimeError as exc:
        raise TriageError(f"check-runs read failed: {exc}") from exc
    try:
        diff = _pr_files(repo, pr, fetch)
    except RuntimeError:
        diff = set()

    base_failing: set[str] | None = None

    def failing_on_base(name: str) -> bool:
        nonlocal base_failing
        if base_failing is None:
            base_failing = set()
            base_sha = _base_head(repo, pull, fetch)
            if base_sha:
                try:
                    for run in _check_runs(repo, base_sha, fetch):
                        if str(run.get("conclusion") or "") in FAILING_CONCLUSIONS:
                            base_failing.add(str(run.get("name") or ""))
                except RuntimeError:
                    pass
        return name in base_failing

    checks: list[dict[str, Any]] = []
    for run in sorted(runs, key=lambda r: str(r.get("name") or "")):
        name = str(run.get("name") or "")
        result = classify_run(repo, run, fetch)
        owner = "unknown"
        if result["verdict"] not in (PASS, PENDING):
            if any(path in diff for path in result["failing_paths"]):
                owner = "this_pr"
            elif failing_on_base(name):
                owner = "base"
        checks.append(
            {
                "name": name,
                "conclusion": run.get("conclusion"),
                "verdict": result["verdict"],
                "evidence": result["evidence"],
                "failing_paths": result["failing_paths"],
                "owner_hint": owner,
            }
        )
    return {
        "schema": SCHEMA,
        "repo": repo,
        "pr": pr,
        "head": str(head),
        "grants_permission": False,
        "checks": checks,
    }


def _fetch_from_env() -> Fetch:
    fixture = os.environ.get(FIXTURE_ENV)
    if not fixture:
        return live_fetch
    return fixture_fetch(json.loads(Path(fixture).read_text(encoding="utf-8")))


def _render_text(doc: dict[str, Any]) -> str:
    lines = [f"{doc['repo']}#{doc['pr']} @ {doc['head'][:12]}  (grants_permission: false)"]
    for check in doc["checks"]:
        paths = ", ".join(check["failing_paths"][:5])
        lines.append(
            f"  {check['verdict']:<15} {check['owner_hint']:<8} {check['name']}"
            + (f"  [{paths}]" if paths else "")
        )
        if check["verdict"] not in (PASS, PENDING):
            lines.append(f"      {check['evidence']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "ci_triage").splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    cls = sub.add_parser("classify", help="classify every check on a PR head")
    cls.add_argument("--repo", required=True, help="owner/name")
    cls.add_argument("--pr", required=True, type=int)
    cls.add_argument("--sha", help="head sha to classify (default: the PR head)")
    cls.add_argument("--json", action="store_true", help="emit l9.ci-triage/v1 JSON")
    args = parser.parse_args(argv)
    try:
        doc = classify(args.repo, args.pr, args.sha, _fetch_from_env())
    except (TriageError, OSError, json.JSONDecodeError) as exc:
        print(f"ci_triage: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(doc, indent=2, ensure_ascii=False) if args.json else _render_text(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
