#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-PEC-001"
component_name: "Pre-Execution Mistake Checker"
layer: "operations"
domain: "learning"
type: "checker"
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
dependencies: ["python3", "json", "pathlib", "re", "os"]
integrates_with: ["OPS-FLE-001", "OPS-PET-001", "OPS-MCS-001"]
data_sources: ["learning/failures/repeated-mistakes.md", "ops/logs/memory_index.json"]
outputs: ["prevention_rules", "blocked_actions", "audit_log"]

# === OPERATIONAL METADATA ===
execution_mode: "real-time"
monitoring_required: true
logging_level: "info"
performance_tier: "real-time"

# === BUSINESS METADATA ===
purpose: "Block actions that match known mistakes before execution"
summary: "Real-time mistake prevention through pattern matching and severity-based blocking"
business_value: "Prevents repeated mistakes in real-time, reducing rework and improving quality"
success_metrics: ["prevention_rate >= 95%", "check_latency < 100ms", "false_positive_rate < 5%"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "prevention", "real-time", "mistake_checker", "governance"]
keywords: ["pre-execution", "mistake", "prevention", "checker", "real-time", "blocking"]
related_components: ["OPS-FLE-001", "OPS-PET-001", "OPS-MCS-001"]
"""

import json
import re
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import hashlib

# Configuration - Use Dropbox as single source of truth
def get_global_commands_path():
    """Get GlobalCommands path, preferring Dropbox location"""
    fallback_log = Path.home() / ".cursor-globalcommands-fallback.log"
    disable_fallback = os.environ.get("DISABLE_FALLBACK", "0") == "1"
    
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
        if disable_fallback:
            raise FileNotFoundError(
                "Dropbox GlobalCommands not found and DISABLE_FALLBACK=1. "
                "Set DISABLE_FALLBACK=0 to allow fallback, or fix Dropbox path."
            )
        
        # Log fallback usage
        log_entry = f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FALLBACK USED: Library path instead of Dropbox
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: pre_execution_checker.py
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
REPEATED_MISTAKES_FILE = GLOBAL_COMMANDS / "learning/failures/repeated-mistakes.md"
MEMORY_INDEX = GLOBAL_COMMANDS / "ops/logs/memory_index.json"
CACHE_FILE = GLOBAL_COMMANDS / "ops/scripts/pre_execution_checker_config.json"
AUDIT_LOG_FILE = GLOBAL_COMMANDS / "ops/logs/pre_execution_checker_audit.jsonl"


class PreExecutionChecker:
    """Pre-execution mistake checker with pattern matching and severity-based blocking"""
    
    def __init__(self):
        self.lessons = []
        self.pattern_cache = {}
        self.cache_loaded = False
        self._load_lessons()
        self._build_pattern_cache()
    
    def _load_lessons(self):
        """Load lessons from repeated-mistakes.md"""
        if not REPEATED_MISTAKES_FILE.exists():
            print(f"⚠️  Repeated mistakes file not found: {REPEATED_MISTAKES_FILE}")
            return
        
        content = REPEATED_MISTAKES_FILE.read_text()
        
        # Extract all lessons
        lesson_pattern = r'### \*\*(\d+)\.\s*(.*?)\*\*\n\*\*Mistake:\*\*\s*(.*?)\n\*\*Impact:\*\*\s*(.*?)\n\*\*Prevention:\*\*\s*(.*?)\n\*\*Rule:\*\*\s*(.*?)(?:\n\*\*Date Added:|\n---|\n\n###)'
        matches = re.findall(lesson_pattern, content, re.DOTALL)
        
        for match in matches:
            lesson_num, title, mistake, impact, prevention, rule = match
            
            # Extract severity if present
            severity_match = re.search(r'\*\*Severity:\*\*\s*(CRITICAL|HIGH|MEDIUM|LOW)', content[content.find(match[0]):content.find(match[0])+500])
            severity = severity_match.group(1) if severity_match else "MEDIUM"
            
            # Check for CRITICAL marker
            if "🚨 CRITICAL" in title or "CRITICAL" in title:
                severity = "CRITICAL"
            
            self.lessons.append({
                'id': f"lesson_{lesson_num}",
                'number': int(lesson_num),
                'title': title.strip(),
                'mistake': mistake.strip(),
                'impact': impact.strip(),
                'prevention': prevention.strip(),
                'rule': rule.strip(),
                'severity': severity,
                'keywords': self._extract_keywords(mistake + ' ' + title)
            })
        
        print(f"✅ Loaded {len(self.lessons)} lessons from repeated-mistakes.md")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for pattern matching"""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'}
        
        # Extract words (4+ characters)
        words = re.findall(r'\b\w{4,}\b', text.lower())
        keywords = [w for w in words if w not in stop_words]
        
        # Return top 10 keywords
        return list(set(keywords))[:10]
    
    def _build_pattern_cache(self):
        """Build pattern cache for fast matching"""
        if CACHE_FILE.exists():
            try:
                with open(CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                    cache_timestamp = cache_data.get('timestamp', '')
                    
                    # Check if cache is fresh (less than 1 hour old)
                    if cache_timestamp:
                        cache_time = datetime.fromisoformat(cache_timestamp)
                        age_hours = (datetime.now() - cache_time).total_seconds() / 3600
                        if age_hours < 1.0:
                            self.pattern_cache = cache_data.get('patterns', {})
                            self.cache_loaded = True
                            print(f"✅ Loaded pattern cache ({len(self.pattern_cache)} patterns)")
                            return
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Rebuild cache
        self.pattern_cache = {}
        for lesson in self.lessons:
            pattern_key = f"lesson_{lesson['number']}"
            self.pattern_cache[pattern_key] = {
                'keywords': lesson['keywords'],
                'mistake_text': lesson['mistake'].lower(),
                'title': lesson['title'].lower(),
                'severity': lesson['severity'],
                'prevention': lesson['prevention'],
                'rule': lesson['rule']
            }
        
        # Save cache
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'patterns': self.pattern_cache
        }
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        self.cache_loaded = True
        print(f"✅ Built pattern cache ({len(self.pattern_cache)} patterns)")
    
    def check_action(self, action_description: str) -> Dict[str, Any]:
        """
        Check action against mistake database
        
        Args:
            action_description: Description of the action to check
            
        Returns:
            {
                'allowed': bool,
                'matched_mistake': str or None,
                'prevention_rule': str or None,
                'severity': str or None,
                'confidence': float,
                'matched_keywords': List[str]
            }
        """
        action_lower = action_description.lower()
        matches = []
        
        # Check against each lesson pattern
        for lesson in self.lessons:
            # Keyword matching
            keyword_matches = sum(1 for kw in lesson['keywords'] if kw in action_lower)
            
            # Text similarity (simple substring matching)
            mistake_in_action = lesson['mistake'].lower() in action_lower or any(kw in action_lower for kw in lesson['keywords'][:5])
            
            if keyword_matches >= 2 or mistake_in_action:
                confidence = min(keyword_matches / len(lesson['keywords']) if lesson['keywords'] else 0, 1.0)
                if mistake_in_action:
                    confidence = max(confidence, 0.7)
                
                matches.append({
                    'lesson': lesson,
                    'confidence': confidence,
                    'keyword_matches': keyword_matches,
                    'matched_keywords': [kw for kw in lesson['keywords'] if kw in action_lower]
                })
        
        if not matches:
            return {
                'allowed': True,
                'matched_mistake': None,
                'prevention_rule': None,
                'severity': None,
                'confidence': 0.0,
                'matched_keywords': []
            }
        
        # Sort by confidence and severity
        matches.sort(key=lambda x: (
            {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}.get(x['lesson']['severity'], 0),
            x['confidence']
        ), reverse=True)
        
        best_match = matches[0]
        lesson = best_match['lesson']
        
        # Determine if action should be blocked
        severity = lesson['severity']
        allowed = severity not in ['CRITICAL', 'HIGH']  # Block CRITICAL and HIGH
        
        # Log to audit
        self._log_to_audit(action_description, lesson, best_match['confidence'], allowed)
        
        return {
            'allowed': allowed,
            'matched_mistake': lesson['mistake'],
            'prevention_rule': lesson['rule'],
            'prevention_steps': lesson['prevention'],
            'severity': severity,
            'confidence': best_match['confidence'],
            'matched_keywords': best_match['matched_keywords'],
            'lesson_id': lesson['id'],
            'lesson_number': lesson['number']
        }
    
    def _log_to_audit(self, action_description: str, lesson: Dict, confidence: float, allowed: bool):
        """Log check result to audit file"""
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        audit_entry = {
            'timestamp': datetime.now().isoformat(),
            'action_description': action_description[:200],  # Truncate
            'lesson_id': lesson['id'],
            'lesson_number': lesson['number'],
            'severity': lesson['severity'],
            'confidence': confidence,
            'allowed': allowed,
            'prevention_applied': not allowed
        }
        
        with open(AUDIT_LOG_FILE, 'a') as f:
            f.write(json.dumps(audit_entry) + '\n')
    
    def refresh_cache(self):
        """Refresh pattern cache (call when lessons change)"""
        self._load_lessons()
        self._build_pattern_cache()
        print("✅ Pattern cache refreshed")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get checker statistics"""
        return {
            'lessons_loaded': len(self.lessons),
            'patterns_cached': len(self.pattern_cache),
            'cache_fresh': self.cache_loaded,
            'severity_breakdown': {
                'CRITICAL': len([l for l in self.lessons if l['severity'] == 'CRITICAL']),
                'HIGH': len([l for l in self.lessons if l['severity'] == 'HIGH']),
                'MEDIUM': len([l for l in self.lessons if l['severity'] == 'MEDIUM']),
                'LOW': len([l for l in self.lessons if l['severity'] == 'LOW'])
            }
        }


def main():
    """CLI interface for testing"""
    import sys
    
    checker = PreExecutionChecker()
    
    if len(sys.argv) > 1:
        action = ' '.join(sys.argv[1:])
        result = checker.check_action(action)
        
        print(f"\n🔍 Pre-Execution Check Result:")
        print(f"   Action: {action}")
        print(f"   Allowed: {'✅ YES' if result['allowed'] else '❌ NO'}")
        
        if result['matched_mistake']:
            print(f"   Matched Mistake: {result['matched_mistake'][:100]}...")
            print(f"   Severity: {result['severity']}")
            print(f"   Confidence: {result['confidence']:.2%}")
            print(f"   Prevention Rule: {result['prevention_rule']}")
            if not result['allowed']:
                print(f"\n🚫 ACTION BLOCKED - This matches a known mistake!")
                print(f"   Apply prevention: {result['prevention_steps']}")
        else:
            print("   ✅ No matching mistakes found")
    else:
        # Show statistics
        stats = checker.get_statistics()
        print(f"\n📊 Pre-Execution Checker Statistics:")
        print(f"   Lessons Loaded: {stats['lessons_loaded']}")
        print(f"   Patterns Cached: {stats['patterns_cached']}")
        print(f"   Severity Breakdown:")
        for severity, count in stats['severity_breakdown'].items():
            print(f"     {severity}: {count}")


if __name__ == "__main__":
    main()

