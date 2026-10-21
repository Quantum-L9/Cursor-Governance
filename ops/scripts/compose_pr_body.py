#!/usr/bin/env python3
"""Autonomous PR-body compile for make pr, and the one PR-body renderer.

Fills the organization's canonical template (``<owner>/.github`` ->
``.github/pull_request_template.md``, resolved at an exact commit) from
measured facts: commit subjects, name-status, additive_only paths,
ALLOW-ROOT-DELETION markers, and gate/L4 receipts.

Measured content lives in *machine-owned regions* delimited by
``<!-- NAME:START -->`` / ``<!-- NAME:END -->``. A refresh (``--refresh-body``)
rewrites only those regions in an existing PR body, so reviewer prose outside
them survives every push. The same code serves ``make pr`` and the org
``governance-pr.yml`` event refresh (``--remote``): there is no second renderer.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA = "l9.pr_body_completion.v1"
UNMEASURED = "not measured by open_pr_after_gate.sh — do not treat as verified"
PROTECTED_STAMP = "<!-- L9_PROTECTED_ROOT_PR -->"
NA = "n/a — not this change"
#: Reason on an unchecked ``## Gates`` box. A gate is a claim about the change
#: (a regression test exists, semgrep is clean) that make pr cannot measure, so
#: "n/a — not this change" there was a confident negative nobody checked. The
#: org PR gate (Quantum-L9/.github pr-gates.yml / governance-pr.yml) also needs
#: a >=4-character word right after the separator, which "n/a — not ..." never
#: had, so every composed body failed six Gate lines. "unverified" satisfies
#: that rule and says what is actually known.
GATE_UNVERIFIED = (
    "unverified — make pr cannot measure this gate; reviewer ticks it or states why not"
)
FIX_PLACEHOLDER = (
    "<!-- What you changed to make the problem above go away. "
    "Note alternatives you rejected and why. -->"
)
REVIEWER_PLACEHOLDER = (
    "<!-- Where to look hardest. Trade-offs accepted. Deferred follow-ups, with issue links. -->"
)
DELETION_RE = re.compile(r"ALLOW-ROOT-DELETION:\s*(?P<path>\S+?)\s*(?:—|-)\s+(?P<reason>\S.*)")
TYPE_LABELS = (
    "Bug fix",
    "Feature / enhancement",
    "Refactor (no behavior change)",
    "Documentation",
    "CI / governance change",
    "Breaking change",
)
RISK_LABELS = (
    "Low — additive, reversible, no data or contract change",
    "Medium — touches shared code, config, or a public interface",
    "High — breaking change, migration, IAM/network, or irreversible",
)

GOV_PREFIXES = (
    "commands/",
    "rules/",
    "skills/",
    "ops/",
    ".github/",
    "environment/",
)
DOCS_PREFIXES = ("docs/", "docs/plans/")

COMPOSER_MARKER = "<!-- autonomous compile from open_pr_after_gate.sh -->"
TEMPLATE_PATH = ".github/pull_request_template.md"
TEMPLATE_PROVENANCE_RE = re.compile(r"<!-- l9-pr-template: [^\n]*?-->")

#: Machine-owned PR-body regions, in template order. Everything a refresh may
#: rewrite is inside one of these; everything outside belongs to people.
REGION_PROTECTED_PATHS = "PROTECTED-ROOT-PATHS"
REGION_EVIDENCE = "EVIDENCE"
REGION_INTENT = "CHANGES-BY-INTENT"
REGION_FILES = "FILES-TOUCHED"
MACHINE_REGIONS = (REGION_PROTECTED_PATHS, REGION_EVIDENCE, REGION_INTENT, REGION_FILES)
#: Headings and regions the canonical template must carry. A template that
#: lacks one cannot be refreshed safely, so resolution fails closed on it.
REQUIRED_TEMPLATE_HEADINGS = (
    "## Problem",
    "## Risk",
    "## Evidence",
    "## Gates",
    "## Changes by intent",
    "## Files touched",
)
#: Regions a template must already carry. The composer wraps the older
#: placeholders in the others itself, so this is the floor, not the full set.
REQUIRED_TEMPLATE_REGIONS = (REGION_FILES,)
#: pr-files.yml wrapped the inventory in <details> past this many rows.
COLLAPSE_AFTER = 60
STATUS_WORDS = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "typechange",
}
INTENT_PROVENANCE = (
    "<!-- Paths are machine-owned: one row per `git diff -M -C --name-status base...head` "
    "entry, refreshed on every push. The text after a path is yours; it survives refresh. "
    "A new path starts from the subject of the newest commit that touched it. -->"
)
EVIDENCE_HEAD_RE = re.compile(r"^composed at head ([0-9a-f]{7,40})$", re.M)
EVIDENCE_STALE_PREFIX = "STALE:"


class TemplateError(RuntimeError):
    """The canonical PR template could not be resolved or failed validation."""


class GitRangeError(RuntimeError):
    """A git measurement the body depends on failed; never render it as empty."""


@dataclass
class MechanicalFacts:
    # Oldest first. `git log base..HEAD` is newest-first, and the composer used
    # to take element 0 of that as "the" subject, so every Problem / Fix / Why
    # line in a multi-commit PR quoted whichever commit happened to be last.
    commits: list[str] = field(default_factory=list)
    # Parallel to `commits`: the body of each commit, or "" when it has none.
    commit_bodies: list[str] = field(default_factory=list)
    changed_files: list[str] = field(default_factory=list)
    # path -> subject of the newest commit in the range that touched it. Lets a
    # per-path bullet say why *that* file changed rather than repeating one line.
    path_subjects: dict[str, str] = field(default_factory=dict)
    issue_closes: list[int] = field(default_factory=list)
    gate_receipt: dict[str, Any] | None = None
    l4_receipt: dict[str, Any] | None = None
    # `.l9/autonomy/breakglass.json`, written by l4_local when an environment
    # variable rather than a receipt allowed remote. Reported only when its
    # `head` is this HEAD: an older trail describes an older push.
    breakglass: dict[str, Any] | None = None
    head: str = ""
    campaign_body: str = ""
    template_path: str = ""
    # "<owner>/.github@<commit>" of the canonical template, when resolved.
    template_revision: str = ""
    # `git diff --shortstat base...HEAD`, verbatim.
    shortstat: str = ""
    additive_only_paths: list[str] = field(default_factory=list)
    deletion_markers: dict[str, str] = field(default_factory=dict)
    # False when no caller measured the range. An empty list then means "unknown",
    # not "none", and the Protected-root block must not claim otherwise.
    additive_only_measured: bool = True


@dataclass
class ComposeResult:
    body: str
    needs_completion: list[str]
    mechanical_filled: list[str]


def _run_git(workspace: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(workspace), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout


def _run_git_strict(workspace: Path, *args: str) -> str:
    """Like ``_run_git`` but a failure raises instead of reading as "no output".

    The changed-file inventory is a claim in the PR body. ``_run_git`` turns a
    bad range into an empty string, which used to publish "no files" for a PR
    whose base was simply not fetched.
    """
    proc = subprocess.run(
        ["git", "-C", str(workspace), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if proc.returncode != 0:
        msg = f"git {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}"
        raise GitRangeError(msg)
    return proc.stdout


@dataclass(frozen=True)
class DiffRow:
    """One ``--name-status`` row. ``old_path`` is set for renames and copies."""

    status: str
    path: str
    old_path: str = ""

    @property
    def key(self) -> str:
        # pr-files.yml's row key; a rename is one row, never two endpoints.
        return f"{self.old_path} -> {self.path}" if self.old_path else self.path

    @property
    def word(self) -> str:
        return STATUS_WORDS.get(self.status[:1], self.status)

    def line(self) -> str:
        if self.old_path:
            return f"{self.status}\t{self.old_path}\t{self.path}"
        return f"{self.status}\t{self.path}"


def parse_row(line: str) -> DiffRow:
    parts = line.split("\t")
    status = parts[0].strip() if parts else "M"
    if status[:1] in {"R", "C"} and len(parts) >= 3:
        return DiffRow(status, parts[2], parts[1])
    return DiffRow(status, parts[-1] if len(parts) > 1 else line)


def diff_rows(workspace: Path, pr_base: str, head: str = "HEAD") -> list[DiffRow]:
    """The PR's changed files, from the merge base, with renames and copies.

    ``-z`` keeps non-ASCII and special paths byte-exact (no C-quoting), and
    ``-M -C`` reports a rename as one row instead of an add plus a delete.
    """
    out = _run_git_strict(
        workspace, "diff", "-z", "--name-status", "-M", "-C", f"{pr_base}...{head}"
    )
    tokens = out.split("\0")
    rows: list[DiffRow] = []
    i = 0
    while i < len(tokens):
        status = tokens[i]
        if not status:
            i += 1
            continue
        if status[:1] in {"R", "C"}:
            rows.append(DiffRow(status, tokens[i + 2], tokens[i + 1]))
            i += 3
        else:
            rows.append(DiffRow(status, tokens[i + 1]))
            i += 2
    return rows


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _l4_state_path(workspace: Path, resolver: str, fallback_name: str) -> Path:
    """Ask l4_local where a piece of L4 state is; never re-derive the location here.

    L4 state is not always at <workspace>/.l9/autonomy: L9_AUTONOMY_STATE_DIR
    relocates it, and a relocated directory is namespaced per workspace. A
    second component resolving the same state by its own rule is how a
    consumer silently reads nothing — the PR body would simply lose its L4
    section, with no error to notice. One owner, one resolver. ``resolver``
    names the l4_local function (``receipt_path``, ``breakglass_path``).
    """
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autonomy"))
        import l4_local

        return getattr(l4_local, resolver)(workspace)
    except Exception:  # noqa: BLE001 — fall back rather than break PR composition
        return workspace / ".l9" / "autonomy" / fallback_name


def _l4_receipt_path(workspace: Path) -> Path:
    return _l4_state_path(workspace, "receipt_path", "l4-release-receipt.json")


def _breakglass_path(workspace: Path) -> Path:
    return _l4_state_path(workspace, "breakglass_path", "breakglass.json")


def _issue_numbers(text: str) -> list[int]:
    found: list[int] = []
    patterns = (
        r"(?:Fixes|Closes)\s+#(\d+)",
        r"Issue-Remediation-Cycle:\s*\S+#(\d+)",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            number = int(match.group(1))
            if number not in found:
                found.append(number)
    return found


def _deletion_markers(text: str) -> dict[str, str]:
    markers: dict[str, str] = {}
    for match in DELETION_RE.finditer(text):
        markers[match.group("path").strip()] = match.group("reason").strip()
    return markers


MAINLINE_REF = "origin/main"


def _narrative_range(workspace: Path, pr_base: str) -> list[str]:
    """The revision arguments for "what this branch says about itself".

    ``pr_base..HEAD`` alone is the wrong range for a stacked PR whose parent
    was cut before the parent's own base was refreshed: it then inherits
    mainline commits the parent has not caught up to, plus the merge commits
    that brought them in, and the composer's *oldest* commit — the PR title —
    becomes somebody else's ``main`` change. Exclude everything reachable from
    ``origin/main``, from every other head on the open-PR chain the stack
    resolver walked (``.l9/pr/stack-base.json`` ``chain``), and every merge
    commit; what remains is this branch's own story. A ref that is not fetched
    is skipped, so the worst case is the bare range, never a failure.
    """
    args = ["--no-merges", f"{pr_base}..HEAD"]
    if pr_base in {MAINLINE_REF, "main"}:
        return args
    own = pr_base.removeprefix("origin/")
    exclude = [MAINLINE_REF] + [f"origin/{head}" for head in _stack_chain(workspace) if head != own]
    for ref in exclude:
        if _run_git(workspace, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").strip():
            args.append(f"^{ref}")
    return args


def _stack_chain(workspace: Path) -> list[str]:
    """Open-PR heads root→tip from the stack-base receipt, or [] when absent.

    The tip alone is what ``pr_base`` already names. The parents above it are
    the ones a stale child inherits from: #601 was cut from #600 before #600
    merged main, so #602 (based on #601) saw #600's later commit as its own.
    """
    doc = _load_json(workspace / ".l9" / "pr" / "stack-base.json")
    if not isinstance(doc, dict) or doc.get("schema") != "l9.stack_base.v1":
        return []
    chain = doc.get("chain")
    if not isinstance(chain, list):
        return []
    return [str(head) for head in chain if isinstance(head, str) and head]


def _collect_path_subjects(workspace: Path, pr_base: str) -> dict[str, str]:
    """Map each changed path to the subject of the newest commit that touched it.

    One `git log --name-only` pass over the range, oldest first, overwriting as
    it goes — so the surviving value for a path is the most recent commit that
    changed it. One process for the whole range, not one per path.
    """
    # %x00 marks a commit boundary; subjects and paths never contain NUL.
    out = _run_git(
        workspace,
        "log",
        "--reverse",
        "--name-only",
        "--format=%x00%s",
        *_narrative_range(workspace, pr_base),
    )
    subjects: dict[str, str] = {}
    for block in out.split("\x00"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        subject, paths = lines[0], lines[1:]
        for rel in paths:
            subjects[rel] = subject
    return subjects


def collect_mechanical(
    workspace: Path,
    *,
    pr_base: str,
    template_path: str = "",
    campaign_body: str = "",
    additive_only_paths: list[str] | None = None,
    additive_only_measured: bool = True,
) -> MechanicalFacts:
    log = _run_git(
        workspace,
        "log",
        "--reverse",
        "--format=%s%n%b---END---",
        *_narrative_range(workspace, pr_base),
    )
    commits: list[str] = []
    bodies: list[str] = []
    issue_closes: list[int] = []
    markers: dict[str, str] = {}
    for block in log.split("---END---"):
        raw_lines = block.strip("\n").splitlines()
        lines = [line.strip() for line in raw_lines if line.strip()]
        if not lines:
            continue
        commits.append(lines[0])
        bodies.append("\n".join(raw_lines[1:]).strip())
        issue_closes.extend(_issue_numbers(block))
        markers.update(_deletion_markers(block))
    changed = [row.line() for row in diff_rows(workspace, pr_base)]
    shortstat = _run_git_strict(workspace, "diff", "--shortstat", f"{pr_base}...HEAD").strip()
    unique_issues: list[int] = []
    for number in issue_closes:
        if number not in unique_issues:
            unique_issues.append(number)
    return MechanicalFacts(
        commits=commits,
        commit_bodies=bodies,
        changed_files=changed,
        shortstat=shortstat,
        path_subjects=_collect_path_subjects(workspace, pr_base),
        issue_closes=unique_issues,
        gate_receipt=_load_json(workspace / ".l9" / "pr" / "gate-receipt.json"),
        l4_receipt=_load_json(_l4_receipt_path(workspace)),
        breakglass=_load_json(_breakglass_path(workspace)),
        head=_run_git(workspace, "rev-parse", "HEAD").strip(),
        campaign_body=campaign_body.strip(),
        template_path=template_path,
        additive_only_paths=[p for p in (additive_only_paths or []) if p.strip()],
        deletion_markers=markers,
        additive_only_measured=additive_only_measured,
    )


def _bullet_list(items: list[str]) -> str:
    if not items:
        return "_none measured_"
    return "\n".join(f"- {item}" for item in items)


def _rows(facts: MechanicalFacts) -> list[DiffRow]:
    return [parse_row(line) for line in facts.changed_files if line.strip()]


def _changed_paths(facts: MechanicalFacts) -> list[str]:
    # The destination of a rename/copy, never the "old\tnew" pair.
    return [row.path for row in _rows(facts) if row.path]


NO_SUBJECT = "measured change (no commit subject)"

#: Printed under Problem when the oldest commit carries no body paragraph. The
#: composer has no prose source beyond commit subjects and that one paragraph,
#: so a subject-only Problem is the honest floor, not a description — PR #614
#: shipped one and its author had to rewrite the body by hand after noticing.
#: Saying so in the body, and on stderr at compile time, is what makes the thin
#: case visible before a reviewer reads it.
THIN_PROBLEM_NOTE = (
    "_Composer note: the oldest commit carries no body paragraph, so this Problem "
    "is its subject line only. Rewrite it before review._"
)


def _first_paragraph(body: str) -> str:
    for para in re.split(r"\n\s*\n", body.strip()):
        text = " ".join(line.strip() for line in para.splitlines() if line.strip())
        # Trailers (Closes #, ALLOW-ROOT-DELETION:, Co-authored-by:) are not prose.
        if text and not re.match(r"^[A-Za-z-]+:\s", text) and not DELETION_RE.match(text):
            return text
    return ""


def range_problem(facts: MechanicalFacts) -> str:
    """The Problem statement for the whole range.

    The oldest commit is where the work started, so its subject — and its body's
    first paragraph, when the author wrote one — is the closest measured thing to
    "what was wrong". A multi-commit range says how many commits follow, so the
    line cannot be read as the entire change.
    """
    if not facts.commits:
        return NO_SUBJECT
    head = facts.commits[0]
    body = facts.commit_bodies[0] if facts.commit_bodies else ""
    para = _first_paragraph(body)
    more = len(facts.commits) - 1
    suffix = f" (+{more} more commit{'s' if more != 1 else ''} below)" if more else ""
    return f"{head}{suffix}\n\n{para or THIN_PROBLEM_NOTE}"


def range_summary(facts: MechanicalFacts) -> str:
    """One line: the oldest subject plus the count of what follows."""
    if not facts.commits:
        return NO_SUBJECT
    more = len(facts.commits) - 1
    return facts.commits[0] + (f" (+{more} more)" if more else "")


def range_title(facts: MechanicalFacts) -> str:
    """The PR title: the oldest own subject, no count. Empty when the range is empty
    so the caller can fall back to the branch name."""
    return facts.commits[0] if facts.commits else ""


def range_fix(facts: MechanicalFacts) -> str:
    """The Fix: every commit subject, oldest first. One commit reads as one line."""
    if not facts.commits:
        return NO_SUBJECT
    if len(facts.commits) == 1:
        return facts.commits[0]
    return "\n".join(f"- {subject}" for subject in facts.commits)


def path_why(facts: MechanicalFacts, path: str) -> str:
    """Why this path changed: the subject of the commit that last touched it."""
    return facts.path_subjects.get(path) or range_summary(facts)


def infer_type_of_change(facts: MechanicalFacts) -> str:
    paths = _changed_paths(facts)
    if facts.deletion_markers:
        return "Breaking change"
    if paths and all(path.startswith(DOCS_PREFIXES) or path.startswith("docs/") for path in paths):
        return "Documentation"
    if paths and all(path.startswith(GOV_PREFIXES) or path.startswith("docs/") for path in paths):
        return "CI / governance change"
    return "Feature / enhancement"


def infer_risk(facts: MechanicalFacts) -> str:
    if facts.deletion_markers:
        return RISK_LABELS[2]
    paths = _changed_paths(facts)
    if paths and all(path.startswith("docs/") for path in paths):
        return RISK_LABELS[0]
    return RISK_LABELS[1]


def _security_passed(facts: MechanicalFacts) -> bool:
    receipt = facts.gate_receipt or {}
    if not receipt:
        return False
    if receipt.get("security") in {"pass", "passed", "ok", True}:
        return True
    waves = receipt.get("waves")
    if isinstance(waves, dict):
        sec = waves.get("security")
        if sec in {"pass", "passed", True}:
            return True
        if isinstance(sec, dict) and sec.get("status") in {"pass", "passed"}:
            return True
    return receipt.get("schema") == "l9.pr_gate_receipt.v2"


def _needs_completion(template: str | None) -> list[str]:
    # Autonomous compile fills every heading the one template still carries.
    del template
    return []


def _annotate_unchecked_boxes(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if (
            re.match(r"^- \[ \] ", line)
            and UNMEASURED not in line
            and GATE_UNVERIFIED not in line
            and " — n/a" not in line
            and " — n/a —" not in line
        ):
            lines.append(f"{line} — {UNMEASURED}")
        else:
            lines.append(line)
    return "\n".join(lines)


def _receipt_binding(receipt: dict[str, Any]) -> str:
    """Name what a receipt is actually bound to, per its own schema.

    A v2 gate receipt is keyed on content digests and carries no `head`, so
    reading that one field for every schema printed `head=None` — a PR body
    stating the receipt was bound to nothing.
    """
    for field_name in ("content_digest", "tree_digest", "report_sha256"):
        value = receipt.get(field_name)
        if value:
            return f"{field_name}={value}"
    head = receipt.get("head") or receipt.get("head_sha")
    if head:
        return f"head={head}"
    return "binding=none recorded"


def _evidence_lines(facts: MechanicalFacts) -> list[str]:
    evidence: list[str] = []
    if facts.gate_receipt:
        evidence.append(
            f"gate-receipt.json present: schema={facts.gate_receipt.get('schema')} "
            f"{_receipt_binding(facts.gate_receipt)} "
            f"passed_at={facts.gate_receipt.get('passed_at')}"
        )
    else:
        evidence.append("gate-receipt.json absent — local gate result not measured here")
    if facts.l4_receipt:
        evidence.append(
            f"L4 receipt present: phase={facts.l4_receipt.get('phase')} "
            f"{_receipt_binding(facts.l4_receipt)}"
        )
    else:
        evidence.append("L4 receipt absent — release authorization not measured here")
    trail = _breakglass_for_head(facts)
    if trail:
        evidence.append(
            f"BREAKGLASS {trail.get('variable')}={trail.get('reason')} "
            f"head={trail.get('head')} used_at={trail.get('used_at')} — "
            "remote was allowed by an environment variable, not by a receipt"
        )
    return evidence


def _breakglass_for_head(facts: MechanicalFacts) -> dict[str, Any] | None:
    """The breakglass trail, only if it describes this HEAD.

    The file is rewritten on every use and never cleaned up, so its presence
    alone says nothing about this PR. A trail whose head matches is a claim
    about the push being composed; any other trail is history and stays out.
    """
    trail = facts.breakglass
    if not trail or not facts.head:
        return None
    if trail.get("head") != facts.head:
        return None
    return trail


def _check_box(text: str, label: str) -> str:
    pattern = re.compile(rf"^- \[ \] ([^\n]*{re.escape(label)}[^\n]*)$", re.M)
    return pattern.sub(r"- [x] \1", text, count=1)


def _na_unchecked_in_section(text: str, heading: str, until: str | None, reason: str = NA) -> str:
    start = text.find(heading)
    if start < 0:
        return text
    end = len(text)
    if until:
        nxt = text.find(until, start + len(heading))
        if nxt >= 0:
            end = nxt
    chunk = text[start:end]
    new_lines: list[str] = []
    for line in chunk.splitlines():
        if re.match(r"^- \[ \] ", line) and " — n/a" not in line and reason not in line:
            new_lines.append(f"{line} — {reason}")
        else:
            new_lines.append(line)
    # Keep the newline that ended the section, or the next heading is glued on.
    tail = "\n" if chunk.endswith("\n") else ""
    return text[:start] + "\n".join(new_lines) + tail + text[end:]


_PATHS_PH = re.compile(r"^- ` `$", re.M)
_EVIDENCE_PH = re.compile(r"```\n\$ pytest -q\n\$ ruff check \. && pyright\n```")
_FILES_PH = re.compile(r"_pending — the bot fills this in on push_")
_INTENT_PH = re.compile(r"\*\*Added\*\*.*?\*\*Deleted\*\*\n- `path/to/dead.py`[^\n]*", re.S)
_REGION_PLACEHOLDERS = {
    REGION_PROTECTED_PATHS: _PATHS_PH,
    REGION_EVIDENCE: _EVIDENCE_PH,
    REGION_INTENT: _INTENT_PH,
}


def _fill_protected_root(text: str, facts: MechanicalFacts) -> str:
    paths = facts.additive_only_paths
    if PROTECTED_STAMP not in text and paths:
        text = PROTECTED_STAMP + "\n" + text
    text = _put_region(text, REGION_PROTECTED_PATHS, render_protected_paths(facts), _PATHS_PH)
    if not paths:
        if facts.additive_only_measured:
            why = "N/A — no additive_only root files in this diff."
            citation = "N/A — append-only — none."
        else:
            # Never convert an absent measurement into a negative claim.
            why = "Not measured here — the additive_only range was never computed."
            citation = "Not measured — treat the Root-file gate verdict as unknown."
        text = text.replace(
            "<!-- What cannot be done in a non-root path. Composer fills. -->",
            why,
            1,
        )
        text = text.replace(
            "<!-- Issue, failing gate, or law citation. Empty if every path is append-only. -->",
            citation,
            1,
        )
        text = _na_unchecked_in_section(text, "### Edit mode", "## Problem")
        return text
    rewrite = any(path in facts.deletion_markers for path in paths)
    if rewrite:
        text = text.replace(
            "- [ ] **Justified rewrite**",
            "- [x] **Justified rewrite**",
            1,
        )
        reasons = "; ".join(
            f"{path}: {facts.deletion_markers[path]}"
            for path in paths
            if path in facts.deletion_markers
        )
        proof = reasons or "ALLOW-ROOT-DELETION present in range."
    else:
        text = text.replace(
            "- [ ] **Append-only**",
            "- [x] **Append-only**",
            1,
        )
        proof = "append-only — none."
    text = _na_unchecked_in_section(text, "### Edit mode", "## Problem")
    # Why a root file: the commits that actually touched the protected paths,
    # not whichever subject happens to sit at one end of the range.
    root_why = sorted({path_why(facts, path) for path in paths})
    text = text.replace(
        "<!-- What cannot be done in a non-root path. Composer fills. -->",
        "\n".join(f"- `{path}` — {path_why(facts, path)}" for path in paths)
        if len(root_why) > 1
        else root_why[0],
        1,
    )
    text = text.replace(
        "<!-- Issue, failing gate, or law citation. Empty if every path is append-only. -->",
        proof,
        1,
    )
    return text


def _fill_type_of_change(text: str, facts: MechanicalFacts) -> str:
    chosen = infer_type_of_change(facts)
    for label in TYPE_LABELS:
        if label == chosen:
            text = _check_box(text, label)
        else:
            text = re.sub(
                rf"^- \[ \] ([^\n]*{re.escape(label)}[^\n]*)$",
                rf"- [ ] \1 — {NA}",
                text,
                count=1,
                flags=re.M,
            )
    return text


def _fill_risk(text: str, facts: MechanicalFacts) -> str:
    chosen = infer_risk(facts)
    for label in RISK_LABELS:
        if label == chosen:
            text = _check_box(text, label)
        else:
            text = re.sub(
                rf"^- \[ \] ({re.escape(label)})$",
                rf"- [ ] \1 — {NA}",
                text,
                count=1,
                flags=re.M,
            )
    return text


# --------------------------------------------------------------------------
# Machine-owned regions
# --------------------------------------------------------------------------


def region_markers(name: str) -> tuple[str, str]:
    return f"<!-- {name}:START -->", f"<!-- {name}:END -->"


def _region_span(text: str, name: str) -> tuple[int, int] | None:
    """(content_start, content_end) between a region's markers, or None."""
    start, end = region_markers(name)
    i = text.find(start)
    if i < 0:
        return None
    j = text.find(end, i + len(start))
    if j < 0:
        return None
    return i + len(start), j


def region_content(text: str, name: str) -> str | None:
    span = _region_span(text, name)
    if span is None:
        return None
    return text[span[0] : span[1]].strip("\n")


def set_region(text: str, name: str, content: str) -> str:
    span = _region_span(text, name)
    if span is None:
        return text
    return text[: span[0]] + "\n" + content.strip("\n") + "\n" + text[span[1] :]


def wrap_region(name: str, content: str) -> str:
    start, end = region_markers(name)
    return f"{start}\n{content.strip(chr(10))}\n{end}"


def _put_region(text: str, name: str, content: str, placeholder: re.Pattern[str]) -> str:
    """Fill a region: in place when the template carries its markers, else wrap
    the placeholder the older template had, so every body comes out refreshable."""
    if _region_span(text, name) is not None:
        return set_region(text, name, content)
    match = placeholder.search(text)
    if match is None:
        return text
    return text[: match.start()] + wrap_region(name, content) + text[match.end() :]


_INTENT_BULLET = re.compile(r"^- `(?P<key>[^`]+)`(?: — (?P<why>.*))?$")


def declared_intent(text: str) -> dict[str, str]:
    """``key -> why`` for every path bullet under Changes by intent.

    Reads the region when present, else the whole ``## Changes by intent``
    section (a body composed before regions existed). Template placeholders
    (``path/to/...``) are not declarations.
    """
    section = region_content(text, REGION_INTENT)
    if section is None:
        match = re.search(r"^## Changes by intent\n([\s\S]*?)(?=^## |\Z)", text, re.M)
        section = match.group(1) if match else ""
    declared: dict[str, str] = {}
    for line in section.splitlines():
        match = _INTENT_BULLET.match(line.strip())
        if match and not match.group("key").startswith("path/to/"):
            declared[match.group("key")] = (match.group("why") or "").strip()
    return declared


def render_changes_by_intent(facts: MechanicalFacts, keep_why: dict[str, str] | None = None) -> str:
    """Every row exactly once, grouped by status. ``keep_why`` carries reviewer
    text forward so a refresh changes the path set, never someone's words."""
    keep_why = keep_why or {}
    groups: dict[str, list[str]] = {"Added": [], "Modified": [], "Renamed": [], "Deleted": []}
    for row in _rows(facts):
        why = keep_why.get(row.key)
        if not why:
            why = path_why(facts, row.path)
            if row.old_path:
                why = f"{why} ({row.word})"
        bullet = f"- `{row.key}` — {why}"
        if row.old_path:
            groups["Renamed"].append(bullet)
        elif row.status.startswith("A"):
            groups["Added"].append(bullet)
        elif row.status.startswith("D"):
            groups["Deleted"].append(bullet)
        else:
            groups["Modified"].append(bullet)
    block = [INTENT_PROVENANCE, ""]
    for heading, bullets in groups.items():
        # Renamed/copied is the one group the template never had; show it only
        # when it has rows so a rename-free body keeps the template's shape.
        if heading == "Renamed" and not bullets:
            continue
        block.append(f"**{heading}**")
        block.extend(bullets or ["- n/a"])
        block.append("")
    return "\n".join(block).rstrip("\n")


def render_files_touched(facts: MechanicalFacts) -> str:
    """Grouped inventory, one entry per row, in the layout pr-files.yml used."""
    rows = _rows(facts)
    count = len(rows)
    head = f"**{count} file{'' if count == 1 else 's'}**"
    if facts.shortstat:
        head += f" — {facts.shortstat}"
    if not rows:
        return head + "\n\n_no changed files in the measured range_"
    groups: dict[str, list[DiffRow]] = {}
    for row in rows:
        directory = row.path.rsplit("/", 1)[0] if "/" in row.path else "(root)"
        groups.setdefault(directory, []).append(row)
    out = [head]
    many = count > COLLAPSE_AFTER
    if many:
        out += ["", "<details><summary>Expand file list</summary>"]
    for directory in sorted(groups):
        out += ["", f"`{directory}/`"]
        for row in groups[directory]:
            name = row.path.rsplit("/", 1)[-1]
            if row.status.startswith("D"):
                out.append(f"- ~~`{name}`~~ — deleted")
            elif row.old_path:
                out.append(f"- `{name}` — {row.word} from `{row.old_path}`")
            else:
                out.append(f"- `{name}` — {row.word}")
    if many:
        out += ["", "</details>"]
    return "\n".join(out)


def render_evidence(facts: MechanicalFacts) -> str:
    lines = []
    if facts.head:
        lines.append(f"composed at head {facts.head}")
    lines.extend(_evidence_lines(facts))
    return "```\n" + "\n".join(lines) + "\n```"


def stale_evidence(existing: str, head: str) -> str:
    """Evidence region after a push that no local gate measured.

    The receipts above describe the head they were composed at. When the PR
    head moved without ``make pr`` (another client, a bot, a web edit), keep
    them as history and say plainly that nothing here describes the new head.
    Deterministic in (existing, head): repeated refreshes do not stack notes.
    """
    match = EVIDENCE_HEAD_RE.search(existing)
    if match and head.startswith(match.group(1)):
        return existing
    lines = [
        line
        for line in existing.strip().strip("`").strip("\n").splitlines()
        if line.strip() and not line.startswith(EVIDENCE_STALE_PREFIX)
    ]
    recorded = match.group(1) if match else "an unrecorded head"
    notice = (
        f"{EVIDENCE_STALE_PREFIX} receipts below were composed at {recorded}; "
        f"PR head is now {head} and no local gate measured it — unverified for this head"
    )
    return "```\n" + "\n".join([notice, *lines]) + "\n```"


def render_protected_paths(facts: MechanicalFacts) -> str:
    if facts.additive_only_paths:
        return "\n".join(f"- `{path}`" for path in facts.additive_only_paths)
    if facts.additive_only_measured:
        return "- N/A — no additive_only root files"
    # Never convert an absent measurement into a negative claim.
    return "- NOT MEASURED — validate_root_file_protection.py did not run"


def check_inventory(body: str, rows: list[DiffRow]) -> tuple[list[str], list[str]]:
    """(undeclared, phantom): diff rows missing from Changes by intent, and
    declared paths that are not rows. Both empty is the only passing state."""
    declared = declared_intent(body)
    keys = [row.key for row in rows]
    undeclared = [key for key in keys if key not in declared]
    phantom = [key for key in declared if key not in set(keys)]
    return undeclared, phantom


def _fill_gates(text: str, facts: MechanicalFacts) -> str:
    if _security_passed(facts):
        text = text.replace(
            "- [ ] No secrets, tokens, or customer data in code, tests, fixtures, or logs",
            "- [x] No secrets, tokens, or customer data in code, tests, fixtures, or logs",
            1,
        )
    return _na_unchecked_in_section(text, "## Gates", "## Reviewer focus", GATE_UNVERIFIED)


def _fill_template(template: str, facts: MechanicalFacts) -> str:
    text = template
    closes = ", ".join(f"#{n}" for n in facts.issue_closes) if facts.issue_closes else "#"
    problem = range_problem(facts)
    fix = range_fix(facts)
    text = _fill_protected_root(text, facts)
    error_fence = (
        "```\npaste the error / failing output here, or delete this block and describe the gap\n```"
    )
    text = text.replace(error_fence, problem, 1)
    if "## Summary" in text:
        text = text.replace(
            "<!-- One-sentence description of what this PR does. -->",
            range_summary(facts),
            1,
        )
    text = re.sub(r"Closes #<!-- issue number -->", f"Closes {closes}", text, count=1)
    text = re.sub(r"Closes #(?!\d)", f"Closes {closes}", text, count=1)
    text = _fill_type_of_change(text, facts)
    if "## Fix" in text:
        text = text.replace(FIX_PLACEHOLDER, fix, 1)
        text = text.replace("<!-- What you changed -->", fix, 1)
    text = _fill_risk(text, facts)
    text = re.sub(r"(?m)^Rollback:\s*$", "Rollback: revert this PR", text, count=1)
    text = re.sub(
        r"(?m)^Blast radius:\s*$",
        "Blast radius: measured paths in Changes by intent",
        text,
        count=1,
    )
    text = _put_region(text, REGION_EVIDENCE, render_evidence(facts), _EVIDENCE_PH)
    text = _put_region(text, REGION_FILES, render_files_touched(facts), _FILES_PH)
    text = _fill_gates(text, facts)
    if "## Reviewer focus" in text:
        text = text.replace(
            REVIEWER_PLACEHOLDER,
            "See Changes by intent and Protected-root (if any additive_only path).",
            1,
        )
    text = _put_region(text, REGION_INTENT, render_changes_by_intent(facts), _INTENT_PH)
    if facts.l4_receipt and facts.l4_receipt.get("phase") == "release_authorized":
        text = text.replace("- [ ] **L4 local autonomy**", "- [x] **L4 local autonomy**", 1)
    return _annotate_unchecked_boxes(text)


def compose_pr_body(facts: MechanicalFacts, template: str | None) -> ComposeResult:
    parts: list[str] = []
    filled = [
        "commits",
        "changed_files",
        "problem",
        "type of change",
        "risk",
        "rollback",
        "changes by intent",
    ]
    if facts.campaign_body:
        parts.append(facts.campaign_body.rstrip())
        parts.append("")
    parts.append(COMPOSER_MARKER)
    if facts.template_revision:
        parts.append(f"<!-- l9-pr-template: {facts.template_revision} -->")
    if template and template.strip():
        parts.append(_fill_template(template, facts))
        if facts.additive_only_paths:
            filled.append("protected-root")
    else:
        closes = ", ".join(f"#{n}" for n in facts.issue_closes)
        parts.extend(
            [
                "## Problem",
                "",
                range_problem(facts),
                "",
                f"Closes {closes or '#'}",
                "",
                "## Evidence",
                "",
                wrap_region(REGION_EVIDENCE, render_evidence(facts)),
                "",
                "## Changes by intent",
                "",
                wrap_region(REGION_INTENT, render_changes_by_intent(facts)),
                "",
                "## Files touched",
                "",
                wrap_region(REGION_FILES, render_files_touched(facts)),
            ]
        )
    # No appended "## Commits" / "## Test plan" / "## Changed files": Fix lists
    # every subject, Evidence carries the receipts, and Files touched is the
    # one inventory. A second file list is how bodies drifted from their diff.
    if facts.gate_receipt:
        filled.append("gate receipt in Evidence")
    if facts.l4_receipt:
        filled.append("L4 receipt in Evidence")
    return ComposeResult(
        body="\n".join(parts).rstrip() + "\n",
        needs_completion=_needs_completion(template),
        mechanical_filled=filled,
    )


def refresh_body(
    existing: str,
    facts: MechanicalFacts,
    *,
    remote: bool = False,
    template: Callable[[], str] | None = None,
) -> tuple[str, str]:
    """Rewrite only the machine-owned regions of an open PR's body.

    Returns ``(body, status)`` with status one of ``unchanged``, ``updated``,
    ``migrated`` (a pre-region composer body was given regions), or
    ``unmanaged`` (no regions and not composer-authored: left untouched). A
    person's body with only the older FILES-TOUCHED markers gets that region.

    ``remote`` is the event-driven refresh: no local receipts and no
    additive_only measurement exist there, so Evidence is only ever marked
    stale for a new head and Protected-root paths are left as measured.

    ``template`` loads the canonical template. It is called only when a local
    refresh measures a different protected-root path set or edit mode: then
    the whole Protected-root section (paths, Edit mode, Why, Proof) is
    recomposed, because every one of those claims described the old range.
    Without a loader that case raises TemplateError rather than leaving a
    stale declaration under a current stamp.
    """
    body = existing.replace("\r\n", "\n")
    status = "updated"
    if _region_span(body, REGION_INTENT) is None:
        if COMPOSER_MARKER in body:
            body = _migrate_legacy(body, facts, remote=remote)
            status = "migrated"
        elif _region_span(body, REGION_FILES) is None:
            return existing, "unmanaged"
    if _region_span(body, REGION_INTENT) is not None:
        keep_why = declared_intent(body)
        body = set_region(body, REGION_INTENT, render_changes_by_intent(facts, keep_why))
    # A person's body from an older template still gets the inventory it asked
    # for (its FILES-TOUCHED markers); its own Changes by intent stays theirs.
    body = set_region(body, REGION_FILES, render_files_touched(facts))
    evidence = region_content(body, REGION_EVIDENCE)
    if evidence is not None:
        fresh = stale_evidence(evidence, facts.head) if remote else render_evidence(facts)
        body = set_region(body, REGION_EVIDENCE, fresh)
    if not remote and _region_span(body, REGION_PROTECTED_PATHS) is not None:
        body = _refresh_protected_root(body, facts, template)
        if facts.additive_only_paths and PROTECTED_STAMP not in body:
            body = PROTECTED_STAMP + "\n" + body
    if status == "updated" and body == existing.replace("\r\n", "\n"):
        return existing, "unchanged"
    return body, status


_EDIT_MODE_RE = re.compile(r"^- \[x\] \*\*(Append-only|Justified rewrite)\*\*", re.M)


def _protected_claims(text: str) -> tuple[str, tuple[str, ...]]:
    paths = (region_content(text, REGION_PROTECTED_PATHS) or "").strip()
    return paths, tuple(_EDIT_MODE_RE.findall(text))


def _refresh_protected_root(
    body: str, facts: MechanicalFacts, template: Callable[[], str] | None
) -> str:
    """Recompose the Protected-root section when its measured claims moved."""
    fresh_paths = render_protected_paths(facts).strip()
    current_paths, current_mode = _protected_claims(body)
    if current_paths == fresh_paths:
        rewrite = any(path in facts.deletion_markers for path in facts.additive_only_paths)
        expected = ("Justified rewrite",) if rewrite else ("Append-only",)
        if not facts.additive_only_paths or current_mode == expected:
            return body
    if template is None:
        msg = (
            "the protected-root path set or edit mode changed; the canonical template is "
            "needed to recompose Edit mode, Why and Proof"
        )
        raise TemplateError(msg)
    fresh = compose_pr_body(facts, template()).body
    old_bounds = _section_bounds(body, "## Protected-root")
    new_bounds = _section_bounds(fresh, "## Protected-root")
    if old_bounds is None or new_bounds is None:
        return set_region(body, REGION_PROTECTED_PATHS, fresh_paths)
    section = fresh[new_bounds[0] : new_bounds[1]]
    return body[: old_bounds[0]] + section + body[old_bounds[1] :]


_LEGACY_APPENDIX = ("## Commits", "## Test plan", "## Changed files", "## Mechanical evidence")


def _section_bounds(text: str, heading: str) -> tuple[int, int] | None:
    match = re.search(rf"^{re.escape(heading)}[ \t]*$", text, re.M)
    if match is None:
        return None
    nxt = re.search(r"^## ", text[match.end() :], re.M)
    end = match.end() + nxt.start() if nxt else len(text)
    return match.end(), end


def _migrate_legacy(body: str, facts: MechanicalFacts, *, remote: bool) -> str:
    """Give a composer-authored body from before regions its regions, once.

    Bounded: only the sections the composer always wrote are touched, the
    reviewer's per-path text under Changes by intent is carried over, and the
    old appended sections (a second file list among them) are removed.
    """
    for heading in _LEGACY_APPENDIX:
        bounds = _section_bounds(body, heading)
        if bounds is not None:
            start = body.rfind("\n", 0, bounds[0] - len(heading) - 1) + 1
            body = body[:start].rstrip("\n") + "\n" + body[bounds[1] :]
    keep_why = declared_intent(body)
    bounds = _section_bounds(body, "## Changes by intent")
    if bounds is not None:
        block = wrap_region(REGION_INTENT, render_changes_by_intent(facts, keep_why))
        body = body[: bounds[0]] + "\n\n" + block + "\n\n" + body[bounds[1] :].lstrip("\n")
    if _region_span(body, REGION_FILES) is None:
        bounds = _section_bounds(body, "## Files touched")
        block = wrap_region(REGION_FILES, render_files_touched(facts))
        if bounds is not None:
            body = body[: bounds[0]] + "\n\n" + block + "\n\n" + body[bounds[1] :].lstrip("\n")
        else:
            body = body.rstrip("\n") + "\n\n## Files touched\n\n" + block + "\n"
    bounds = _section_bounds(body, "## Evidence")
    if bounds is not None and _region_span(body, REGION_EVIDENCE) is None:
        section = body[bounds[0] : bounds[1]]
        fence = re.search(r"```\n[\s\S]*?gate-receipt\.json[\s\S]*?```", section)
        if fence is not None:
            old = fence.group(0)
            new = stale_evidence(old, facts.head) if remote else render_evidence(facts)
            section = section.replace(old, wrap_region(REGION_EVIDENCE, new), 1)
            body = body[: bounds[0]] + section + body[bounds[1] :]
    return body.rstrip("\n") + "\n"


def write_handoff(
    path: Path,
    *,
    result: ComposeResult,
    facts: MechanicalFacts,
    pr_number: int | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "schema": SCHEMA,
        "pr_number": pr_number,
        "template": facts.template_path,
        "template_revision": facts.template_revision,
        "needs_completion": result.needs_completion,
        "mechanical_filled": result.mechanical_filled,
        "thin_problem": THIN_PROBLEM_NOTE in result.body,
        "commit_count": len(facts.commits),
        "changed_file_count": len(facts.changed_files),
        "additive_only_paths": facts.additive_only_paths,
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


GhApi = Callable[[str], Any]


def _gh_api(endpoint: str) -> Any:
    proc = subprocess.run(
        ["gh", "api", endpoint], capture_output=True, text=True, check=False, timeout=60
    )
    if proc.returncode != 0:
        msg = f"gh api {endpoint} failed: {proc.stderr.strip() or proc.returncode}"
        raise TemplateError(msg)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        msg = f"gh api {endpoint} returned non-JSON output"
        raise TemplateError(msg) from exc


GitTemplate = Callable[[str], tuple[str, str]]


def _git_template(owner: str) -> tuple[str, str]:
    """(commit, template text) of ``<owner>/.github`` at its default-branch head, over git.

    The same bytes at the same exact commit the REST route reads. Some session
    gateways scope the REST API to the session's own repositories while still
    serving git for others, so this is a transport swap, not another source.
    """
    url = f"https://github.com/{owner}/.github"
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}

    def git(*args: str) -> str:
        try:
            proc = subprocess.run(
                ["git", *args], capture_output=True, text=True, check=False, timeout=60, env=env
            )
        except subprocess.TimeoutExpired as exc:
            msg = f"git {args[0]} {url} timed out"
            raise TemplateError(msg) from exc
        if proc.returncode != 0:
            msg = f"git {args[0]} {url} failed: {proc.stderr.strip() or proc.returncode}"
            raise TemplateError(msg)
        return proc.stdout

    heads = [line.split("\t") for line in git("ls-remote", url, "HEAD").splitlines()]
    sha = next((row[0] for row in heads if len(row) == 2 and row[1] == "HEAD"), "")
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        msg = f"{url} HEAD did not resolve to a commit over git"
        raise TemplateError(msg)
    with tempfile.TemporaryDirectory() as tmp:
        git("init", "--bare", "-q", tmp)
        git("-C", tmp, "fetch", "-q", "--depth=1", url, sha)
        return sha, git("-C", tmp, "show", f"{sha}:{TEMPLATE_PATH}")


def validate_template(text: str) -> list[str]:
    """Why a template cannot be the canonical one; empty when it can."""
    errors = [
        f"missing heading {heading!r}"
        for heading in REQUIRED_TEMPLATE_HEADINGS
        if not re.search(rf"^{re.escape(heading)}[ \t]*$", text, re.M)
    ]
    errors.extend(
        f"missing region markers {region_markers(name)[0]} ... {region_markers(name)[1]}"
        for name in REQUIRED_TEMPLATE_REGIONS
        if _region_span(text, name) is None
    )
    # Every other machine region needs its markers or the exact placeholder
    # the composer knows how to wrap; otherwise _put_region would insert
    # nothing and the body would ship boilerplate where a measurement belongs.
    errors.extend(
        f"region {name}: neither its markers nor the supported placeholder"
        for name, placeholder in _REGION_PLACEHOLDERS.items()
        if _region_span(text, name) is None and placeholder.search(text) is None
    )
    return errors


@dataclass(frozen=True)
class TemplateSource:
    text: str
    #: "<owner>/.github@<commit>": which bytes, from where.
    revision: str


def _rest_template(owner: str, gh: GhApi) -> tuple[str, str]:
    repo = gh(f"repos/{owner}/.github")
    branch = repo.get("default_branch") if isinstance(repo, dict) else None
    if not branch:
        msg = f"{owner}/.github has no default branch in the API response"
        raise TemplateError(msg)
    commit = gh(f"repos/{owner}/.github/commits/{branch}")
    sha = commit.get("sha", "") if isinstance(commit, dict) else ""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        msg = f"{owner}/.github@{branch} did not resolve to a commit"
        raise TemplateError(msg)
    doc = gh(f"repos/{owner}/.github/contents/{TEMPLATE_PATH}?ref={sha}")
    is_file = isinstance(doc, dict) and doc.get("type") == "file"
    if not is_file or doc.get("encoding") != "base64":
        msg = f"{owner}/.github@{sha}:{TEMPLATE_PATH} is not a base64 file object"
        raise TemplateError(msg)
    return sha, base64.b64decode(doc.get("content", "")).decode("utf-8")


def resolve_template(
    workspace: Path,
    owner: str,
    name: str,
    *,
    gh: GhApi = _gh_api,
    git: GitTemplate = _git_template,
) -> TemplateSource:
    """The organization's canonical PR template at one exact commit.

    ``<owner>/.github`` owns the template. A consumer's local copy is never
    read here — a divergent copy must not change what the body is composed
    from — and there is no stale fallback: an unreachable or invalid template
    is an error, not a silent switch to some other bytes. The org repository
    composes its own PRs from the template at its own PR head.
    """
    if not owner:
        msg = "cannot resolve the repository owner, so the org PR template has no source"
        raise TemplateError(msg)
    if name == ".github":
        try:
            sha = _run_git_strict(workspace, "rev-parse", "HEAD").strip()
            text = _run_git_strict(workspace, "show", f"HEAD:{TEMPLATE_PATH}")
        except GitRangeError as exc:
            raise TemplateError(str(exc)) from exc
    else:
        try:
            sha, text = _rest_template(owner, gh)
        except TemplateError as rest_error:
            # REST unreachable is a transport failure; read the same commit over git.
            try:
                sha, text = git(owner)
            except TemplateError as git_error:
                msg = f"{rest_error}; git transport also failed: {git_error}"
                raise TemplateError(msg) from git_error
    revision = f"{owner}/.github@{sha}"
    errors = validate_template(text)
    if errors:
        msg = f"canonical PR template {revision}:{TEMPLATE_PATH} is not usable: " + "; ".join(
            errors
        )
        raise TemplateError(msg)
    return TemplateSource(text=text, revision=revision)


def _load_additive_only(path: Path | None) -> list[str]:
    if path is None:
        return []
    if not path.is_file():
        # The caller named a measurement file; a missing one is an unmeasured
        # range, which must not silently become "no additive_only root files".
        msg = f"--additive-only-file does not exist: {path}"
        raise FileNotFoundError(msg)
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--pr-base", default="origin/main")
    parser.add_argument(
        "--template",
        type=Path,
        default=None,
        help="Explicit template file (tests and direct callers). make pr resolves the "
        "canonical org template instead, via --org-owner/--repo-name",
    )
    parser.add_argument("--org-owner", default="", help="Owner of <owner>/.github")
    parser.add_argument("--repo-name", default="", help="Repository the PR is in")
    parser.add_argument("--handoff", type=Path, default=None)
    parser.add_argument("--campaign-body-file", type=Path, default=None)
    parser.add_argument("--additive-only-file", type=Path, default=None)
    parser.add_argument(
        "--additive-only-unmeasured",
        action="store_true",
        help="No caller computed the additive_only range; say so instead of claiming none",
    )
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument(
        "--print-title",
        action="store_true",
        help="Print only the PR title (this branch's oldest own commit subject) and exit",
    )
    parser.add_argument(
        "--refresh-body",
        type=Path,
        default=None,
        help="Existing PR body file: print it with only the machine-owned regions refreshed",
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Event-driven refresh with no local receipts: never claim a measurement",
    )
    parser.add_argument(
        "--check-body",
        type=Path,
        default=None,
        help="Exit 1 when Changes by intent misses a diff row or declares a path not in it",
    )
    parser.add_argument("--status-file", type=Path, default=None)
    args = parser.parse_args(argv)
    workspace = args.workspace.resolve()

    try:
        return _main(args, workspace)
    except (GitRangeError, TemplateError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


def _write_status(path: Path | None, doc: dict[str, Any]) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _main(args: argparse.Namespace, workspace: Path) -> int:
    if args.print_title:
        # Same range the body is told from. open_pr_after_gate.sh used to run its
        # own `git log base..HEAD | head -1`, a second copy of the range rule
        # that titled PR #602 with a main commit.
        facts = collect_mechanical(workspace, pr_base=args.pr_base)
        print(range_title(facts))
        return 0

    if args.check_body is not None:
        rows = diff_rows(workspace, args.pr_base)
        undeclared, phantom = check_inventory(args.check_body.read_text(encoding="utf-8"), rows)
        _write_status(
            args.status_file,
            {"rows": len(rows), "undeclared": undeclared, "phantom": phantom},
        )
        for key in undeclared:
            print(f"UNDECLARED: {key}", file=sys.stderr)
        for key in phantom:
            print(f"PHANTOM: {key}", file=sys.stderr)
        return 1 if undeclared or phantom else 0

    campaign = ""
    if args.campaign_body_file and args.campaign_body_file.is_file():
        campaign = args.campaign_body_file.read_text(encoding="utf-8")
    facts = collect_mechanical(
        workspace,
        pr_base=args.pr_base,
        campaign_body=campaign,
        additive_only_paths=_load_additive_only(args.additive_only_file),
        additive_only_measured=not args.additive_only_unmeasured,
    )
    if args.remote:
        # Whatever .l9 happens to hold on a runner describes no push of this PR.
        facts.gate_receipt = None
        facts.l4_receipt = None
        facts.breakglass = None

    if args.refresh_body is not None:
        existing = args.refresh_body.read_text(encoding="utf-8")
        loader: Callable[[], str] | None = None
        if args.template and args.template.is_file():
            loader = args.template.read_text
        elif args.org_owner:

            def loader() -> str:
                return resolve_template(workspace, args.org_owner, args.repo_name).text

        body, status = refresh_body(existing, facts, remote=args.remote, template=loader)
        _write_status(
            args.status_file,
            {"status": status, "head": facts.head, "rows": len(facts.changed_files)},
        )
        print(f"REFRESH-STATUS: {status}", file=sys.stderr)
        print(body, end="")
        return 0

    template_text = ""
    if args.template and args.template.is_file():
        template_text = args.template.read_text(encoding="utf-8")
        facts.template_path = str(args.template)
    elif args.org_owner:
        source = resolve_template(workspace, args.org_owner, args.repo_name)
        template_text = source.text
        facts.template_path = TEMPLATE_PATH
        facts.template_revision = source.revision
    result = compose_pr_body(facts, template_text or None)
    if args.handoff:
        write_handoff(args.handoff, result=result, facts=facts, pr_number=args.pr_number)
    print(result.body, end="")
    if result.needs_completion:
        print(
            "PR body requires completion: " + "; ".join(result.needs_completion),
            file=sys.stderr,
        )
    if THIN_PROBLEM_NOTE in result.body:
        print(
            "WARN: PR body Problem is a commit subject only (the oldest commit has no "
            "body paragraph); rewrite it before review",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
