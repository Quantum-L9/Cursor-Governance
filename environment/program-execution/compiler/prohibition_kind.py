"""Tell a filesystem prohibition from a semantic one (W8/S1 split).

A campaign's DO_NOT_BUILD carries two different kinds of rule in one field.
Some are paths -- ``src/**``, ``environment/program-execution/`` -- which the
Controller can match against the files an attempt changed. The rest are
architecture laws in prose: "a second Program Execution runtime or Controller",
"compiler-owned mutable runtime state". Those are enforced by review and
conformance, not by globbing.

Writing a law into ``path_or_pattern`` did not make it enforced; it made the
``do_not_build`` gate report PASS having matched nothing, because a sentence
never appears inside a repository path. Classifying at emission keeps each rule
in a channel that can actually carry it.

The rule is deliberately conservative in favour of ``path``: anything that
still parses as a repo path or glob keeps being matched exactly as before, so
no existing enforcement is lost. Only statements that cannot be paths --
whitespace-bearing prose, chiefly -- are reclassified.
"""

from __future__ import annotations

import re

PATH = "path"
SEMANTIC = "semantic"

#: A repo path or glob: no whitespace, and carrying at least one of a separator,
#: a glob metacharacter, or a file extension. `README` alone is prose here, and
#: is treated as such rather than silently matched as a bare filename.
_PATH_SHAPE = re.compile(r"^[^\s]+$")
_PATH_EVIDENCE = re.compile(r"[/*?\[\]]|\.[A-Za-z0-9]{1,8}$")


def classify(statement: object) -> str:
    """Return ``path`` when ``statement`` can be matched against file paths.

    Anything else is ``semantic``: a real rule that this seam must carry
    without pretending the Controller can glob it.
    """
    if not isinstance(statement, str):
        return SEMANTIC
    candidate = statement.strip()
    if not candidate:
        return SEMANTIC
    if not _PATH_SHAPE.match(candidate):
        return SEMANTIC
    if not _PATH_EVIDENCE.search(candidate):
        return SEMANTIC
    return PATH


def entry(
    *,
    identifier: str,
    statement: str,
    reason: str,
    detection: str,
    exception_authority: str,
) -> dict[str, object]:
    """Build one DO_NOT_BUILD entry in the channel its statement belongs to.

    A path entry keeps ``path_or_pattern`` so the Controller matches it. A
    semantic entry deliberately omits that field -- there is nothing to glob --
    and keeps the statement where a reviewer and the conformance suite read it.
    """
    kind = classify(statement)
    row: dict[str, object] = {
        "id": identifier,
        "kind": kind,
        "statement": statement,
        "reason": reason,
        "detection": detection,
        "exception_authority": exception_authority,
    }
    if kind == PATH:
        row["path_or_pattern"] = statement
    return row
