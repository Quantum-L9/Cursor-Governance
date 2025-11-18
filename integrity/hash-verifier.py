#!/usr/bin/env python3
# Version: 1.0.0
Canonical-Source: 10X Governance Suite
Generated: 2025-10-06T17:22:56Z

"""
hash-verifier.py
- Snapshot mode: build/update integrity/manifest-lock.json with SHA-256 and Base64 snapshots
- Verify mode: compare current files to manifest
- Repair mode: restore missing/modified files from manifest
Logs to: /ops/logs/integrity_report.json and /ops/logs/integrity_activity.log
"""

import os, sys, json, hashlib, base64, datetime
from pathlib import Path

ROOT = Path.cwd()
INTEGRITY_DIR = ROOT / "integrity"
MANIFEST_PATH = INTEGRITY_DIR / "manifest-lock.json"
OPS_LOG_DIR = ROOT / "ops" / "logs"
META_AUDIT = ROOT / "intelligence" / "meta-audit.md"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def b64_file(p: Path) -> str:
    with open(p, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def load_manifest():
    if not MANIFEST_PATH.exists():
        return None
    return json.loads(MANIFEST_PATH.read_text())

def save_manifest(data):
    MANIFEST_PATH.write_text(json.dumps(data, indent=2))

def ensure_logs():
    OPS_LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_activity(msg: str):
    ensure_logs()
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(OPS_LOG_DIR / "integrity_activity.log", "a") as f:
        f.write(f"[{stamp}] {msg}\n")

def write_report(payload: dict):
    ensure_logs()
    (OPS_LOG_DIR / "integrity_report.json").write_text(json.dumps(payload, indent=2))

def update_meta_audit(title: str, details: str):
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    META_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    if not META_AUDIT.exists():
        META_AUDIT.write_text("")
    with open(META_AUDIT, "a") as f:
        f.write(f"\n## Integrity Reflection — {stamp}\n**{title}**\n{details}\n")

def should_exclude(path: Path, excludes):
    for ex in excludes:
        parts = [p for p in path.parts]
        if ex in parts or (str(path).startswith(str(ROOT / ex))):
            return True
    if str(path).startswith(str(INTEGRITY_DIR)):
        return True
    return False

def iter_governed_files(roots, excludes):
    for root_rel in roots:
        base = ROOT / root_rel
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and not should_exclude(p.relative_to(ROOT), excludes):
                yield p

def snapshot():
    manifest = load_manifest()
    if manifest is None:
        manifest = {
            "version": "1.0.0",
            "generated": "",
            "roots": [".cursor", "commands", "pipeline", "security", "ops", "intelligence"],
            "excludes": ["integrity"],
            "files": []
        }
    files = []
    for p in iter_governed_files(manifest["roots"], manifest.get("excludes", [])):
        rel = str(p.relative_to(ROOT))
        files.append({
            "path": rel,
            "sha256": sha256_file(p),
            "b64": b64_file(p)
        })
    manifest["files"] = files
    manifest["generated"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    save_manifest(manifest)
    log_activity(f"Snapshot created with {len(files)} files.")
    update_meta_audit("Snapshot Created", f"Total files snapshotted: {len(files)}")
    write_report({"mode": "snapshot", "timestamp": manifest["generated"], "files": len(files)})

def verify_and_repair(auto_repair=True):
    manifest = load_manifest()
    if manifest is None or not manifest.get("files"):
        log_activity("No manifest found; running snapshot instead of verify.")
        snapshot()
        return
    cur = {}
    for p in iter_governed_files(manifest["roots"], manifest.get("excludes", [])):
        rel = str(p.relative_to(ROOT))
        cur[rel] = sha256_file(p)

    by_path = {entry["path"]: entry for entry in manifest["files"]}
    drift = []
    repaired = []
    missing = []

    for rel, entry in by_path.items():
        if rel not in cur:
            missing.append(rel)
            if auto_repair:
                target = ROOT / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "wb") as f:
                    f.write(base64.b64decode(entry["b64"].encode("utf-8")))
                repaired.append(rel)
        else:
            if cur[rel] != entry["sha256"]:
                drift.append(rel)
                if auto_repair:
                    target = ROOT / rel
                    with open(target, "wb") as f:
                        f.write(base64.b64decode(entry["b64"].encode("utf-8")))
                    repaired.append(rel)

    extras = [rel for rel in cur.keys() if rel not in by_path]

    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    report = {
        "mode": "verify",
        "timestamp": stamp,
        "drift": drift,
        "missing": missing,
        "repaired": repaired,
        "extras": extras
    }
    write_report(report)
    log_activity(f"Verify complete. drift={len(drift)} missing={len(missing)} repaired={len(repaired)} extras={len(extras)}")
    update_meta_audit("Verify & Repair Completed", json.dumps(report, indent=2))

def main():
    args = sys.argv[1:]
    if "--snapshot" in args:
        snapshot()
        return
    auto_repair = True
    if "--no-repair" in args:
        auto_repair = False
    verify_and_repair(auto_repair=auto_repair)

if __name__ == "__main__":
    main()
