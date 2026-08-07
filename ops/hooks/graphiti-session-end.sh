#!/usr/bin/env bash
# sessionEnd — Graphiti-only; memory-bank deprecated (no T0 fallback)
set -uo pipefail
set +x

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"

REPO="${CURSOR_PROJECT_DIR:-}"
[ -n "$REPO" ] || exit 0

graphiti_resolve_cli
graphiti_load_env
export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-${CURSOR_SESSION_ID:-default}}"

SESSION_SUMMARY=""
INPUT="$(cat 2>/dev/null || true)"
if [ -n "$INPUT" ]; then
  SESSION_SUMMARY="$(INPUT="$INPUT" python3 - <<'PY'
import json, os
raw = os.environ.get("INPUT", "")
if not raw.strip():
    raise SystemExit
try:
    data = json.loads(raw)
    print(
        data.get("summary")
        or data.get("session_summary")
        or data.get("user_message")
        or data.get("message")
        or data.get("text")
        or ""
    )
except json.JSONDecodeError:
    print(raw[:1500])
PY
)"
fi

if [ -z "$SESSION_SUMMARY" ]; then
  echo "INFO: no session summary — nothing to write" >&2
  exit 0
fi

if ! graphiti_enabled; then
  echo "WARN: Graphiti disabled — session summary not persisted (memory-bank deprecated)" >&2
  exit 0
fi

GROUP_ID="$(python3 "$GRAPHITI_CLI" resolve 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('group_id',''))" 2>/dev/null || echo "")"
if [ -z "$GROUP_ID" ]; then
  echo "WARN: group_id unresolvable — session summary not persisted (memory-bank deprecated)" >&2
  exit 0
fi

PAYLOAD="$SESSION_SUMMARY"
if [ -n "${OPENAI_API_KEY:-}" ]; then
  DISTILL_BUDGET="${MEMORY_DISTILL_TOKEN_BUDGET:-300}"
  DISTILLED="$(SESSION_SUMMARY="$SESSION_SUMMARY" DISTILL_BUDGET="$DISTILL_BUDGET" python3 - <<'PY'
import json, os, urllib.request, urllib.error

summary = os.environ.get("SESSION_SUMMARY", "")[:1500]
budget = int(os.environ.get("DISTILL_BUDGET", "300"))
payload = json.dumps({
    "model": "gpt-4o-mini",
    "max_tokens": budget,
    "messages": [
        {
            "role": "system",
            "content": (
                "Extract durable facts from this session. Output ONLY a JSON object with keys: "
                "decisions, constraints, ci_gotchas, preferences, tech_debt (lists). "
                "Omit empty keys. No prose."
            ),
        },
        {"role": "user", "content": summary},
    ],
}).encode()
req = urllib.request.Request(
    "https://api.openai.com/v1/chat/completions",
    data=payload,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
    },
)
try:
    with urllib.request.urlopen(req, timeout=25) as resp:
        body = json.loads(resp.read())
    text = body["choices"][0]["message"]["content"].strip()
    json.loads(text)
    print(text)
except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
    print(json.dumps({"error": str(exc), "fallback": summary[:200]}))
PY
)"
  PAYLOAD="$DISTILLED"
fi

if python3 "$GRAPHITI_CLI" write "$PAYLOAD" --kind session_summary --group-id "$GROUP_ID" >/dev/null 2>&1; then
  echo "INFO: T1 Graphiti episode written for $GROUP_ID" >&2
  exit 0
fi

echo "WARN: T1 episode write failed — session summary not persisted (memory-bank deprecated)" >&2
exit 0
