#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TXT="$ROOT_DIR/handoffs/current/FINDINGS.txt"
JSON="$ROOT_DIR/handoffs/current/findings.json"
[ -s "$TXT" ] || { echo "missing FINDINGS.txt" >&2; exit 1; }
[ -s "$JSON" ] || { echo "missing findings.json" >&2; exit 1; }
grep -q "What's inside" "$TXT" || { echo "FINDINGS.txt missing What's inside for undecided rows" >&2; exit 1; }
python3 - "$JSON" "$ROOT_DIR/handoffs/findings.schema.json" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1], encoding="utf-8"))
schema = json.load(open(sys.argv[2], encoding="utf-8"))
assert doc.get("schema") == schema["properties"]["schema"]["const"]
assert "findings" in doc and "repair" in doc
assert doc["apply_allowed"] is False
by_id = {item["id"]: item for item in doc["findings"]}
assert by_id["C6"]["safe_to_delete"] is True
assert by_id["C9"]["safe_to_delete"] is True
assert by_id["C6"]["phase"] == "A"
assert by_id["C9"]["phase"] == "A"
undecided = [
    item for item in doc["findings"]
    if not item["safe_to_delete"]
    and item["guard"] != "never"
    and item.get("proposed_action") != "deleted"
]
assert undecided, "expected undecided findings"
for item in undecided:
    assert "inspect" in item, f"{item['id']} missing inspect"
print("findings_pair=pass")
PY
