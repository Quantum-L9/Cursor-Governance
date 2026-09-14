#!/usr/bin/env python3
"""CI gate for STANDARD.md Section 6. Exit non-zero on violation.

Ratchet: set ALWAYS_BUDGET to the current measured value on first commit,
then lower it as retiering lands. Never raise it.
"""
import os, re, sys, pathlib

ALWAYS_BUDGET = int(os.environ.get("RULES_ALWAYS_BUDGET", "12288"))
SINGLE_MAX = 4096
LINE_MAX = 500
NATIVE = {"description", "globs", "alwaysApply"}

rd = pathlib.Path("rules")
errs, warns = [], []

if not rd.is_dir():
    sys.exit("rules/ not found")

md = [p.name for p in rd.glob("*.md") if not p.name.startswith("RULES-MANIFEST")]
if md:
    errs.append("`.md` files in rules/ are ignored by Cursor: %s" % ", ".join(md))

prefixes, always_total, files = {}, 0, 0
for p in sorted(rd.glob("*.mdc")):
    if p.name.startswith("RULES-MANIFEST"):
        continue
    files += 1
    text = p.read_text(encoding="utf-8", errors="replace")
    size = len(text.encode())
    nlines = text.count("\n") + 1

    if " " in p.name:
        errs.append("%s: filename contains a space" % p.name)
    m = re.match(r"^(\d{2})-", p.name)
    if not m:
        errs.append("%s: missing NN- numeric prefix" % p.name)
    else:
        prefixes.setdefault(m.group(1), []).append(p.name)

    if nlines > LINE_MAX:
        errs.append("%s: %d lines exceeds %d" % (p.name, nlines, LINE_MAX))

    if not text.startswith("---"):
        errs.append("%s: no frontmatter" % p.name)
        continue
    end = text.find("\n---", 3)
    if end == -1:
        errs.append("%s: unterminated frontmatter" % p.name)
        continue
    raw = text[4:end]
    keys = set()
    for line in raw.splitlines():
        if ":" in line and not line.strip().startswith(("#", "-")):
            keys.add(line.partition(":")[0].strip())
    extra = keys - NATIVE
    if extra:
        errs.append("%s: non-native frontmatter fields: %s"
                    % (p.name, ", ".join(sorted(extra))))

    aa = re.search(r"^alwaysApply:\s*true\s*$", raw, re.M) is not None
    has_globs = "globs" in keys
    has_desc = "description" in keys

    if aa:
        always_total += size
        if size > SINGLE_MAX:
            errs.append("%s: always-apply rule is %d bytes, over %d"
                        % (p.name, size, SINGLE_MAX))
        if has_globs:
            errs.append("%s: globs present with alwaysApply: true (ignored by Cursor)"
                        % p.name)
    else:
        if not has_globs and not has_desc:
            warns.append("%s: manual-only (no globs, no description)" % p.name)

    if "globs" in keys and re.search(r"^globs:\s*$", raw, re.M):
        errs.append("%s: globs uses YAML list form; use comma-separated string" % p.name)

for pre, names in sorted(prefixes.items()):
    if len(names) > 1:
        errs.append("prefix %s- shared by %d files: %s"
                    % (pre, len(names), ", ".join(sorted(names))))

if always_total > ALWAYS_BUDGET:
    errs.append("always-apply total %d bytes (~%d tokens/turn) exceeds budget %d"
                % (always_total, always_total // 4, ALWAYS_BUDGET))

print("rules checked: %d" % files)
print("always-apply: %d bytes (~%d tokens/turn), budget %d"
      % (always_total, always_total // 4, ALWAYS_BUDGET))
for w in warns:
    print("  warn: %s" % w)
if errs:
    print("\nFAIL (%d)" % len(errs))
    for e in errs:
        print("  - %s" % e)
    sys.exit(1)
print("\nPASS")
