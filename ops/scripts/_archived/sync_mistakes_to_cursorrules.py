#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "OPS-SYN-001"
component_name: "Cursorrules Sync Service"
layer: "operations"
domain: "learning"
type: "synchronizer"
status: "active"
created: "2025-10-06T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["python3", "pathlib"]
integrates_with: ["OPS-UPD-001", "OPS-LEA-001", "FND-LG-001"]
data_sources: ["learning/failures/repeated-mistakes.md"]
outputs: ["~/.cursorrules"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Sync repeated mistakes to global .cursorrules for AI auto-loading"
summary: "Automatically embeds learning content into .cursorrules for immediate AI access"
business_value: "Ensures AI never repeats documented mistakes"
success_metrics: ["sync_success_rate >= 99%", "mistakes_embedded", "no_content_corruption"]

# === TAGS & CLASSIFICATION ===
tags: ["sync", "cursorrules", "learning", "automation", "prevention"]
keywords: ["cursorrules", "sync", "mistakes", "embedding", "automation"]
related_components: ["OPS-UPD-001", "OPS-LEA-001", "FND-LG-001"]
"""

import os
import re
from datetime import datetime
from pathlib import Path

def get_global_commands_path():
    """Resolve GlobalCommands, preferring the ~/.cursor-governance SSOT clone.

    Order: ~/.cursor-governance (SSOT) -> legacy Dropbox -> Library fallback (logged).
    """
    import os
    fallback_log = Path.home() / ".cursor-globalcommands-fallback.log"
    disable_fallback = os.environ.get("DISABLE_FALLBACK", "0") == "1"

    # SSOT clone first, then legacy Dropbox (transition fallback).
    for candidate in (
        Path.home() / ".cursor-governance",
        Path.home() / "Dropbox/Cursor Governance/GlobalCommands",
    ):
        if candidate.is_dir():
            return candidate

    # Last-resort Library fallback (logged).
    library_path = Path.home() / "Library/Application Support/Cursor/GlobalCommands"
    if library_path.is_dir():
        if disable_fallback:
            raise FileNotFoundError(
                "GlobalCommands not found under ~/.cursor-governance or Dropbox and "
                "DISABLE_FALLBACK=1. Set DISABLE_FALLBACK=0 to allow the Library fallback, "
                "or clone Cursor-Governance to ~/.cursor-governance."
            )

        # Log fallback usage
        log_entry = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FALLBACK USED: Library path instead of SSOT clone (~/.cursor-governance)
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: sync_mistakes_to_cursorrules.py
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Path: {library_path}
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   User: {os.getenv('USER', 'unknown')}
---
"""
        with open(fallback_log, 'a') as f:
            f.write(log_entry)

        print("\n⚠️  WARNING: Using Library fallback (logged to ~/.cursor-globalcommands-fallback.log)")
        return library_path

    raise FileNotFoundError("GlobalCommands directory not found under ~/.cursor-governance, Dropbox, or Library")

def sync_mistakes_to_cursorrules():
    """Embed repeated mistakes directly into .cursorrules for auto-loading"""
    
    # Paths
    global_commands = get_global_commands_path()
    mistakes_file = global_commands / "learning/failures/repeated-mistakes.md"
    cursorrules_file = Path.home() / ".cursorrules"
    
    print("🔄 Syncing repeated mistakes to .cursorrules...")
    
    # Read repeated mistakes
    if not mistakes_file.exists():
        print(f"❌ Mistakes file not found: {mistakes_file}")
        return False
    
    with open(mistakes_file, 'r') as f:
        mistakes_content = f.read()
    
    # Extract just the critical mistakes section
    mistakes_match = re.search(
        r'## 🚨 \*\*CRITICAL FAILURES TO NEVER REPEAT\*\*(.*?)---\n\n## 🔄',
        mistakes_content,
        re.DOTALL
    )
    
    if not mistakes_match:
        print("❌ Could not parse mistakes content")
        return False
    
    mistakes_section = mistakes_match.group(1).strip()
    
    # Parse individual mistakes
    mistake_pattern = r'### \*\*(\d+)\. (.*?)\*\*\n\*\*Mistake:\*\* (.*?)\n.*?\*\*Rule:\*\* (.*?)(?:\n\*\*Date Added:|---|\n\n###)'
    mistakes = re.findall(mistake_pattern, mistakes_section, re.DOTALL)
    
    # Build the embedded section
    embedded_section = f"""## 🚫 REPEATED MISTAKES - NEVER DO THESE AGAIN

**Source:** `{global_commands}/learning/failures/repeated-mistakes.md`
"""
    
    for num, title, mistake, rule in mistakes:
        # Clean up the text
        mistake_clean = ' '.join(mistake.strip().split())
        rule_clean = ' '.join(rule.strip().split())
        
        embedded_section += f"""
### {num}. {title}
❌ {mistake_clean}
✅ {rule_clean}
"""
    
    embedded_section += f"""
**Zero Tolerance Policy: ACTIVE**
**Auto-synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**

---

*These rules apply GLOBALLY to every Cursor workspace*
*Last Updated: {datetime.now().strftime('%Y-%m-%d')}*
"""
    
    # Read current .cursorrules
    if not cursorrules_file.exists():
        print(f"❌ .cursorrules not found: {cursorrules_file}")
        return False
    
    with open(cursorrules_file, 'r') as f:
        cursorrules_content = f.read()
    
    # Replace the repeated mistakes section
    pattern = r'## 🚫 REPEATED MISTAKES - NEVER DO THESE AGAIN.*?(?=\*These rules apply GLOBALLY|\Z)'
    
    if re.search(pattern, cursorrules_content, re.DOTALL):
        # Section exists - replace it
        new_content = re.sub(
            pattern,
            embedded_section.rstrip() + '\n\n',
            cursorrules_content,
            flags=re.DOTALL
        )
    else:
        # Section doesn't exist - add it before the footer
        footer_pattern = r'\n---\n\n\*These rules apply GLOBALLY'
        if re.search(footer_pattern, cursorrules_content):
            new_content = re.sub(
                footer_pattern,
                f'\n---\n\n{embedded_section}',
                cursorrules_content
            )
        else:
            # Just append
            new_content = cursorrules_content + '\n\n' + embedded_section
    
    # Write updated content
    with open(cursorrules_file, 'w') as f:
        f.write(new_content)
    
    print(f"✅ Synced {len(mistakes)} mistakes to .cursorrules")
    print(f"📝 File: {cursorrules_file}")
    
    return True

if __name__ == '__main__':
    success = sync_mistakes_to_cursorrules()
    exit(0 if success else 1)

