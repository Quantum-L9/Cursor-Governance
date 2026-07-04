#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "OPS-PCE-001"
component_name: "Chat Export Parser"
layer: "operations"
domain: "learning"
type: "parser"
status: "active"
created: "2025-10-06T17:10:32Z"
updated: "2026-01-04T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "medium"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["json", "hashlib", "datetime", "os"]
integrates_with: ["OPS-AGG-001", "OPS-EXP-001"]
api_endpoints: []
data_sources: ["ops/logs/chat_exports/"]
outputs: ["ops/logs/memory_index.json"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: false
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Parse chat export data into structured memory index"
summary: "Walks chat exports directory and creates indexed JSON with file hashes"
business_value: "Enables deduplication and tracking of processed chat exports"
success_metrics: ["parse_success = 100%"]

# === MIGRATION METADATA ===
canonical_source: "10X Governance Suite"
generated: "2025-10-06T17:10:32Z"
migration_notes: "Enhanced with L9 Governance canonical header"

# === TAGS & CLASSIFICATION ===
tags: ["parsing", "chat", "export", "indexing", "memory"]
keywords: ["parse", "chat", "export", "index", "hash"]
related_components: ["OPS-AGG-001", "OPS-EXP-001"]

# === DESCRIPTION ===
Parse chat export data into structured memory index.
Walks the chat exports directory and creates an indexed JSON file with file hashes.
"""

import os
import json
import hashlib
import datetime
from pathlib import Path

BASE = Path(os.getcwd()) / "ops" / "logs" / "chat_exports"
INDEX = Path(os.getcwd()) / "ops" / "logs" / "memory_index.json"

def main():
    """Parse chat exports and create memory index."""
    entries = []
    
    if not BASE.exists():
        print(f"Chat exports directory not found: {BASE}")
        return
    
    for root, _, files in os.walk(BASE):
        for f in files:
            path = os.path.join(root, f)
            try:
                with open(path, 'rb') as file_handle:
                    file_hash = hashlib.sha256(file_handle.read()).hexdigest()
                entries.append({"file": path, "hash": file_hash})
            except Exception as e:
                print(f"Error processing {path}: {e}")
    
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    
    with open(INDEX, "w") as out:
        json.dump({
            "updated": datetime.datetime.utcnow().isoformat() + "Z",
            "entries": entries
        }, out, indent=2)
    
    print(f"✅ Parsed {len(entries)} files into memory index: {INDEX}")

if __name__ == "__main__":
    main()
