#!/bin/bash
# ops/scripts/show_context.sh
# Display last session context
# Used by session_init.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_COMMANDS="$(dirname "$(dirname "$SCRIPT_DIR")")"
SESSIONS_DIR="$GLOBAL_COMMANDS/intelligence/context-memory/sessions"

# Check if we have any sessions
if [ ! -d "$SESSIONS_DIR" ] || [ -z "$(ls -A "$SESSIONS_DIR" 2>/dev/null)" ]; then
    return 0  # No sessions yet, silently continue
fi

# Get latest session (exclude index.json)
LATEST_SESSION=$(ls -t "$SESSIONS_DIR"/*.json 2>/dev/null | grep -v "index.json" | head -1)

if [ -z "$LATEST_SESSION" ]; then
    return 0  # No sessions yet
fi

# Display context using Python
python3 - "$LATEST_SESSION" << 'EOF'
import json
import sys
from datetime import datetime
from pathlib import Path

if len(sys.argv) < 2:
    sys.exit(0)

session_file = Path(sys.argv[1])
if not session_file.exists():
    sys.exit(0)

with open(session_file) as f:
    ctx = json.load(f)

# Calculate time ago
ts = datetime.fromisoformat(ctx['timestamp'])
now = datetime.now()
delta = now - ts
hours_ago = int(delta.total_seconds() / 3600)

if hours_ago == 0:
    time_str = "< 1 hour ago"
elif hours_ago < 24:
    time_str = f"{hours_ago} hours ago"
else:
    days = hours_ago // 24
    time_str = f"{days} days ago"

print("\n" + "="*60)
print("📋 LAST SESSION CONTEXT")
print("="*60)
print(f"⏰ Time: {time_str}")
print(f"📁 Project: {ctx['project']}")
print(f"📝 Summary: {ctx['summary'][:80]}...")

if ctx.get('key_actions'):
    print(f"\n✅ Actions:")
    for action in ctx['key_actions'][:3]:
        print(f"   • {action}")

if ctx.get('decisions'):
    print(f"\n🎯 Decisions:")
    for decision in ctx['decisions'][:2]:
        print(f"   • {decision}")

if ctx.get('files_modified'):
    print(f"\n📄 Files ({len(ctx['files_modified'])}):")
    for f in ctx['files_modified'][:5]:
        print(f"   • {f}")

if ctx.get('next_steps'):
    print(f"\n⏭️  Next Steps:")
    for step in ctx['next_steps'][:2]:
        print(f"   • {step}")

print("="*60 + "\n")
EOF

