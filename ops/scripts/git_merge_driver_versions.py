#!/usr/bin/env python3
"""Git merge driver for module version churn (``merge=l9-versions``).

Invoked by git as ``git_merge_driver_versions.py %O %A %B %P`` (base, ours,
theirs, pathname). The result is written to ``%A``. Exit 0 means a clean merge,
non-zero means git keeps the conflict.

Every PR in an Odoo-style repository bumps the module version and appends a test
import, so each merge into the integration branch made every sibling PR conflict
on the same three lines. This driver resolves exactly those lines and nothing
else:

* ``__manifest__.py``: when both sides changed ``"version"``, take the higher
  version and bump its last component by one, so the merged version is strictly
  higher than both sides. A merge never reuses a version, because an Odoo
  upgrade needs a version strictly higher than anything already installed.
* ``README.md``: front-matter ``module_version:`` gets the same merge function
  over its own three values. The README carries the same value as the manifest
  beside it on every side, so it follows the merged manifest by construction.
  The driver does not read the manifest, because git merges ``README.md``
  before ``__manifest__.py`` (index order) and ``git merge-tree`` has no work
  tree at all.
* ``tests/__init__.py``: when every line on every side is an import, a comment
  or blank, the result is the union of the import lines: ours in order, then
  theirs' additions in theirs' order. A line one side deleted stays deleted.

After the version fields are normalised, the file goes through
``git merge-file``, the same three-way text merge git runs without a driver.
So a conflicting non-version edit still conflicts, and a README without
``module_version`` merges exactly as it would without this attribute. A path
this driver does not recognise always exits non-zero.

Standard library only, plus ``git merge-file``.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

CONFLICT = 1
CLEAN = 0

# "version": "19.0.1.2.3" or 'version': '1.0' in a manifest dict literal.
_MANIFEST_VERSION = re.compile(r"""(['"])version\1\s*:\s*(?P<q>['"])(?P<v>[^'"\n]+)(?P=q)""")
# module_version: 19.0.1.2.3 (optionally quoted) inside YAML front matter.
_README_VERSION = re.compile(
    r"""^module_version:[ \t]*(?P<q>['"]?)(?P<v>[^'"\s]+)(?P=q)[ \t]*$""", re.MULTILINE
)
_VERSION_SHAPE = re.compile(r"^\d+(?:\.\d+)*$")
_IMPORT_LINE = re.compile(r"^\s*(?:from\s+\S+\s+import\s+.+|import\s+.+)$")


def kind_for(pathname: str) -> str | None:
    """Return the resolution kind for a pathname, or None when unrecognised."""
    path = PurePosixPath(pathname)
    if path.name == "__manifest__.py":
        return "manifest"
    if path.name == "README.md":
        return "readme"
    if path.name == "__init__.py" and path.parent.name == "tests":
        return "tests_init"
    return None


def _parse(version: str) -> tuple[int, ...] | None:
    if not _VERSION_SHAPE.match(version):
        return None
    return tuple(int(part) for part in version.split("."))


def merge_versions(base: str | None, ours: str, theirs: str) -> str | None:
    """Merged value for one version field, or None when not mechanical.

    Only one side changed it: that side wins (plain three-way semantics). Both
    sides changed it, even to the same value: the higher one with its last
    component bumped by one, which is strictly above both. Unparseable versions
    are not mechanical.
    """
    both_changed = ours != base and theirs != base
    if not both_changed:
        return ours if theirs == base else theirs
    ours_t, theirs_t = _parse(ours), _parse(theirs)
    if ours_t is None or theirs_t is None:
        return None
    width = max(len(ours_t), len(theirs_t))
    high = max(ours_t + (0,) * (width - len(ours_t)), theirs_t + (0,) * (width - len(theirs_t)))
    return ".".join(str(part) for part in (*high[:-1], high[-1] + 1))


def _single(pattern: re.Pattern[str], text: str) -> re.Match[str] | None:
    """The one version field in text; None when absent or ambiguous."""
    matches = list(pattern.finditer(text))
    return matches[0] if len(matches) == 1 else None


def _find_version(kind: str, text: str) -> re.Match[str] | None:
    if kind == "manifest":
        return _single(_MANIFEST_VERSION, text)
    # README: only inside a leading YAML front-matter block.
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return _single(_README_VERSION, text[:end])


def _set_version(text: str, match: re.Match[str], version: str) -> str:
    start, end = match.span("v")
    return text[:start] + version + text[end:]


def normalise_versions(kind: str, base: str, ours: str, theirs: str) -> tuple[str, str, str | None]:
    """Rewrite ours/theirs so their version fields agree when both changed it.

    Returns (ours, theirs, detail); detail is None when nothing was rewritten.
    """
    m_ours, m_theirs = _find_version(kind, ours), _find_version(kind, theirs)
    if m_ours is None or m_theirs is None:
        return ours, theirs, None
    m_base = _find_version(kind, base)
    v_base = m_base.group("v") if m_base else None
    v_ours, v_theirs = m_ours.group("v"), m_theirs.group("v")
    if v_ours == v_base or v_theirs == v_base:
        # At most one side changed it: the text merge resolves that already.
        return ours, theirs, None
    merged = merge_versions(v_base, v_ours, v_theirs)
    if merged is None:
        return ours, theirs, None
    detail = f"version {v_ours} + {v_theirs} (base {v_base}) -> {merged}"
    return _set_version(ours, m_ours, merged), _set_version(theirs, m_theirs, merged), detail


def _is_import_only(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not _IMPORT_LINE.match(line):
            return False
    return True


def union_imports(base: str, ours: str, theirs: str) -> str | None:
    """Union of tests/__init__.py import lines, or None when not import-only."""
    if not all(_is_import_only(text) for text in (base, ours, theirs)):
        return None
    base_lines = set(base.splitlines())
    theirs_lines = theirs.splitlines()
    theirs_set = set(theirs_lines)
    # Ours in order, minus what theirs deleted from base.
    result = [line for line in ours.splitlines() if line in theirs_set or line not in base_lines]
    present = set(result)
    # Then theirs' additions, in theirs' order.
    for line in theirs_lines:
        if line not in present and line not in base_lines:
            result.append(line)
            present.add(line)
    return "".join(f"{line}\n" for line in result)


def text_merge(base: str, ours: str, theirs: str, pathname: str) -> tuple[str, bool]:
    """``git merge-file`` over three texts. Returns (result, clean)."""
    with tempfile.TemporaryDirectory(prefix="l9-versions-") as tmp:
        root = Path(tmp)
        paths = {}
        for label, content in (("ours", ours), ("base", base), ("theirs", theirs)):
            paths[label] = root / label
            paths[label].write_text(content, encoding="utf-8")
        proc = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [
                "git",
                "merge-file",
                "-L",
                f"ours:{pathname}",
                "-L",
                f"base:{pathname}",
                "-L",
                f"theirs:{pathname}",
                str(paths["ours"]),
                str(paths["base"]),
                str(paths["theirs"]),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        # merge-file exits with the number of conflicts (capped at 127), or a
        # negative / >127 status on error.
        if proc.returncode < 0 or proc.returncode > 127:
            raise RuntimeError(f"git merge-file failed: {proc.stderr.strip()}")
        return paths["ours"].read_text(encoding="utf-8"), proc.returncode == 0


def resolve(base: str, ours: str, theirs: str, pathname: str) -> tuple[str, bool, str]:
    """Merge three texts for pathname. Returns (result, clean, detail).

    A text merge git itself refuses (binary input) leaves ours in place and
    reports a conflict, exactly as git does without a driver.
    """
    try:
        return _resolve(base, ours, theirs, pathname)
    except RuntimeError as exc:
        return ours, False, f"{exc}: left as a conflict"


def _resolve(base: str, ours: str, theirs: str, pathname: str) -> tuple[str, bool, str]:
    kind = kind_for(pathname)
    if kind is None:
        result, _clean = text_merge(base, ours, theirs, pathname)
        return result, False, "unrecognised path: left as a conflict"
    if kind == "tests_init":
        union = union_imports(base, ours, theirs)
        if union is not None:
            return union, True, "tests_init: union of import lines"
        result, clean = text_merge(base, ours, theirs, pathname)
        state = "clean" if clean else "conflicted"
        return result, clean, f"tests_init: not import-only, text merge {state}"
    ours, theirs, detail = normalise_versions(kind, base, ours, theirs)
    result, clean = text_merge(base, ours, theirs, pathname)
    state = "clean" if clean else "conflicted"
    return result, clean, f"{kind}: {detail or 'no version rewrite'}; text merge {state}"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 4:
        print("usage: git_merge_driver_versions.py %O %A %B %P", file=sys.stderr)
        return 2
    base_path, ours_path, theirs_path, pathname = args
    try:
        base, ours, theirs = (
            Path(p).read_text(encoding="utf-8") for p in (base_path, ours_path, theirs_path)
        )
    except (OSError, UnicodeDecodeError) as exc:
        print(f"l9-versions: {pathname}: cannot read merge inputs: {exc}", file=sys.stderr)
        return CONFLICT
    try:
        result, clean, detail = resolve(base, ours, theirs, pathname)
    except OSError as exc:
        print(f"l9-versions: {pathname}: {exc}", file=sys.stderr)
        return CONFLICT
    Path(ours_path).write_text(result, encoding="utf-8")
    print(f"l9-versions: {pathname}: {detail}", file=sys.stderr)
    return CLEAN if clean else CONFLICT


if __name__ == "__main__":
    sys.exit(main())
