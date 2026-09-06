"""Repository identity and namespace *hints* for memory requests.

Cursor may determine which repository it is in and which namespaces look
relevant. Only ``l9-graphite-memory`` decides whether the principal may read
or write any of them (INV-07). Nothing returned here is an authorization: the
``write_namespace_hint`` is what Cursor will *request* as the single write
namespace (INV-08), and ``read_namespace_hints`` is the fan-in it will
request for hydration. An explicit operator override becomes a requested
namespace, never an authorized one.

The registry consulted is ``ops/graphiti/group_registry.yaml``, reclassified
by this module as alias/request hints (plan §17). The legacy resolver's
``readonly`` verdict is deliberately *not* surfaced as authorization; it is
reduced to a warning about identity confidence.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GRAPHITI_DIR = _REPO_ROOT / "ops" / "graphiti"
if str(_GRAPHITI_DIR) not in sys.path:
    sys.path.insert(0, str(_GRAPHITI_DIR))

from group_resolver import load_registry, resolve_group_id  # noqa: E402

_REMOTE_SLUG = re.compile(r"[:/](?P<owner>[^/:]+)/(?P<name>[^/]+?)(?:\.git)?/?$")


@dataclass(frozen=True)
class NamespaceContext:
    workspace: str
    git_root: str | None
    repository_identity: str | None
    write_namespace_hint: str | None
    read_namespace_hints: tuple[str, ...]
    method: str
    explicit_request: str | None = None
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
            "warnings": list(self.warnings),
            # Stated so no consumer mistakes this for a grant.
            "authorization": "not_decided_here",
        }


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


def repository_identity_for(workspace: Path) -> tuple[str | None, str | None]:
    """``(git_root, owner/name)`` from the checkout's origin remote, if any."""

    root = _git(workspace, "rev-parse", "--show-toplevel")
    remote = _git(workspace, "remote", "get-url", "origin") if root else None
    identity: str | None = None
    if remote:
        match = _REMOTE_SLUG.search(remote)
        if match:
            identity = f"{match.group('owner')}/{match.group('name')}"
    return root, identity


def repository_state_digest(workspace: Path) -> str | None:
    """HEAD commit of the checkout; the truth a stale continuation loses to."""

    return _git(workspace, "rev-parse", "HEAD")


def resolve_namespace_context(
    workspace: str | Path,
    *,
    explicit: str | None = None,
) -> NamespaceContext:
    path = Path(workspace).expanduser().resolve()
    git_root, identity = repository_identity_for(path)
    resolved = resolve_group_id(path, explicit=explicit)
    registry = load_registry()
    workspace_group = str(registry.get("workspace_group") or "")
    forbidden = {str(item) for item in registry.get("forbidden_groups") or []}

    warnings: list[str] = []
    group = resolved.get("group_id")
    method = str(resolved.get("method") or "unresolved")
    write_hint: str | None = None

    if explicit:
        if explicit in forbidden:
            warnings.append(f"explicit namespace request {explicit!r} is forbidden by registry")
        elif resolved.get("error"):
            # The override contradicts the repository match. Memory would
            # refuse the write anyway; say why the hint is absent.
            warnings.append(str(resolved["error"]))
        else:
            write_hint = explicit
            method = "explicit_request"
    elif group and not resolved.get("readonly"):
        write_hint = str(group)
    else:
        warnings.append(
            str(resolved.get("error") or resolved.get("warning") or "no repository match")
        )
        if method == "fallback_readonly":
            method = "no_unique_match"

    read_hints: list[str] = []
    if write_hint:
        read_hints.append(write_hint)
    elif group and group != workspace_group:
        # Identity is plausible but not unique enough to write; still a read hint.
        read_hints.append(str(group))
    if workspace_group and workspace_group not in read_hints:
        read_hints.append(workspace_group)

    return NamespaceContext(
        workspace=str(path),
        git_root=git_root,
        repository_identity=identity,
        write_namespace_hint=write_hint,
        read_namespace_hints=tuple(read_hints),
        method=method,
        explicit_request=explicit,
        warnings=tuple(warnings),
    )


__all__ = [
    "NamespaceContext",
    "repository_identity_for",
    "repository_state_digest",
    "resolve_namespace_context",
]
