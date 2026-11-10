"""Publish L9 reports: GMP reports onto the open PR, end-session handoffs to their owners.

One owner for report rendering and placement, so the GMP executor and the
end-session handoff hooks cannot drift apart:

    reports/
      gmp/                              GMP execution reports (committed with the work)
      end-session/
        session-handoff/                legacy location; handoffs are no longer committed
        governance-handoff/             legacy location; handoffs are no longer committed

End-session handoffs are delivered, never committed (``ops/reports/handoff_delivery.py``):
the session handoff (l9.session_handoff.v1) becomes one PR comment, edited in
place on later publications of the same PR; the governance handoff
(l9.governance_handoff.v1) goes to the Cursor-Governance friction intake, one
issue per friction id, with a PR comment as the fallback. A local copy is kept
under the git directory. The PR head never moves for a handoff.

GMP report publication commits ONLY the report paths it was handed (``git commit -- <paths>``
after ``git add -f -- <paths>``: ``reports/`` is commonly gitignored as local
scratch, and these reports are deliberately published) and pushes the current
branch to the PR's head branch without force. It refuses, and says why, when the
checkout is not on that branch, is detached, or is on a default branch. It never
rewrites history and never touches a path it was not given.

``L9_REPORT_PUBLISH`` selects how far a GMP report goes: ``push`` (default),
``commit`` (commit locally, no push) or ``write`` / ``0`` (write the file only).

CLI (any surface, e.g. Cursor or a manual ``/end-session``)::

    python -m ops.reports.publish dirs --workspace <repo>
    python -m ops.reports.publish handoffs --workspace <repo>    # deliver, never commit
    python -m ops.reports.publish next-gmp-id --workspace <repo>
    python -m ops.reports.publish gmp --workspace <repo> <GMP-Report-NNN-Name.md>...
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

REPORTS_DIR = Path("reports")
PR_SUMMARY_REL = Path(".l9") / "pr" / "pr-summary.json"
DEFAULT_BRANCHES = frozenset({"main", "master", "develop", "trunk"})
PUBLISH_ENV = "L9_REPORT_PUBLISH"
#: Per git call. The callers are Stop hooks with 60-90 s timeouts, so a hung
#: remote must fail fast and be reported, never stall the hook into a kill.
GIT_TIMEOUT_S = float(os.environ.get("L9_REPORT_GIT_TIMEOUT") or 20)
PUSH_ATTEMPTS = 2


class ReportKind(StrEnum):
    GMP = "gmp"
    SESSION_HANDOFF = "session-handoff"
    GOVERNANCE_HANDOFF = "governance-handoff"


#: The only place the layout is spelled.
SUBDIRS: dict[ReportKind, Path] = {
    ReportKind.GMP: REPORTS_DIR / "gmp",
    ReportKind.SESSION_HANDOFF: REPORTS_DIR / "end-session" / "session-handoff",
    ReportKind.GOVERNANCE_HANDOFF: REPORTS_DIR / "end-session" / "governance-handoff",
}

TITLES: dict[ReportKind, str] = {
    ReportKind.GMP: "GMP report",
    ReportKind.SESSION_HANDOFF: "Session handoff",
    ReportKind.GOVERNANCE_HANDOFF: "Governance handoff",
}


# --- Layout --------------------------------------------------------------------


def report_dir(root: Path, kind: ReportKind) -> Path:
    """``<root>/reports/<subdir>`` for ``kind``, created when absent."""
    path = Path(root) / SUBDIRS[kind]
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_layout(root: Path) -> list[Path]:
    return [report_dir(root, kind) for kind in ReportKind]


def slugify(text: str, limit: int = 40) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower())[:limit].strip("-")


def handoff_filename(pr_number: int, head_sha: str, when: datetime | None = None) -> str:
    """``<YYYY-MM-DD>-pr<N>-<sha12>.md`` — one file per publication."""
    stamp = (when or datetime.now(UTC)).strftime("%Y-%m-%d")
    sha = re.sub(r"[^0-9a-f]", "", head_sha.lower())[:12] or "nohead"
    return f"{stamp}-pr{int(pr_number)}-{sha}.md"


def clean_markdown(text: str) -> str:
    """No trailing whitespace, exactly one final newline (formatter-stable)."""
    lines = [line.rstrip() for line in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


# --- L9_META (consumer contract C-18) -------------------------------------------
#
# Repositories that adopt L9_META headers (contract C-18, e.g.
# Cognitive.Engine.Graphs ``docs/contracts/L9_META_HEADERS.md``) fail CI on a
# tracked markdown file without one. A report published there must carry the
# repository's own header, or every publication turns the PR red. The header is
# never invented: its fields are copied from markdown the repository already
# headers, and a repository with no such file gets no header at all.

#: Schema-1 fields, in contract order.
L9_META_FIELDS = ("l9_schema", "origin", "engine", "layer", "tags", "owner", "status")
#: The markdown header form, at the top of the file.
_L9_META_BLOCK = re.compile(r"\A<!-- L9_META\n(?P<body>.*?)\n/L9_META -->\n", re.DOTALL)
#: Files read while looking for the repository's header (the callers are Stop hooks).
L9_META_SCAN_LIMIT = 200
_L9_META_READ_BYTES = 4096

L9_META_TAGS: dict[ReportKind, str] = {
    ReportKind.GMP: "gmp-report",
    ReportKind.SESSION_HANDOFF: "session-handoff",
    ReportKind.GOVERNANCE_HANDOFF: "governance-handoff",
}


def l9_meta_fields(text: str) -> dict[str, str] | None:
    """The schema-1 L9_META fields ``text`` opens with, or None."""
    match = _L9_META_BLOCK.match(text)
    if not match:
        return None
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            return None
        fields[key.strip()] = value.strip()
    return fields if tuple(fields) == L9_META_FIELDS else None


def _tracked_markdown(root: Path) -> list[Path]:
    try:
        proc = _git(root, "ls-files", "-z", "--", "*.md")
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return [root / rel for rel in sorted(proc.stdout.split("\0")) if rel]


def repository_l9_meta(root: Path, exclude: Path | None = None) -> dict[str, str] | None:
    """The L9_META convention ``root`` already uses for markdown, or None.

    Report siblings under ``reports/`` are consulted first, then tracked
    markdown; the first schema-1 header found wins (sorted, bounded scan).
    """
    root = Path(root)
    reports = root / REPORTS_DIR
    siblings = sorted(reports.rglob("*.md")) if reports.is_dir() else []
    seen: set[Path] = set()
    for path in [*siblings, *_tracked_markdown(root)]:
        if len(seen) >= L9_META_SCAN_LIMIT:
            break
        if path in seen or (exclude is not None and path == exclude):
            continue
        seen.add(path)
        try:
            with path.open(encoding="utf-8", errors="replace") as fh:
                head = fh.read(_L9_META_READ_BYTES)
        except OSError:
            continue
        fields = l9_meta_fields(head)
        if fields is not None:
            return fields
    return None


def l9_meta_header(fields: dict[str, str], kind: ReportKind) -> str:
    """A report's header in the repository's convention; layer and tag are the report's own."""
    values = {**fields, "layer": "[reports]", "tags": f"[{L9_META_TAGS[kind]}]"}
    body = [f"{key}: {values[key]}" for key in L9_META_FIELDS]
    return "\n".join(["<!-- L9_META", *body, "/L9_META -->"])


def write_report(root: Path, kind: ReportKind, filename: str, text: str) -> Path:
    if Path(filename).name != filename or not filename.endswith(".md"):
        raise ValueError(f"report filename must be a bare *.md name, got {filename!r}")
    path = report_dir(root, kind) / filename
    text = clean_markdown(text)
    if l9_meta_fields(text) is None:
        fields = repository_l9_meta(root, exclude=path)
        if fields is not None:
            # The consumer's injector form: header, one blank line, body.
            text = l9_meta_header(fields, kind) + "\n\n" + text.lstrip("\n")
    path.write_text(text, encoding="utf-8")
    return path


# --- Rendering -----------------------------------------------------------------


_KEY = re.compile(r"[A-Za-z][A-Za-z _-]{0,39}")


def lines_to_markdown(lines: Iterable[str]) -> list[str]:
    """Convert the handoff renderers' ``key: value`` / ``key:`` + ``  - item`` text.

    The renderers in ``ops/memory`` stay the single source of the content; this
    only changes its typography so it reads as markdown on GitHub.
    """
    out: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        stripped = line.lstrip()
        if not stripped:
            continue
        if stripped.startswith("- "):
            out.append(stripped)
            continue
        head, sep, value = stripped.partition(":")
        if sep and not value.strip():
            out += ["", f"## {head.strip().capitalize()}", ""]
        elif sep and _KEY.fullmatch(head.strip()):
            out += ["", f"**{head.strip()}:** {value.strip()}"]
        else:
            out += ["", stripped]
    return out


def render_report(
    kind: ReportKind,
    *,
    subject: str,
    meta: dict[str, Any],
    body_lines: Iterable[str],
) -> str:
    """A complete markdown report: title, metadata table, converted body."""
    lines = [f"# {TITLES[kind]} — {subject}", "", "| Field | Value |", "|---|---|"]
    for key, value in meta.items():
        if value in (None, ""):
            continue
        cell = str(value).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {key} | {cell} |")
    lines += lines_to_markdown(body_lines)
    return clean_markdown("\n".join(lines))


# --- Publication ---------------------------------------------------------------


@dataclass(frozen=True)
class PublishResult:
    # pushed | committed | unchanged | written | skipped | failed (GMP reports)
    # delivered | fallback | written | failed (end-session handoffs)
    status: str
    detail: str = ""
    commit: str = ""
    urls: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.status in {
            "pushed",
            "committed",
            "unchanged",
            "written",
            "delivered",
            "fallback",
        }

    def line(self, paths: Sequence[Path], root: Path) -> str:
        rels = ", ".join(_rel(p, root) for p in paths)
        tail = f" ({self.detail})" if self.detail else ""
        sha = f" @ {self.commit[:12]}" if self.commit else ""
        where = f" → {', '.join(self.urls)}" if self.urls else ""
        return f"report {self.status}{sha}: {rels}{tail}{where}"


def _rel(path: Path, root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        return str(path)


def _git(
    root: Path, *args: str, timeout: float = GIT_TIMEOUT_S
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
    )


def _first_line(proc: subprocess.CompletedProcess[str]) -> str:
    """The first meaningful output line (git prints its ``hint:`` lines last)."""
    text = [
        line.strip()
        for line in (proc.stderr or proc.stdout or "").splitlines()
        if line.strip() and not line.lstrip().startswith("hint:")
    ]
    return text[0][:240] if text else f"exit {proc.returncode}"


@contextlib.contextmanager
def _publish_lock(root: Path) -> Iterator[None]:
    """Serialize publishers in one clone (the two Stop hooks run in parallel)."""
    proc = _git(root, "rev-parse", "--git-path", "l9-report-publish.lock")
    lock_path = Path(proc.stdout.strip() or ".git/l9-report-publish.lock")
    if not lock_path.is_absolute():
        lock_path = Path(root) / lock_path
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _is_report_file(root: Path, path: Path) -> bool:
    reports = (Path(root) / REPORTS_DIR).resolve()
    target = Path(path) if Path(path).is_absolute() else Path(root) / path
    target = target.resolve()
    return target.is_file() and target.is_relative_to(reports)


def publish_mode() -> str:
    raw = (os.environ.get(PUBLISH_ENV) or "push").strip().lower()
    if raw in {"0", "false", "no", "off", "write"}:
        return "write"
    return "commit" if raw == "commit" else "push"


def publish(
    root: Path,
    paths: Sequence[Path],
    *,
    message: str,
    expected_branch: str = "",
    remote: str = "origin",
    allow_push: bool = True,
) -> PublishResult:
    """Commit exactly ``paths`` and push to ``expected_branch`` (the PR head).

    ``allow_push=False`` commits only: a branch with no open PR is first
    published by ``make pr`` (CANONICAL_LAW §6.2.8), never by this module.
    """
    root = Path(root)
    if not paths:
        return PublishResult("skipped", "no report paths")
    outside = [str(p) for p in paths if not _is_report_file(root, p)]
    if outside:
        # Only report files under <root>/reports/ are ever force-added: a
        # directory or any other path could stage ignored content.
        return PublishResult("failed", f"not a report file under reports/: {', '.join(outside)}")
    mode = publish_mode()
    if mode == "write":
        return PublishResult("written", f"{PUBLISH_ENV}=write: not committed")
    try:
        inside = _git(root, "rev-parse", "--is-inside-work-tree")
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return PublishResult("skipped", "not a git work tree")
        branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
        if not branch:
            return PublishResult("skipped", "detached HEAD: no PR branch to publish to")
        if branch in DEFAULT_BRANCHES:
            return PublishResult("skipped", f"on default branch {branch}: never pushed")
        if expected_branch and branch != expected_branch:
            return PublishResult(
                "skipped", f"checkout is on {branch}, PR head is {expected_branch}"
            )
        rels = [_rel(p, root) for p in paths]
        with _publish_lock(root):
            added = _git(root, "add", "-f", "--", *rels)
            if added.returncode != 0:
                return PublishResult("failed", f"git add: {_first_line(added)}")
            staged = _git(root, "diff", "--cached", "--quiet", "--", *rels)
            if staged.returncode == 0:
                return PublishResult("unchanged", "already committed")
            # Pathspec commit: only these files, whatever else is staged.
            committed = _git(root, "commit", "-m", message, "--", *rels)
            if committed.returncode != 0:
                return PublishResult("failed", f"git commit: {_first_line(committed)}")
            sha = _git(root, "rev-parse", "HEAD").stdout.strip()
            if mode == "commit":
                return PublishResult("committed", f"{PUBLISH_ENV}=commit: not pushed", sha)
            if not allow_push:
                return PublishResult(
                    "committed", f"no open PR for {branch}: make pr publishes it", sha
                )
            return _push(root, branch, remote, sha)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return PublishResult("failed", f"{type(exc).__name__}: {str(exc)[:200]}")


def _push_blocker(root: Path, branch: str, remote: str) -> str:
    """Why pushing HEAD would publish something other than reports, or "".

    The PR head was validated by ``make pr``. A report push may advance it only
    by report files: every path between the remote head and HEAD must sit under
    ``reports/``. Anything else waits for ``make pr`` (PR #806 review).
    """
    listed = _git(root, "ls-remote", remote, f"refs/heads/{branch}")
    if listed.returncode != 0:
        return f"cannot read {remote}/{branch}: {_first_line(listed)}"
    remote_sha = listed.stdout.split()[0] if listed.stdout.strip() else ""
    if not remote_sha:
        return f"{remote}/{branch} does not exist: make pr publishes the branch first"
    if _git(root, "merge-base", "--is-ancestor", remote_sha, "HEAD").returncode != 0:
        return f"{remote}/{branch} moved; fast-forward first (never force)"
    changed = _git(root, "diff", "--name-only", remote_sha, "HEAD").stdout.splitlines()
    others = [p for p in changed if p and not p.startswith(f"{REPORTS_DIR.as_posix()}/")]
    if others:
        return (
            f"{len(others)} non-report path(s) ahead of the PR head (e.g. {others[0]}): "
            "make pr publishes them with the report"
        )
    return ""


def _push(root: Path, branch: str, remote: str, sha: str) -> PublishResult:
    blocker = _push_blocker(root, branch, remote)
    if blocker:
        return PublishResult("committed", f"not pushed — {blocker}", sha)
    last = ""
    for attempt in range(PUSH_ATTEMPTS):
        pushed = _git(root, "push", remote, f"HEAD:refs/heads/{branch}")
        if pushed.returncode == 0:
            return PublishResult("pushed", f"{remote}/{branch}", sha)
        last = _first_line(pushed)
        full = f"{pushed.stderr}\n{pushed.stdout}"
        if any(m in full for m in ("[rejected]", "non-fast-forward", "fetch first")):
            return PublishResult(
                "committed",
                f"push rejected, remote {branch} moved; commit kept locally — "
                "fast-forward and push again (never force)",
                sha,
            )
        time.sleep(2**attempt)
    return PublishResult("committed", f"push failed: {last}; commit kept locally", sha)


# --- Publication receipt -------------------------------------------------------


def pr_summary(root: Path) -> dict[str, Any] | None:
    try:
        data = json.loads((Path(root) / PR_SUMMARY_REL).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("number") else None


# --- End-session handoffs ------------------------------------------------------


def publish_session_handoff(
    root: Path,
    pub: dict[str, Any],
    body_lines: Iterable[str],
    *,
    session_id: str = "",
    agent_id: str = "",
    transport: Any = None,
) -> tuple[Path, PublishResult]:
    """Keep a local copy and post the session handoff as the PR's handoff comment."""
    return _publish_handoff(
        ReportKind.SESSION_HANDOFF,
        root,
        pub,
        body_lines,
        session_id=session_id,
        agent_id=agent_id,
        transport=transport,
    )


def publish_governance_handoff(
    root: Path,
    pub: dict[str, Any],
    body_lines: Iterable[str],
    *,
    session_id: str = "",
    agent_id: str = "",
    friction: Sequence[dict[str, str]] | None = None,
    transport: Any = None,
) -> tuple[Path, PublishResult]:
    """Keep a local copy and send ``friction`` to the Cursor-Governance intake.

    ``friction`` is ``handoff_delivery.friction_items(brief)``. Without items
    there is nothing for the intake (the memory record still carries the brief).
    """
    return _publish_handoff(
        ReportKind.GOVERNANCE_HANDOFF,
        root,
        pub,
        body_lines,
        session_id=session_id,
        agent_id=agent_id,
        friction=friction,
        transport=transport,
    )


def _publish_handoff(
    kind: ReportKind,
    root: Path,
    pub: dict[str, Any],
    body_lines: Iterable[str],
    *,
    session_id: str,
    agent_id: str,
    friction: Sequence[dict[str, str]] | None = None,
    transport: Any = None,
) -> tuple[Path, PublishResult]:
    from ops.reports import handoff_delivery

    number = int(pub["number"])
    head_sha = str(pub.get("head_sha") or "")
    label = str(pub.get("label") or f"{pub.get('repo', '')}#{number}")
    text = render_report(
        kind,
        subject=label,
        meta={
            "Publication": label,
            "PR": pub.get("url") or "",
            "Head branch": pub.get("head") or "",
            "Head SHA": head_sha,
            "Session": session_id,
            "Agent": agent_id,
            "Written": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        body_lines=body_lines,
    )
    # Never committed, so never given an L9_META header and never in the work tree.
    path = handoff_delivery.write_local_copy(
        root, kind.value, handoff_filename(number, head_sha), text
    )
    delivery = handoff_delivery.deliver(
        kind.value,
        pub,
        text,
        friction=friction,
        session_id=session_id,
        agent_id=agent_id,
        transport=transport,
    )
    return path, PublishResult(delivery.status, delivery.detail, urls=delivery.urls)


# --- GMP reports ---------------------------------------------------------------


def current_branch(root: Path) -> str:
    try:
        return _git(root, "symbolic-ref", "--quiet", "--short", "HEAD").stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def publish_gmp_report(root: Path, sources: Sequence[Path]) -> tuple[list[Path], PublishResult]:
    """Place GMP reports in ``reports/gmp/`` and commit them with the work.

    A report written anywhere (scratchpad, repo root, legacy ``reports/``) is
    copied into ``reports/gmp/`` under its own name. It is committed even when
    ``reports/`` is gitignored. It is pushed only when this branch already has
    an open PR (``.l9/pr/pr-summary.json`` names it as head); otherwise the
    commit rides the next ``make pr``.
    """
    from ops.reports import gmp

    root = Path(root).resolve()
    resolved = [Path(s).expanduser().resolve() for s in sources]
    for src in resolved:
        if not src.is_file() or src.suffix != ".md" or not src.name.upper().startswith("GMP"):
            raise ValueError(f"not a GMP markdown report: {src}")
        error = gmp.name_error(src)
        if error:
            raise ValueError(f"{src.name}: {error} (rules/81-gmp-audit.mdc)")
    target_dir = report_dir(root, ReportKind.GMP)
    placed: list[Path] = []
    for src in resolved:
        dest = target_dir / src.name
        if src != dest:
            dest.write_text(clean_markdown(src.read_text(encoding="utf-8")), encoding="utf-8")
            with contextlib.suppress(ValueError):
                # A copy left in the clone (legacy reports/ root) would be a
                # second, untracked SSOT; scratch outside the clone is left alone.
                src.relative_to(root)
                src.unlink()
        placed.append(dest)
    branch = current_branch(root)
    summary = pr_summary(root) or {}
    open_pr = bool(branch) and str(summary.get("head") or "") == branch
    names = ", ".join(p.name for p in placed)
    result = publish(
        root,
        placed,
        message=f"docs(reports): GMP report {names}",
        expected_branch=branch if open_pr else "",
        allow_push=open_pr,
    )
    return placed, result


def _publication_from_summary(root: Path) -> dict[str, Any]:
    summary = pr_summary(root)
    if summary is None:
        raise SystemExit(f"no publication receipt at {Path(root) / PR_SUMMARY_REL}; run make pr")
    number = int(summary["number"])
    repo = str(summary.get("repo") or "")
    return {
        "repo": repo,
        "number": number,
        "url": str(summary.get("url") or ""),
        "head": str(summary.get("head") or ""),
        "head_sha": str(summary.get("head_sha") or ""),
        "label": f"{repo}#{number}",
    }


def _cli_handoffs(root: Path, session_id: str, agent_id: str) -> int:
    from ops.memory import governance_handoff, session_handoff
    from ops.reports import handoff_delivery

    pub = _publication_from_summary(root)
    rc = 0
    published = False
    try:
        brief = session_handoff.load(root, pr_number=pub["number"])
    except session_handoff.HandoffError as exc:
        print(f"session handoff: not published ({exc})")
    else:
        path, result = publish_session_handoff(
            root,
            pub,
            session_handoff.render(brief).splitlines(),
            session_id=session_id,
            agent_id=agent_id,
        )
        print(result.line([path], root))
        rc |= 0 if result.ok else 1
        published = True
    try:
        gbrief = governance_handoff.load(root, pr_number=pub["number"])
    except governance_handoff.HandoffError as exc:
        print(f"governance handoff: not published ({exc})")
    else:
        path, result = publish_governance_handoff(
            root,
            pub,
            governance_handoff.render_sections(gbrief),
            session_id=session_id,
            agent_id=agent_id,
            friction=handoff_delivery.friction_items(gbrief),
        )
        print(result.line([path], root))
        rc |= 0 if result.ok else 1
        published = True
    return rc if published else 2


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ops.reports.publish", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("dirs", "create reports/gmp and reports/end-session/{session,governance}-handoff"),
        (
            "handoffs",
            "deliver .l9/memory handoff briefs: PR comment + Cursor-Governance friction intake",
        ),
        ("gmp", "validate, place in reports/gmp/ and commit GMP report(s); push if a PR is open"),
        ("next-gmp-id", "print the next GMP id for this clone (GMP-NNN)"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--workspace", default=os.getcwd(), help="the work clone")
        if name == "gmp":
            cmd.add_argument("reports", nargs="+", type=Path, help="GMP report .md file(s)")
        if name == "handoffs":
            cmd.add_argument("--session-id", default=os.environ.get("CLAUDE_SESSION_ID", ""))
            cmd.add_argument("--agent-id", default=os.environ.get("L9_MEMORY_AGENT_ID", ""))
    args = parser.parse_args(argv)
    root = Path(args.workspace).resolve()
    if args.command == "dirs":
        for path in ensure_layout(root):
            print(_rel(path, root))
        return 0
    if args.command == "next-gmp-id":
        from ops.reports import gmp

        print(gmp.format_gmp_id(gmp.next_gmp_number(root)))
        return 0
    if args.command == "gmp":
        try:
            paths, result = publish_gmp_report(root, args.reports)
        except ValueError as exc:
            print(f"gmp report: not published ({exc})")
            return 2
        print(result.line(paths, root))
        return 0 if result.ok else 1
    return _cli_handoffs(root, args.session_id, args.agent_id)


if __name__ == "__main__":
    sys.exit(main())
