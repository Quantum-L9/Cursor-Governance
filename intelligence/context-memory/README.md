# Context Memory System

**Provides long-term memory for AI sessions through automated context capture and restoration.**

## Overview

The context-memory system runs hourly to capture session context from chat exports, then restores that context when you start a new session. This solves the "cold start" problem and gives the AI continuity across sessions.

## Architecture

```
intelligence/context-memory/
├── context-extractor.py       # Extracts context from chat exports
├── sessions/                  # Hourly context snapshots
│   ├── 2025-11-08-14.json
│   ├── 2025-11-08-15.json
│   └── index.json
└── README.md

ops/scripts/
├── process_context.sh         # Runs hourly via launchd
├── install_context_processor.sh    # Installs automation
└── show_context.sh            # Displays context (used by session_init)
```

## How It Works

### Automated Capture (Hourly)

```yaml
Every Hour:
  1. export_chats.sh runs (existing)
  2. process_context.sh runs (new)
     - Extracts from last hour of chats
     - Detects project, actions, decisions, files
     - Saves to sessions/ if meaningful
     - Updates index.json
```

### Session Restoration (On Shell Start)

```yaml
Terminal Opens:
  1. session_init.sh runs (existing, enhanced)
  2. show_context.sh runs (new)
     - Loads last session context
     - Displays formatted summary
     - Shows project, actions, next steps
```

## What Gets Captured

```json
{
  "timestamp": "2025-11-08T14:30:00",
  "hour": "2025-11-08-14",
  "project": "cursor-load-pack",
  "summary": "Completed GitHub repository setup",
  "key_actions": [
    "Created .gitignore",
    "Committed 1,041 files"
  ],
  "decisions": [
    "Use dual governance structure"
  ],
  "files_modified": [
    ".gitignore",
    "GlobalCommands/*"
  ],
  "next_steps": [
    "Add context-memory system"
  ],
  "context_signals": {
    "has_code": true,
    "has_commits": true,
    "has_completion": true
  }
}
```

## Installation

```bash
# Install hourly automation
cd ~/Dropbox/Cursor\ Governance/GlobalCommands/ops/scripts
./install_context_processor.sh

# Verify installation
launchctl list | grep cursor.context
```

## Manual Operations

```bash
# Extract context manually
cd ~/Dropbox/Cursor\ Governance/GlobalCommands
./ops/scripts/process_context.sh

# Show last context
./ops/scripts/show_context.sh

# View sessions
ls -la intelligence/context-memory/sessions/

# Read specific session
cat intelligence/context-memory/sessions/2025-11-08-14.json | jq
```

## Session Display Format

When you open a terminal, you'll see:

```
============================================================
📋 LAST SESSION CONTEXT
============================================================
⏰ Time: 2 hours ago
📁 Project: cursor-load-pack
📝 Summary: Completed GitHub repository setup

✅ Actions:
   • Created comprehensive .gitignore
   • Committed 1,041 files to GitHub

🎯 Decisions:
   • Use dual governance structure

📄 Files (3):
   • .gitignore
   • GlobalCommands/*
   • Cursor_Governance_Source/*

⏭️  Next Steps:
   • Add context-memory system
============================================================
```

## Integration with Learning System

| System | Purpose | Output |
|--------|---------|--------|
| **Learning** | Captures patterns & mistakes | `learning/` |
| **Context** | Captures narrative & state | `context-memory/sessions/` |

Both run hourly using same infrastructure (launchd + chat exports).

## Retention

- Contexts are kept for 7 days (168 hours)
- Index automatically maintains last 168 sessions
- Older sessions are pruned automatically

## Logs

```bash
# View processing log
tail -f ~/.cursor-governance/logs/context_processing.log

# View errors
tail -f ~/.cursor-governance/logs/context_processing.err
```

## Context Signals

The system tracks various signals to understand session type:

- `has_code`: Code was written
- `has_commits`: Git operations occurred
- `has_errors`: Debugging session
- `has_completion`: Task was completed
- `has_questions`: Planning/exploration
- `is_planning`: Architecture/design work

## Meaningful Context Threshold

A session is saved only if it has:
- Key actions performed, OR
- Files modified, OR  
- Decisions made, OR
- 3+ message exchanges

This filters out trivial check-ins and quick lookups.

## Troubleshooting

### No context showing on startup

```bash
# Check if sessions exist
ls ~/Dropbox/Cursor\ Governance/GlobalCommands/intelligence/context-memory/sessions/

# Check if processor is running
launchctl list | grep cursor.context

# Check logs
cat ~/.cursor-governance/logs/context_processing.log
```

### Context not capturing

```bash
# Run manually to see errors
cd ~/Dropbox/Cursor\ Governance/GlobalCommands
./ops/scripts/process_context.sh

# Check chat exports exist
ls -la ops/logs/chat_exports/
```

## Related Systems

- `intelligence/learning/` - Pattern extraction
- `ops/scripts/export_chats.sh` - Chat export
- `ops/scripts/session_init.sh` - Session startup
- `ops/scripts/process_learnings.sh` - Learning processor

## Version

- Created: 2025-11-08
- Pattern: Mirrors recursive learning system
- Integration: Cursor Governance Suite 6

