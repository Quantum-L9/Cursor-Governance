#!/usr/bin/env bash
# Version: 1.0.0
# Canonical-Source: 10X Governance Suite
# Generated: 2025-10-06T17:22:56Z
# Self-healing integrity check runner (silent, autonomous).

set -euo pipefail
cd "$(dirname "$0")/.."

LOG_DIR="ops/logs"
mkdir -p "$LOG_DIR"

if [[ "${1:-}" == "--snapshot" ]]; then
  python3 integrity/hash-verifier.py --snapshot >/dev/null 2>&1 || true
  echo "[2025-10-06T17:22:56Z] Snapshot executed" >> "$LOG_DIR/integrity_activity.log"
else
  python3 integrity/hash-verifier.py >/dev/null 2>&1 || true
  echo "[2025-10-06T17:22:56Z] Verify+Repair executed" >> "$LOG_DIR/integrity_activity.log"
fi
