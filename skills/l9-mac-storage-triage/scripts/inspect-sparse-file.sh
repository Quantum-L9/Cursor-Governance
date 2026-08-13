#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT_DIR/scripts/lib/common.sh"
require_macos
FILE="${1:-}"
[ -n "$FILE" ] || die "Provide one existing file path."
[ -f "$FILE" ] || die "File not found: $FILE"
LOGICAL="$(stat -f '%z' "$FILE")"
BLOCKS="$(stat -f '%b' "$FILE")"
ALLOCATED=$((BLOCKS*512))
awk -v logical="$LOGICAL" -v allocated="$ALLOCATED" -v path="$FILE" 'BEGIN {
  printf "path=%s\nlogical_bytes=%.0f\nallocated_bytes=%.0f\nlogical_gib=%.2f\nallocated_gib=%.2f\n", path, logical, allocated, logical/1073741824, allocated/1073741824
}'
