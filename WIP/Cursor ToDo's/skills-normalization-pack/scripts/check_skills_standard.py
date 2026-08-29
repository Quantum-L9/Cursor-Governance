#!/usr/bin/env python3
"""CI gate for the skill STANDARD.md. Mirrors check_rules_standard.py.

Env:
  SKILLS_DISCOVERY_BUDGET  max bytes of live name+description (default 16384)
"""
import os, re, sys, pathlib

BUDGET = int(os.environ.get("SKILLS_DISCOVERY_BUDGET", "16384"))
NATIVE = {"name", "description", "paths", "disable-model-invocation", "metadata"}
DESC_MIN, DESC_MAX = 150, 500
BODY_MAX = 500

sd = pathlib.Path("skills")
if not sd.is_dir():
    sys.exit("skills/ not found")

errs, warns = [], []
disc = 0
live = arch = 0

for p in sorted(sd.rglob("SKILL.md")):
    rel = str(p)
    is_arch = "_archived" in p.parts
    text = p.read_text(encoding="utf-8", errors="replace")

    if not text.startswith("---"):
        errs.append("%s: no frontmatter" % rel)
        continue
    end = text.find("\n---", 3)
    if end == -1:
        errs.append("%s: unterminated frontmatter" % rel)
        continue
    raw, body = text[4:end], text[end + 4:]

    keys, kv = set(), {}
    for line in raw.splitlines():
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_.-]*)\s*:(.*)$", line)
        if m:
            keys.add(m.group(1))
            kv[m.group(1)] = m.group(2).strip()

    extra = keys - NATIVE
    if extra:
        errs.append("%s: non-native top-level keys (nest under metadata): %s"
                    % (rel, ", ".join(sorted(extra))))

    if "name" not in keys:
        errs.append("%s: missing required `name`" % rel)
    else:
        name = kv["name"]
        folder = p.parent.name
        if name != folder:
            errs.append("%s: name %r != folder %r" % (rel, name, folder))
        if not re.fullmatch(r"[a-z0-9-]+", name):
            errs.append("%s: name %r must be lowercase/numbers/hyphens" % (rel, name))

    if "description" not in keys:
        errs.append("%s: missing required `description`" % rel)
    else:
        desc = kv["description"]
        if not is_arch:
            n = len(desc)
            if n < DESC_MIN:
                warns.append("%s: description %d chars, under %d - triggers likely missing"
                             % (rel, n, DESC_MIN))
            elif n > DESC_MAX:
                warns.append("%s: description %d chars, over %d - body leaking into frontmatter"
                             % (rel, n, DESC_MAX))
            if "use when" not in desc.lower() and "use for" not in desc.lower():
                warns.append("%s: description has no `use when`/`use for` trigger clause" % rel)

    dmi = kv.get("disable-model-invocation", "").lower() in ("true", "yes")
    if is_arch:
        arch += 1
        if not dmi:
            errs.append("%s: archived skill without disable-model-invocation: true "
                        "(prose 'do not activate' is not a mechanism)" % rel)
    else:
        live += 1
        disc += len(kv.get("name", "").encode()) + len(kv.get("description", "").encode())

    nlines = body.count("\n") + 1
    if nlines > BODY_MAX:
        errs.append("%s: body %d lines exceeds %d - use progressive disclosure"
                    % (rel, nlines, BODY_MAX))

    if "paths" in keys and not kv["paths"]:
        errs.append("%s: empty `paths` would hide the skill; remove the key instead" % rel)

print("skills: %d live, %d archived" % (live, arch))
print("discovery footprint: %d bytes (~%d tokens/turn), budget %d"
      % (disc, disc // 4, BUDGET))
if disc > BUDGET:
    errs.append("discovery footprint %d exceeds budget %d" % (disc, BUDGET))

for w in warns:
    print("  warn: %s" % w)
if errs:
    print("\nFAIL (%d)" % len(errs))
    for e in errs:
        print("  - %s" % e)
    sys.exit(1)
print("\nPASS")
