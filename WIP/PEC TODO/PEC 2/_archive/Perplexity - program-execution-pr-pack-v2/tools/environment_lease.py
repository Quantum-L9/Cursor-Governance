#!/usr/bin/env python3
"""tools/environment_lease.py"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path

def lease_path(reports_dir, node_id):
    d = reports_dir / "leases"; d.mkdir(parents=True, exist_ok=True); return d / f"{node_id}.environment_lease.json"

def load_all_leases(reports_dir):
    d = reports_dir / "leases"
    return [json.loads(p.read_text()) for p in d.glob("*.environment_lease.json")] if d.exists() else []

def cmd_claim(args):
    reports_dir = Path(args.reports_dir)
    for lease in load_all_leases(reports_dir):
        if lease["state"] != "active": continue
        if args.db_branch and lease["resources"].get("db_branch") == args.db_branch:
            raise SystemExit(f"FAIL: db_branch '{args.db_branch}' already leased by {lease['node_id']}")
        if args.port_range:
            a_start, a_end = args.port_range
            b_start, b_end = lease["resources"].get("port_range", [0, 0])
            if a_start <= b_end and b_start <= a_end:
                raise SystemExit(f"FAIL: port range overlaps lease held by {lease['node_id']}")
    lease = {"node_id": args.node_id, "worktree": args.worktree,
              "resources": {"db_branch": args.db_branch, "preview_url": args.preview_url, "port_range": args.port_range},
              "claimed_at": time.time(), "ttl_seconds": args.ttl, "state": "active"}
    lease_path(Path(args.reports_dir), args.node_id).write_text(json.dumps(lease, indent=2))
    print(f"PASS: claimed environment lease for {args.node_id}")

def cmd_release(args):
    path = lease_path(Path(args.reports_dir), args.node_id)
    if not path.exists(): print(f"PASS: no lease found for {args.node_id} (already released)"); return
    lease = json.loads(path.read_text()); lease["state"] = "released"
    path.write_text(json.dumps(lease, indent=2))
    print(f"PASS: released environment lease for {args.node_id}")

def cmd_verify(args):
    path = lease_path(Path(args.reports_dir), args.node_id)
    if not path.exists(): raise SystemExit(f"FAIL: no lease found for {args.node_id}")
    lease = json.loads(path.read_text())
    age = time.time() - lease["claimed_at"]
    if lease["state"] != "active": raise SystemExit(f"FAIL: lease for {args.node_id} is {lease['state']}, not active")
    if age > lease["ttl_seconds"]: raise SystemExit(f"FAIL: lease for {args.node_id} expired ({age:.0f}s > {lease['ttl_seconds']}s)")
    if args.expect_db_branch and lease["resources"].get("db_branch") != args.expect_db_branch:
        raise SystemExit(f"FAIL: EN003 mismatch: leased={lease['resources'].get('db_branch')} actual={args.expect_db_branch}")
    print(f"PASS: lease for {args.node_id} is active and consistent")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reports-dir", required=True)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("claim")
    c.add_argument("--node-id", required=True, dest="node_id"); c.add_argument("--worktree", required=True)
    c.add_argument("--db-branch", dest="db_branch"); c.add_argument("--preview-url", dest="preview_url")
    c.add_argument("--port-range", nargs=2, type=int, dest="port_range"); c.add_argument("--ttl", type=int, default=3600)
    c.set_defaults(func=cmd_claim)
    r = sub.add_parser("release"); r.add_argument("--node-id", required=True, dest="node_id"); r.set_defaults(func=cmd_release)
    v = sub.add_parser("verify"); v.add_argument("--node-id", required=True, dest="node_id")
    v.add_argument("--expect-db-branch", dest="expect_db_branch"); v.set_defaults(func=cmd_verify)
    args = p.parse_args(); args.func(args)

if __name__ == "__main__":
    main()
