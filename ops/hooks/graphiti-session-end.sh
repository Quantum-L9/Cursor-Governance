#!/usr/bin/env bash
# sessionEnd — automatic Phase A/B close (PICKUP + atomic writes); fail-open
# Budget: hooks.json Graphiti sessionEnd timeout is 30s (Phase A ≤8s, B ≤18s).
set -uo pipefail
set +x

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"

# Resolve project dir from Cursor env / stdin — never ~/.cursor cwd
REPO="${CURSOR_PROJECT_DIR:-}"
INPUT="$(cat 2>/dev/null || true)"
SESSION_ID="${CURSOR_CONVERSATION_ID:-${CURSOR_SESSION_ID:-default}}"
REASON="completed"
TRANSCRIPT_PATH=""
IS_BG="0"

if [ -n "$INPUT" ]; then
  PARSED="$(INPUT="$INPUT" python3 - <<'PY'
import json, os
raw = os.environ.get("INPUT", "")
out = {"repo": "", "session_id": "", "reason": "completed", "transcript_path": "", "background": "0"}
try:
    data = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    data = {}
if isinstance(data, dict):
    roots = data.get("workspace_roots") or data.get("workspaceRoots") or []
    if isinstance(roots, list) and roots:
        out["repo"] = str(roots[0])
    for key in ("cwd", "workspace_root", "project_dir", "CURSOR_PROJECT_DIR"):
        if data.get(key):
            out["repo"] = str(data[key])
            break
    out["session_id"] = str(
        data.get("session_id")
        or data.get("conversation_id")
        or data.get("CURSOR_CONVERSATION_ID")
        or ""
    )
    out["reason"] = str(
        data.get("reason")
        or data.get("status")
        or data.get("end_reason")
        or "completed"
    )
    tp = data.get("transcript_path") or data.get("transcriptPath") or ""
    out["transcript_path"] = str(tp) if tp else ""
    if data.get("is_background_agent") or data.get("isBackgroundAgent"):
        out["background"] = "1"
print(json.dumps(out))
PY
)"
  REPO_FROM_STDIN="$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('repo',''))" 2>/dev/null || true)"
  [ -n "$REPO_FROM_STDIN" ] && REPO="$REPO_FROM_STDIN"
  SID_FROM_STDIN="$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || true)"
  [ -n "$SID_FROM_STDIN" ] && SESSION_ID="$SID_FROM_STDIN"
  REASON="$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reason','completed'))" 2>/dev/null || echo completed)"
  TRANSCRIPT_PATH="$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('transcript_path',''))" 2>/dev/null || true)"
  IS_BG="$(echo "$PARSED" | python3 -c "import sys,json; print(json.load(sys.stdin).get('background','0'))" 2>/dev/null || echo 0)"
fi

[ -n "$REPO" ] || {
  echo "WARN: no project dir (CURSOR_PROJECT_DIR / workspace_roots) — close skipped" >&2
  exit 0
}

export L9_MEMORY_AGENT_ID="${L9_MEMORY_AGENT_ID:-cursor}"
export USER_ID="${USER_ID:-cursor_agent}"
export CURSOR_CONVERSATION_ID="$SESSION_ID"

graphiti_load_env
if ! graphiti_enabled; then
  echo "WARN: Graphiti disabled — close skipped" >&2
  exit 0
fi

GOV_ROOT="$(cd "$(dirname "$REAL_HOOK")/../.." && pwd)"
if [ ! -f "$GOV_ROOT/ops/graphiti/hydration/cli.py" ]; then
  GOV_ROOT="${L9_GOVERNANCE_DIR:-$HOME/.cursor-governance}"
fi
if [ ! -f "$GOV_ROOT/ops/graphiti/hydration/cli.py" ]; then
  echo "WARN: hydration CLI missing — close skipped" >&2
  exit 0
fi

PY="${GOV_ROOT}/.venv/bin/python3"
[ -x "$PY" ] || PY="python3"

CLOSE_ARGS=(
  --project-dir "$REPO"
  --session-id "$SESSION_ID"
  --reason "$REASON"
  --agent-id "$L9_MEMORY_AGENT_ID"
)
[ -n "$TRANSCRIPT_PATH" ] && CLOSE_ARGS+=(--transcript-path "$TRANSCRIPT_PATH")
[ "$IS_BG" = "1" ] && CLOSE_ARGS+=(--background)

# Ensure cwd for any incidental resolve matches the project (close passes --project-dir)
cd "$REPO" || true

# Capture stdout even when close exits 2 (enqueue fail-loud after Phase A success).
REPORT="$(cd "$GOV_ROOT" && PYTHONPATH="$GOV_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
    "$PY" -m ops.graphiti.hydration.cli close \
    "${CLOSE_ARGS[@]}" 2>/dev/null)"
CLOSE_RC=$?

if [ -n "$REPORT" ]; then
  echo "$REPORT" | python3 -c '
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print("INFO: session close finished (unparsed)", file=sys.stderr)
    raise SystemExit(0)
status = d.get("status", "?")
writes = len(d.get("writes") or [])
agent = (d.get("receipt") or {}).get("agent_id") or d.get("agent_id") or ""
gid = d.get("group_id") or ""
print(
    "INFO: session close status=%s writes=%s group=%s agent=%s"
    % (status, writes, gid, agent),
    file=sys.stderr,
)
if status == "idempotent_skip":
    print("INFO: close receipt already present — skipped duplicate writes", file=sys.stderr)
if d.get("phase_b"):
    print(
        "INFO: Phase B distill completed packet=%s"
        % (d.get("signal_packet_id") or ""),
        file=sys.stderr,
    )
if d.get("enqueue_ok") is False:
    print(
        "ERROR: distill S3 enqueue failed — %s"
        % (d.get("enqueue_error") or "unknown"),
        file=sys.stderr,
    )
if d.get("enqueue_ok") is True:
    enq = d.get("enqueue") or {}
    print("INFO: distill job enqueued key=%s" % (enq.get("key") or ""), file=sys.stderr)
for w in d.get("warnings") or []:
    level = "ERROR" if str(w).startswith("ERROR:") else "WARN"
    print("%s: %s" % (level, w), file=sys.stderr)
' 2>&1 || echo "INFO: session close finished" >&2
elif [ "$CLOSE_RC" -ne 0 ] && [ "$CLOSE_RC" -ne 2 ]; then
  echo "WARN: session close failed — Phase A may be missing; use /end-session force-retry" >&2
fi
# Fail-loud on enqueue (cli exit 2); keep Graphiti availability fail-open otherwise.
if [ "${CLOSE_RC:-0}" = "2" ]; then
  exit 2
fi
exit 0
