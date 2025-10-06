#!/bin/bash
# 🛡️ Hardened Governance Dashboard Generator

cd /Users/ib-mac/Workspace/Cursor-Governance || exit

OUT="Governance_Dashboard.md"
LOG="meta_index.md"
timestamp=$(date "+%Y-%m-%d %H:%M:%S")

{
echo "# 🛡️ Governance Compliance Dashboard"
echo
echo "**Generated:** ${timestamp}"
echo
echo "<!-- This is a Markdown file, not executable code. -->"
echo
echo "| Timestamp | Status | Notes |"
echo "|------------|---------|-------|"

# Detailed event log table
awk -F'|' '
/enforcement/ {
  gsub(/^ +| +$/, "", $2);
  gsub(/^ +| +$/, "", $3);
  gsub(/^ +| +$/, "", $4);
  ts=$2;
  note=$4;
  if (note ~ /✅/) status="✅ Passed";
  else if (note ~ /⚠️/) status="⚠️ Warning";
  else if (note ~ /❌/) status="❌ Failed";
  else status="ℹ️ Info";
  printf("| %s | %s | %s |\n", ts, status, note);
}' "$LOG"

echo
echo "## 📊 Daily Summary"
echo
echo "| Date | ✅ Passed | ⚠️ Warnings | ❌ Failed |"
echo "|-------|------------|--------------|-----------|"

# Aggregate daily stats
awk -F'|' '
/enforcement/ {
  gsub(/^ +| +$/, "", $2);
  gsub(/^ +| +$/, "", $4);
  date=substr($2,1,10);
  if ($4 ~ /✅/) pass[date]++;
  else if ($4 ~ /⚠️/) warn[date]++;
  else if ($4 ~ /❌/) fail[date]++;
}
END {
  PROCINFO["sorted_in"] = "@ind_str_asc";
  for (d in pass) {
    printf("| %s | %d | %d | %d |\n", d, pass[d]+0, warn[d]+0, fail[d]+0);
  }
}' "$LOG"

echo
echo "_Auto-generated summary based on enforcement logs._"
} > "$OUT"

echo "✅ Governance dashboard updated at ${timestamp}"

