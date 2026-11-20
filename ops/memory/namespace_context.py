"""Repository identity and namespace *hints* for memory requests (plan §17).

Cursor may determine which repository it is in and which namespaces look
relevant. Only ``l9-graphite-memory`` decides whether the principal may read
or write any of them (INV-07). Nothing returned here is an authorization:
``write_namespace_hint`` is what Cursor will *request* as the single write
namespace (INV-08), and ``read_namespace_hints`` is the fan-in it will
request for hydration; memory answers each request on its own terms. An
explicit operator override becomes a requested namespace, never an
authorized one.

Stage C2 made this module the only producer of identity and hints. The
registry it consults, ``ops/graphiti/group_registry.yaml``, is reclassified
as alias/request hints: repository slugs, remote patterns, path hints, and
the shared namespaces Cursor may *ask* to read. The legacy resolver shim
(``ops/graphiti/group_resolver.py``) was deleted at stage C11; its
``readonly`` verdict was never an authorization and survives only as the
identity-confidence warning this module emits.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = _REPO_ROOT / "ops" / "graphiti" / "group_registry.yaml"

#: An explicit namespace *request* from the operator. It is recorded and
#: forwarded; memory decides whether the principal may use it.
ENV_NAMESPACE_REQUEST = "L9_MEMORY_NAMESPACE_REQUEST"

_REMOTE_SLUG = re.compile(r"[:/](?P<owner>[^/:]+)/(?P<name>[^/]+?)(?:\.git)?/?$")

METHOD_REGISTRY = "registry"
METHOD_EXPLICIT = "explicit_request"
METHOD_AMBIGUOUS = "ambiguous"
METHOD_UNRESOLVED = "unresolved"
#: A repository with an origin remote but no registry entry (operator decision
#: 2026-11-20: memory works in any checked-out repository). The namespace is
#: derived deterministically from ``owner/name``; it is a request, never a grant.
METHOD_DERIVED = "derived_from_remote"
#: The memory store's namespace grammar (l9_graphite_memory projection names).
_NAMESPACE_GRAMMAR = re.compile(r"^[a-z][a-z0-9-]{0,61}$")


# ---------------------------------------------------------------------------
# Registry (hints, never grants)
# ---------------------------------------------------------------------------


def load_registry(path: Path | None = None) -> dict[str, Any]:
    with open(path or REGISTRY_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def shared_read_namespaces(registry: Mapping[str, Any]) -> tuple[str, ...]:
    """Namespaces Cursor may *ask* to read alongside its own (memory decides)."""

    raw = registry.get("shared_read_namespaces") or []
    return tuple(str(item) for item in raw if str(item).strip())


def forbidden_namespaces(registry: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(str(item) for item in registry.get("forbidden_groups") or [])


def aliases_for(registry: Mapping[str, Any], slug: str) -> tuple[str, ...]:
    """GitHub identities this slug is known under (renames, moves)."""

    config = (registry.get("repos") or {}).get(slug) or {}
    names = [config.get("github"), *(config.get("github_aliases") or [])]
    return tuple(str(name) for name in names if name)


def legacy_namespaces_for(registry: Mapping[str, Any], slug: str) -> tuple[str, ...]:
    """Namespaces a renamed slug wrote under before; read so history stays reachable."""

    config = (registry.get("repos") or {}).get(slug) or {}
    return tuple(str(n) for n in config.get("legacy_namespaces") or [] if str(n).strip())


def derive_namespace(identity: str | None) -> str | None:
    """A namespace for an unregistered repository, from its ``owner/name``.

    Lowercase, every run of other characters becomes one hyphen, owner and name
    joined by a hyphen (``acme/My_Repo`` -> ``acme-my-repo``). ``None`` when the
    result does not fit the memory store's grammar.
    """

    if not identity or "/" not in identity:
        return None
    candidate = re.sub(r"[^a-z0-9]+", "-", identity.lower()).strip("-")
    return candidate if _NAMESPACE_GRAMMAR.match(candidate) else None


def match_registry_slugs(
    registry: Mapping[str, Any], *, remote: str | None, path_parts: set[str]
) -> list[str]:
    """Sorted registry slugs whose remote patterns or path hints match.

    The origin remote is the stronger evidence: when any slug matches it, only
    remote matches are returned, so a checkout nested inside another
    repository's tree (whose path carries both names) resolves to its own
    identity. Path hints decide only when no remote matched, and they are
    anchored to whole path segments: a hint matches only when it equals one
    of the directory components, never as a substring.
    """

    repos: Mapping[str, Any] = registry.get("repos") or {}
    by_remote: list[str] = []
    by_path: list[str] = []
    for slug, config in repos.items():
        if remote and any(
            fnmatch(remote, pattern) for pattern in config.get("remote_patterns") or []
        ):
            by_remote.append(slug)
        if any(hint in path_parts for hint in config.get("path_hints") or []):
            by_path.append(slug)
    return sorted(set(by_remote or by_path))


# ---------------------------------------------------------------------------
# Git probes (identity evidence)
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def git_toplevel(cwd: Path) -> Path | None:
    top = _git(cwd, "rev-parse", "--show-toplevel")
    return Path(top).resolve() if top else None


def git_remote_url(cwd: Path) -> str | None:
    return _git(cwd, "remote", "get-url", "origin")


def child_git_roots(cwd: Path) -> list[Path]:
    """Immediate child directories that are git work trees.

    ``$HOME`` is never a workspace: scanning its child clones matches every
    sibling repository and returns an ambiguous identity.
    """

    try:
        resolved = cwd.resolve()
        if resolved == Path.home().resolve():
            return []
    except OSError:
        return []
    roots: list[Path] = []
    try:
        for child in resolved.iterdir():
            if child.is_dir() and (child / ".git").exists():
                roots.append(child.resolve())
    except OSError:
        return []
    return roots


def repository_matches(registry: Mapping[str, Any], cwd: Path) -> list[str]:
    return match_registry_slugs(registry, remote=git_remote_url(cwd), path_parts=set(cwd.parts))


def repository_identity_for(workspace: Path) -> tuple[str | None, str | None]:
    """``(git_root, owner/name)`` from the checkout's origin remote, if any."""

    root = git_toplevel(workspace)
    remote = git_remote_url(workspace) if root else None
    identity: str | None = None
    if remote:
        match = _REMOTE_SLUG.search(remote)
        if match:
            identity = f"{match.group('owner')}/{match.group('name')}"
    return (str(root) if root else None), identity


def repository_state_digest(workspace: Path) -> str | None:
    """HEAD commit of the checkout; the truth a stale continuation loses to."""

    return _git(workspace, "rev-parse", "HEAD")


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NamespaceContext:
    workspace: str
    git_root: str | None
    repository_identity: str | None
    write_namespace_hint: str | None
    read_namespace_hints: tuple[str, ...]
    method: str
    explicit_request: str | None = None
    #: Registry slugs the workspace plausibly is (more than one = ambiguous).
    candidates: tuple[str, ...] = ()
    #: GitHub identities the resolved slug is known under.
    aliases: tuple[str, ...] = ()
    #: The enclosing checkout when this workspace is a nested child repository.
    parent_git_root: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def has_write_hint(self) -> bool:
        return self.write_namespace_hint is not None

    def as_dict(self) -> dict[str, object]:
        return {
            "workspace": self.workspace,
            "git_root": self.git_root,
            "repository_identity": self.repository_identity,
            "write_namespace_hint": self.write_namespace_hint,
            "read_namespace_hints": list(self.read_namespace_hints),
            "method": self.method,
            "explicit_request": self.explicit_request,
            "candidates": list(self.candidates),
            "aliases": list(self.aliases),
            "parent_git_root": self.parent_git_root,
            "warnings": list(self.warnings),
            # Stated so no consumer mistakes this for a grant.
            "authorization": "not_decided_here",
        }


def _candidates(registry: Mapping[str, Any], path: Path) -> tuple[list[str], str | None]:
    """Registry slugs for the workspace, and the enclosing checkout if nested."""

    matches = repository_matches(registry, path)
    toplevel = git_toplevel(path)
    if not matches and toplevel is not None and toplevel != path:
        matches = repository_matches(registry, toplevel)
    if not matches:
        hits: list[str] = []
        for root in child_git_roots(path):
            hits.extend(repository_matches(registry, root))
        matches = sorted(set(hits))
    parent: str | None = None
    if toplevel is not None:
        above = git_toplevel(toplevel.parent) if toplevel.parent != toplevel else None
        if above is not None and above != toplevel:
            parent = str(above)
    return matches, parent


def resolve_namespace_context(
    workspace: str | Path,
    *,
    explicit: str | None = None,
    env: Mapping[str, str] | None = None,
    registry: Mapping[str, Any] | None = None,
) -> NamespaceContext:
    path = Path(workspace).expanduser().resolve()
    environment = os.environ if env is None else env
    registry = load_registry() if registry is None else registry
    forbidden = forbidden_namespaces(registry)
    shared = shared_read_namespaces(registry)

    git_root, identity = repository_identity_for(path)
    candidates, parent_root = _candidates(registry, path)
    requested = (explicit or environment.get(ENV_NAMESPACE_REQUEST) or "").strip() or None

    warnings: list[str] = []
    write_hint: str | None = None
    method = METHOD_UNRESOLVED
    resolved_slug: str | None = None

    if requested:
        method = METHOD_EXPLICIT
        if requested in forbidden:
            warnings.append(f"explicit namespace request {requested!r} is forbidden by registry")
        elif candidates and requested not in candidates:
            # The request contradicts what the checkout is. Memory would
            # decide anyway; Cursor does not forward a write hint it knows
            # to be a different repository's identity.
            shown = candidates[0] if len(candidates) == 1 else f"one of {candidates}"
            warnings.append(
                f"explicit namespace request {requested!r} contradicts repository identity {shown}"
            )
        else:
            write_hint = requested
            resolved_slug = requested if requested in candidates else None
    elif len(candidates) == 1:
        method = METHOD_REGISTRY
        write_hint = candidates[0]
        resolved_slug = candidates[0]
    elif len(candidates) > 1:
        method = METHOD_AMBIGUOUS
        warnings.append(
            f"ambiguous repository identity {candidates}; set {ENV_NAMESPACE_REQUEST} "
            "to request one"
        )
    else:
        derived = derive_namespace(identity) if git_root else None
        registered = set((registry.get("repos") or {}).keys())
        if derived and derived not in forbidden and derived not in registered:
            method = METHOD_DERIVED
            write_hint = derived
            warnings.append(
                f"repository {identity} is not in the namespace registry; "
                f"namespace {derived!r} is derived from its origin remote"
            )
        else:
            warnings.append("no repository match in the namespace registry")

    read_hints: list[str] = []
    if write_hint:
        read_hints.append(write_hint)
    if resolved_slug:
        # A renamed slug keeps its history readable under the old namespace.
        for legacy in legacy_namespaces_for(registry, resolved_slug):
            if legacy not in read_hints and legacy not in forbidden:
                read_hints.append(legacy)
    elif len(candidates) == 1:
        # Identity is plausible but the request contradicted it: still a read hint.
        read_hints.append(candidates[0])
    for namespace in shared:
        if namespace not in read_hints:
            read_hints.append(namespace)

    return NamespaceContext(
        workspace=str(path),
        git_root=git_root,
        repository_identity=identity,
        write_namespace_hint=write_hint,
        read_namespace_hints=tuple(read_hints),
        method=method,
        explicit_request=requested,
        candidates=tuple(candidates),
        aliases=aliases_for(registry, resolved_slug) if resolved_slug else (),
        parent_git_root=parent_root,
        warnings=tuple(warnings),
    )


#: What a best-effort ``Path.resolve()`` can raise here. A permission or
#: missing-component fault surfaces as OSError, but CPython reports a symlink
#: loop as RuntimeError on 3.12 (only later versions fold it into OSError), so
#: catching OSError alone still let the canonical broken-link case crash write
#: routing.
_RESOLVE_ERRORS = (OSError, RuntimeError)


def locate_clone_for_namespace(
    slug: str, *, from_workspace: str | Path | None = None
) -> Path | None:
    """Find a local checkout whose registry identity is ``slug``.

    Used when a remediator session is sitting in Cursor-Governance but the
    write is for another registered repo. The grant is cwd-scoped, so the
    write must run at that clone — this is not a second prefetch.
    """

    registry = load_registry()
    config = (registry.get("repos") or {}).get(slug) or {}
    hints = [str(item) for item in config.get("path_hints") or [] if str(item).strip()]
    # Resolution is best-effort throughout this helper: the roots loop below
    # already treats an OSError from `.resolve()` as "skip this hint, keep
    # looking". This first resolution bypassed that and raised instead, so a
    # broken symlink or an unreadable parent on the *starting* path crashed
    # write routing rather than degrading to "no clone located" — which the
    # caller already handles by staying in the session workspace.
    raw_start = Path(from_workspace or os.getcwd()).expanduser()
    try:
        start = raw_start.resolve()
    except _RESOLVE_ERRORS:
        # An unreadable start is "no clone located". Searching Path.home()
        # from here finds whatever checkout the host happens to have.
        return None
    if not start.is_dir():
        return None
    try:
        if slug in repository_matches(registry, start):
            return start
    except _RESOLVE_ERRORS:
        # Start path is not this slug or cannot be read; keep looking.
        pass
    roots: list[Path] = []
    for raw in (start, start.parent, Path.home()):
        try:
            resolved = raw.resolve()
        except _RESOLVE_ERRORS:
            continue
        if resolved not in roots:
            roots.append(resolved)
    for root in roots:
        for hint in hints:
            candidate = root / hint
            if not candidate.is_dir():
                continue
            if not ((candidate / ".git").exists() or (candidate / ".git").is_file()):
                continue
            if slug in repository_matches(registry, candidate):
                return candidate.resolve()
    return None


#: Exclusion reason for a second checkout of an already-selected repository.
DROPPED_DUPLICATE_NAMESPACE = "duplicate_namespace"


@dataclass(frozen=True)
class WorkspaceNamespaces:
    """Per-repository write namespaces for a workspace that may hold several.

    A namespace identifies a REPOSITORY, never a container. A cloud container
    root (several checkouts side by side) is correctly ambiguous for one write
    hint, so callers that report readiness must resolve each repository root
    instead. Root selection is the shared ``select_workspace_roots`` with the
    same cap and predicate the SessionStart prefetch hydrates under, so this
    report and the hydrated set cannot disagree.
    """

    workspace: str
    multi_repo: bool
    namespaces: tuple[tuple[str, str], ...]
    excluded: tuple[tuple[str, str], ...]

    @property
    def resolved(self) -> bool:
        return bool(self.namespaces)


def select_namespace_roots(
    workspace: str | Path,
    *,
    cap: int | None = None,
    registry: Mapping[str, Any] | None = None,
):
    """The repository roots in memory scope for ``workspace``: one per namespace.

    The single selection both SessionStart hydration
    (``memory_prefetch._hydration_selection``) and the bootstrap readiness
    report use, so what is reported in scope is exactly what is hydrated.
    It is the shared ``select_workspace_roots`` with a predicate that admits a
    root only when it resolves to a write namespace of its OWN that no earlier
    root already claimed. A second checkout of one repository (a linked
    worktree beside its clone) must not take a slot under the cap and push a
    distinct repository out of scope; it is returned in ``dropped`` as
    ``duplicate_namespace``. A resolver fault never drops a root.
    """

    from ops.scripts.lib.workspace_roots import (  # noqa: PLC0415
        DEFAULT_MAX_ROOTS,
        RootSelection,
        select_workspace_roots,
    )

    path = Path(workspace).expanduser().resolve()
    reg = load_registry() if registry is None else registry
    claimed: set[str] = set()
    duplicates: list[tuple[Path, str]] = []

    def _eligible(root: Path) -> bool:
        # Broad by design: a resolver fault must not drop a root.
        # nosemgrep: l9.baseline.python.broad-except
        try:
            namespace = resolve_namespace_context(root, registry=reg, env={}).write_namespace_hint
        except Exception:  # noqa: BLE001
            return True
        if not namespace:
            return False
        if namespace in claimed:
            duplicates.append((root, DROPPED_DUPLICATE_NAMESPACE))
            return False
        claimed.add(namespace)
        return True

    selection = select_workspace_roots(
        path,
        cap=DEFAULT_MAX_ROOTS if cap is None else cap,
        predicate=_eligible,
    )
    duplicate_roots = {root for root, _ in duplicates}
    dropped = [item for item in selection.dropped if item[0] not in duplicate_roots]
    return RootSelection(selection.selected, dropped + duplicates)


def resolve_workspace_namespaces(
    workspace: str | Path,
    *,
    cap: int | None = None,
    registry: Mapping[str, Any] | None = None,
) -> WorkspaceNamespaces:
    """Write namespace per repository root in memory scope for ``workspace``.

    The roots are ``select_namespace_roots``: the same set SessionStart
    hydrates. A single repository yields its own namespace; a container
    yields one entry per selected repository, and every excluded child with
    the rule that excluded it (``cap``, ``no_namespace``,
    ``duplicate_namespace``).
    """

    from ops.scripts.lib.workspace_roots import is_repository  # noqa: PLC0415

    path = Path(workspace).expanduser().resolve()
    reg = load_registry() if registry is None else registry
    selection = select_namespace_roots(path, cap=cap, registry=reg)
    pairs = [
        (str(root), ns)
        for root in selection.selected
        if (ns := resolve_namespace_context(root, registry=reg, env={}).write_namespace_hint)
    ]
    return WorkspaceNamespaces(
        workspace=str(path),
        multi_repo=not is_repository(path) and bool(pairs),
        namespaces=tuple(pairs),
        excluded=tuple((str(root), reason) for root, reason in selection.dropped),
    )


__all__ = [
    "DROPPED_DUPLICATE_NAMESPACE",
    "ENV_NAMESPACE_REQUEST",
    "METHOD_AMBIGUOUS",
    "METHOD_DERIVED",
    "METHOD_EXPLICIT",
    "METHOD_REGISTRY",
    "METHOD_UNRESOLVED",
    "REGISTRY_PATH",
    "NamespaceContext",
    "WorkspaceNamespaces",
    "aliases_for",
    "child_git_roots",
    "derive_namespace",
    "forbidden_namespaces",
    "git_remote_url",
    "git_toplevel",
    "legacy_namespaces_for",
    "load_registry",
    "locate_clone_for_namespace",
    "match_registry_slugs",
    "repository_identity_for",
    "repository_matches",
    "repository_state_digest",
    "resolve_namespace_context",
    "resolve_workspace_namespaces",
    "select_namespace_roots",
    "shared_read_namespaces",
]
