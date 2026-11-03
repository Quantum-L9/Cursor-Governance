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
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import org_dotgithub

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
#: Every PR-body field is composed: measured from git, or a stated measurement
#: of why a box stays unticked. No field is left for an author to write, so a
#: body is complete the moment it is composed (``needs_completion`` is empty).
#: GATE_UNVERIFIED and the *_UNRESOLVED constants below are kept so a body
#: composed before this contract is still recognised on refresh.
GATE_SEMGREP_UNMEASURED = (
    "unmeasured here: semgrep runs in Organization CI (Core) on this PR and no "
    "local receipt bound to this head records it"
)
GATE_SECRETS_UNMEASURED = (
    "unmeasured here: no local receipt bound to this head records a secret scan"
)
GATE_OBSERVABILITY = (
    "unmeasurable from a diff: whether a metric, log, trace or alert covers the "
    "new path is not visible in changed lines"
)
FIX_PLACEHOLDER = (
    "<!-- What you changed to make the problem above go away. "
    "Note alternatives you rejected and why. -->"
)
REVIEWER_PLACEHOLDER = (
    "<!-- Where to look hardest. Trade-offs accepted. Deferred follow-ups, with issue links. -->"
)
#: Reviewer focus is judgment about where a change is risky. Nothing the
#: composer measures establishes it, so the field says so instead of pointing
#: at another section and reading as answered.
REVIEWER_UNRESOLVED = (
    "_Unresolved — where to look hardest is the author's judgment; the composer "
    "measures no basis for it. State it here; this text survives refresh._"
)
#: Heading line of the composed Reviewer focus (render_reviewer_focus).
REVIEWER_MEASURED = "_Ranked from the measured diff: riskiest paths first._"
#: Paths that make the ``## Semantic change`` section applicable. Measured from
#: the diff rows (both endpoints of a rename), never assumed. Two families:
#: the organization's canonical semantic sources and release records live
#: under these prefixes (Quantum-L9/.github ``semantics/``,
#: ``docs/semantic-foundation/<version>/``) ...
SEMANTIC_PREFIXES = ("semantics/", "docs/semantic-foundation/")
#: ... and a product repository carries its authoritative product artifacts at
#: exact paths: the ProductTopology (``l9.schema/product-topology@1``, the
#: product contract), the derived ProductManifest
#: (``l9.schema/product-manifest@1``) and the repository's release binding
#: (ADR-094). Exact paths, not basenames: a scaffold or a copy elsewhere
#: (``templates/semantic-authoring/product-topology.yaml``) is not the
#: authoritative artifact and must not make the section applicable.
SEMANTIC_ARTIFACTS = {
    "product-topology.yaml": "ProductTopology",
    "release-work/product-manifest.json": "ProductManifest",
    "release-work/product-release-binding.yaml": "product release binding",
}
SEMANTIC_NA = (
    "- [x] N/A — no canonical semantic artifact or release record changed "
    "(measured: no `semantics/` or `docs/semantic-foundation/` path and no "
    "`product-topology.yaml`, `release-work/product-manifest.json` or "
    "`release-work/product-release-binding.yaml` in this diff)"
)
SEMANTIC_FIELD_UNRESOLVED = "_unresolved — the author states this; the composer cannot measure it_"
SEMANTIC_FOUNDATION_FIELD = "Foundation / release candidate affected:"
#: Type of Change is ticked from conventional-commit types in this branch's own
#: commits (and docs-only / .github-only diffs). With no such evidence nothing
#: is ticked: a guessed type is a fabricated claim.
TYPE_NOT_INDICATED = "not indicated by this branch's commit types"
TYPE_UNRESOLVED = (
    "unresolved — no conventional-commit type (fix:, feat:, refactor:, docs:, ci:, build:) "
    "in this branch's commits; author ticks one"
)
CONVENTIONAL_TYPES = {
    "fix": "Bug fix",
    "revert": "Bug fix",
    "feat": "Feature / enhancement",
    "perf": "Feature / enhancement",
    "refactor": "Refactor (no behavior change)",
    "style": "Refactor (no behavior change)",
    "test": "Refactor (no behavior change)",
    "docs": "Documentation",
    "ci": "CI / governance change",
    "build": "CI / governance change",
    "chore": "CI / governance change",
}
#: Paths whose change is CI / governance / tooling rather than product code.
GOVERNANCE_PREFIXES = (".github/", ".circleci/", "ci/", "ops/", "rules/", "policies/", ".l9/")
GOVERNANCE_FILES = (
    "Makefile",
    ".pre-commit-config.yaml",
    ".gitlab-ci.yml",
    "CODEOWNERS",
    ".gitignore",
    ".gitattributes",
)
TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]+$|_test\.[a-z]+$|\.(test|spec)\.[a-z]+$"
)
TYPE_INFERRED = "inferred from the changed paths (no conventional-commit type in this range)"
CONVENTIONAL_RE = re.compile(r"^(?P<type>[a-z]+)(?:\([^)]*\))?(?P<bang>!)?:\s")
RISK_NOTE = (
    "_Risk tick measured from the diff: High on an ALLOW-ROOT-DELETION marker or a "
    "changed workflow permission; Low on a docs-only or test-only diff; Medium otherwise._"
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

DOCS_PREFIXES = ("docs/",)

COMPOSER_MARKER = "<!-- autonomous compile from open_pr_after_gate.sh -->"
TEMPLATE_PATH = ".github/pull_request_template.md"
TEMPLATE_PROVENANCE_RE = re.compile(r"<!-- l9-pr-template: [^\n]*?-->")

#: Machine-owned PR-body regions, in template order. Everything a refresh may
#: rewrite is inside one of these; everything outside belongs to people.
REGION_PROTECTED_PATHS = "PROTECTED-ROOT-PATHS"
REGION_EVIDENCE = "EVIDENCE"
REGION_INTENT = "CHANGES-BY-INTENT"
REGION_FILES = "FILES-TOUCHED"
#: The composer's ranked Reviewer focus. Machine-owned so it follows every push
#: like the inventory; text a reviewer writes outside it survives refresh.
REGION_REVIEWER = "REVIEWER-FOCUS"
MACHINE_REGIONS = (
    REGION_PROTECTED_PATHS,
    REGION_EVIDENCE,
    REGION_INTENT,
    REGION_FILES,
    REGION_REVIEWER,
)
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
#: Visible once per region: a commit subject is context, not a per-file
#: rationale, and the body must not let one read as the other.
INTENT_NOTE = (
    "_Text after each path is the subject of the newest commit in this branch that "
    "touched it (commit context); text written after a path survives refresh._"
)
NO_OWN_COMMIT = "_no own commit in this range touched this path — it arrived through a merge_"
#: The marker bodies composed before carried; still recognised on refresh.
LEGACY_NO_OWN_COMMIT = "_unresolved — no commit in this branch's own range touched this path_"
EVIDENCE_HEAD_RE = re.compile(r"^composed at head ([0-9a-f]{7,40})$", re.M)
EVIDENCE_STALE_PREFIX = "STALE:"
EVIDENCE_UNVERIFIED_PREFIX = "UNVERIFIED:"
#: Template sample lines inside the EVIDENCE region. They are an example of
#: what evidence looks like, never a measurement, and must not survive into a
#: refreshed body as if they were receipts.
EVIDENCE_TEMPLATE_LINES = frozenset({"$ pytest -q", "$ ruff check . && pyright"})
#: Receipt binding verdicts (``MechanicalFacts.gate_binding`` / ``l4_binding``).
BOUND = "bound"
STALE = "stale"
UNVERIFIED = "unverified"


class TemplateError(org_dotgithub.OrgFileError):
    """The canonical PR template could not be resolved or failed validation."""


class GitRangeError(RuntimeError):
    """A git measurement the body depends on failed; never render it as empty."""


#: Schema of the author's PR intent file, ``<workspace>/.l9/pr/pr-intent.json``.
INTENT_SCHEMA = "l9.pr_intent.v1"
#: Where open_pr_after_gate.sh looks for it.
INTENT_RELPATH = ".l9/pr/pr-intent.json"
#: Handoff detail for a field the author supplied through that file.
INTENT_DETAIL = f"the author's text from {INTENT_RELPATH}, bound to this head"


@dataclass(frozen=True)
class PrIntent:
    """Author prose for the fields nothing the composer measures can supply.

    Commit subjects and one body paragraph are the composer's only prose
    sources, so on a long branch the title was the oldest subject, Problem was
    that commit's message and Reviewer focus stayed unresolved. The author
    writes this file before ``make pr``; an empty field keeps the composer's
    floor for that field.
    """

    title: str = ""
    problem: str = ""
    reviewer_focus: str = ""


def load_intent(path: Path | None, head: str) -> PrIntent | None:
    """The intent at *path* when it names *head*, else None (with a WARN).

    Bound to HEAD like every other receipt here: an intent written for an
    earlier branch or head must not describe this one. ``head`` in the file may
    be abbreviated to 7+ characters.
    """
    if path is None or not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"WARN: {path} is not readable JSON ({exc}); intent ignored", file=sys.stderr)
        return None
    if not isinstance(doc, dict) or doc.get("schema") != INTENT_SCHEMA:
        print(f"WARN: {path} is not schema {INTENT_SCHEMA}; intent ignored", file=sys.stderr)
        return None
    named = str(doc.get("head") or "").strip().lower()
    if len(named) < 7 or not head or not head.lower().startswith(named):
        print(
            f"WARN: {path} names head {named or '(none)'}, not {head[:12] or '(unknown)'}; "
            "intent ignored — rewrite it for this head",
            file=sys.stderr,
        )
        return None

    def text(key: str) -> str:
        value = doc.get(key)
        return value.strip() if isinstance(value, str) else ""

    return PrIntent(
        title=text("title"), problem=text("problem"), reviewer_focus=text("reviewer_focus")
    )


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
    # Whether each receipt still describes the tree being composed: BOUND,
    # STALE or UNVERIFIED, plus the reason. "" means no caller checked, which
    # reads as UNVERIFIED — presence of a receipt file is never proof.
    gate_binding: str = ""
    gate_binding_detail: str = ""
    l4_binding: str = ""
    l4_binding_detail: str = ""
    # path -> (lines added, lines deleted), `git diff --numstat`; binary -> (0, 0).
    numstat: dict[str, tuple[int, int]] = field(default_factory=dict)
    # path -> the lines this range adds to it (`git diff -U0`), for the Gates
    # measurements (action pins, workflow permissions, secret patterns).
    added_lines: dict[str, list[str]] = field(default_factory=dict)
    # semantic path -> (blob at the merge base, blob at HEAD); "" when absent.
    blob_ids: dict[str, tuple[str, str]] = field(default_factory=dict)
    # The author's prose (load_intent), bound to `head`; None when absent.
    intent: PrIntent | None = None
    # changed workflow present at HEAD -> whether that file states its token
    # permissions (top level, or on every job). An omitted block inherits the
    # repository default, which is neither enumerated nor least privilege.
    workflow_permissions: dict[str, bool] = field(default_factory=dict)


#: Completion status of one PR-body field in the handoff (``fields``):
#: measured and bound to this head; measured not applicable; unverified but
#: not the author's to supply (a composer default, an unbound receipt — a
#: reviewer may tick it); or the author's to complete. ``needs_completion``
#: lists exactly the last kind, so an unknown is never reported as done.
COMPLETION_VERIFIED = "verified"
COMPLETION_NOT_APPLICABLE = "not_applicable"
COMPLETION_UNVERIFIED = "unverified"
COMPLETION_NEEDS_AUTHOR = "needs_author"
#: Composed from measured facts rather than read from an author or a receipt.
COMPLETION_DERIVED = "derived"


@dataclass
class ComposeResult:
    body: str
    needs_completion: list[str]
    mechanical_filled: list[str]
    # field -> {"status": COMPLETION_*, "detail": why}; see completion_fields.
    fields: dict[str, dict[str, str]] = field(default_factory=dict)


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


GATE_SCRIPT = Path(__file__).resolve().parent / "run_pr_gate.sh"


def verify_gate_receipt(workspace: Path, receipt: dict[str, Any] | None) -> tuple[str, str]:
    """(verdict, detail) for the local gate receipt against the tree now.

    The digest is the gate's own, read through its single
    ``run_pr_gate.sh --print-state-digest`` seam — never re-implemented here.
    It is computed with the receipt's own ``pr_base`` so only paths and
    contents are compared; a recorded ``head_sha`` must also equal HEAD,
    because committing a hook rewrite moves HEAD over identical bytes.
    """
    if not receipt:
        return "", ""
    want = " ".join(
        str(receipt.get(key) or "") for key in ("paths_digest", "content_digest", "pr_base")
    )
    if not receipt.get("content_digest"):
        return UNVERIFIED, "receipt records no content digest"
    env = {**os.environ, "WS": str(workspace), "PR_BASE": str(receipt.get("pr_base") or "")}
    try:
        proc = subprocess.run(
            ["bash", str(GATE_SCRIPT), "--print-state-digest"],
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return UNVERIFIED, f"gate state digest could not be computed: {exc}"
    lines = proc.stdout.strip().splitlines()
    current = lines[-1].strip() if lines else ""
    if proc.returncode != 0 or not current or current.startswith("unreadable-"):
        return UNVERIFIED, "gate state digest could not be computed"
    if current != want:
        return STALE, "the receipt's digest does not match this tree"
    recorded = str(receipt.get("head_sha") or "")
    head = _run_git(workspace, "rev-parse", "HEAD").strip()
    if recorded and head and recorded != head:
        return STALE, f"the receipt was written at {recorded[:12]}, HEAD is {head[:12]}"
    return BOUND, "digest matches this tree" + (f" at {head[:12]}" if recorded else "")


def verify_l4_receipt(workspace: Path, receipt: dict[str, Any] | None) -> tuple[str, str]:
    """(verdict, detail) for the L4 release receipt, judged by l4_local itself."""
    if not receipt:
        return "", ""
    # Broad by design; the handler below carries the reason.
    # nosemgrep: l9.baseline.python.broad-except
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "autonomy"))
        import l4_local

        decision = l4_local._allow_from_receipt(  # noqa: SLF001 — the one binding judge
            workspace, receipt, None, l4_local.current_branch(workspace)
        )
    except Exception as exc:  # noqa: BLE001 — an unjudged receipt is UNVERIFIED, not BOUND
        return UNVERIFIED, f"l4_local could not judge the receipt: {exc}"
    if decision is None:
        return UNVERIFIED, f"phase {receipt.get('phase')!r} is not release_authorized"
    allowed, detail = decision
    return (BOUND if allowed else STALE), detail


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
    verify: bool = True,
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
    rows = diff_rows(workspace, pr_base)
    changed = [row.line() for row in rows]
    shortstat = _run_git_strict(workspace, "diff", "--shortstat", f"{pr_base}...HEAD").strip()
    numstat, added_lines = _measure_lines(workspace, pr_base)
    blob_ids = _semantic_blobs(workspace, pr_base, rows)
    unique_issues: list[int] = []
    for number in issue_closes:
        if number not in unique_issues:
            unique_issues.append(number)
    gate_receipt = _load_json(workspace / ".l9" / "pr" / "gate-receipt.json")
    l4_receipt = _load_json(_l4_receipt_path(workspace))
    gate_binding, gate_detail = verify_gate_receipt(workspace, gate_receipt) if verify else ("", "")
    l4_binding, l4_detail = verify_l4_receipt(workspace, l4_receipt) if verify else ("", "")
    return MechanicalFacts(
        commits=commits,
        commit_bodies=bodies,
        changed_files=changed,
        shortstat=shortstat,
        path_subjects=_collect_path_subjects(workspace, pr_base),
        issue_closes=unique_issues,
        gate_receipt=gate_receipt,
        l4_receipt=l4_receipt,
        breakglass=_load_json(_breakglass_path(workspace)),
        head=_run_git(workspace, "rev-parse", "HEAD").strip(),
        campaign_body=campaign_body.strip(),
        template_path=template_path,
        additive_only_paths=[p for p in (additive_only_paths or []) if p.strip()],
        deletion_markers=markers,
        additive_only_measured=additive_only_measured,
        gate_binding=gate_binding,
        gate_binding_detail=gate_detail,
        l4_binding=l4_binding,
        l4_binding_detail=l4_detail,
        numstat=numstat,
        added_lines=added_lines,
        blob_ids=blob_ids,
        workflow_permissions=_workflow_permissions(workspace, rows),
    )


def _measure_lines(
    workspace: Path, pr_base: str
) -> tuple[dict[str, tuple[int, int]], dict[str, list[str]]]:
    """Per-path line counts and added lines of the range, from the merge base."""
    numstat: dict[str, tuple[int, int]] = {}
    for line in _run_git_strict(
        workspace, "diff", "--numstat", "--no-renames", f"{pr_base}...HEAD"
    ).splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            added = int(parts[0]) if parts[0].isdigit() else 0
            deleted = int(parts[1]) if parts[1].isdigit() else 0
            numstat[parts[2]] = (added, deleted)
    added_lines: dict[str, list[str]] = {}
    current = ""
    for line in _run_git_strict(
        workspace, "diff", "-U0", "--no-color", "--no-ext-diff", "--no-renames", f"{pr_base}...HEAD"
    ).splitlines():
        if line.startswith("+++ "):
            target = line[4:]
            current = target[2:] if target.startswith("b/") else ""
        elif line.startswith("+") and current:
            added_lines.setdefault(current, []).append(line[1:])
    return numstat, added_lines


def _workflow_permissions(workspace: Path, rows: list[DiffRow]) -> dict[str, bool]:
    """Whether each changed workflow still at HEAD states its token permissions."""
    found: dict[str, bool] = {}
    for row in rows:
        if row.status.startswith("D") or not WORKFLOW_PATH_RE.match(row.path):
            continue
        text = _run_git(workspace, "show", f"HEAD:{row.path}")
        found[row.path] = permissions_enumerated(text)
    return found


def permissions_enumerated(text: str) -> bool:
    """True when a workflow declares ``permissions:`` at the top level, or on
    every job. YAML is read structurally by indentation only: the composer is
    stdlib-only, and a file this cannot read is reported as not enumerated."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    if any(re.match(r"^permissions:", ln) for ln in lines):
        return True
    try:
        start = next(i for i, ln in enumerate(lines) if re.match(r"^jobs:\s*(#.*)?$", ln))
    except StopIteration:
        return False
    body: list[str] = []
    for ln in lines[start + 1 :]:
        if ln and not ln[0].isspace() and not ln.startswith("#"):
            break
        if ln.strip() and not ln.lstrip().startswith("#"):
            body.append(ln)
    if not body:
        return False
    indent = len(body[0]) - len(body[0].lstrip())
    jobs: list[list[str]] = []
    for ln in body:
        depth = len(ln) - len(ln.lstrip())
        if depth == indent:
            jobs.append([])
        elif depth > indent and jobs:
            jobs[-1].append(ln)
    if not jobs:
        return False
    for children in jobs:
        if not children:
            return False
        child = len(children[0]) - len(children[0].lstrip())
        if not any(
            len(c) - len(c.lstrip()) == child and c.lstrip().startswith("permissions:")
            for c in children
        ):
            return False
    return True


def _semantic_blobs(
    workspace: Path, pr_base: str, rows: list[DiffRow]
) -> dict[str, tuple[str, str]]:
    """Blob ids at the merge base and at HEAD for every semantic path in the diff."""
    base = _run_git(workspace, "merge-base", pr_base, "HEAD").strip()
    blobs: dict[str, tuple[str, str]] = {}
    for row in rows:
        for path in (row.old_path, row.path):
            if not path or not semantic_kind(path) or path in blobs:
                continue
            before = (
                _run_git(workspace, "rev-parse", "--verify", "-q", f"{base}:{path}").strip()
                if base
                else ""
            )
            after = _run_git(workspace, "rev-parse", "--verify", "-q", f"HEAD:{path}").strip()
            blobs[path] = (before, after)
    return blobs


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
    "_Composer note: no commit body in this range states the problem, so it is "
    "composed from the oldest commit subject and the measured diff._"
)
#: The note bodies composed before this contract carried.
LEGACY_THIN_PROBLEM_NOTE = (
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
        # No own commit (the range is a merge): the diff is the only measurement.
        return f"{NO_SUBJECT}\n\n{THIN_PROBLEM_NOTE} {measured_change(facts)}"
    head = facts.commits[0]
    body = facts.commit_bodies[0] if facts.commit_bodies else ""
    para = _first_paragraph(body)
    more = len(facts.commits) - 1
    suffix = f" (+{more} more commit{'s' if more != 1 else ''} below)" if more else ""
    if para:
        return f"{head}{suffix}\n\n{para}"
    return f"{head}{suffix}\n\n{THIN_PROBLEM_NOTE} {measured_change(facts)}"


def _top_areas(paths: list[str], limit: int = 4) -> list[str]:
    """Top-level directories (or root files) the paths fall in, most-touched first."""
    counts: dict[str, int] = {}
    for path in paths:
        area = path.split("/", 1)[0] + "/" if "/" in path else "(root)"
        counts[area] = counts.get(area, 0) + 1
    return [area for area, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:limit]


def measured_change(facts: MechanicalFacts) -> str:
    """One sentence of what the diff measurably changes: counts by status and areas."""
    rows = _rows(facts)
    if not rows:
        return "The diff against the base is empty."
    by: dict[str, int] = {}
    for row in rows:
        by[row.word] = by.get(row.word, 0) + 1
    counts = ", ".join(f"{n} {word}" for word, n in sorted(by.items()))
    areas = ", ".join(f"`{a}`" for a in _top_areas(_changed_paths(facts)))
    stat = f" ({facts.shortstat})" if facts.shortstat else ""
    return f"Measured: {len(rows)} path(s) — {counts} — in {areas}{stat}."


def range_summary(facts: MechanicalFacts) -> str:
    """One line: the oldest subject plus the count of what follows."""
    if not facts.commits:
        return NO_SUBJECT
    more = len(facts.commits) - 1
    return facts.commits[0] + (f" (+{more} more)" if more else "")


def range_title(facts: MechanicalFacts) -> str:
    """The PR title: the author's intent title, else the oldest own subject, no
    count. Empty when both are absent so the caller can fall back to the branch
    name."""
    if facts.intent is not None and facts.intent.title:
        return facts.intent.title
    return facts.commits[0] if facts.commits else ""


def _later_paragraphs(body: str) -> list[str]:
    """A commit body's prose after its first paragraph (the Problem), trailers dropped."""
    paras: list[str] = []
    seen_first = False
    for para in re.split(r"\n\s*\n", body.strip()):
        lines = [line.rstrip() for line in para.splitlines() if line.strip()]
        if not lines:
            continue
        if all(
            re.match(r"^[A-Za-z-]+:\s", line.strip()) or DELETION_RE.match(line.strip())
            for line in lines
        ):
            continue
        if not seen_first:
            seen_first = True
            continue
        paras.append("\n".join(lines))
    return paras


def range_fix(facts: MechanicalFacts) -> str:
    """The Fix: every commit subject, oldest first, with what each commit body
    says after its Problem paragraph. Measured: nothing here is invented."""
    if not facts.commits:
        return f"{NO_SUBJECT}: {measured_change(facts)}"
    bodies = facts.commit_bodies or [""] * len(facts.commits)
    if len(facts.commits) == 1:
        detail = _later_paragraphs(bodies[0])
        return "\n\n".join([facts.commits[0], *detail])
    lines: list[str] = []
    for subject, body in zip(facts.commits, bodies, strict=False):
        lines.append(f"- {subject}")
        for para in _later_paragraphs(body):
            lines.extend(f"  {line}" for line in para.splitlines())
    return "\n".join(lines)


def path_why(facts: MechanicalFacts, path: str) -> str:
    """The subject of the newest own commit that touched this path.

    Context, not a rationale: render_changes_by_intent says so once above the
    list. A path no own commit touched gets an explicit unresolved marker, not
    the range summary — that borrowed some other change's words for it.
    """
    return facts.path_subjects.get(path) or NO_OWN_COMMIT


def infer_type_of_change(facts: MechanicalFacts) -> list[str]:
    """Type labels this range shows evidence for, in template order.

    Evidence is a conventional-commit type on one of this branch's own commits
    (``fix:``, ``feat!:``, ...), a ``BREAKING CHANGE`` trailer or an
    ALLOW-ROOT-DELETION marker, or a diff that is docs/-only or .github/-only.
    No evidence returns ``[]``: the reader is told the type is unresolved
    rather than handed a default.
    """
    chosen: set[str] = set()
    for index, subject in enumerate(facts.commits):
        match = CONVENTIONAL_RE.match(subject)
        body = facts.commit_bodies[index] if index < len(facts.commit_bodies) else ""
        if match:
            label = CONVENTIONAL_TYPES.get(match.group("type"))
            if label:
                chosen.add(label)
            if match.group("bang"):
                chosen.add("Breaking change")
        if re.search(r"^BREAKING[ -]CHANGE:", body, re.M):
            chosen.add("Breaking change")
    if facts.deletion_markers:
        chosen.add("Breaking change")
    paths = _changed_paths(facts)
    if paths and all(path.startswith(DOCS_PREFIXES) for path in paths):
        chosen.add("Documentation")
    if paths and all(path.startswith(".github/") for path in paths):
        chosen.add("CI / governance change")
    if not chosen and paths:
        chosen.add(_type_from_paths(paths))
    return [label for label in TYPE_LABELS if label in chosen]


def _is_governance_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return path.startswith(GOVERNANCE_PREFIXES) or path in GOVERNANCE_FILES or name.endswith(".mk")


def _type_from_paths(paths: list[str]) -> str:
    """The type a diff's paths show when no commit names one."""
    if all(path.startswith(DOCS_PREFIXES) or path.endswith(".md") for path in paths):
        return "Documentation"
    if all(_is_governance_path(path) for path in paths):
        return "CI / governance change"
    if all(TEST_PATH_RE.search(path) for path in paths):
        return "Refactor (no behavior change)"
    return "Feature / enhancement"


def type_inferred_from_paths(facts: MechanicalFacts) -> bool:
    """True when no commit evidence named a type and the paths decided it."""
    for index, subject in enumerate(facts.commits):
        match = CONVENTIONAL_RE.match(subject)
        if match and CONVENTIONAL_TYPES.get(match.group("type")):
            return False
        body = facts.commit_bodies[index] if index < len(facts.commit_bodies) else ""
        if match and match.group("bang") or re.search(r"^BREAKING[ -]CHANGE:", body, re.M):
            return False
    if facts.deletion_markers:
        return False
    paths = _changed_paths(facts)
    if paths and (
        all(p.startswith(DOCS_PREFIXES) for p in paths)
        or all(p.startswith(".github/") for p in paths)
    ):
        return False
    return bool(paths)


def infer_risk(facts: MechanicalFacts) -> str:
    if facts.deletion_markers or workflow_permission_changes(facts):
        return RISK_LABELS[2]
    paths = _changed_paths(facts)
    if paths and all(path.startswith("docs/") for path in paths):
        return RISK_LABELS[0]
    if paths and all(TEST_PATH_RE.search(path) for path in paths):
        return RISK_LABELS[0]
    return RISK_LABELS[1]


def _security_passed(facts: MechanicalFacts) -> bool:
    """True only for a receipt bound to this tree that records a passing scan.

    The blocking security wave (gitleaks, semgrep, bandit, pip-audit on the
    changed files) is what a ticked secrets/semgrep box claims. A receipt that
    no longer describes the tree, or that does not say the wave ran blocking
    and passed, proves nothing about this head — including a bare v2 receipt,
    which used to tick the box by its schema name alone.
    """
    receipt = facts.gate_receipt or {}
    if not receipt or facts.gate_binding != BOUND:
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
    return False


def completion_fields(body: str, facts: MechanicalFacts) -> dict[str, dict[str, str]]:
    """Per-field completion status, read off the composed body itself.

    The handoff and the rendered Markdown must tell one truth, so every
    status here is derived from the marker the body carries (the unresolved
    text, the ticked box, the receipt verdict), never from a parallel
    bookkeeping of what the composer meant to write. A field the template
    does not carry is absent, not "done".
    """
    fields: dict[str, dict[str, str]] = {}
    intent = facts.intent or PrIntent()

    def put(name: str, status: str, detail: str) -> None:
        fields[name] = {"status": status, "detail": detail}

    if THIN_PROBLEM_NOTE in body:
        put(
            "problem",
            COMPLETION_DERIVED,
            "no commit body states it — composed from the oldest subject and the measured diff",
        )
    elif "## Problem" in body and intent.problem and intent.problem in body:
        put("problem", COMPLETION_VERIFIED, INTENT_DETAIL)
    elif "## Problem" in body:
        put("problem", COMPLETION_VERIFIED, "oldest own commit subject and its body paragraph")
    if "## Type of Change" in body:
        if TYPE_INFERRED in body:
            put(
                "type_of_change",
                COMPLETION_DERIVED,
                "ticked from the changed paths: " + ", ".join(infer_type_of_change(facts)),
            )
        else:
            put(
                "type_of_change",
                COMPLETION_VERIFIED,
                "ticked from this branch's commit types: " + ", ".join(infer_type_of_change(facts)),
            )
    if RISK_NOTE in body:
        put("risk", COMPLETION_DERIVED, "ticked from the measured diff: " + infer_risk(facts))
    if facts.gate_receipt:
        put(
            "gate_receipt",
            COMPLETION_VERIFIED if facts.gate_binding == BOUND else COMPLETION_UNVERIFIED,
            facts.gate_binding_detail or "present; no caller checked its binding",
        )
    else:
        put("gate_receipt", COMPLETION_UNVERIFIED, "gate-receipt.json absent — not measured here")
    if facts.l4_receipt:
        put(
            "l4_receipt",
            COMPLETION_VERIFIED if facts.l4_binding == BOUND else COMPLETION_UNVERIFIED,
            facts.l4_binding_detail or "present; no caller checked its binding",
        )
    else:
        put("l4_receipt", COMPLETION_UNVERIFIED, "L4 receipt absent — not measured here")
    if "## Gates" in body:
        if _security_passed(facts):
            put(
                "security_gates",
                COMPLETION_VERIFIED,
                "secrets and semgrep boxes ticked from a bound receipt whose security wave passed",
            )
        else:
            put(
                "security_gates",
                COMPLETION_UNVERIFIED,
                "no bound passing receipt; every Gate box is unticked and marked unverified",
            )
    if semantic_paths(facts) and "## Semantic change" in body:
        put(
            "semantic_change",
            COMPLETION_DERIVED,
            "applicable — measured coordinates for "
            + ", ".join(f"{path} ({semantic_kind(path)})" for path in semantic_paths(facts)),
        )
    elif SEMANTIC_NA in body:
        put(
            "semantic_change",
            COMPLETION_NOT_APPLICABLE,
            "no canonical semantic artifact or release record in the measured diff",
        )
    # The author's intent wins when given; otherwise the composer ranks it.
    if intent.reviewer_focus and intent.reviewer_focus in body:
        put("reviewer_focus", COMPLETION_VERIFIED, INTENT_DETAIL)
    elif REVIEWER_MEASURED in body:
        put("reviewer_focus", COMPLETION_DERIVED, "ranked from measured risk in the diff")
    if facts.additive_only_paths:
        mode = _edit_mode_expected(facts)
        put(
            "protected_root",
            COMPLETION_VERIFIED,
            "measured additive_only paths: "
            + ", ".join(facts.additive_only_paths)
            + f"; edit mode {mode[0] if mode else 'unresolved'}",
        )
    elif facts.additive_only_measured:
        put("protected_root", COMPLETION_NOT_APPLICABLE, "no additive_only root file in the diff")
    else:
        put(
            "protected_root",
            COMPLETION_UNVERIFIED,
            "the additive_only range was not measured; the Root-file gate verdict is unknown",
        )
    return fields


def _needs_completion(fields: dict[str, dict[str, str]]) -> list[str]:
    """The fields only the author can complete, as the body reports them."""
    return [
        f"{name}: {entry['detail']}"
        for name, entry in fields.items()
        if entry["status"] == COMPLETION_NEEDS_AUTHOR
    ]


def _annotate_unchecked_boxes(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        if (
            re.match(r"^- \[ \] ", line)
            and not re.search(r"\S — \S", line)
            and UNMEASURED not in line
            and GATE_UNVERIFIED not in line
            and TYPE_NOT_INDICATED not in line
            and TYPE_UNRESOLVED not in line
            and SEMANTIC_FIELD_UNRESOLVED not in line
            and " — not applicable: this diff changes " not in line
            and EDIT_MODE_STALE_PREFIX not in line
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


def _binding_verdict(verdict: str, detail: str) -> str:
    """The receipt's relation to this head, in words a reviewer can act on."""
    if verdict == BOUND:
        return f"BOUND ({detail}) — describes this head"
    if verdict == STALE:
        return f"STALE ({detail}) — does not describe this head; unverified"
    reason = detail or "no caller checked its binding"
    return f"UNVERIFIED ({reason}) — not evidence for this head"


def _evidence_lines(facts: MechanicalFacts) -> list[str]:
    evidence: list[str] = []
    if facts.gate_receipt:
        security = facts.gate_receipt.get("security")
        evidence.append(
            f"gate-receipt.json present: schema={facts.gate_receipt.get('schema')} "
            f"{_receipt_binding(facts.gate_receipt)} "
            f"passed_at={facts.gate_receipt.get('passed_at')}"
            + (f" security={security}" if security else " security=not recorded")
            + " — "
            + _binding_verdict(facts.gate_binding, facts.gate_binding_detail)
        )
    else:
        evidence.append("gate-receipt.json absent — local gate result not measured here")
    if facts.l4_receipt:
        evidence.append(
            f"L4 receipt present: phase={facts.l4_receipt.get('phase')} "
            f"{_receipt_binding(facts.l4_receipt)} — "
            + _binding_verdict(facts.l4_binding, facts.l4_binding_detail)
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


def _heading_span(text: str, heading: str) -> tuple[int, int] | None:
    """(start, end) of a heading line's section: up to the next heading of the
    same or a higher level, so template order never decides where it stops."""
    match = re.search(rf"^{re.escape(heading)}[^\n]*$", text, re.M)
    if match is None:
        return None
    level = len(heading) - len(heading.lstrip("#"))
    nxt = re.search(rf"^#{{1,{level}}} ", text[match.end() :], re.M)
    return match.start(), match.end() + nxt.start() if nxt else len(text)


def _na_unchecked_in_section(text: str, heading: str, reason: str = NA) -> str:
    span = _heading_span(text, heading)
    if span is None:
        return text
    start, end = span
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
        text = _na_unchecked_in_section(text, "### Edit mode")
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
    text = _na_unchecked_in_section(text, "### Edit mode")
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
    reason = TYPE_NOT_INDICATED if chosen else TYPE_UNRESOLVED
    inferred = type_inferred_from_paths(facts)
    for label in TYPE_LABELS:
        if label in chosen:
            text = _check_box(text, label)
            if inferred:
                text = re.sub(
                    rf"^(- \[x\] [^\n]*{re.escape(label)}[^\n]*)$",
                    lambda m: f"{m.group(1)} — {TYPE_INFERRED}",
                    text,
                    count=1,
                    flags=re.M,
                )
        else:
            text = re.sub(
                rf"^- \[ \] ([^\n]*{re.escape(label)}[^\n]*)$",
                lambda m: f"- [ ] {m.group(1)} — {reason}",
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
        # The composer's own unresolved marker is a measurement, not someone's
        # words: it is remeasured every refresh, so an own commit that now
        # touches the path replaces it instead of leaving a false "no commit".
        if not why or why.startswith((NO_OWN_COMMIT, LEGACY_NO_OWN_COMMIT)):
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
    block = [INTENT_PROVENANCE, INTENT_NOTE, ""]
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
        if line.strip()
        and not line.startswith((EVIDENCE_STALE_PREFIX, EVIDENCE_UNVERIFIED_PREFIX))
        and line.strip() not in EVIDENCE_TEMPLATE_LINES
        and not re.fullmatch(r"_[^_]*_", line.strip())
    ]
    if match is None and not any("receipt" in line for line in lines):
        # Never composed by make pr: there are no receipts to call stale, and
        # the template's sample commands are not evidence of anything.
        notice = (
            f"{EVIDENCE_UNVERIFIED_PREFIX} no make pr receipt was recorded for this PR; "
            f"head {head} has no measured evidence — add yours below this block"
        )
        return "```\n" + "\n".join([notice, *lines]) + "\n```"
    recorded = match.group(1) if match else "an unrecorded head"
    notice = (
        f"{EVIDENCE_STALE_PREFIX} receipts below were composed at {recorded}; "
        f"PR head is now {head} and no local gate measured it — unverified for this head"
    )
    return "```\n" + "\n".join([notice, *lines]) + "\n```"


PROTECTED_REMOTE_UNMEASURED = (
    "- NOT MEASURED — the governance-pr refresh could not run "
    "validate_root_file_protection.py for this head; make pr measures additive_only "
    "paths, and the Root-file gate judges the diff either way"
)
#: Region line a remote refresh writes under the measured path list when the
#: declarations below it (Edit mode, Why, Proof) were composed for another
#: path set or edit mode. Deterministic in (head, old head): a repeated
#: refresh of the same head rewrites nothing.
PROTECTED_REMOTE_NOTICE_PREFIX = "- UNVERIFIED for head "
#: Appended to every Edit mode box a remote refresh invalidates, after the
#: box is unticked. Its presence also keeps the box out of the generic
#: "not measured" annotation.
EDIT_MODE_STALE_PREFIX = "STALE: composed for an earlier head"

ROOT_PROTECT_SCRIPT = "ops/scripts/validate_root_file_protection.py"
ROOT_PROTECT_CONFIG = "ops/config/root-file-protection.json"


def measure_additive_only(workspace: Path, pr_base: str) -> tuple[list[str], bool]:
    """(paths, measured): additive_only root files touched in ``pr_base..HEAD``.

    Measured by the one owner of that rule — the workspace's own
    ``validate_root_file_protection.py`` over its ``root-file-protection.json``
    — never re-derived here. Mirrors open_pr_after_gate.sh: a workspace with
    no policy file has no additive_only contract, so the empty list is a
    measured answer; a policy file whose validator is absent or fails is an
    unmeasured range, and the caller must say so rather than claim none.
    """
    config = workspace / ROOT_PROTECT_CONFIG
    script = workspace / ROOT_PROTECT_SCRIPT
    if not config.is_file():
        return [], True
    if not script.is_file():
        return [], False
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(script),
                "--list-touched-additive-only",
                "--base",
                pr_base,
                "--head",
                "HEAD",
                "--repo",
                str(workspace),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError):
        return [], False
    if proc.returncode != 0:
        return [], False
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()], True


def _is_placeholder(content: str | None) -> bool:
    """A region still holding template text: ``- ` ``` or one ``_pending ..._`` line."""
    if content is None:
        return False
    text = content.strip()
    return text in {"- ` `", ""} or bool(re.fullmatch(r"_pending\b[^\n]*_", text))


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


#: Gate boxes a bound, passing gate receipt is evidence for: its security wave
#: ran gitleaks and semgrep (p/secrets plus the repo rules) on the changed files.
SECURITY_GATE_BOXES = (
    "No secrets, tokens, or customer data in code, tests, fixtures, or logs",
    "`semgrep` clean, or findings triaged below",
)


WORKFLOW_PATH_RE = re.compile(r"^\.github/workflows/[^/]+\.ya?ml$")
IAM_PATH_RE = re.compile(r"(^|/)(iam|policies|roles?)(/|\.)|\.tf$|(^|/)terraform/", re.I)
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^'\"\s#]+)")
FULL_SHA_RE = re.compile(r"@[0-9a-f]{40}$")
#: A container action is pinned only by an image digest; a tag is mutable.
DOCKER_DIGEST_RE = re.compile(r"@sha256:[0-9a-f]{64}$")
PERMISSION_LINE_RE = re.compile(
    r"^\s*(permissions:|(actions|attestations|checks|contents|deployments|discussions|id-token|"
    r"issues|packages|pages|pull-requests|repository-projects|security-events|statuses):\s*\S)"
)
INTERFACE_PATH_RE = re.compile(
    r"(^|/)(openapi|swagger)[^/]*\.(ya?ml|json)$|\.proto$|\.graphql$|(^|/)__init__\.py$|"
    r"(^|/)index\.(ts|js)$|(^|/)package\.json$|(^|/)pyproject\.toml$|schema[^/]*\.(ya?ml|json)$",
    re.I,
)


def added_action_refs(facts: MechanicalFacts) -> list[tuple[str, str]]:
    """(path, ref) for every remote action, reusable workflow or container
    action (``docker://``) a line adds. Only a local ``./`` action is exempt."""
    refs: list[tuple[str, str]] = []
    for path, lines in facts.added_lines.items():
        if not path.endswith((".yml", ".yaml")):
            continue
        for line in lines:
            match = USES_RE.match(line)
            if match and not match.group(1).startswith("./"):
                refs.append((path, match.group(1)))
    return refs


def ref_pinned(ref: str) -> bool:
    """A remote action pins a full commit SHA; a container action an image digest."""
    if ref.startswith("docker://"):
        return bool(DOCKER_DIGEST_RE.search(ref))
    return bool(FULL_SHA_RE.search(ref))


def workflow_permission_changes(facts: MechanicalFacts) -> list[tuple[str, str]]:
    """(path, line) for every workflow permission line this range adds."""
    found: list[tuple[str, str]] = []
    for path, lines in facts.added_lines.items():
        if WORKFLOW_PATH_RE.match(path):
            found.extend((path, line.strip()) for line in lines if PERMISSION_LINE_RE.match(line))
    return found


def _gate_line(text: str, label: str, ticked: bool, reason: str) -> str:
    """Rewrite one Gates box: tick it, or leave it unticked with a measured reason.

    The org PR gate needs a word of four or more letters right after the
    separator on an unticked Gates line; every reason here starts with one.
    """
    pattern = rf"^- \[ \] {re.escape(label)}[^\n]*$"
    box = "x" if ticked else " "
    return re.sub(pattern, lambda _m: f"- [{box}] {label} — {reason}", text, count=1, flags=re.M)


def _short(items: list[str], limit: int = 4) -> str:
    shown = ", ".join(f"`{i}`" for i in items[:limit])
    return shown + (f" (+{len(items) - limit} more)" if len(items) > limit else "")


def _fill_gates(text: str, facts: MechanicalFacts) -> str:
    """Every Gates box from a measurement of this range: ticked when the diff or a
    receipt bound to this head proves it, otherwise unticked with what was measured."""
    paths = _changed_paths(facts)
    added_total = sum(len(v) for v in facts.added_lines.values())

    tests = [p for p in paths if TEST_PATH_RE.search(p)]
    text = _gate_line(
        text,
        "Regression test added that fails without this fix",
        False,
        f"measured: {len(tests)} test file(s) changed: {_short(tests)}; "
        "failing without the fix is not measured"
        if tests
        else "measured: no test file in this diff",
    )

    secure = _security_passed(facts)
    text = _gate_line(
        text,
        "No secrets, tokens, or customer data in code, tests, fixtures, or logs",
        secure,
        "measured: the security wave of the gate receipt bound to this head passed "
        f"over {added_total} added line(s)"
        if secure
        else GATE_SECRETS_UNMEASURED,
    )
    text = _gate_line(
        text,
        "`semgrep` clean, or findings triaged below",
        secure,
        "measured: the gate receipt bound to this head records a passing semgrep wave"
        if secure
        else GATE_SEMGREP_UNMEASURED,
    )

    perms = workflow_permission_changes(facts)
    iam = [p for p in paths if IAM_PATH_RE.search(p)]
    workflows = [p for p in paths if WORKFLOW_PATH_RE.match(p)]
    if perms or iam:
        listed = "; ".join(f"`{p}`: `{line}`" for p, line in perms[:4]) or _short(iam)
        reason = f"measured: permission or IAM change to review: {listed}"
        ok = False
    elif workflows:
        present = [
            r.path
            for r in _rows(facts)
            if WORKFLOW_PATH_RE.match(r.path) and not r.status.startswith("D")
        ]
        inherited = [p for p in present if facts.workflow_permissions.get(p) is False]
        unread = [p for p in present if p not in facts.workflow_permissions]
        if inherited:
            reason = (
                f"measured: {len(inherited)} changed workflow(s) declare no permissions, so "
                f"they inherit the repository's default token: {_short(inherited)}"
            )
            ok = False
        elif unread:
            reason = (
                "unmeasured here: whether these workflows declare their permissions was not "
                f"read at this head: {_short(unread)}"
            )
            ok = False
        elif present:
            reason = (
                f"measured: {len(present)} changed workflow(s) each declare their permissions, "
                "and this diff adds no permission line"
            )
            ok = True
        else:
            reason = "measured: workflow file(s) only removed; no permission is granted"
            ok = True
    else:
        reason = "measured: no workflow, IAM or infrastructure file in this diff"
        ok = True
    text = _gate_line(
        text, "New IAM / workflow permissions are least privilege and enumerated", ok, reason
    )

    refs = added_action_refs(facts)
    loose = [ref for _, ref in refs if not ref_pinned(ref)]
    if loose:
        reason, ok = (
            f"measured: {len(loose)} added reference(s) not pinned to a full commit SHA "
            f"or image digest: {_short(loose)}",
            False,
        )
    elif refs:
        reason, ok = (
            f"measured: all {len(refs)} added action reference(s) pin a full commit SHA "
            "or image digest",
            True,
        )
    else:
        reason, ok = "measured: no action or reusable-workflow reference added", True
    text = _gate_line(text, "Third-party actions pinned to a full commit SHA", ok, reason)

    interface = [p for p in paths if INTERFACE_PATH_RE.search(p)]
    text = _gate_line(
        text,
        "Public interface change is documented and versioned",
        not interface,
        "measured: interface file(s) changed, documentation and versioning to review: "
        f"{_short(interface)}"
        if interface
        else "measured: no API schema, proto, package manifest or entry-point file in this diff",
    )
    text = _gate_line(
        text,
        "Observability exists for the new path (metric, log, trace, or alert)",
        False,
        GATE_OBSERVABILITY,
    )
    # A box this composer does not know (a template that grew one) still gets a
    # reason; every known box above already carries its measurement.
    span = _heading_span(text, "## Gates")
    if span is None:
        return text
    start, end = span
    lines = [
        f"{line} — {GATE_UNVERIFIED}"
        if re.match(r"^- \[ \] ", line) and " — " not in line
        else line
        for line in text[start:end].splitlines()
    ]
    tail = "\n" if text[start:end].endswith("\n") else ""
    return text[:start] + "\n".join(lines) + tail + text[end:]


def semantic_kind(path: str) -> str:
    """What a path is to the Semantic change section, or "" when nothing.

    An exact authoritative artifact path names its kind; a path under a
    canonical prefix names the family. Anything else — another YAML, a doc, a
    scaffold under ``templates/`` — is not semantic, whatever its basename.
    """
    kind = SEMANTIC_ARTIFACTS.get(path)
    if kind:
        return kind
    if path.startswith("docs/semantic-foundation/"):
        return "semantic foundation release record"
    if path.startswith("semantics/"):
        return "canonical semantic source"
    return ""


def semantic_paths(facts: MechanicalFacts) -> list[str]:
    """Diff paths (either end of a rename) that make Semantic change applicable."""
    found: list[str] = []
    for row in _rows(facts):
        for path in (row.old_path, row.path):
            if path and semantic_kind(path) and path not in found:
                found.append(path)
    return found


def _foundation_versions(paths: list[str]) -> list[str]:
    """Release-record version directories the diff touches, e.g. ``v3.21.0``."""
    versions: list[str] = []
    for path in paths:
        match = re.match(r"^docs/semantic-foundation/(v\d+(?:\.\d+)*)/", path)
        if match and match.group(1) not in versions:
            versions.append(match.group(1))
    return versions


def _fill_semantic(text: str, facts: MechanicalFacts) -> str:
    """Classify ``## Semantic change`` from the diff instead of leaving its labels.

    Not applicable (the measured diff has no semantic path): the section is the
    one ticked N/A line saying why. Applicable: the N/A line names what the
    diff changes and the kind of each artifact, the Foundation field carries
    the release-record version the diff establishes (when one is in it), and
    every other field label and box is marked unresolved for the author —
    the composer cannot know a release coordinate, a dependent's revalidation
    or an admission decision, and an empty ``Foundation:`` reads like an
    answered blank.
    """
    span = _heading_span(text, "## Semantic change")
    if span is None:
        return text
    start, end = span
    section = text[start:end]
    heading, _, rest = section.partition("\n")
    tail = "\n" if section.endswith("\n") else ""
    paths = semantic_paths(facts)
    if not paths:
        return text[:start] + f"{heading}\n\n{SEMANTIC_NA}\n{tail}" + text[end:]
    versions = _foundation_versions(paths)
    blobs = facts.blob_ids
    prior = "; ".join(
        f"`{p}` blob `{blobs.get(p, ('', ''))[0][:12] or 'absent'}`" for p in paths[:5]
    )
    new = "; ".join(
        f"`{p}` blob `{blobs.get(p, ('', ''))[1][:12] or 'deleted'}`" for p in paths[:5]
    )
    more = f" (+{len(paths) - 5} more)" if len(paths) > 5 else ""
    validate = any(p.startswith("scripts/validate-semantics") for p in _changed_paths(facts))
    measured_fields = {
        SEMANTIC_FOUNDATION_FIELD: (
            "measured in this diff: "
            + ", ".join(f"`docs/semantic-foundation/{v}/`" for v in versions)
            if versions
            else "measured: no release-record directory in this diff; the change is to "
            + ", ".join(sorted({semantic_kind(p) for p in paths}))
        ),
        "Prior exact coordinate or source identity (artifact_id, digest, contract/binding id):": (
            f"measured at the merge base: {prior}{more}"
        ),
        "New exact coordinate (when applicable):": f"measured at this head: {new}{more}",
    }
    box_reasons = {
        "Transitive semantic dependents revalidated": (
            "measured: dependents are revalidated by `scripts/validate-semantics.py` in "
            "Validate starters on this PR, not by a local receipt"
        ),
        "`scripts/validate-semantics.py` result pasted under Evidence": (
            "measured: the validator runs in Validate starters on this PR; "
            "its result is that check's"
            + (" (this diff also changes the validator)" if validate else "")
        ),
        "`docs/semantic-foundation/<version>/` manifest": (
            "measured: release-record files in this diff: "
            + _short([p for p in paths if p.startswith("docs/semantic-foundation/")])
            if versions
            else "measured: no release-record file in this diff"
        ),
        "Admission / successor requirement checked": (
            "measured: canonical bytes change at "
            + _short([p for p in paths if blobs.get(p, ("", ""))[0] and blobs.get(p, ("", ""))[1]])
            + "; an admitted revision with changed bytes needs a successor"
        ),
    }
    lines: list[str] = []
    for line in rest.splitlines():
        if re.match(r"^- \[ \] N/A\b", line):
            listed = ", ".join(f"`{path}` ({semantic_kind(path)})" for path in paths[:5])
            lines.append(f"{line} — not applicable: this diff changes {listed}{more}")
        elif re.match(r"^- \[ \] ", line):
            reason = next((r for key, r in box_reasons.items() if key in line), None)
            lines.append(f"{line} — {reason or 'measured: not derivable from this diff'}")
        elif re.match(r"^- [^\[][^\n]*:\s*$", line):
            label = line.strip()[2:]
            value = next((v for key, v in measured_fields.items() if label.startswith(key)), None)
            lines.append(f"{line.rstrip()} {value or 'measured: not derivable from this diff'}")
        else:
            lines.append(line)
    return text[:start] + heading + "\n" + "\n".join(lines) + tail + text[end:]


_CLOSES_LINE = re.compile(r"\n+Closes #(?:<!-- issue number -->)?[ \t]*(?=\n|\Z)")


def _fill_closes(text: str, facts: MechanicalFacts, problem: str | None) -> str:
    """Closing keywords only for issues a commit names; never a dangling ``Closes #``.

    The older template carried a bare ``Closes #`` line; it is filled or
    removed. The canonical template carries none, so a measured issue list is
    written at the end of the Problem text. ``problem`` is that text when the
    composer wrote it; it is located here, at insertion time, because any
    substitution made before this one (the Summary line, for instance) shifts
    every offset computed earlier.
    """
    closes = ", ".join(f"#{n}" for n in facts.issue_closes)
    if _CLOSES_LINE.search(text):
        line = f"\n\nCloses {closes}" if closes else ""
        return _CLOSES_LINE.sub(lambda _m: line, text, count=1)
    if not closes or not problem:
        return text
    start, end = _heading_span(text, "## Problem") or (0, len(text))
    at = text.find(problem, start, end)
    if at < 0:
        return text
    problem_end = at + len(problem)
    return text[:problem_end] + f"\n\nCloses {closes}" + text[problem_end:]


ERROR_FENCE = (
    "```\npaste the error / failing output here, or delete this block and describe the gap\n```"
)


def _fill_template(template: str, facts: MechanicalFacts) -> str:
    text = template
    intent = facts.intent or PrIntent()
    problem = intent.problem or range_problem(facts)
    fix = range_fix(facts)
    text = _fill_protected_root(text, facts)
    problem_written = False
    at = text.find(ERROR_FENCE)
    if at >= 0:
        text = text[:at] + problem + text[at + len(ERROR_FENCE) :]
        problem_written = True
    if "## Summary" in text:
        text = text.replace(
            "<!-- One-sentence description of what this PR does. -->",
            range_summary(facts),
            1,
        )
    text = _fill_closes(text, facts, problem if problem_written else None)
    text = _fill_type_of_change(text, facts)
    if "## Fix" in text:
        text = text.replace(FIX_PLACEHOLDER, fix, 1)
        text = text.replace("<!-- What you changed -->", fix, 1)
    text = _fill_risk(text, facts)
    rows = len(_rows(facts))
    text = re.sub(
        r"(?m)^Rollback:[ \t]*$", lambda _m: f"Rollback: {measured_rollback(facts)}", text, count=1
    )
    areas = ", ".join(f"`{a}`" for a in _top_areas(_changed_paths(facts)))
    text = re.sub(
        r"(?m)^Blast radius:[ \t]*$",
        lambda _m: (
            f"Blast radius: {rows} changed file{'' if rows == 1 else 's'} (Files touched) "
            f"in {areas or 'no area'}" + (f"; {facts.shortstat}" if facts.shortstat else "")
        ),
        text,
        count=1,
    )
    text = re.sub(
        r"(?m)^(Rollback:[^\n]*)$", lambda m: f"{m.group(1)}\n\n{RISK_NOTE}", text, count=1
    )
    text = _put_region(text, REGION_EVIDENCE, render_evidence(facts), _EVIDENCE_PH)
    text = _put_region(text, REGION_FILES, render_files_touched(facts), _FILES_PH)
    text = _fill_semantic(text, facts)
    text = _fill_gates(text, facts)
    if "## Reviewer focus" in text:
        # An intent file's Reviewer focus is the author's own and stays as
        # written; without one the composer ranks it in a refreshed region.
        text = text.replace(
            REVIEWER_PLACEHOLDER,
            intent.reviewer_focus or wrap_region(REGION_REVIEWER, render_reviewer_focus(facts)),
            1,
        )
    text = _put_region(text, REGION_INTENT, render_changes_by_intent(facts), _INTENT_PH)
    if facts.l4_binding == BOUND:
        text = text.replace("- [ ] **L4 local autonomy**", "- [x] **L4 local autonomy**", 1)
    return _annotate_unchecked_boxes(text)


MIGRATION_PATH_RE = re.compile(r"(^|/)(migrations?|alembic|db/migrate)/", re.I)
SENSITIVE_PATH_RE = re.compile(
    r"(^|/)(SECURITY\.md|CODEOWNERS|\.env[^/]*|[^/]*secret[^/]*|[^/]*credential[^/]*|[^/]*\.pem|auth[^/]*)$",
    re.I,
)


def measured_rollback(facts: MechanicalFacts) -> str:
    """How to undo this range, from what it measurably changes."""
    rows = _rows(facts)
    deleted = [r.path for r in rows if r.status.startswith("D")]
    renamed = [f"{r.old_path} → {r.path}" for r in rows if r.old_path]
    migrations = [p for p in _changed_paths(facts) if MIGRATION_PATH_RE.search(p)]
    parts = ["revert this PR"]
    if deleted:
        parts.append(f"the revert restores {len(deleted)} deleted path(s): {_short(deleted)}")
    if renamed:
        parts.append(f"and undoes {len(renamed)} rename(s): {_short(renamed)}")
    if migrations:
        parts.append(
            f"measured: migration path(s) changed ({_short(migrations)}); "
            "a revert does not undo data a migration already applied"
        )
    else:
        parts.append(
            "measured: no migration path in this diff, so a revert restores the prior state"
        )
    return "; ".join(parts)


def render_reviewer_focus(facts: MechanicalFacts) -> str:
    """Where to look hardest, ranked from measured risk in the diff. Never empty."""
    rows = _rows(facts)
    paths = _changed_paths(facts)
    bullets: list[str] = []
    if facts.additive_only_paths:
        bullets.append(
            f"- Append-only root files: {_short(facts.additive_only_paths)} — "
            "confirm only lines were added."
        )
    if facts.deletion_markers:
        bullets.append(
            "- Justified rewrites (ALLOW-ROOT-DELETION): "
            + "; ".join(f"`{p}` — {why}" for p, why in list(facts.deletion_markers.items())[:4])
        )
    perms = workflow_permission_changes(facts)
    if perms:
        bullets.append(
            "- Workflow permissions added: "
            + "; ".join(f"`{p}`: `{line}`" for p, line in perms[:4])
        )
    inherited = [p for p, declared in facts.workflow_permissions.items() if not declared]
    if inherited:
        bullets.append(
            f"- Workflows with no permissions block (default token): {_short(inherited)}"
        )
    loose = [ref for _, ref in added_action_refs(facts) if not ref_pinned(ref)]
    if loose:
        bullets.append(f"- Action references not pinned to a SHA or digest: {_short(loose)}")
    workflows = [p for p in paths if WORKFLOW_PATH_RE.match(p)]
    if workflows:
        bullets.append(
            f"- CI behaviour changes in {_short(workflows)} — they run on every PR and push."
        )
    sensitive = [p for p in paths if SENSITIVE_PATH_RE.search(p)]
    if sensitive:
        bullets.append(f"- Security or ownership routing: {_short(sensitive)}")
    semantic = semantic_paths(facts)
    if semantic:
        bullets.append(
            f"- Canonical semantic artifacts: {_short(semantic)} — "
            "release coordinates under Semantic change."
        )
    migrations = [p for p in paths if MIGRATION_PATH_RE.search(p)]
    if migrations:
        bullets.append(f"- Migrations: {_short(migrations)} — not undone by a revert.")
    gone = [r.key for r in rows if r.status.startswith("D") or r.old_path]
    if gone:
        bullets.append(
            f"- Deleted or renamed: {_short(gone)} — check nothing still refers to the old path."
        )
    churn = sorted(facts.numstat.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:3]
    if churn:
        bullets.append(
            "- Largest changes: " + ", ".join(f"`{p}` (+{a}/-{d})" for p, (a, d) in churn)
        )
    elif paths:
        bullets.append(f"- Changed paths: {_short(paths)}")
    if not (facts.gate_receipt and facts.gate_binding == BOUND):
        bullets.append(
            "- No local gate receipt is bound to this head: "
            "this PR's CI checks are the verification."
        )
    if not bullets:
        bullets.append("- The diff against the base is empty; nothing to review.")
    return "\n".join([REVIEWER_MEASURED, "", *bullets])


#: Sections the composer derives in full from the measured range. Unlike the
#: machine-owned regions they carry no markers (the org template's gates parse
#: them as written), so ownership is proven by content instead: the composer
#: records a digest of each as it wrote it, and a refresh recomposes a section
#: only while its text still matches that digest. Text a person edited no
#: longer matches and is left as theirs.
DERIVED_SECTIONS = ("## Type of Change", "## Fix", "## Risk", "## Gates", "## Semantic change")
DERIVED_STAMP_RE = re.compile(r"^<!-- l9-derived: ([^\n]*?) -->$", re.M)


def _derived_key(heading: str) -> str:
    return heading.lstrip("# ").lower().replace(" ", "-")


def _section_digest(text: str) -> str:
    normalized = "\n".join(line.rstrip() for line in text.strip().splitlines())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def derived_digests(body: str) -> dict[str, str]:
    """key -> digest of each derived section present in ``body``."""
    found: dict[str, str] = {}
    for heading in DERIVED_SECTIONS:
        span = _heading_span(body, heading)
        if span is not None:
            found[_derived_key(heading)] = _section_digest(body[span[0] : span[1]])
    return found


def derived_stamp(digests: dict[str, str]) -> str:
    return "<!-- l9-derived: " + " ".join(f"{k}={v}" for k, v in digests.items()) + " -->"


def read_derived_stamp(body: str) -> dict[str, str] | None:
    match = DERIVED_STAMP_RE.search(body)
    if match is None:
        return None
    pairs = (item.partition("=") for item in match.group(1).split())
    return {k: v for k, _, v in pairs if k and v}


def _refresh_derived(body: str, facts: MechanicalFacts, template: Callable[[], str] | None) -> str:
    """Recompose every derived section the composer still owns (see DERIVED_SECTIONS).

    A body with no stamp predates it, and nothing proves which of its section
    text is the composer's: it is left as written. Without a template loader
    there is nothing to recompose from, and the same holds.
    """
    recorded = read_derived_stamp(body)
    if recorded is None or template is None:
        return body
    # Same head, same facts: what was measured for it (a bound local receipt
    # included) still stands, and a remote pass must not downgrade it.
    if facts.head and recorded.get("head") == facts.head[:12]:
        return body
    owned: list[str] = []
    for heading in DERIVED_SECTIONS:
        span = _heading_span(body, heading)
        if span is not None and recorded.get(_derived_key(heading)) == _section_digest(
            body[span[0] : span[1]]
        ):
            owned.append(heading)
    if not owned:
        return body
    fresh = _fill_template(template(), facts)
    digests = dict(recorded)
    if facts.head:
        digests["head"] = facts.head[:12]
    for heading in owned:
        key = _derived_key(heading)
        span = _heading_span(body, heading)
        new_span = _heading_span(fresh, heading)
        if span is None or new_span is None:
            continue
        replacement = fresh[new_span[0] : new_span[1]]
        if not replacement.endswith("\n"):
            replacement += "\n"
        body = body[: span[0]] + replacement + body[span[1] :]
        new_span = _heading_span(body, heading)
        if new_span is not None:
            digests[key] = _section_digest(body[new_span[0] : new_span[1]])
    return DERIVED_STAMP_RE.sub(lambda _m: derived_stamp(digests), body, count=1)


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
        filled_text = _fill_template(template, facts)
        digests = derived_digests(filled_text)
        if digests:
            if facts.head:
                digests = {"head": facts.head[:12], **digests}
            parts.append(derived_stamp(digests))
        parts.append(filled_text)
        if facts.additive_only_paths:
            filled.append("protected-root")
    else:
        # Same visible order as the canonical template: inventory first.
        closes = ", ".join(f"#{n}" for n in facts.issue_closes)
        problem = range_problem(facts) + (f"\n\nCloses {closes}" if closes else "")
        parts.extend(
            [
                "## Files touched",
                "",
                wrap_region(REGION_FILES, render_files_touched(facts)),
                "",
                "## Changes by intent",
                "",
                wrap_region(REGION_INTENT, render_changes_by_intent(facts)),
                "",
                "## Problem",
                "",
                problem,
                "",
                "## Evidence",
                "",
                wrap_region(REGION_EVIDENCE, render_evidence(facts)),
            ]
        )
    # No appended "## Commits" / "## Test plan" / "## Changed files": Fix lists
    # every subject, Evidence carries the receipts, and Files touched is the
    # one inventory. A second file list is how bodies drifted from their diff.
    if facts.gate_receipt:
        filled.append("gate receipt in Evidence")
    if facts.l4_receipt:
        filled.append("L4 receipt in Evidence")
    body = "\n".join(parts).rstrip() + "\n"
    fields = completion_fields(body, facts)
    return ComposeResult(
        body=body,
        needs_completion=_needs_completion(fields),
        mechanical_filled=filled,
        fields=fields,
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
    if _region_span(body, REGION_REVIEWER) is not None:
        body = set_region(body, REGION_REVIEWER, render_reviewer_focus(facts))
    if _region_span(body, REGION_PROTECTED_PATHS) is not None:
        if remote:
            body = _refresh_protected_root_remote(body, facts)
        else:
            body = _refresh_protected_root(body, facts, template)
        if facts.additive_only_paths and PROTECTED_STAMP not in body:
            body = PROTECTED_STAMP + "\n" + body
    # The author's intent replaces only text the composer itself wrote; text a
    # person already wrote in those sections is theirs and stays.
    if facts.intent is not None:
        if facts.intent.problem:
            body = _replace_composed_problem(body, facts, facts.intent.problem)
        if facts.intent.reviewer_focus:
            # The composer's ranked region (or the older unresolved marker) is
            # the composer's own text; the author's focus replaces it.
            span = _region_span(body, REGION_REVIEWER)
            if span is not None:
                open_marker, close_marker = region_markers(REGION_REVIEWER)
                start, end = span[0] - len(open_marker), span[1] + len(close_marker)
                body = body[:start] + facts.intent.reviewer_focus + body[end:]
            elif REVIEWER_UNRESOLVED in body:
                body = body.replace(REVIEWER_UNRESOLVED, facts.intent.reviewer_focus, 1)
    body = _refresh_derived(body, facts, template)
    if status == "updated" and body == existing.replace("\r\n", "\n"):
        return existing, "unchanged"
    return body, status


def _replace_composed_problem(body: str, facts: MechanicalFacts, problem: str) -> str:
    """Swap the Problem the composer derived from commits for the author's text.

    Matches only the exact text range_problem writes for this branch's oldest
    commit (its subject, any "(+N more commits below)" count, then its first
    body paragraph or THIN_PROBLEM_NOTE). The count is free because the branch
    grows between pushes; anything else a person edited there is left alone.
    """
    if not facts.commits:
        return body
    span = _heading_span(body, "## Problem")
    if span is None:
        return body
    start, end = span
    oldest = facts.commit_bodies[0] if facts.commit_bodies else ""
    para = _first_paragraph(oldest)
    # A body-less commit's Problem is the composer's note plus a measured
    # sentence whose counts move between pushes, or the older bare note.
    tail = (
        re.escape(para)
        if para
        else "(?:"
        + re.escape(THIN_PROBLEM_NOTE)
        + r" Measured: [^\n]*"
        + "|"
        + re.escape(LEGACY_THIN_PROBLEM_NOTE)
        + ")"
    )
    composed = re.compile(
        re.escape(facts.commits[0]) + r"(?: \(\+\d+ more commits? below\))?\n\n" + tail
    )
    match = composed.search(body, start, end)
    if match is None:
        return body
    return body[: match.start()] + problem + body[match.end() :]


def _composed_head(body: str) -> str:
    """The head make pr composed the body at, from its Evidence region, or ""."""
    match = EVIDENCE_HEAD_RE.search(region_content(body, REGION_EVIDENCE) or "")
    return match.group(1) if match else ""


def _declared_protected_paths(region: str) -> str:
    """The path lines of the Protected-root region, without a refresh notice."""
    kept = [
        line
        for line in region.strip().splitlines()
        if not line.startswith(PROTECTED_REMOTE_NOTICE_PREFIX)
        and not line.startswith("- NOT MEASURED")
    ]
    return "\n".join(kept).strip()


def _edit_mode_expected(facts: MechanicalFacts) -> tuple[str, ...]:
    if not facts.additive_only_paths:
        return ()
    rewrite = any(path in facts.deletion_markers for path in facts.additive_only_paths)
    return ("Justified rewrite",) if rewrite else ("Append-only",)


_EDIT_MODE_LINE_RE = re.compile(
    r"^- \[[ xX]\] (?P<rest>\*\*(?:Append-only|Justified rewrite)\*\*[^\n]*)$", re.M
)
_EDIT_MODE_SUFFIX_RE = re.compile(
    rf"(?: — {re.escape(NA)}| — {re.escape(EDIT_MODE_STALE_PREFIX)}[^\n]*)+$"
)


def _invalidate_edit_mode(body: str, head: str) -> str:
    """Untick every Edit mode box and say why: it described another head.

    The boxes sit outside the machine-owned region but were ticked by the
    composer, so they are its claims to withdraw. Why and Proof prose is
    left exactly as written — a person's justification is not a measurement
    to redo — and the region notice says it is unverified for this head.
    """
    span = _heading_span(body, "### Edit mode")
    if span is None:
        return body
    start, end = span
    chunk = body[start:end]

    def untick(match: re.Match[str]) -> str:
        rest = _EDIT_MODE_SUFFIX_RE.sub("", match.group("rest"))
        return f"- [ ] {rest} — {EDIT_MODE_STALE_PREFIX}; not remeasured by make pr for {head}"

    return body[:start] + _EDIT_MODE_LINE_RE.sub(untick, chunk) + body[end:]


def _protected_remote_notice(facts: MechanicalFacts, old: str) -> str:
    paths = facts.additive_only_paths
    markers = [path for path in paths if path in facts.deletion_markers]
    if not paths:
        measured = "no additive_only root file in this diff"
    elif markers:
        measured = "ALLOW-ROOT-DELETION marker in this branch's commits for " + ", ".join(
            f"`{path}`" for path in markers
        )
    else:
        measured = "no ALLOW-ROOT-DELETION marker for these paths in this branch's commits"
    return (
        f"{PROTECTED_REMOTE_NOTICE_PREFIX}{facts.head}: the list above was measured by the "
        f"governance-pr refresh ({measured}); Edit mode, Why and Proof below were composed by "
        f"make pr at {old or 'an earlier head'} for a different path set or edit mode and "
        "describe that head — make pr recomposes them"
    )


def _refresh_protected_root_remote(body: str, facts: MechanicalFacts) -> str:
    """Protected-root on an event-driven refresh: remeasure, or withdraw.

    The paths are remeasured by the repository's own validator (the caller
    says whether that happened). Declarations that still describe the
    measured set are left exactly as they are. When the set or the edit mode
    moved — a root file newly touched, its change dropped, an
    ALLOW-ROOT-DELETION marker added — the region takes the measured list and
    every composer-ticked Edit mode box is withdrawn, because each of them was
    verified for the head make pr measured, not this one. An unmeasured
    moved head keeps no declaration as current truth either.
    """
    current = region_content(body, REGION_PROTECTED_PATHS)
    if current is None:
        return body
    old = _composed_head(body)
    moved = not old or not facts.head.startswith(old)
    ticked = tuple(_EDIT_MODE_RE.findall(body))
    if not facts.additive_only_measured:
        if _is_placeholder(current):
            return set_region(body, REGION_PROTECTED_PATHS, PROTECTED_REMOTE_UNMEASURED)
        notice = (
            f"{PROTECTED_REMOTE_UNMEASURED}; the declarations composed at "
            f"{old or 'an earlier head'} are unverified for {facts.head}"
        )
        # Nothing moved, or nothing is left to withdraw: no rewrite.
        if not moved or (current in (PROTECTED_REMOTE_UNMEASURED, notice) and not ticked):
            return body
        body = set_region(body, REGION_PROTECTED_PATHS, notice)
        return _invalidate_edit_mode(body, facts.head)
    fresh = render_protected_paths(facts).strip()
    if _is_placeholder(current):
        # Opened from the template, never composed: the measured list is a
        # fact; the untouched boxes and placeholders below claim nothing.
        return set_region(body, REGION_PROTECTED_PATHS, fresh)
    declared = _declared_protected_paths(current)
    already = PROTECTED_REMOTE_NOTICE_PREFIX in current
    if declared == fresh and not already and ticked == _edit_mode_expected(facts):
        return body
    notice = _protected_remote_notice(facts, old)
    body = set_region(body, REGION_PROTECTED_PATHS, f"{fresh}\n{notice}")
    return _invalidate_edit_mode(body, facts.head)


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
        "fields": result.fields,
        "mechanical_filled": result.mechanical_filled,
        "thin_problem": THIN_PROBLEM_NOTE in result.body,
        "commit_count": len(facts.commits),
        "changed_file_count": len(facts.changed_files),
        "additive_only_paths": facts.additive_only_paths,
    }
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


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
    # One region, one place: a second START marker would let a refresh fill one
    # copy and leave the other as a duplicate, divergent inventory.
    errors.extend(
        f"region {name} is declared more than once"
        for name in MACHINE_REGIONS
        if text.count(region_markers(name)[0]) > 1 or text.count(region_markers(name)[1]) > 1
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


def resolve_template(
    workspace: Path,
    owner: str,
    name: str,
    *,
    gh: org_dotgithub.GhApi = org_dotgithub.gh_api,
    git: org_dotgithub.GitRead = org_dotgithub.git_read,
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
            org = org_dotgithub.read_org_file(owner, TEMPLATE_PATH, gh=gh, git=git)
        except org_dotgithub.OrgFileError as exc:
            raise TemplateError(str(exc)) from exc
        sha, text = org.sha, org.text
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
        help="Print only the PR title (the intent title, else this branch's oldest own "
        "commit subject) and exit",
    )
    parser.add_argument(
        "--intent-file",
        type=Path,
        default=None,
        help=f"Author prose ({INTENT_SCHEMA}: title, problem, reviewer_focus, head); "
        f"make pr passes <workspace>/{INTENT_RELPATH} when it exists. Ignored unless "
        "its head is this HEAD",
    )
    parser.add_argument(
        "--print-intent-title",
        action="store_true",
        help="Print the intent file's title for this HEAD, or nothing, and exit. The "
        "open-PR refresh retitles only from this, never from a commit subject",
    )
    parser.add_argument(
        "--check-template",
        action="store_true",
        help="Resolve the canonical org template (--org-owner/--repo-name) and print "
        "TEMPLATE_OK <revision>; exit 2 if it cannot be read. make pr runs this before "
        "pushing, so an unreadable template never leaves a pushed branch with no PR",
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
    if args.check_template:
        source = resolve_template(workspace, args.org_owner, args.repo_name)
        print(f"TEMPLATE_OK {source.revision}")
        return 0

    if args.print_title or args.print_intent_title:
        # Same range the body is told from. open_pr_after_gate.sh used to run its
        # own `git log base..HEAD | head -1`, a second copy of the range rule
        # that titled PR #602 with a main commit.
        facts = collect_mechanical(workspace, pr_base=args.pr_base, verify=False)
        facts.intent = load_intent(args.intent_file, facts.head)
        if args.print_intent_title:
            print(facts.intent.title if facts.intent is not None else "")
        else:
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
    additive_paths = _load_additive_only(args.additive_only_file)
    additive_measured = not args.additive_only_unmeasured
    if args.remote and args.additive_only_file is None and additive_measured:
        # No caller measured the range on the runner. Measure it with the
        # workspace's own validator, or say it is unmeasured — never let the
        # empty default read as "no additive_only root files".
        additive_paths, additive_measured = measure_additive_only(workspace, args.pr_base)
    facts = collect_mechanical(
        workspace,
        pr_base=args.pr_base,
        campaign_body=campaign,
        additive_only_paths=additive_paths,
        additive_only_measured=additive_measured,
        # A remote refresh drops every receipt below; judging them is wasted work.
        verify=not args.remote,
    )
    if args.remote:
        # Whatever .l9 happens to hold on a runner describes no push of this PR.
        facts.gate_receipt = None
        facts.l4_receipt = None
        facts.breakglass = None
    else:
        facts.intent = load_intent(args.intent_file, facts.head)

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
            "NOTE: no commit body states the problem; Problem was composed from the "
            "oldest commit subject and the measured diff",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
