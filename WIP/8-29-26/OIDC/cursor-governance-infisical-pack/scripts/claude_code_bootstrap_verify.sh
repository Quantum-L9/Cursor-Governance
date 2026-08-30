#!/usr/bin/env bash
# Verifies that Infisical-injected secrets required by Claude Code bootstrap
# are present as job-scoped env vars and are not persisted to disk.
set -euo pipefail

REQUIRED_VARS=(
  "ANTHROPIC_API_KEY"
)

missing=0
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "::error::Required secret ${var} not present in environment"
    missing=1
  fi
done

if [ "$missing" -eq 1 ]; then
  echo "One or more required secrets are missing — check Infisical project role / secret path scoping."
  exit 1
fi

if [ -f "$(pwd)/.env" ]; then
  echo "::error::.env found at repo root post-bootstrap — this is a Claude Code auto-read exposure path"
  exit 1
fi

echo "Claude Code bootstrap secrets verified present and not persisted to disk."
