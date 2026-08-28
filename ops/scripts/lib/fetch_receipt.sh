#!/usr/bin/env bash
# Fetch receipt: one git fetch origin BASE_REF per make pr when the SHA is fresh.
# shellcheck shell=bash
#
# The gate prefetches during writers (PR_EARLY_OVERLAP=1). open_pr_after_gate.sh
# reuses this receipt when it is younger than FETCH_RECEIPT_TTL_S (default 60)
# and fetched_sha still matches the local origin/$BASE_REF cache. Stale, missing,
# or SHA-mismatched receipts fetch as before. Never skip on TTL alone.
#
# Usage:
#   source ops/scripts/lib/fetch_receipt.sh
#   fetch_receipt_write "$WS" "$BASE_REF" "$sha"
#   if fetch_receipt_reusable "$WS" "$BASE_REF"; then skip fetch; fi
#
# Env:
#   FETCH_RECEIPT_TTL_S  max age in seconds (default 60)

FETCH_RECEIPT_TTL_S="${FETCH_RECEIPT_TTL_S:-60}"
FETCH_RECEIPT_REL=".l9/pr/fetch-receipt.json"

fetch_receipt_path() {
  printf '%s/%s' "$1" "$FETCH_RECEIPT_REL"
}

fetch_receipt_write() {
  local ws="$1" ref="$2" sha="$3" path
  path="$(fetch_receipt_path "$ws")"
  mkdir -p "$(dirname "$path")"
  python3 - "$path" "$ref" "$sha" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, ref, sha = sys.argv[1], sys.argv[2], sys.argv[3]
doc = {
    "schema": "l9.fetch_receipt.v1",
    "base_ref": ref,
    "fetched_sha": sha,
    "fetched_at": datetime.now(timezone.utc)
    .replace(microsecond=0)
    .isoformat()
    .replace("+00:00", "Z"),
}
with open(path, "w", encoding="utf-8") as handle:
    handle.write(json.dumps(doc, indent=2) + "\n")
print(f"fetch receipt written: {path}")
PY
}

# Exit 0 when open_pr / overlap may skip git fetch.
fetch_receipt_reusable() {
  local ws="$1" ref="$2" path live ttl
  path="$(fetch_receipt_path "$ws")"
  [[ -f "$path" ]] || return 1
  live="$(git -C "$ws" rev-parse "origin/${ref}" 2>/dev/null)" || return 1
  ttl="${FETCH_RECEIPT_TTL_S:-60}"
  python3 - "$path" "$ref" "$live" "$ttl" <<'PY'
import json
import sys
from datetime import datetime, timezone

path, ref, live, ttl_s = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
try:
    doc = json.loads(open(path, encoding="utf-8").read())
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
if doc.get("schema") != "l9.fetch_receipt.v1":
    raise SystemExit(1)
if doc.get("base_ref") != ref:
    raise SystemExit(1)
if doc.get("fetched_sha") != live:
    raise SystemExit(1)
raw = str(doc.get("fetched_at") or "")
try:
    stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
except ValueError:
    raise SystemExit(1)
age = (datetime.now(timezone.utc) - stamp).total_seconds()
raise SystemExit(0 if 0 <= age <= ttl_s else 1)
PY
}
