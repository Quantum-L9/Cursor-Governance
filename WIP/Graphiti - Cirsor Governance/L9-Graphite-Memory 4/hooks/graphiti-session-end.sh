#!/usr/bin/env bash
# sessionEnd — T0 memory-bank update + optional T1 Graphiti JSON episode
set -uo pipefail
set +x

REAL_HOOK="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "${BASH_SOURCE[0]}")"
# shellcheck source=graphiti_common.sh
source "$(dirname "$REAL_HOOK")/graphiti_common.sh"

graphiti_enabled || exit 0

REPO="${CURSOR_PROJECT_DIR:-}"
graphiti_resolve_cli
graphiti_scaffold_memory_bank "$REPO"
[ -n "$REPO" ] || exit 0

graphiti_load_env
export CURSOR_CONVERSATION_ID="${CURSOR_CONVERSATION_ID:-${CURSOR_SESSION_ID:-default}}"

TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
BANK="$REPO/memory-bank"
mkdir -p "$BANK"

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

cat > "$BANK/activeContext.md" <<EOF
# Where we left off (max ~1 screen)

**Last session:** $TIMESTAMP
**Repo:** $REPO
**Branch:** $(git -C "$REPO" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

## Session Summary
${SESSION_SUMMARY:-No summary provided.}

## Last Modified Files
$(git -C "$REPO" diff --name-only HEAD 2>/dev/null | head -10 || echo "none")

**Next action:** (update manually or via end-session command)
EOF

if [ -f "$BANK/tasks.md" ]; then
  cat >> "$BANK/tasks.md" <<EOF

---
## Session $TIMESTAMP
${SESSION_SUMMARY:-No summary.}
EOF
fi

if [ -z "$SESSION_SUMMARY" ]; then
  echo "INFO: no session summary — T0 complete, T1 skipped" >&2
  exit 0
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "INFO: OPENAI_API_KEY not set — T0 complete, T1 skipped" >&2
  exit 0
fi

GROUP_ID="$(python3 "$GRAPHITI_CLI" resolve 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin).get('group_id',''))" 2>/dev/null || echo "")"
if [ -z "$GROUP_ID" ]; then
  echo "WARN: group_id unresolvable — T0 complete, T1 skipped" >&2
  exit 0
fi

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

python3 "$GRAPHITI_CLI" write "$DISTILLED" --kind session_summary --group-id "$GROUP_ID" >/dev/null 2>&1 \
  || echo "WARN: T1 episode write failed — T0 complete" >&2

echo "INFO: T0 memory-bank updated; T1 episode attempted for $GROUP_ID" >&2
exit 0
