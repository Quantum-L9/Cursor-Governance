#!/usr/bin/env python3
"""Normalize rules/*.mdc frontmatter to Cursor-native fields only.

Dry-run by default. Pass --apply to write. Pass --archive PATH to dump
original frontmatter first.

Keeps only: description, globs, alwaysApply (in that order).
Drops globs when alwaysApply is true (Cursor ignores them).
Converts YAML-list globs to comma-separated string form.
"""
import argparse, pathlib, re, sys

NATIVE = ("description", "globs", "alwaysApply")


def split_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    return text[4:end], text[end + 4:].lstrip("\n")


def parse_fm(raw):
    fields, order, key = {}, [], None
    for line in raw.splitlines():
        if re.match(r"^\s*-\s+", line) and key:
            fields[key].append(line.strip()[1:].strip().strip('"\''))
        elif ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            key = k.strip()
            v = v.strip()
            if v == "":
                fields[key] = []
            elif v.startswith("[") and v.endswith("]"):
                inner = v[1:-1].strip()
                fields[key] = [x.strip().strip('"\'') for x in inner.split(",") if x.strip()]
            else:
                fields[key] = v.strip('"\'')
            order.append(key)
    return fields, order


def as_globs(val):
    if isinstance(val, list):
        return ", ".join(val)
    return str(val)


def build_fm(fields, dropped):
    aa = str(fields.get("alwaysApply", "false")).lower() in ("true", "yes")
    out = ["---"]
    if fields.get("description"):
        desc = str(fields["description"]).replace('"', "'")
        out.append("description: %s" % desc)
    if not aa:
        g = as_globs(fields.get("globs", ""))
        if g:
            out.append("globs: %s" % g)
    elif fields.get("globs"):
        dropped.setdefault("globs (ignored under alwaysApply)", 0)
        dropped["globs (ignored under alwaysApply)"] += 1
    out.append("alwaysApply: %s" % ("true" if aa else "false"))
    out.append("---")
    return "\n".join(out) + "\n\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules-dir", default="rules")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--archive")
    args = ap.parse_args()

    rd = pathlib.Path(args.rules_dir)
    if not rd.is_dir():
        sys.exit("not found: %s" % rd)

    dropped, changed, failed, archive = {}, [], [], []
    before = after = 0

    for p in sorted(rd.glob("*.mdc")):
        if p.name.startswith("RULES-MANIFEST"):
            continue
        text = p.read_text(encoding="utf-8")
        raw, body = split_fm(text)
        if raw is None:
            failed.append(p.name)
            continue
        fields, order = parse_fm(raw)
        archive.append((p.name, dict(fields)))
        aa = str(fields.get("alwaysApply", "false")).lower() in ("true", "yes")
        size = len(text.encode())
        if aa:
            before += size
        for k in order:
            if k not in NATIVE:
                dropped[k] = dropped.get(k, 0) + 1
        new = build_fm(fields, dropped) + body
        if new != text:
            changed.append((p.name, len(text) - len(new)))
            if args.apply:
                p.write_text(new, encoding="utf-8")
        if aa:
            after += len(new.encode())

    if args.archive:
        ar = pathlib.Path(args.archive)
        ar.parent.mkdir(parents=True, exist_ok=True)
        with ar.open("w", encoding="utf-8") as fh:
            fh.write("# Original frontmatter, pre-normalization. Undo record.\n")
            for name, fields in archive:
                fh.write("%s:\n" % name)
                for k, v in fields.items():
                    fh.write("  %s: %r\n" % (k, v))
        print("archived %d files -> %s" % (len(archive), ar))

    print("mode: %s" % ("APPLY" if args.apply else "DRY-RUN"))
    print("files scanned: %d, changed: %d, unparseable: %d"
          % (len(archive), len(changed), len(failed)))
    if dropped:
        print("\nnon-native fields removed:")
        for k, n in sorted(dropped.items(), key=lambda x: -x[1]):
            print("  %-40s %d file(s)" % (k, n))
    if failed:
        print("\nFAILED TO PARSE: %s" % ", ".join(failed))
    print("\nalways-apply bytes: %d -> %d (delta %+d, ~%+d tokens/turn)"
          % (before, after, after - before, (after - before) // 4))
    if not args.apply:
        print("\nre-run with --apply to write changes")


if __name__ == "__main__":
    main()
