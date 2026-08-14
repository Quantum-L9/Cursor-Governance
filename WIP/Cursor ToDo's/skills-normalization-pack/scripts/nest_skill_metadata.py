#!/usr/bin/env python3
"""Move non-native SKILL.md frontmatter keys under `metadata:`. Lossless.

Dry-run by default. --apply to write. --archive PATH to dump originals first.
Native top-level keys: name, description, paths, disable-model-invocation, metadata
"""
import argparse, pathlib, re, sys

NATIVE = ["name", "description", "paths", "disable-model-invocation", "metadata"]


def split_fm(text):
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    return text[4:end], text[end + 4:].lstrip("\n")


def parse_fm(raw):
    """Returns list of (key, raw_value_lines). Preserves nesting crudely."""
    entries, cur = [], None
    for line in raw.splitlines():
        if re.match(r"^[A-Za-z_][A-Za-z0-9_.-]*\s*:", line):
            key = line.split(":", 1)[0].strip()
            cur = [key, [line]]
            entries.append(cur)
        elif cur is not None and (line.startswith((" ", "\t")) or line.strip().startswith("-")):
            cur[1].append(line)
        elif line.strip() == "":
            continue
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-dir", default="skills")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--archive")
    ap.add_argument("--include-archived", action="store_true",
                    help="also process skills/_archived/**")
    args = ap.parse_args()

    sd = pathlib.Path(args.skills_dir)
    if not sd.is_dir():
        sys.exit("not found: %s" % sd)

    moved, changed, failed, archive, mismatch = {}, [], [], [], []
    disc_bytes = 0
    live = 0

    for p in sorted(sd.rglob("SKILL.md")):
        is_arch = "_archived" in p.parts
        if is_arch and not args.include_archived:
            continue
        text = p.read_text(encoding="utf-8")
        raw, body = split_fm(text)
        if raw is None:
            failed.append(str(p))
            continue
        entries = parse_fm(raw)
        archive.append((str(p), raw))

        by_key = {k: v for k, v in entries}
        folder = p.parent.name
        name = ""
        if "name" in by_key:
            name = by_key["name"][0].split(":", 1)[1].strip()
        if name and name != folder:
            mismatch.append((str(p), name, folder))

        if not is_arch:
            live += 1
            desc = ""
            if "description" in by_key:
                desc = " ".join(l.strip() for l in by_key["description"])
            disc_bytes += len(name.encode()) + len(desc.encode())

        extras = [(k, v) for k, v in entries if k not in NATIVE]
        for k, _ in extras:
            moved[k] = moved.get(k, 0) + 1

        out = ["---"]
        for key in NATIVE[:-1]:
            if key in by_key:
                out.extend(by_key[key])
        existing_meta = by_key.get("metadata")
        if extras or existing_meta:
            out.append("metadata:")
            if existing_meta:
                for l in existing_meta[1:]:
                    out.append(l if l.startswith("  ") else "  " + l.strip())
            for _, lines in extras:
                for i, l in enumerate(lines):
                    out.append("  " + l.strip() if i == 0 else
                               ("  " + l.strip() if not l.startswith("  ") else l))
        out.append("---")
        new = "\n".join(out) + "\n\n" + body

        if new != text:
            changed.append(str(p))
            if args.apply:
                p.write_text(new, encoding="utf-8")

    if args.archive:
        ar = pathlib.Path(args.archive)
        ar.parent.mkdir(parents=True, exist_ok=True)
        with ar.open("w", encoding="utf-8") as fh:
            fh.write("# Original SKILL.md frontmatter, pre-nesting. Undo record.\n")
            for path, raw in archive:
                fh.write("- path: %s\n  frontmatter: |\n" % path)
                for line in raw.splitlines():
                    fh.write("    %s\n" % line)
        print("archived %d skills -> %s" % (len(archive), ar))

    print("mode: %s" % ("APPLY" if args.apply else "DRY-RUN"))
    print("skills scanned: %d (live: %d), changed: %d, unparseable: %d"
          % (len(archive), live, len(changed), len(failed)))
    if moved:
        print("\nkeys nested under metadata:")
        for k, n in sorted(moved.items(), key=lambda x: -x[1]):
            print("  %-24s %d skill(s)" % (k, n))
    if mismatch:
        print("\nNAME/FOLDER MISMATCH (fix manually - renames break /invocation):")
        for path, name, folder in mismatch:
            print("  %s: name=%r folder=%r" % (path, name, folder))
    if failed:
        print("\nFAILED TO PARSE:")
        for x in failed:
            print("  %s" % x)
    print("\ndiscovery footprint (live name+description): %d bytes (~%d tokens/turn)"
          % (disc_bytes, disc_bytes // 4))
    if not args.apply:
        print("\nre-run with --apply to write changes")


if __name__ == "__main__":
    main()
