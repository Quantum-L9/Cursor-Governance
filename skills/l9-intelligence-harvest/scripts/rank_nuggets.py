#!/usr/bin/env python3
import sys

from _common import dump, load_json

PRI = {"PORT": 0, "PORT_WITH_HARDENING": 1, "CONFIGURE": 2, "MERGE_WITH_EXISTING": 3}


def rank(obj):
    viable = []
    for c in obj.get("concepts", []):
        if c.get("nugget"):
            c["rank_score"] = int(c.get("leverage") or 0) * 10 + int(c.get("compounding") or 0)
            viable.append(c)
    viable.sort(key=lambda c: (-c["rank_score"], PRI.get(c.get("disposition"), 99), c["id"]))
    obj["highest_leverage_nugget"] = viable[0]["id"] if viable else None
    return obj


def main():
    obj = rank(load_json(sys.argv[1]))
    dump(obj, sys.argv[2] if len(sys.argv) > 2 else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
