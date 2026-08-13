#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
find "$ROOT_DIR/bin" "$ROOT_DIR/scripts" -type f \( -name '*.sh' -o -path '*/mac-storage-triage' \) -print0 |
while IFS= read -r -d '' file; do
  bash -n "$file"
done
printf 'shell_syntax=pass\n'
