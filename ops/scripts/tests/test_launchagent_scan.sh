#!/usr/bin/env bash
# Fake LaunchAgents dir: Dropbox plist FAIL, missing dir warn/PASS, SSOT-only PASS.
# Does not touch ~/Library/LaunchAgents.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCAN="$OPS_DIR/scan_launchagents.py"
PYTHON="${PYTHON:-${OPS_DIR%/ops/scripts}/.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  PYTHON=python3
fi

PASS=0
pass() {
  PASS=$((PASS + 1))
  echo "PASS T$PASS: $1"
}
fail_now() {
  echo "FAIL: $1" >&2
  exit 1
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/l9-launchagent-scan.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

SSOT="$TMP/ssot"
mkdir -p "$SSOT/ops/scripts"
printf '#!/bin/sh\n' >"$SSOT/ops/scripts/ok.sh"

# Missing directory → warn, exit 0.
out="$("$PYTHON" "$SCAN" --dir "$TMP/absent" --ssot "$SSOT" 2>&1 || true)"
rc=0
"$PYTHON" "$SCAN" --dir "$TMP/absent" --ssot "$SSOT" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 0 ] || fail_now "missing dir must exit 0, got $rc: $out"
echo "$out" | grep -q 'WARN:' || fail_now "missing dir must warn: $out"
pass "missing LaunchAgents dir warns and PASSes"

# Dropbox plist → FAIL even if we never consult launchctl.
AGENTS="$TMP/LaunchAgents"
mkdir -p "$AGENTS"
cat >"$AGENTS/com.cursor.governance-monitor.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.cursor.governance-monitor</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/x/Dropbox/Cursor Governance/GlobalCommands/ops/scripts/governance-monitor-wrapper.sh</string>
  </array>
  <key>StandardOutPath</key>
  <string>/Users/x/Dropbox/Cursor Governance/GlobalCommands/ops/logs/out</string>
</dict>
</plist>
EOF
rc=0
out="$("$PYTHON" "$SCAN" --dir "$AGENTS" --ssot "$SSOT" 2>&1 || true)"
"$PYTHON" "$SCAN" --dir "$AGENTS" --ssot "$SSOT" >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 1 ] || fail_now "Dropbox plist must exit 1, got $rc: $out"
echo "$out" | grep -q 'Dropbox' || fail_now "Dropbox finding missing: $out"
echo "$out" | grep -q 'report-only' || fail_now "must declare report-only: $out"
pass "Dropbox plist FAILs without launchctl"

# SSOT-only path → PASS.
rm -f "$AGENTS/com.cursor.governance-monitor.plist"
cat >"$AGENTS/com.l9.ok.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.l9.ok</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SSOT/ops/scripts/ok.sh</string>
  </array>
</dict>
</plist>
EOF
rc=0
out="$("$PYTHON" "$SCAN" --dir "$AGENTS" --ssot "$SSOT" 2>&1 || true)"
"$PYTHON" "$SCAN" --dir "$AGENTS" --ssot "$SSOT" >/dev/null || rc=$?
[ "$rc" -eq 0 ] || fail_now "SSOT-only plist must exit 0, got $rc: $out"
pass "SSOT-only plist PASSes"

if grep -q 'launchctl unload' "$OPS_DIR/check_governance_wiring.sh" \
  || grep -q 'launchctl bootout' "$OPS_DIR/check_governance_wiring.sh"; then
  fail_now "check_governance_wiring.sh must not unload/bootout LaunchAgents"
fi
pass "wiring checker does not mutate LaunchAgents"

echo "RESULT: PASS — launchagent scan ($PASS checks)"
