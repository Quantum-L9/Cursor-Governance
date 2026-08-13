#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT_DIR/tests/test-shell-syntax.sh"
"$ROOT_DIR/tests/test-diagnose-first-gates.sh"
"$ROOT_DIR/tests/test-layout.sh"
"$ROOT_DIR/tests/test-findings.sh"
