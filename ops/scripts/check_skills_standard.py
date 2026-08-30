#!/usr/bin/env python3
"""CI gate for docs/skills-standard.md.

Env:
  SKILLS_DISCOVERY_BUDGET  max bytes of live name+description (default 16384)
"""

from __future__ import annotations

import os
import re
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

BUDGET = int(os.environ.get("SKILLS_DISCOVERY_BUDGET", "16384"))
NATIVE = {"name", "description", "paths", "disable-model-invocation", "metadata"}
DESC_MIN, DESC_MAX = 150, 500
BODY_MAX = 500


def _load_frontmatter(text: str) -> tuple[dict, str] | tuple[None, str]:
    if not text.startswith("---"):
        return None, "no frontmatter"
    end = text.find("\n---", 3)
    if end == -1:
        return None, "unterminated frontmatter"
    raw, body = text[4:end], text[end + 4 :]
    if yaml is None:
        return None, "PyYAML is required"
    fm = yaml.safe_load(raw) or {}
    if not isinstance(fm, dict):
        return None, "frontmatter must be a mapping"
    return fm, body


def is_test_fixture(path: Path) -> bool:
    """True for a SKILL.md that belongs to a pack's test fixtures, not discovery."""
    return "fixtures" in path.parts


def check_skills(root: Path) -> tuple[list[str], list[str], int, int, int]:
    """Return (errors, warnings, live, archived, discovery_bytes)."""
    skills_dir = root / "skills"
    errs: list[str] = []
    warns: list[str] = []
    if not skills_dir.is_dir():
        return [f"skills/ not found under {root}"], [], 0, 0, 0

    disc = 0
    live = 0
    arch = 0
    for path in sorted(skills_dir.rglob("SKILL.md")):
        if is_test_fixture(path):
            # A pack's own test fixtures are never registered in
            # AUTONOMY_MANIFEST.yaml, never symlinked into an adapter, and so
            # cost nothing per turn. Counting them spends the discovery budget
            # on files no agent can ever discover.
            continue
        rel = path.relative_to(root).as_posix()
        is_arch = "_archived" in path.parts
        text = path.read_text(encoding="utf-8", errors="replace")
        loaded = _load_frontmatter(text)
        if loaded[0] is None:
            errs.append(f"{rel}: {loaded[1]}")
            continue
        fm, body = loaded
        extra = set(fm) - NATIVE
        if extra:
            errs.append(
                f"{rel}: non-native top-level keys (nest under metadata): "
                + ", ".join(sorted(extra))
            )

        name = str(fm.get("name") or "")
        if not name:
            errs.append(f"{rel}: missing required `name`")
        else:
            folder = path.parent.name
            if name != folder:
                errs.append(f"{rel}: name {name!r} != folder {folder!r}")
            if not re.fullmatch(r"[a-z0-9-]+", name):
                errs.append(f"{rel}: name {name!r} must be lowercase/numbers/hyphens")

        desc = str(fm.get("description") or "")
        if "description" not in fm:
            errs.append(f"{rel}: missing required `description`")
        elif not is_arch:
            n = len(desc)
            if n < DESC_MIN:
                warns.append(
                    f"{rel}: description {n} chars, under {DESC_MIN} - triggers likely missing"
                )
            elif n > DESC_MAX:
                warns.append(
                    f"{rel}: description {n} chars, over {DESC_MAX} - body leaking into frontmatter"
                )
            if "use when" not in desc.lower() and "use for" not in desc.lower():
                warns.append(f"{rel}: description has no `use when`/`use for` trigger clause")

        dmi = fm.get("disable-model-invocation") is True
        if is_arch:
            arch += 1
            if not dmi:
                errs.append(
                    f"{rel}: archived skill without disable-model-invocation: true "
                    "(prose 'do not activate' is not a mechanism)"
                )
        else:
            live += 1
            disc += len(name.encode()) + len(desc.encode())

        nlines = body.count("\n") + 1
        if nlines > BODY_MAX:
            warns.append(
                f"{rel}: body {nlines} lines exceeds {BODY_MAX} - use progressive disclosure"
            )

        paths = fm.get("paths")
        if "paths" in fm and not paths:
            errs.append(f"{rel}: empty `paths` would hide the skill; remove the key instead")
        elif paths and not dmi and not is_arch:
            # The empty-paths check above was the only one, and it could not catch
            # the case that actually bit: seven skills declared auto_invoke in
            # AUTONOMY_MANIFEST carried a NON-empty `paths` and were absent from
            # every session roster until a matching file was touched. Measured
            # 2026-08-30: 7/7 path-gated skills missing, 0/16 listed skills gated.
            # `paths` reads like a Cursor rule `globs:` (19 rules/*.mdc use that
            # key with this same comma-separated glob syntax) where scoping is
            # free, but for a skill it removes the entry from discovery, so an
            # intent-triggered skill becomes unreachable by the request that
            # should trigger it.
            errs.append(
                f"{rel}: `paths` on a model-invocable skill hides it from the skill listing "
                "until a matching file is in context, so a skill declared auto_invoke is "
                "silently absent. Remove `paths`, or set disable-model-invocation: true to "
                "hide it deliberately."
            )

    if disc > BUDGET:
        errs.append(f"discovery footprint {disc} exceeds budget {BUDGET}")
    return errs, warns, live, arch, disc


def main() -> int:
    root = Path.cwd()
    errs, warns, live, arch, disc = check_skills(root)
    print(f"skills: {live} live, {arch} archived")
    print(f"discovery footprint: {disc} bytes (~{disc // 4} tokens/turn), budget {BUDGET}")
    for warn in warns:
        print(f"  warn: {warn}")
    if errs:
        print(f"\nFAIL ({len(errs)})")
        for err in errs:
            print(f"  - {err}")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
