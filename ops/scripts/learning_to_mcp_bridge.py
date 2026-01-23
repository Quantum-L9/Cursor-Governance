#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "OPS-LMB-001"
component_name: "Learning to MCP-Memory Bridge"
layer: "operations"
domain: "learning"
type: "bridge"
status: "active"
created: "2025-11-17T00:00:00Z"
updated: "2026-01-04T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["httpx", "json", "hashlib", "pathlib", "dataclasses"]
integrates_with: ["MCP-MEMORY", "OPS-AGG-001", "LRN-RM-001"]
api_endpoints: []
data_sources: ["repeated-mistakes.md", "memory_index.json"]
outputs: ["MCP-Memory entries"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Bridge learning extraction pipeline to MCP-Memory for semantic retrieval"
summary: "Migrates gold lessons and extracted memories to MCP-Memory API"
business_value: "Enables cross-session semantic search of learned patterns"
success_metrics: ["migration_success >= 99%", "api_latency < 500ms"]

# === TAGS & CLASSIFICATION ===
tags: ["mcp-memory", "bridge", "learning", "migration", "semantic"]
keywords: ["mcp", "memory", "bridge", "learning", "migration"]
related_components: ["MCP-MEMORY", "OPS-AGG-001", "LRN-RM-001"]

# === DESCRIPTION ===
Learning to MCP-Memory Bridge

Bridges the learning extraction pipeline to MCP-Memory for semantic retrieval.

Flow:
    repeated-mistakes.md → parse → filter → format → MCP-Memory API

Usage:
    # Migrate gold lessons from repeated-mistakes.md
    python learning_to_mcp_bridge.py --migrate-gold
    
    # Ingest from memory_index.json (automated extraction output)
    python learning_to_mcp_bridge.py --ingest-extracted
    
    # Dry run (show what would be migrated)
    python learning_to_mcp_bridge.py --migrate-gold --dry-run
"""

import os
import re
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# MCP-Memory API endpoint (via Cloudflare/Caddy or local)
MCP_MEMORY_URL = os.environ.get(
    "MCP_MEMORY_URL", 
    "https://l9.quantumaipartners.com/mcp/memory"
)

# Default user_id for Cursor-originated lessons
DEFAULT_USER_ID = os.environ.get("MCP_USER_ID", "cursor")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # L9 root
REPEATED_MISTAKES_PATH = PROJECT_ROOT / ".cursor-commands/learning/failures/repeated-mistakes.md"
MEMORY_INDEX_PATH = PROJECT_ROOT / ".cursor-commands/ops/logs/memory_index.json"
MIGRATION_LOG_PATH = PROJECT_ROOT / ".cursor-commands/ops/logs/mcp_migration.jsonl"

# Confidence thresholds
MIN_CONFIDENCE_FOR_MIGRATION = 0.7
HIGH_IMPORTANCE_THRESHOLD = 0.9


@dataclass
class Lesson:
    """Structured lesson ready for MCP-Memory."""
    id: str
    title: str
    content: str
    mistake: str
    prevention: str
    rule: str
    tags: List[str]
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    importance: float  # 0.0 - 1.0
    confidence: float  # 0.0 - 1.0
    source: str  # "repeated-mistakes.md", "memory_aggregator", etc.
    mcp_id: Optional[str] = None
    date_added: Optional[str] = None
    
    def to_mcp_payload(self, user_id: str = DEFAULT_USER_ID) -> Dict[str, Any]:
        """Convert to MCP-Memory SaveMemoryWithConfidenceRequest format."""
        # Build rich content for semantic search
        full_content = f"""LESSON: {self.title}

MISTAKE: {self.mistake}

PREVENTION: {self.prevention}

RULE: {self.rule}

SEVERITY: {self.severity}
"""
        return {
            "content": full_content,
            "kind": "lesson",
            "scope": "cursor",  # Cursor-originated
            "duration": "long_term",  # Lessons are permanent
            "user_id": user_id,
            "tags": self.tags,
            "importance": self.importance,
            "confidence": self.confidence,
            "source": self.source,
            "related_memory_ids": [],
            "metadata": {
                "lesson_id": self.id,
                "mcp_id": self.mcp_id,
                "title": self.title,
                "severity": self.severity,
                "date_added": self.date_added,
                "content_hash": self._content_hash()
            }
        }
    
    def _content_hash(self) -> str:
        """Generate content hash for deduplication."""
        content = f"{self.title}:{self.mistake}:{self.prevention}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class LearningToMCPBridge:
    """
    Bridge between learning extraction pipeline and MCP-Memory.
    
    Responsibilities:
    - Parse lessons from repeated-mistakes.md
    - Parse patterns from memory_index.json
    - Filter by confidence threshold
    - Deduplicate against existing MCP memories
    - Format and submit to MCP-Memory API
    """
    
    def __init__(
        self,
        mcp_url: str = MCP_MEMORY_URL,
        user_id: str = DEFAULT_USER_ID,
        dry_run: bool = False
    ):
        self.mcp_url = mcp_url
        self.user_id = user_id
        self.dry_run = dry_run
        self.migrated_hashes: set = set()
        self._load_migration_log()
    
    def _load_migration_log(self):
        """Load previously migrated lesson hashes."""
        if MIGRATION_LOG_PATH.exists():
            with open(MIGRATION_LOG_PATH, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('status') == 'success':
                            self.migrated_hashes.add(entry.get('content_hash', ''))
                    except json.JSONDecodeError:
                        continue
        logger.info(f"Loaded {len(self.migrated_hashes)} previously migrated lessons")
    
    def _log_migration(self, lesson: Lesson, status: str, mcp_response: Optional[Dict] = None):
        """Log migration attempt for idempotency."""
        MIGRATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "lesson_id": lesson.id,
            "title": lesson.title,
            "content_hash": lesson._content_hash(),
            "status": status,
            "mcp_response": mcp_response,
            "user_id": self.user_id
        }
        
        with open(MIGRATION_LOG_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    # =========================================================================
    # Parse Gold Lessons from repeated-mistakes.md
    # =========================================================================
    
    def parse_gold_lessons(self) -> List[Lesson]:
        """Parse curated lessons from repeated-mistakes.md."""
        if not REPEATED_MISTAKES_PATH.exists():
            logger.error(f"repeated-mistakes.md not found at {REPEATED_MISTAKES_PATH}")
            return []
        
        content = REPEATED_MISTAKES_PATH.read_text()
        lessons = []
        
        # Parse each lesson block (### **N. Title**)
        pattern = r'### \*\*(\d+)\. (.+?)\*\*.*?\n\*\*Mistake:\*\* (.+?)\n.*?\*\*Prevention:\*\* (.+?)\n\*\*Rule:\*\* (.+?)\n.*?\*\*Tags:\*\* `(.+?)`.*?\*\*MCP-ID:\*\* `(.+?)`'
        
        # Simpler approach: split by ### and parse each section
        sections = re.split(r'\n### \*\*', content)
        
        for section in sections[1:]:  # Skip header
            try:
                lesson = self._parse_lesson_section(section)
                if lesson:
                    lessons.append(lesson)
            except Exception as e:
                logger.warning(f"Failed to parse section: {e}")
                continue
        
        logger.info(f"Parsed {len(lessons)} gold lessons from repeated-mistakes.md")
        return lessons
    
    def _parse_lesson_section(self, section: str) -> Optional[Lesson]:
        """Parse a single lesson section."""
        lines = section.strip().split('\n')
        if not lines:
            return None
        
        # Parse title line: "1. Data Fabrication** 🔴 CRITICAL"
        title_match = re.match(r'(\d+)\. (.+?)\*\*', lines[0])
        if not title_match:
            return None
        
        lesson_num = title_match.group(1)
        title = title_match.group(2).strip()
        
        # Determine severity from emojis/text
        severity = "MEDIUM"
        if "ULTRA CRITICAL" in section or "🚨🚨🚨" in section:
            severity = "ULTRA-CRITICAL"
        elif "CRITICAL" in section or "🔴" in section:
            severity = "CRITICAL"
        elif "HIGH" in section or "💎" in section:
            severity = "HIGH"
        
        # Extract fields
        mistake = self._extract_field(section, "Mistake")
        prevention = self._extract_field(section, "Prevention")
        rule = self._extract_field(section, "Rule")
        tags_str = self._extract_field(section, "Tags")
        mcp_id = self._extract_field(section, "MCP-ID")
        date_added = self._extract_field(section, "Date Added")
        
        # Parse tags
        tags = []
        if tags_str:
            tags = [t.strip().strip('`') for t in tags_str.split(',')]
        
        # Calculate importance based on severity
        importance_map = {
            "ULTRA-CRITICAL": 1.0,
            "CRITICAL": 0.95,
            "HIGH": 0.85,
            "MEDIUM": 0.7,
            "LOW": 0.5
        }
        importance = importance_map.get(severity, 0.7)
        
        return Lesson(
            id=f"gold-{lesson_num}",
            title=title,
            content=section[:500],  # First 500 chars as summary
            mistake=mistake or "Not specified",
            prevention=prevention or "Not specified",
            rule=rule or "Not specified",
            tags=tags,
            severity=severity,
            importance=importance,
            confidence=1.0,  # Gold lessons are high confidence
            source="repeated-mistakes.md",
            mcp_id=mcp_id,
            date_added=date_added
        )
    
    def _extract_field(self, text: str, field_name: str) -> Optional[str]:
        """Extract a field value from lesson text."""
        pattern = rf'\*\*{field_name}:\*\* (.+?)(?:\n|$)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip().strip('`')
        return None
    
    # =========================================================================
    # Parse Extracted Patterns from memory_index.json
    # =========================================================================
    
    def parse_extracted_patterns(self, min_confidence: float = MIN_CONFIDENCE_FOR_MIGRATION) -> List[Lesson]:
        """Parse patterns from memory_aggregator output."""
        if not MEMORY_INDEX_PATH.exists():
            logger.warning(f"memory_index.json not found at {MEMORY_INDEX_PATH}")
            return []
        
        with open(MEMORY_INDEX_PATH, 'r') as f:
            data = json.load(f)
        
        learnings = data.get('learnings', [])
        lessons = []
        
        for learning in learnings:
            # Skip low-confidence patterns
            enhanced = learning.get('enhanced_context', {})
            confidence = enhanced.get('confidence', 0.5)
            
            if confidence < min_confidence:
                continue
            
            # Skip "Unknown pattern" noise
            content = learning.get('content', '')
            if 'Unknown pattern' in content:
                continue
            
            lesson = Lesson(
                id=f"extracted-{learning.get('hash', 'unknown')}",
                title=content[:100],
                content=content,
                mistake=enhanced.get('error_pattern', content),
                prevention=enhanced.get('quick_fix', 'Review pattern context'),
                rule="Apply prevention protocol",
                tags=self._infer_tags(learning),
                severity=enhanced.get('severity', 'MEDIUM'),
                importance=enhanced.get('correction_value', 0.7),
                confidence=confidence,
                source="memory_aggregator",
                date_added=learning.get('timestamp')
            )
            lessons.append(lesson)
        
        logger.info(f"Parsed {len(lessons)} extracted patterns (confidence >= {min_confidence})")
        return lessons
    
    def _infer_tags(self, learning: Dict) -> List[str]:
        """Infer tags from learning pattern type."""
        enhanced = learning.get('enhanced_context', {})
        tags = []
        
        pattern_type = enhanced.get('pattern_type', 'unknown')
        if pattern_type:
            tags.append(pattern_type)
        
        trigger_type = enhanced.get('trigger_type', '')
        if trigger_type:
            tags.append(trigger_type)
        
        # Infer from content
        content = learning.get('content', '').lower()
        if 'auth' in content:
            tags.append('authentication')
        if 'json' in content:
            tags.append('json')
        if 'path' in content:
            tags.append('paths')
        
        return tags[:5]  # Max 5 tags
    
    # =========================================================================
    # MCP-Memory Integration
    # =========================================================================
    
    def migrate_to_mcp(self, lessons: List[Lesson]) -> Dict[str, int]:
        """Migrate lessons to MCP-Memory."""
        stats = {"success": 0, "skipped": 0, "failed": 0}
        
        for lesson in lessons:
            content_hash = lesson._content_hash()
            
            # Skip if already migrated
            if content_hash in self.migrated_hashes:
                logger.info(f"Skipping already migrated: {lesson.title[:50]}")
                stats["skipped"] += 1
                continue
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would migrate: {lesson.title[:50]}")
                stats["success"] += 1
                continue
            
            # Submit to MCP-Memory
            try:
                result = self._submit_to_mcp(lesson)
                if result:
                    self._log_migration(lesson, "success", result)
                    self.migrated_hashes.add(content_hash)
                    stats["success"] += 1
                    logger.info(f"✅ Migrated: {lesson.title[:50]}")
                else:
                    self._log_migration(lesson, "failed")
                    stats["failed"] += 1
                    logger.error(f"❌ Failed: {lesson.title[:50]}")
            except Exception as e:
                self._log_migration(lesson, "error")
                stats["failed"] += 1
                logger.error(f"❌ Error migrating {lesson.title[:50]}: {e}")
        
        return stats
    
    def _submit_to_mcp(self, lesson: Lesson) -> Optional[Dict]:
        """Submit lesson to MCP-Memory API."""
        import urllib.request
        import urllib.error
        
        payload = lesson.to_mcp_payload(self.user_id)
        
        try:
            req = urllib.request.Request(
                f"{self.mcp_url}/save",
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error: {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            logger.error(f"URL error: {e.reason}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    # =========================================================================
    # CLI Commands
    # =========================================================================
    
    def migrate_gold_lessons(self) -> Dict[str, int]:
        """Migrate gold lessons from repeated-mistakes.md."""
        lessons = self.parse_gold_lessons()
        return self.migrate_to_mcp(lessons)
    
    def ingest_extracted(self) -> Dict[str, int]:
        """Ingest extracted patterns from memory_aggregator."""
        lessons = self.parse_extracted_patterns()
        return self.migrate_to_mcp(lessons)
    
    def full_sync(self) -> Dict[str, int]:
        """Full sync: gold lessons + extracted patterns."""
        gold = self.parse_gold_lessons()
        extracted = self.parse_extracted_patterns()
        all_lessons = gold + extracted
        return self.migrate_to_mcp(all_lessons)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Learning to MCP-Memory Bridge')
    parser.add_argument('--migrate-gold', action='store_true', help='Migrate gold lessons from repeated-mistakes.md')
    parser.add_argument('--ingest-extracted', action='store_true', help='Ingest patterns from memory_index.json')
    parser.add_argument('--full-sync', action='store_true', help='Full sync: gold + extracted')
    parser.add_argument('--dry-run', action='store_true', help='Dry run - show what would be migrated')
    parser.add_argument('--user-id', default=DEFAULT_USER_ID, help='MCP user_id (default: cursor)')
    parser.add_argument('--mcp-url', default=MCP_MEMORY_URL, help='MCP-Memory API URL')
    
    args = parser.parse_args()
    
    bridge = LearningToMCPBridge(
        mcp_url=args.mcp_url,
        user_id=args.user_id,
        dry_run=args.dry_run
    )
    
    print("=" * 60)
    print("LEARNING TO MCP-MEMORY BRIDGE")
    print("=" * 60)
    print(f"MCP URL: {args.mcp_url}")
    print(f"User ID: {args.user_id}")
    print(f"Dry Run: {args.dry_run}")
    print("=" * 60)
    
    if args.migrate_gold:
        print("\n📚 Migrating Gold Lessons...")
        stats = bridge.migrate_gold_lessons()
    elif args.ingest_extracted:
        print("\n🔍 Ingesting Extracted Patterns...")
        stats = bridge.ingest_extracted()
    elif args.full_sync:
        print("\n🔄 Full Sync...")
        stats = bridge.full_sync()
    else:
        # Default: show parsed lessons
        print("\n📋 Parsed Gold Lessons:")
        lessons = bridge.parse_gold_lessons()
        for i, lesson in enumerate(lessons, 1):
            print(f"\n{i}. [{lesson.severity}] {lesson.title}")
            print(f"   Mistake: {lesson.mistake[:80]}...")
            print(f"   Tags: {', '.join(lesson.tags)}")
            print(f"   MCP-ID: {lesson.mcp_id}")
        
        print(f"\nTotal: {len(lessons)} lessons ready for migration")
        print("\nRun with --migrate-gold to migrate to MCP-Memory")
        return
    
    print("\n" + "=" * 60)
    print("MIGRATION RESULTS")
    print("=" * 60)
    print(f"✅ Success: {stats['success']}")
    print(f"⏭️  Skipped: {stats['skipped']}")
    print(f"❌ Failed:  {stats['failed']}")
    print("=" * 60)


if __name__ == '__main__':
    main()




