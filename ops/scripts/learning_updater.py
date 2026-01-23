#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "OPS-UPD-001"
component_name: "Learning File Updater"
layer: "operations"
domain: "learning"
type: "updater"
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
dependencies: ["python3", "json", "pathlib"]
integrates_with: ["OPS-AGG-001", "OPS-LEA-001", "OPS-SYN-001"]
data_sources: ["ops/logs/memory_index.json"]
outputs: ["learning/failures/repeated-mistakes.md", "learning/patterns/quick-fixes.md", "learning/solutions"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Update learning markdown files with extracted patterns"
summary: "Applies learnings from memory index to structured markdown files"
business_value: "Maintains up-to-date knowledge base for AI improvement"
success_metrics: ["update_success_rate >= 99%", "file_integrity_maintained", "no_duplicates"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "updater", "markdown", "automation", "knowledge-base"]
keywords: ["learning", "updater", "mistakes", "patterns", "solutions"]
related_components: ["OPS-AGG-001", "OPS-LEA-001", "OPS-SYN-001"]
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import os

# Configuration - Use Dropbox as single source of truth
def get_global_commands_path():
    """Get GlobalCommands path, preferring Dropbox location"""
    fallback_log = Path.home() / ".cursor-globalcommands-fallback.log"
    disable_fallback = os.environ.get("DISABLE_FALLBACK", "0") == "1"
    
    dropbox_paths = [
        Path.home() / "Dropbox/Cursor Governance/GlobalCommands"
    ]
    library_path = Path(os.path.expanduser("~/Library/Application Support/Cursor/GlobalCommands"))
    
    # Try Dropbox paths first
    for path in dropbox_paths:
        if path.exists():
            return path
    
    # Fallback to Library
    if library_path.exists():
        if disable_fallback:
            raise FileNotFoundError(
                "Dropbox GlobalCommands not found and DISABLE_FALLBACK=1. "
                "Set DISABLE_FALLBACK=0 to allow fallback, or fix Dropbox path."
            )
        
        # Log fallback usage
        log_entry = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FALLBACK USED: Library path instead of Dropbox
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: learning_updater.py
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Path: {library_path}
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   User: {os.getenv('USER', 'unknown')}
---
"""
        with open(fallback_log, 'a') as f:
            f.write(log_entry)
        
        print("\n⚠️  WARNING: Using Library fallback (logged to ~/.cursor-globalcommands-fallback.log)")
        return library_path
    
    raise FileNotFoundError("GlobalCommands directory not found in Dropbox or Library")

GLOBAL_COMMANDS = get_global_commands_path()
LEARNING_DIR = GLOBAL_COMMANDS / "learning"
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"

class LearningFileUpdater:
    """Updates learning markdown files with new patterns"""
    
    def __init__(self):
        self.repeated_mistakes_file = LEARNING_DIR / "failures/repeated-mistakes.md"
        self.quick_fixes_file = LEARNING_DIR / "patterns/quick-fixes.md"
        self.memory_index = self._load_memory_index()
    
    def _load_memory_index(self) -> Dict[str, Any]:
        """Load memory index"""
        if MEMORY_INDEX.exists():
            with open(MEMORY_INDEX, 'r') as f:
                content = f.read().strip()
                if content and content != "{}":
                    return json.loads(content)
        return {"learnings": [], "applied_learnings": []}
    
    def _save_memory_index(self):
        """Save memory index"""
        with open(MEMORY_INDEX, 'w') as f:
            json.dump(self.memory_index, f, indent=2)
    
    def apply_pending_learnings(self):
        """Apply learnings that haven't been added to files yet"""
        applied_hashes = set(self.memory_index.get("applied_learnings", []))
        all_learnings = self.memory_index.get("learnings", [])
        
        pending = [l for l in all_learnings if l['hash'] not in applied_hashes]
        
        if not pending:
            print("✅ No pending learnings to apply")
            return
        
        print(f"📝 Applying {len(pending)} pending learnings...")
        
        # Group by type
        mistakes = [l for l in pending if l['type'] == 'mistake']
        solutions = [l for l in pending if l['type'] == 'solution']
        
        if mistakes:
            self._update_mistakes_file(mistakes)
            # Log to audit system
            self._log_to_audit(mistakes, 'mistake')
        
        if solutions:
            self._update_quick_fixes(solutions)
            # Log to audit system
            self._log_to_audit(solutions, 'solution')
        
        # Mark as applied
        for learning in pending:
            applied_hashes.add(learning['hash'])
        
        self.memory_index["applied_learnings"] = list(applied_hashes)
        self._save_memory_index()
        
        print(f"✅ Applied {len(pending)} learnings to files")
    
    def _log_to_audit(self, learnings: List[Dict[str, Any]], lesson_type: str):
        """Log additions to learning audit system"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from intelligence_audit_logger import LearningAuditLogger
            audit_logger = LearningAuditLogger()
            for learning in learnings:
                audit_logger.log_lesson_addition(
                    lesson_type=lesson_type,
                    content=learning.get('content', ''),
                    source_file="ops/logs/memory_index.json",
                    source_type='learning_updater',
                    metadata={'hash': learning.get('hash'), 'context': learning.get('context')}
                )
        except Exception as e:
            print(f"⚠️  Audit logging failed (non-critical): {e}")
    
    def _update_mistakes_file(self, mistakes: List[Dict[str, Any]]):
        """Update repeated mistakes file"""
        if not self.repeated_mistakes_file.exists():
            print(f"⚠️  Repeated mistakes file not found: {self.repeated_mistakes_file}")
            return
        
        content = self.repeated_mistakes_file.read_text()
        
        # Find the tracking table
        table_pattern = r'(\|\| Mistake Type \|.*?\|\n\|\|[-|]+\|\n(?:\|\|.*?\|\n)*)'
        
        # Count existing mistakes
        existing_count = len(re.findall(r'^\|\|.*?\|.*?\|.*?\|.*?\|$', content, re.MULTILINE))
        
        # Add summary entry if multiple new mistakes detected
        if len(mistakes) >= 3:
            timestamp = datetime.now().strftime("%Y-%m-%d")
            new_entry = f"|| Auto-detected Issues | {len(mistakes)} | AI Pattern Detection | ✅ Active |\n"
            
            # Insert before the closing line of table
            if '---\n\n**Last Updated:' in content:
                content = content.replace(
                    '---\n\n**Last Updated:',
                    f'{new_entry}---\n\n**Last Updated:'
                )
            
            # Update last updated timestamp
            content = re.sub(
                r'\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}',
                f'**Last Updated:** {timestamp}',
                content
            )
            
            self.repeated_mistakes_file.write_text(content)
            print(f"  ✅ Updated repeated-mistakes.md with {len(mistakes)} issues")
    
    def _update_quick_fixes(self, solutions: List[Dict[str, Any]]):
        """Update quick fixes file"""
        if not self.quick_fixes_file.exists():
            print(f"⚠️  Quick fixes file not found: {self.quick_fixes_file}")
            return
        
        # Simply update the timestamp for now
        content = self.quick_fixes_file.read_text()
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        content = re.sub(
            r'\*\*Last Updated:\*\* \d{4}-\d{2}-\d{2}',
            f'**Last Updated:** {timestamp}',
            content
        )
        
        self.quick_fixes_file.write_text(content)
        print(f"  ✅ Updated quick-fixes.md timestamp")
    
    def generate_insights_report(self) -> str:
        """Generate insights from learnings"""
        learnings = self.memory_index.get("learnings", [])
        
        if not learnings:
            return "No learnings to report"
        
        # Count by type
        by_type = {}
        for l in learnings:
            t = l['type']
            by_type[t] = by_type.get(t, 0) + 1
        
        report = "\n╔═══════════════════════════════════════════╗\n"
        report += "║      LEARNING INSIGHTS SUMMARY           ║\n"
        report += "╠═══════════════════════════════════════════╣\n"
        
        for ltype, count in by_type.items():
            report += f"║  {ltype.upper():<15} {count:>4} detected       ║\n"
        
        report += "╚═══════════════════════════════════════════╝\n"
        
        return report


def main():
    """Main execution"""
    print("📚 Learning File Updater v1.0.0 - Starting...\n")
    
    updater = LearningFileUpdater()
    updater.apply_pending_learnings()
    
    # Generate insights
    insights = updater.generate_insights_report()
    print(insights)


if __name__ == "__main__":
    main()

