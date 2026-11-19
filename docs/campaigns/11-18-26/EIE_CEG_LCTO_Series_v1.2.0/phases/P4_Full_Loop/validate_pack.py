#!/usr/bin/env python3
"""Standalone byte/header integrity check for a compiled campaign handoff.
This is NOT an L9 conformance or remote runtime validator.
"""

import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parent
m = json.loads((R / "MANIFEST.json").read_text())
actual = {}
for p in R.rglob("*"):
    if not p.is_file() or p.name == "MANIFEST.json":
        continue
    rel = p.relative_to(R)
    if "__pycache__" in rel.parts or p.name.endswith(".pyc"):
        continue
    actual[rel.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
assert actual == m["files"], "campaign pack file census/hash mismatch"
c = json.loads((R / "CAMPAIGN.json").read_text())
b = (json.dumps(c, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()
assert hashlib.sha256(b).hexdigest() == m["source_spec_sha256"], "source-spec mismatch"
for lane in c["lanes"]:
    p = R / "lanes" / (lane["id"] + ".md")
    content = p.read_text()
    assert content.startswith("```yaml\nrepository_access:\n"), "lane header missing"
    assert "  unlisted_repositories: no_access" in content.split("```", 3)[1], (
        "lane not closed world"
    )
print("PASS: exact file inventory, digests, source binding, first-position lane access headers")
print("NOT RUN: source validity, independent CI, real execution, publication or deployment")
