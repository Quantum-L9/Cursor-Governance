#!/usr/bin/env python3
"""
L9_META
  l9_schema: 1
  artifact_type: parser
  component: chat_export_parser
  tags: [parsing, chat, export, indexing, memory]
  retrieval: on_demand
  status: active

Parse chat export data into structured memory index
"""

import datetime
import hashlib
import json
import os
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
                with open(path, "rb") as file_handle:
                    file_hash = hashlib.sha256(file_handle.read()).hexdigest()
                entries.append({"file": path, "hash": file_hash})
            except Exception as e:
                print(f"Error processing {path}: {e}")

    INDEX.parent.mkdir(parents=True, exist_ok=True)

    with open(INDEX, "w") as out:
        json.dump(
            {"updated": datetime.datetime.utcnow().isoformat() + "Z", "entries": entries},
            out,
            indent=2,
        )

    print(f"✅ Parsed {len(entries)} files into memory index: {INDEX}")


if __name__ == "__main__":
    main()
