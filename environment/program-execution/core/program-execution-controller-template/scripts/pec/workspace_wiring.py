"""What PE generates inside a task worktree, and therefore what is not work.

`ensure_workspace_wired` drops three gitignored links into every task worktree
so a consumer checkout can see governance. Those links are the controller's own
residue, and counting them as worker output would let an empty attempt claim an
implementation. Ignoring them is correct.

Ignoring the directories they happen to sit in is not. The controller used to
suppress `.cursor/rules/`, `.cursor/governance/`, `.claude/` and `.vscode/`
wholesale, so a task whose entire deliverable was a tracked `.cursor/rules/*`
file reported an unmodified worktree: the worker refused to hand off, and scope
verification could not see the change it was meant to judge. A repository's
tracked agent configuration is ordinary source.

This module is the one place that answers the question. The controller and the
worker both read it -- copying the predicate is how the two definitions drifted
apart in the first place.
"""

from __future__ import annotations

from pathlib import Path

# Exactly what ops/scripts/ensure_workspace_wired.sh creates. Two are link
# roots, so their subtrees are generated too; the third is a single file.
GENERATED_LINK_ROOTS = (".cursor-commands", ".cursor/plans")
GENERATED_FILES = (".cursor/governance/CANONICAL_LAW.md",)


def normalize_path(path: str) -> str:
    """Repository-relative posix form, as git reports it."""
    text = str(path).replace("\\", "/").strip()
    if text.startswith("./"):
        text = text[2:]
    return text.rstrip("/")


def is_generated_workspace_wiring(path: str, worktree: Path | None = None) -> bool:
    """True only for an artifact PE itself generated in this worktree.

    `worktree` is accepted so a caller can pass the tree the path belongs to;
    the answer is a property of the wiring contract, not of the checkout, so it
    is not consulted. It stays in the signature because every call site has one,
    and a predicate that silently ignores its scope is worth being explicit
    about rather than dropping.
    """
    del worktree  # the wiring set is fixed; see module docstring
    normalized = normalize_path(path)
    if not normalized:
        return False
    if normalized in GENERATED_FILES:
        return True
    return any(
        normalized == root or normalized.startswith(f"{root}/") for root in GENERATED_LINK_ROOTS
    )


def product_paths(paths: object, worktree: Path | None = None) -> list[str]:
    """The paths that are actually the worker's product, sorted and deduplicated."""
    seen: set[str] = set()
    for path in paths or ():  # type: ignore[union-attr]
        normalized = normalize_path(str(path))
        if normalized and not is_generated_workspace_wiring(normalized, worktree):
            seen.add(normalized)
    return sorted(seen)


def within_writable_path(path: str, writable: object) -> bool:
    """True when `path` is inside one of the contract's declared writable paths.

    A declared path is either the file itself or a directory prefix; the
    contract writes both forms, so both are honoured.
    """
    normalized = normalize_path(path)
    for entry in writable or ():  # type: ignore[union-attr]
        declared = normalize_path(str(entry))
        if not declared:
            continue
        if normalized == declared or normalized.startswith(f"{declared}/"):
            return True
    return False


def relevant_changed_paths(
    paths: object, writable: object, worktree: Path | None = None
) -> list[str]:
    """Changed paths this task was actually authorized to write.

    `HEAD != base_sha` is not evidence that *this* task was implemented: an
    unrelated commit already on the branch satisfies it. The intersection with
    the contract's writable paths is.
    """
    return [
        path
        for path in product_paths(paths, worktree)
        if within_writable_path(path, writable)
    ]
