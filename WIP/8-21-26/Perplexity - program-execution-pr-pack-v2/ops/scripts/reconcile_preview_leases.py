#!/usr/bin/env python3
"""ops/scripts/reconcile_preview_leases.py"""
from __future__ import annotations
import argparse, glob, json, time
from pathlib import Path

def sweep(reports_glob, dry_run):
    released = []
    for path_str in glob.glob(reports_glob):
        path = Path(path_str); lease = json.loads(path.read_text())
        if lease["state"] != "active": continue
        if time.time() - lease["claimed_at"] > lease["ttl_seconds"]:
            if not dry_run: lease["state"] = "expired"; path.write_text(json.dumps(lease, indent=2))
            released.append(lease["node_id"])
    return released

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reports-glob", default="reports/*/leases/*.environment_lease.json")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    print(json.dumps({"expired_or_released": sweep(args.reports_glob, args.dry_run), "dry_run": args.dry_run}, indent=2))

if __name__ == "__main__":
    main()
