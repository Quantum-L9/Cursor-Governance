#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-MCS-001"
component_name: "Memory Compounding System"
layer: "operations"
domain: "learning"
type: "compounding"
status: "active"
created: "2025-11-17T22:06:00Z"
updated: "2025-11-17T22:06:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["python3", "json", "pathlib", "os"]
integrates_with: ["OPS-AGG-001", "OPS-FLE-001", "OPS-CLI-001"]
data_sources: ["ops/logs/memory_index.json", "ops/logs/pattern_weights.json"]
outputs: ["ops/logs/pattern_weights.json", "ops/logs/auto_applied_patterns.jsonl"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Weight patterns by success/failure and auto-apply high-confidence patterns"
summary: "Memory compounding system that tracks pattern weights and automatically applies proven patterns"
business_value: "Enables automatic pattern application and continuous pattern evolution"
success_metrics: ["auto_apply_rate >= 50%", "weight_accuracy >= 90%", "pattern_evolution_rate >= 10%"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "compounding", "memory", "weights", "auto-apply"]
keywords: ["memory", "compounding", "weights", "auto-apply", "pattern", "evolution"]
related_components: ["OPS-AGG-001", "OPS-FLE-001", "OPS-CLI-001"]
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict

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
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: memory_compounding.py
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
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"
PATTERN_WEIGHTS_FILE = GLOBAL_COMMANDS / "ops/logs/pattern_weights.json"
AUTO_APPLIED_PATTERNS_FILE = GLOBAL_COMMANDS / "ops/logs/auto_applied_patterns.jsonl"

# Weight thresholds
SUCCESS_WEIGHT = 1.0
PARTIAL_SUCCESS_WEIGHT = 0.5
FAILURE_WEIGHT = -1.0
AUTO_APPLY_THRESHOLD = 5.0
PRUNE_THRESHOLD = 0.30


class MemoryCompounding:
    """Memory compounding system with weight tracking and auto-apply logic"""
    
    def __init__(self):
        self.pattern_weights = self._load_pattern_weights()
        self.memory_index = self._load_memory_index()
    
    def _load_pattern_weights(self) -> Dict[str, Dict[str, Any]]:
        """Load pattern weights"""
        if PATTERN_WEIGHTS_FILE.exists():
            try:
                with open(PATTERN_WEIGHTS_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get('weights', {})
            except json.JSONDecodeError:
                pass
        
        return {}
    
    def _save_pattern_weights(self):
        """Save pattern weights"""
        PATTERN_WEIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PATTERN_WEIGHTS_FILE, 'w') as f:
            json.dump({
                'weights': self.pattern_weights,
                'last_updated': datetime.now().isoformat(),
                'thresholds': {
                    'auto_apply': AUTO_APPLY_THRESHOLD,
                    'prune': PRUNE_THRESHOLD
                }
            }, f, indent=2)
    
    def _load_memory_index(self) -> Dict[str, Any]:
        """Load memory index"""
        if MEMORY_INDEX.exists():
            try:
                with open(MEMORY_INDEX, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        return {"learnings": []}
    
    def update_weight(self, pattern_hash: str, outcome: str, confidence: float = 1.0):
        """
        Update pattern weight based on outcome
        
        Args:
            pattern_hash: Hash of the pattern
            outcome: 'success', 'partial_success', or 'failure'
            confidence: Confidence in the outcome (0.0-1.0)
        """
        if pattern_hash not in self.pattern_weights:
            self.pattern_weights[pattern_hash] = {
                'weight': 0.0,
                'success_count': 0,
                'failure_count': 0,
                'partial_count': 0,
                'last_updated': datetime.now().isoformat(),
                'first_seen': datetime.now().isoformat()
            }
        
        pattern = self.pattern_weights[pattern_hash]
        
        # Update weight based on outcome
        if outcome == 'success':
            weight_delta = SUCCESS_WEIGHT * confidence
            pattern['success_count'] += 1
        elif outcome == 'partial_success':
            weight_delta = PARTIAL_SUCCESS_WEIGHT * confidence
            pattern['partial_count'] += 1
        elif outcome == 'failure':
            weight_delta = FAILURE_WEIGHT * confidence
            pattern['failure_count'] += 1
        else:
            return  # Unknown outcome
        
        pattern['weight'] += weight_delta
        pattern['last_updated'] = datetime.now().isoformat()
        
        # Ensure weight doesn't go below 0
        pattern['weight'] = max(0.0, pattern['weight'])
        
        self._save_pattern_weights()
    
    def get_pattern_weight(self, pattern_hash: str) -> float:
        """Get current weight for a pattern"""
        return self.pattern_weights.get(pattern_hash, {}).get('weight', 0.0)
    
    def should_auto_apply(self, pattern_hash: str) -> bool:
        """Check if pattern should be auto-applied"""
        weight = self.get_pattern_weight(pattern_hash)
        return weight >= AUTO_APPLY_THRESHOLD
    
    def get_auto_apply_patterns(self) -> List[Dict[str, Any]]:
        """Get list of patterns that should be auto-applied"""
        auto_apply_patterns = []
        
        for pattern_hash, pattern_data in self.pattern_weights.items():
            if pattern_data['weight'] >= AUTO_APPLY_THRESHOLD:
                # Find pattern in memory_index
                pattern_info = self._find_pattern_in_memory(pattern_hash)
                
                auto_apply_patterns.append({
                    'pattern_hash': pattern_hash,
                    'weight': pattern_data['weight'],
                    'success_count': pattern_data['success_count'],
                    'pattern_info': pattern_info
                })
        
        # Sort by weight (highest first)
        auto_apply_patterns.sort(key=lambda x: x['weight'], reverse=True)
        
        return auto_apply_patterns
    
    def _find_pattern_in_memory(self, pattern_hash: str) -> Optional[Dict[str, Any]]:
        """Find pattern information in memory index"""
        learnings = self.memory_index.get('learnings', [])
        for learning in learnings:
            if learning.get('hash') == pattern_hash:
                return learning
        return None
    
    def prune_patterns(self) -> List[str]:
        """Prune patterns with weight below threshold"""
        pruned = []
        
        for pattern_hash, pattern_data in list(self.pattern_weights.items()):
            weight = pattern_data['weight']
            confidence = self._calculate_confidence(pattern_data)
            
            if weight < PRUNE_THRESHOLD or confidence < PRUNE_THRESHOLD:
                # Archive pattern
                pruned.append(pattern_hash)
                # Remove from active weights (but could archive instead)
                del self.pattern_weights[pattern_hash]
        
        if pruned:
            self._save_pattern_weights()
        
        return pruned
    
    def _calculate_confidence(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate confidence score for a pattern"""
        total_uses = pattern_data['success_count'] + pattern_data['failure_count'] + pattern_data['partial_count']
        
        if total_uses == 0:
            return 0.0
        
        # Confidence based on success rate
        success_rate = pattern_data['success_count'] / total_uses
        return success_rate
    
    def evolve_patterns(self):
        """Evolve patterns: improve weights, decay unused patterns, merge similar patterns"""
        # Decay unused patterns (reduce weight by 0.1 per week of non-use)
        current_time = datetime.now()
        for pattern_hash, pattern_data in self.pattern_weights.items():
            last_updated_str = pattern_data.get('last_updated', pattern_data.get('first_seen', datetime.now().isoformat()))
            try:
                last_updated = datetime.fromisoformat(last_updated_str)
                weeks_unused = (current_time - last_updated).days / 7
                
                if weeks_unused > 1:
                    # Decay weight
                    decay_amount = min(weeks_unused * 0.1, pattern_data['weight'])
                    pattern_data['weight'] -= decay_amount
                    pattern_data['weight'] = max(0.0, pattern_data['weight'])
            except (ValueError, TypeError):
                pass
        
        # Merge similar patterns (simplified - would need semantic similarity)
        # For now, just save updated weights
        self._save_pattern_weights()
    
    def log_auto_apply(self, pattern_hash: str, context: str, outcome: str):
        """Log auto-applied pattern"""
        AUTO_APPLIED_PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'pattern_hash': pattern_hash,
            'context': context[:200],
            'outcome': outcome,
            'weight': self.get_pattern_weight(pattern_hash)
        }
        
        with open(AUTO_APPLIED_PATTERNS_FILE, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def initialize_weights_from_memory(self):
        """Initialize weights for existing patterns in memory_index"""
        learnings = self.memory_index.get('learnings', [])
        
        initialized = 0
        for learning in learnings:
            pattern_hash = learning.get('hash')
            if pattern_hash and pattern_hash not in self.pattern_weights:
                # Initialize with neutral weight
                self.pattern_weights[pattern_hash] = {
                    'weight': 0.0,
                    'success_count': 0,
                    'failure_count': 0,
                    'partial_count': 0,
                    'last_updated': datetime.now().isoformat(),
                    'first_seen': learning.get('timestamp', datetime.now().isoformat())
                }
                initialized += 1
        
        if initialized > 0:
            self._save_pattern_weights()
            print(f"✅ Initialized weights for {initialized} patterns")
        
        return initialized
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get compounding statistics"""
        total_patterns = len(self.pattern_weights)
        auto_apply_count = len([p for p in self.pattern_weights.values() if p['weight'] >= AUTO_APPLY_THRESHOLD])
        prunable_count = len([p for p in self.pattern_weights.values() if p['weight'] < PRUNE_THRESHOLD])
        
        avg_weight = sum(p['weight'] for p in self.pattern_weights.values()) / total_patterns if total_patterns > 0 else 0.0
        
        return {
            'total_patterns': total_patterns,
            'auto_apply_count': auto_apply_count,
            'prunable_count': prunable_count,
            'average_weight': avg_weight,
            'auto_apply_rate': (auto_apply_count / total_patterns * 100) if total_patterns > 0 else 0.0
        }


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Memory Compounding System')
    parser.add_argument('--initialize', action='store_true', help='Initialize weights from memory')
    parser.add_argument('--evolve', action='store_true', help='Evolve patterns (decay, merge)')
    parser.add_argument('--prune', action='store_true', help='Prune low-weight patterns')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    args = parser.parse_args()
    
    print("💎 Memory Compounding System v1.0.0 - Starting...\n")
    
    compounding = MemoryCompounding()
    
    if args.initialize:
        count = compounding.initialize_weights_from_memory()
        print(f"✅ Initialized {count} pattern weights")
    
    if args.evolve:
        compounding.evolve_patterns()
        print("✅ Pattern evolution complete")
    
    if args.prune:
        pruned = compounding.prune_patterns()
        print(f"✅ Pruned {len(pruned)} patterns")
    
    if args.stats or (not args.initialize and not args.evolve and not args.prune):
        stats = compounding.get_statistics()
        print(f"\n📊 Memory Compounding Statistics:")
        print(f"   Total Patterns: {stats['total_patterns']}")
        print(f"   Auto-Apply Patterns: {stats['auto_apply_count']}")
        print(f"   Prunable Patterns: {stats['prunable_count']}")
        print(f"   Average Weight: {stats['average_weight']:.2f}")
        print(f"   Auto-Apply Rate: {stats['auto_apply_rate']:.2f}%")


if __name__ == "__main__":
    main()

