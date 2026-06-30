#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "OPS-MLS-001"
component_name: "Meta Learning Sync"
layer: "operations"
domain: "learning"
type: "synchronizer"
status: "active"
created: "2025-11-08T00:00:00Z"
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
integrates_with: ["OPS-AGG-001", "INT-ML-001"]
data_sources: ["ops/logs/memory_index.json"]
outputs: ["intelligence/meta-learning/meta-learning-log.md"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Sync learnings from memory index to meta-learning log"
summary: "Writes extracted learnings to meta-learning-log.md for governance system"
business_value: "Enables recursive learning and continuous governance improvement"
success_metrics: ["sync_success_rate >= 99%", "learnings_persisted", "no_data_loss"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "sync", "meta-learning", "governance", "automation"]
keywords: ["learning", "sync", "meta-learning", "governance", "persistence"]
related_components: ["OPS-AGG-001", "INT-ML-001", "OPS-UPD-001"]
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import os

# Configuration - Use Dropbox as single source of truth
def get_global_commands_path():
    """Get GlobalCommands path, preferring Dropbox location"""
    dropbox_paths = [
        Path.home() / ".cursor-governance"
    ]
    library_path = Path(os.path.expanduser("~/.cursor-governance"))
    
    # Try Dropbox paths first
    for path in dropbox_paths:
        if path.exists():
            return path
    
    # Fallback to Library
    if library_path.exists():
        return library_path
    
    raise FileNotFoundError("GlobalCommands directory not found in Dropbox or Library")

GLOBAL_COMMANDS = get_global_commands_path()
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"
META_LEARNING_LOG = GLOBAL_COMMANDS / "intelligence/meta-learning/meta-learning-log.md"


class MetaLearningSyncer:
    """Syncs learnings from memory index to meta-learning log"""
    
    def __init__(self):
        self.memory_index = self._load_memory_index()
        self.synced_hashes = self._extract_synced_hashes()
    
    def _load_memory_index(self) -> Dict[str, Any]:
        """Load memory index"""
        if MEMORY_INDEX.exists():
            with open(MEMORY_INDEX, 'r') as f:
                content = f.read().strip()
                if content and content != "{}":
                    return json.loads(content)
        return {"learnings": [], "synced_to_meta_learning": []}
    
    def _save_memory_index(self):
        """Save memory index with sync tracking"""
        with open(MEMORY_INDEX, 'w') as f:
            json.dump(self.memory_index, f, indent=2)
    
    def _extract_synced_hashes(self) -> set:
        """Extract hashes of learnings already synced to meta-learning-log"""
        return set(self.memory_index.get("synced_to_meta_learning", []))
    
    def sync_new_learnings(self):
        """Sync new learnings to meta-learning log"""
        all_learnings = self.memory_index.get("learnings", [])
        
        # Find learnings not yet synced
        new_learnings = [l for l in all_learnings if l['hash'] not in self.synced_hashes]
        
        if not new_learnings:
            print("✅ No new learnings to sync to meta-learning log")
            return
        
        print(f"📝 Syncing {len(new_learnings)} new learnings to meta-learning log...")
        
        # Group by type
        mistakes = [l for l in new_learnings if l['type'] == 'mistake']
        solutions = [l for l in new_learnings if l['type'] == 'solution']
        
        # Generate entries
        entries = []
        
        if mistakes:
            entries.append(self._generate_mistake_entry(mistakes))
        
        if solutions:
            entries.append(self._generate_solution_entry(solutions))
        
        # Append to meta-learning log
        self._append_to_meta_learning_log(entries)
        
        # Log to learning audit logger (lessons go to learning/ folder, not intelligence/)
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from intelligence_audit_logger import LearningAuditLogger
            audit_logger = LearningAuditLogger()
            for learning in new_learnings:
                audit_logger.log_lesson_addition(
                    lesson_type=learning.get('type', 'unknown'),
                    content=learning.get('content', ''),
                    source_file=f"ops/logs/memory_index.json",
                    source_type='extracted',
                    metadata={'hash': learning.get('hash'), 'context': learning.get('context')}
                )
        except Exception as e:
            print(f"⚠️  Audit logging failed (non-critical): {e}")
        
        # Mark as synced
        for learning in new_learnings:
            self.synced_hashes.add(learning['hash'])
        
        self.memory_index["synced_to_meta_learning"] = list(self.synced_hashes)
        self._save_memory_index()
        
        print(f"✅ Synced {len(new_learnings)} learnings to meta-learning-log.md")
    
    def _generate_mistake_entry(self, mistakes: List[Dict[str, Any]]) -> str:
        """Generate meta-learning entry for mistakes"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Aggregate mistake types
        mistake_types = {}
        for m in mistakes:
            content = m['content']
            mistake_types[content] = mistake_types.get(content, 0) + 1
        
        entry = f"""
### {today} – Automatic Learning Extraction

#### LP_{int(datetime.now().timestamp())}_pattern_detection – Pattern Detection: {len(mistakes)} issues identified

**Context:**
Detected in conversations from automated chat analysis.

**Summary of Learning:**
Identified {len(mistakes)} potential issues through pattern matching:
"""
        
        for mistake_type, count in mistake_types.items():
            entry += f"- {mistake_type} ({count} occurrence{'s' if count > 1 else ''})\n"
        
        entry += """
**Implications:**
- Review patterns to identify systemic issues
- Update validation rules to prevent recurrence
- Consider adding automated checks for detected patterns

**Generated Rules:**
- Rule ID: LP_{timestamp}_auto_detection
- FOL: ∀p. Pattern(p) ∧ Repeated(p) → Flagged(p)
- Integration: Automatic extraction from conversation analysis
- Confidence: 0.75

**Success Metrics:**
- Pattern detection accuracy >= 80%
- False positive rate < 20%
- Issue prevention measurable

**Related Components:**
- OPS-AGG-001 (Memory Aggregator)
- INT-ML-001 (Meta Learning Log)
- FND-LG-001 (Rule Registry)
"""
        
        return entry
    
    def _generate_solution_entry(self, solutions: List[Dict[str, Any]]) -> str:
        """Generate meta-learning entry for solutions"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        entry = f"""
### {today} – Solution Patterns Detected

**Context:**
Detected {len(solutions)} successful solution patterns in recent conversations.

**Summary of Learning:**
Identified successful resolution patterns that can be reused:
- Quick fixes applied successfully
- User satisfaction indicators detected
- Problem resolution confirmed

**Implications:**
- Document successful patterns for reuse
- Build solution library from validated fixes
- Enable faster problem resolution

**Generated Rules:**
- Rule ID: LP_{int(datetime.now().timestamp())}_solution_patterns
- FOL: ∀s. Solution(s) ∧ Successful(s) → Reusable(s)
- Integration: Automatic extraction from successful conversations
- Confidence: 0.85

**Success Metrics:**
- Solution reuse rate >= 60%
- Time to resolution decreased
- User satisfaction improved

**Related Components:**
- OPS-AGG-001 (Memory Aggregator)
- INT-ML-001 (Meta Learning Log)
- Learning Files (patterns/quick-fixes.md)
"""
        
        return entry
    
    def _append_to_meta_learning_log(self, entries: List[str]):
        """Append entries to meta-learning log"""
        if not META_LEARNING_LOG.exists():
            print(f"⚠️  Meta-learning log not found: {META_LEARNING_LOG}")
            return
        
        content = META_LEARNING_LOG.read_text()
        
        # Append entries at the end
        for entry in entries:
            content += "\n" + entry
        
        META_LEARNING_LOG.write_text(content)


def main():
    """Main execution"""
    print("🔄 Meta Learning Syncer v1.0.0 - Starting...\n")
    
    syncer = MetaLearningSyncer()
    syncer.sync_new_learnings()
    
    print("\n✅ Meta-learning sync complete")


if __name__ == "__main__":
    main()

