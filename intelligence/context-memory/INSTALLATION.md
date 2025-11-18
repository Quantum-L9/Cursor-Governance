# Context-Memory System Installation Guide

## Quick Install

```bash
# Navigate to scripts
cd ~/Dropbox/Cursor\ Governance/GlobalCommands/ops/scripts

# Run installer
./install_context_processor.sh
```

## What Gets Installed

1. **Launchd Job**
   - File: `~/Library/LaunchAgents/com.cursor.context.processor.plist`
   - Schedule: Every hour on the hour
   - Script: `process_context.sh`

2. **Directory Structure**
   - `intelligence/context-memory/` - Main directory
   - `intelligence/context-memory/sessions/` - Session snapshots
   - `~/.cursor-governance/logs/` - Processing logs

3. **Scripts**
   - `context-extractor.py` - Python extractor
   - `process_context.sh` - Hourly processor
   - `show_context.sh` - Display utility

## Verification

```bash
# Check launchd job is loaded
launchctl list | grep cursor.context
# Should show: com.cursor.context.processor

# Check logs directory exists
ls -la ~/.cursor-governance/logs/
# Should show: context_processing.log

# Run manually to test
cd ~/Dropbox/Cursor\ Governance/GlobalCommands
./ops/scripts/process_context.sh
```

## First Run

The system needs existing chat exports to work. If you've been using the learning system, you already have these.

```bash
# Check for chat exports
ls -la ~/Dropbox/Cursor\ Governance/GlobalCommands/ops/logs/chat_exports/

# If empty, wait for next hourly export (export_chats.sh runs hourly)
```

## Manual Test

```bash
# Process current chats manually
cd ~/Dropbox/Cursor\ Governance/GlobalCommands
./ops/scripts/process_context.sh

# View generated context
ls -la intelligence/context-memory/sessions/

# Show last context
./ops/scripts/show_context.sh
```

## Integration with Shell

The context is automatically shown when you open a new terminal because `session_init.sh` has been enhanced to call `show_context.sh`.

## Uninstall

```bash
# Unload launchd job
launchctl unload ~/Library/LaunchAgents/com.cursor.context.processor.plist

# Remove plist
rm ~/Library/LaunchAgents/com.cursor.context.processor.plist

# Optionally remove data
rm -rf ~/Dropbox/Cursor\ Governance/GlobalCommands/intelligence/context-memory/sessions/
```

## Troubleshooting

### Problem: No context showing

**Solution:**
```bash
# Check if sessions exist
ls ~/Dropbox/Cursor\ Governance/GlobalCommands/intelligence/context-memory/sessions/

# If empty, wait 1 hour or run manually
./ops/scripts/process_context.sh
```

### Problem: Launchd job not running

**Solution:**
```bash
# Check status
launchctl list | grep cursor.context

# Reload if needed
launchctl unload ~/Library/LaunchAgents/com.cursor.context.processor.plist
launchctl load ~/Library/LaunchAgents/com.cursor.context.processor.plist
```

### Problem: Python errors

**Solution:**
```bash
# Check Python version
python3 --version
# Need Python 3.6+

# Test extractor directly
cd ~/Dropbox/Cursor\ Governance/GlobalCommands
python3 intelligence/context-memory/context-extractor.py --help
```

## Next Steps

After installation:

1. Work normally for an hour
2. Context will be captured automatically
3. Open new terminal to see context display
4. Review `~/.cursor-governance/logs/context_processing.log`

## Related Documentation

- [README.md](./README.md) - System overview
- [../learning/README.md](../learning/README.md) - Learning system (similar pattern)
- [../../ops/scripts/README_STARTUP_VERIFICATION.md](../../ops/scripts/README_STARTUP_VERIFICATION.md) - Startup verification

