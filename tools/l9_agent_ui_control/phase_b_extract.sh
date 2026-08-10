#!/bin/bash
# Phase B extract via Agent UI Control local_console → sqlcmd (IB-PC or Mac).
# Fails closed if sqlcmd absent or integrity gate rejects outputs.

set -euo pipefail

PACK="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS="$(cd "$PACK/.." && pwd)"
PY="${L9_AGENT_UI_PYTHON:-$HOME/.cursor-governance/.venv/bin/python}"
[ -x "$PY" ] || PY="$(command -v python3)"

SERVER="${CIETRADE_SQL_SERVER:-UCSCIETRADE}"
DB="${CIETRADE_SQL_DB:-cieTrade_SM}"

if [ -n "${1:-}" ]; then
  OUT="$1"
elif [ -n "${CIETRADE_EXTRACT_ROOT:-}" ]; then
  OUT="${CIETRADE_EXTRACT_ROOT}/cieTrade_export_$(date +%Y%m%d_%H%M%S)"
elif [ -n "${PLASTICOS_ROOT:-}" ]; then
  OUT="${PLASTICOS_ROOT}/Current Work - IGNORE/CieTrade Data Extraction/cieTrade_export_$(date +%Y%m%d_%H%M%S)"
else
  echo "Usage: PLASTICOS_ROOT=/path/to/IB-Odoo_19 $0 [OUT_DIR]"
  echo "   or: CIETRADE_EXTRACT_ROOT=/path/to/CieTrade\\ Data\\ Extraction $0"
  exit 2
fi

mkdir -p "$OUT/raw" "$OUT/sql"
cp -f "$PACK/sql/"*.sql "$OUT/sql/" 2>/dev/null || true

CONSOLE=(env PYTHONPATH="$TOOLS" "$PY" "$PACK/local_console.py")

echo "=== Phase B extract → $OUT ==="
"${CONSOLE[@]}" shell --cmd "command -v sqlcmd" --wait 60 | tee "$OUT/sqlcmd_probe.json"
if ! grep -q '"status": "done"' "$OUT/sqlcmd_probe.json" 2>/dev/null; then
  echo "BLOCKED: sqlcmd not available via runner shell"
  exit 2
fi

run_q() {
  local name="$1" sqlfile="$2" outfile="$3"
  local cmd
  cmd=$(printf 'sqlcmd -S %q -E -d %q -W -s "," -i %q -o %q' "$SERVER" "$DB" "$sqlfile" "$outfile")
  echo "Running $name..."
  "${CONSOLE[@]}" shell --cmd "$cmd" --wait 600 | tee "$OUT/${name}.task.json"
}

run_q catalog_tables "$OUT/sql/01_catalog_tables.sql" "$OUT/catalog_tables.csv"
run_q catalog_columns "$OUT/sql/02_catalog_columns.sql" "$OUT/catalog_columns.csv"
run_q discover_payment "$OUT/sql/03_discover_payment_like_tables.sql" "$OUT/discover_payment_like_tables.csv"
run_q p0_targets "$OUT/sql/04_list_p0_dump_targets.sql" "$OUT/p0_dump_targets.csv"

# Dump known high-value tables (best-effort; skip missing)
for t in Payables PayablesBatch Receipt ReceiptBatch AccountingPayment Checks GPLedger CounterParty Address Contact WKSDetail PODetail; do
  outfile="$OUT/raw/dbo.${t}.csv"
  cmd=$(printf 'sqlcmd -S %q -E -d %q -W -s "," -Q %q -o %q' \
    "$SERVER" "$DB" "SET NOCOUNT ON; SELECT * FROM dbo.[$t];" "$outfile")
  echo "Dump $t..."
  "${CONSOLE[@]}" shell --cmd "$cmd" --wait 900 | tee "$OUT/raw/${t}.task.json" || true
done

"$PY" "$PACK/integrity_check.py" "$OUT" | tee "$OUT/integrity_report.txt"
"$PY" "$PACK/integrity_check.py" "$OUT" --json > "$OUT/integrity_report.json" || true

echo "Write EXTRACT_MANIFEST.md manually or via agent after reviewing integrity_report."
echo "DONE: $OUT"
