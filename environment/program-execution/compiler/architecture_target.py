"""Deterministic target resolution for architecture-prose compilation.

A missing target is a compiler-resolution problem until the available evidence
is genuinely ambiguous. Resolution is local and deterministic. It never asks a
model to guess which repository may be mutated.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from .architecture_intent import digest, normalize_source, parse_frontmatter

_REPOSITORY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
_GITHUB_URL = re.compile(
    r"https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/"
    r"(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?(?:[/#?\s)`'\"]|$)",
    re.I,
)
_GITHUB_SSH = re.compile(
    r"git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?(?:\s|$)",
    re.I,
)
_LABELED_TARGET = re.compile(
    r"(?im)^\s*(?:target(?:_repo| repository)?|repository)\s*(?:\||:|=|\bis\b)\s*`?"
    r"(?P<repo>[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*)`?\s*$"
)
_SUBJECT_REPOSITORY = re.compile(
    r"(?i)\b(?:architecture|architectural|microscope|audit|review|design)\b"
    r".{0,40}?\b(?:of|for|against)\s+`?"
    r"(?P<repo>[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*)`?"
)


class TargetResolutionError(ValueError):
    """The target cannot be resolved without inventing authority."""


@dataclass(frozen=True)
class TargetResolution:
    repository_id: str
    source: str
    source_sha256: str
    source_candidates: tuple[str, ...] = ()
    authority_candidates: tuple[str, ...] = ()
    reference_candidates: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "repository_id": self.repository_id,
            "source": self.source,
            "source_sha256": self.source_sha256,
            "source_candidates": list(self.source_candidates),
            "authority_candidates": list(self.authority_candidates),
            "reference_candidates": list(self.reference_candidates),
        }


def _clean_repository_id(value: object | None) -> str:
    raw = str(value or "").strip().strip("`'\"()[]{}<>.,;:!? ")
    if raw.endswith(".git"):
        raw = raw[:-4]
    if not _REPOSITORY_ID.fullmatch(raw):
        return ""
    return raw


def repository_from_origin(value: str) -> str:
    """Return owner/repo for a GitHub origin, otherwise an empty string."""
    raw = str(value or "").strip()
    ssh = re.fullmatch(
        r"git@github\.com:(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?",
        raw,
        re.I,
    )
    if ssh:
        return f"{ssh.group('owner')}/{ssh.group('repo')}"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https", "ssh", "git"}:
        return ""
    if (parsed.hostname or "").lower() != "github.com":
        return ""
    parts = [item for item in parsed.path.split("/") if item]
    if len(parts) < 2:
        return ""
    repo = parts[1][:-4] if parts[1].endswith(".git") else parts[1]
    return _clean_repository_id(f"{parts[0]}/{repo}")


def git_origin_repository(path: Path | None) -> str:
    """Read a checkout's GitHub origin without mutating it."""
    if path is None or not Path(path).is_dir():
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", str(Path(path).resolve()), "remote", "get-url", "origin"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return repository_from_origin(result.stdout.strip())


def _dedupe_repositories(values: Iterable[str]) -> tuple[str, ...]:
    found: list[str] = []
    for candidate in values:
        cleaned = _clean_repository_id(candidate)
        if cleaned and cleaned.casefold() not in {item.casefold() for item in found}:
            found.append(cleaned)
    return tuple(found)


def source_authority_candidates(text: str) -> tuple[str, ...]:
    """Repositories the source identifies as its subject/target.

    Only labeled target/repository declarations and architecture-subject phrases
    carry mutation-target authority. Generic GitHub links are references, not
    authority, because architecture documents routinely cite donor repositories.
    """
    return _dedupe_repositories(
        match.group("repo")
        for pattern in (_LABELED_TARGET, _SUBJECT_REPOSITORY)
        for match in pattern.finditer(text)
    )


def source_reference_candidates(text: str) -> tuple[str, ...]:
    """GitHub repositories merely referenced by URL/SSH syntax."""
    return _dedupe_repositories(
        f"{match.group('owner')}/{match.group('repo')}"
        for pattern in (_GITHUB_URL, _GITHUB_SSH)
        for match in pattern.finditer(text)
    )


def source_repository_candidates(text: str) -> tuple[str, ...]:
    """All repositories named by source, preserving authority/reference evidence."""
    return _dedupe_repositories(
        [*source_authority_candidates(text), *source_reference_candidates(text)]
    )


def _same_repository(left: str, right: str) -> bool:
    return left.casefold() == right.casefold()


def _resolution(
    repository_id: str,
    source: str,
    *,
    source_sha256: str,
    all_candidates: tuple[str, ...],
    authority_candidates: tuple[str, ...],
    reference_candidates: tuple[str, ...],
) -> TargetResolution:
    return TargetResolution(
        repository_id=repository_id,
        source=source,
        source_sha256=source_sha256,
        source_candidates=all_candidates,
        authority_candidates=authority_candidates,
        reference_candidates=reference_candidates,
    )


def resolve_architecture_target(
    path: Path,
    *,
    explicit_target: str | None = None,
    target_checkout: Path | None = None,
    repo_root: Path | None = None,
) -> TargetResolution:
    """Resolve the single repository Program Execution is authorized to mutate.

    Precedence:
      1. explicit compiler target;
      2. declared frontmatter target;
      3. one unambiguous source subject/target declaration;
      4. explicitly supplied target-checkout origin;
      5. execution-workspace origin only when the source names no repository;
      6. fail closed.

    Bare GitHub links are references, not mutation-target authority. A target
    checkout may validate a source-declared target but may never silently replace
    a different source target. The normalized source digest is returned so the
    compiler can prove that target resolution and semantic loading saw the same
    bytes.
    """
    source_path = Path(path)
    text = normalize_source(source_path.read_text(encoding="utf-8"))
    source_sha256 = digest(text)
    frontmatter, _ = parse_frontmatter(text)
    explicit = _clean_repository_id(explicit_target)
    declared_raw = frontmatter.get("target") if isinstance(frontmatter, dict) else None
    declared = _clean_repository_id(declared_raw)
    if explicit_target and not explicit:
        raise TargetResolutionError(
            f"explicit target {explicit_target!r} is not a valid owner/repo repository id"
        )
    if declared_raw and not declared:
        raise TargetResolutionError(
            f"declared architecture target {declared_raw!r} is not a valid owner/repo repository id"
        )
    if explicit and declared and not _same_repository(explicit, declared):
        raise TargetResolutionError(
            f"explicit target {explicit} contradicts declared architecture target {declared}"
        )

    authority_candidates = source_authority_candidates(text)
    reference_candidates = source_reference_candidates(text)
    all_candidates = source_repository_candidates(text)
    checkout_origin = git_origin_repository(target_checkout)
    workspace_origin = git_origin_repository(repo_root)

    # All high-authority target evidence must agree. Explicit input has highest
    # precedence for selection, but it is not permission to retarget a document
    # that identifies a different mutation subject or a checkout bound elsewhere.
    # A contradiction is evidence of operator/input mismatch, not a tiebreaker.
    selected_authority = explicit or declared
    if selected_authority:
        conflicting_source = tuple(
            candidate
            for candidate in authority_candidates
            if not _same_repository(selected_authority, candidate)
        )
        if conflicting_source:
            raise TargetResolutionError(
                f"resolved target authority {selected_authority} contradicts source target/subject "
                + ", ".join(conflicting_source)
            )
        if checkout_origin and not _same_repository(selected_authority, checkout_origin):
            raise TargetResolutionError(
                f"resolved target authority {selected_authority} contradicts target-checkout "
                f"origin {checkout_origin}"
            )

    if explicit:
        return _resolution(
            explicit,
            "explicit_target",
            source_sha256=source_sha256,
            all_candidates=all_candidates,
            authority_candidates=authority_candidates,
            reference_candidates=reference_candidates,
        )
    if declared:
        return _resolution(
            declared,
            "declared_frontmatter",
            source_sha256=source_sha256,
            all_candidates=all_candidates,
            authority_candidates=authority_candidates,
            reference_candidates=reference_candidates,
        )
    if len(authority_candidates) > 1:
        raise TargetResolutionError(
            "architecture source names multiple target/subject repositories; Program Execution "
            "will not choose among mutation targets: " + ", ".join(authority_candidates)
        )
    if len(authority_candidates) == 1:
        selected = authority_candidates[0]
        if checkout_origin and not _same_repository(selected, checkout_origin):
            raise TargetResolutionError(
                f"source target {selected} contradicts target-checkout origin {checkout_origin}"
            )
        return _resolution(
            selected,
            "source_authority_repository",
            source_sha256=source_sha256,
            all_candidates=all_candidates,
            authority_candidates=authority_candidates,
            reference_candidates=reference_candidates,
        )
    if checkout_origin:
        return _resolution(
            checkout_origin,
            "target_checkout_origin",
            source_sha256=source_sha256,
            all_candidates=all_candidates,
            authority_candidates=authority_candidates,
            reference_candidates=reference_candidates,
        )
    if reference_candidates:
        raise TargetResolutionError(
            "architecture source contains GitHub repository references but no target/subject "
            "declaration; references are not mutation authority: " + ", ".join(reference_candidates)
        )
    if workspace_origin:
        return _resolution(
            workspace_origin,
            "execution_workspace_origin",
            source_sha256=source_sha256,
            all_candidates=all_candidates,
            authority_candidates=authority_candidates,
            reference_candidates=reference_candidates,
        )
    raise TargetResolutionError(
        "architecture target repository is not derivable from explicit input, declared/source "
        "target authority, target checkout, or an unambiguous execution workspace"
    )


__all__ = [
    "TargetResolution",
    "TargetResolutionError",
    "git_origin_repository",
    "repository_from_origin",
    "resolve_architecture_target",
    "source_authority_candidates",
    "source_reference_candidates",
    "source_repository_candidates",
]
