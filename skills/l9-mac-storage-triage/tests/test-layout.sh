#!/bin/bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for path in \
  SKILL.md \
  agents/meta.yaml \
  README.md \
  .env.template \
  bin/mac-storage-triage \
  references/modes.md \
  references/safe-noise-allowlist.md \
  references/diagnose-first.md \
  references/remediation-ledger.md \
  references/deletion-log.md \
  references/remediation-plan-mac-mini.md \
  config/scan-excludes.txt \
  config/guarded-paths.txt \
  scripts/00-diagnose.sh \
  scripts/07-inventory-noise.sh \
  scripts/08-focus-layout.sh \
  scripts/09-emit-findings.sh \
  scripts/emit-findings.py \
  handoffs/findings.schema.json \
  handoffs/current/FINDINGS.txt \
  handoffs/current/findings.json \
  config/findings-catalog.json \
  scripts/mode-run.sh \
  scripts/05-apply.sh \
  scripts/actions/purge-stale-caches.sh \
  scripts/actions/docker-prune-unused.sh \
  scripts/actions/empty-trash.sh \
  handoffs/diagnosis-report.schema.yaml; do
  [ -e "$ROOT_DIR/$path" ] || { printf 'missing=%s\n' "$path" >&2; exit 1; }
done
printf 'layout=pass\n'
