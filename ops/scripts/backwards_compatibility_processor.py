#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6"
version: "1.0.0"
component_id: "OPS-BCP-001"
component_name: "Backwards Compatibility Pattern Processor"
layer: "operations"
domain: "learning"
type: "processor"
status: "active"
created: "2025-11-17T23:30:00Z"
updated: "2025-11-17T23:30:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === BUSINESS METADATA ===
purpose: "Re-process older chat exports with enhanced context extraction for backwards compatibility"
summary: "Extracts patterns from pre-reasoning-upgrade chats with rich context for better lesson generation"
business_value: "Maximizes value extraction from historical chat data"
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add script directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from memory_aggregator import MemoryAggregator, LearningPattern

def get_global_commands_path():
    """Get GlobalCommands path"""
    dropbox_path = Path.home() / "Dropbox/Cursor Governance/GlobalCommands"
    if dropbox_path.exists():
        return dropbox_path
    library_path = Path.home() / "Library/Application Support/Cursor/GlobalCommands"
    if library_path.exists():
        return library_path
    raise FileNotFoundError("GlobalCommands directory not found")

GLOBAL_COMMANDS = get_global_commands_path()
CHAT_EXPORTS_DIR = GLOBAL_COMMANDS / "ops/logs/chat_exports"
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"

def main():
    """Re-process older exports with enhanced extraction"""
    print("🔄 Backwards Compatibility Pattern Processor")
    print("=" * 60)
    
    # Load existing memory index
    if MEMORY_INDEX.exists():
        with open(MEMORY_INDEX, 'r') as f:
            memory_data = json.load(f)
        processed_exports = set(memory_data.get('processed_exports', []))
    else:
        processed_exports = set()
    
    # Find all exports
    if not CHAT_EXPORTS_DIR.exists():
        print(f"❌ Chat exports directory not found: {CHAT_EXPORTS_DIR}")
        return
    
    all_exports = sorted([d for d in CHAT_EXPORTS_DIR.iterdir() if d.is_dir()])
    print(f"📂 Found {len(all_exports)} total exports")
    print(f"📊 Already processed: {len(processed_exports)}")
    
    # Re-process ALL exports (including old ones) with enhanced extraction
    print("\n🔄 Re-processing all exports with enhanced context extraction...")
    
    aggregator = MemoryAggregator()
    
    # Clear processed_exports to force re-processing ALL exports
    aggregator.processed_exports = set()
    
    # Process all exports
    aggregator.process_all_exports()
    
    print(f"\n✅ Re-processing complete!")
    print(f"   Total learnings: {len(aggregator.learnings)}")
    print(f"   Enhanced context patterns: {sum(1 for l in aggregator.learnings if isinstance(l, dict) and l.get('enhanced_context'))}")
    
    # Save updated memory index
    aggregator._save_memory_index()
    
    print("\n📋 Next steps:")
    print("   1. Run formal_lesson_extractor.py to generate lessons from re-processed patterns")
    print("   2. Check for new patterns with enhanced context")

if __name__ == "__main__":
    main()

