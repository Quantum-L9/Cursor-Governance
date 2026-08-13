#!/bin/bash
# l9-mac-storage-triage / scripts/09-emit-findings.sh
# purpose: write FINDINGS.txt (human) and findings.json (machine) after diagnosis
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT_DIR/scripts/emit-findings.py"
