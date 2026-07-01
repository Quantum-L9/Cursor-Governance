#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-AUD-001"
component_name: "Learning Folder Audit Logger"
layer: "operations"
domain: "audit"
type: "audit_logger"
status: "active"
created: "2025-11-22T00:00:00Z"
updated: "2025-11-22T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["python3", "json", "pathlib"]
integrates_with: ["OPS-MLS-001", "INT-ML-001"]
data_sources: ["learning/failures/", "learning/patterns/", "learning/solutions/"]
outputs: ["ops/logs/learning_audit.jsonl"]

# === OPERATIONAL METADATA ===
execution_mode: "automatic"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Track all lessons/mistakes added to learning folder with full audit trail"
summary: "Maintains comprehensive audit log of learning folder additions with timestamps, sources, and metadata"
business_value: "Enables full traceability of lesson additions and governance compliance"
success_metrics: ["audit_coverage_100%", "zero_missing_entries", "query_response_time < 100ms"]
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import os

def get_global_commands_path():
    """Get GlobalCommands path"""
    ssot = Path.home() / ".cursor-governance"
    if ssot.is_dir():
        return ssot
    legacy_dropbox = Path.home() / "Dropbox/Cursor Governance/GlobalCommands"
    if legacy_dropbox.is_dir():
        return legacy_dropbox
    library = Path.home() / "Library/Application Support/Cursor/GlobalCommands"
    if library.is_dir():
        return library
    raise FileNotFoundError("GlobalCommands not found")

GLOBAL_COMMANDS = get_global_commands_path()
LEARNING_DIR = GLOBAL_COMMANDS / "learning"
AUDIT_LOG = GLOBAL_COMMANDS / "ops/logs/learning_audit.jsonl"
REPEATED_MISTAKES_FILE = LEARNING_DIR / "failures/repeated-mistakes.md"
QUICK_FIXES_FILE = LEARNING_DIR / "patterns/quick-fixes.md"


class LearningAuditLogger:
    """Tracks all additions to learning folder"""
    
    def __init__(self):
        self.audit_log = self._load_audit_log()
        self.tracked_hashes = set(entry.get('content_hash') for entry in self.audit_log if entry.get('content_hash'))
    
    def _load_audit_log(self) -> List[Dict[str, Any]]:
        """Load existing audit log"""
        if AUDIT_LOG.exists():
            entries = []
            with open(AUDIT_LOG, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            return entries
        return []
    
    def _save_audit_entry(self, entry: Dict[str, Any]):
        """Append audit entry to log"""
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_LOG, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate hash of content for deduplication"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def log_lesson_addition(self, 
                          lesson_type: str,
                          content: str,
                          source_file: Optional[str] = None,
                          source_type: str = "learning",
                          metadata: Optional[Dict[str, Any]] = None):
        """
        Log addition of lesson/mistake to learning folder
        
        Args:
            lesson_type: Type of lesson (mistake, solution, pattern, etc.)
            content: Content of the lesson
            source_file: Source file path (relative to GlobalCommands)
            source_type: Type of source (learning, manual, extracted, etc.)
            metadata: Additional metadata (hash, timestamp, etc.)
        """
        content_hash = self._calculate_content_hash(content)
        
        # Check if already logged
        if content_hash in self.tracked_hashes:
            return False
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'lesson_type': lesson_type,
            'content': content[:500],  # Truncate for storage
            'content_hash': content_hash,
            'source_file': source_file,
            'source_type': source_type,
            'metadata': metadata or {},
            'learning_location': self._determine_learning_location(lesson_type, content)
        }
        
        self._save_audit_entry(entry)
        self.tracked_hashes.add(content_hash)
        return True
    
    def _determine_learning_location(self, lesson_type: str, content: str) -> str:
        """Determine where in learning folder this should be stored"""
        if lesson_type == 'mistake':
            return "learning/failures/repeated-mistakes.md"
        elif lesson_type == 'solution':
            return "learning/solutions/"
        elif lesson_type == 'pattern':
            return "learning/patterns/quick-fixes.md"
        else:
            return "learning/failures/repeated-mistakes.md"
    
    def get_audit_report(self, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        lesson_type: Optional[str] = None) -> Dict[str, Any]:
        """Generate audit report"""
        entries = self.audit_log
        
        # Filter by date range (use date_added from metadata if available, otherwise timestamp)
        if start_date:
            filtered = []
            for e in entries:
                date_added = e.get('metadata', {}).get('date_added')
                if date_added:
                    if date_added >= start_date:
                        filtered.append(e)
                elif e['timestamp'][:10] >= start_date:
                    filtered.append(e)
            entries = filtered
        
        if end_date:
            filtered = []
            for e in entries:
                date_added = e.get('metadata', {}).get('date_added')
                if date_added:
                    if date_added <= end_date:
                        filtered.append(e)
                elif e['timestamp'][:10] <= end_date:
                    filtered.append(e)
            entries = filtered
        
        # Filter by type
        if lesson_type:
            entries = [e for e in entries if e['lesson_type'] == lesson_type]
        
        # Group by date (prefer date_added from metadata)
        by_date = {}
        by_type = {}
        by_source = {}
        
        for entry in entries:
            # Use date_added from metadata if available, otherwise timestamp
            date_added = entry.get('metadata', {}).get('date_added')
            date = date_added if date_added else entry['timestamp'][:10]  # YYYY-MM-DD
            by_date[date] = by_date.get(date, 0) + 1
            by_type[entry['lesson_type']] = by_type.get(entry['lesson_type'], 0) + 1
            source = entry.get('source_type', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1
        
        # Sort entries by date_added (newest first)
        entries.sort(key=lambda e: e.get('metadata', {}).get('date_added', e['timestamp'][:10]), reverse=True)
        
        return {
            'total_entries': len(entries),
            'date_range': {
                'start': entries[0].get('metadata', {}).get('date_added', entries[0]['timestamp'][:10]) if entries else None,
                'end': entries[-1].get('metadata', {}).get('date_added', entries[-1]['timestamp'][:10]) if entries else None
            },
            'by_date': by_date,
            'by_type': by_type,
            'by_source': by_source,
            'recent_entries': entries[:20]  # First 20 entries (newest)
        }
    
    def scan_existing_learning_files(self):
        """Scan learning folder and log any unlogged entries"""
        if not LEARNING_DIR.exists():
            return
        
        # Scan repeated-mistakes.md for lessons
        if REPEATED_MISTAKES_FILE.exists():
            self._scan_repeated_mistakes(REPEATED_MISTAKES_FILE)
        
        # Scan quick-fixes.md for patterns
        if QUICK_FIXES_FILE.exists():
            self._scan_quick_fixes(QUICK_FIXES_FILE)
    
    def _scan_repeated_mistakes(self, file_path: Path):
        """Scan repeated-mistakes.md for lessons"""
        import re
        content = file_path.read_text()
        
        # Extract lesson entries (### **N. Title** ... **Date Added:** YYYY-MM-DD)
        # Pattern matches: ### **N. Title** followed by content until next ### or end
        lesson_pattern = r'### \*\*(\d+)\.\s*(.*?)\*\*\n(.*?)(?=\n### \*\*|\Z)'
        matches = list(re.finditer(lesson_pattern, content, re.DOTALL))
        
        print(f"  Found {len(matches)} lesson patterns in repeated-mistakes.md")
        
        for match in matches:
            lesson_num = match.group(1)
            lesson_title = match.group(2).strip()
            lesson_content = match.group(3).strip()
            
            # Extract date added (may be at end of content)
            date_match = re.search(r'\*\*Date Added:\*\*\s*(\d{4}-\d{2}-\d{2})', lesson_content)
            date_added = date_match.group(1) if date_match else None
            
            # Extract mistake text for hash
            mistake_match = re.search(r'\*\*Mistake:\*\*\s*(.*?)(?=\n\*\*|$)', lesson_content, re.DOTALL)
            mistake_text = mistake_match.group(1).strip() if mistake_match else lesson_title
            
            content_hash = self._calculate_content_hash(f"{lesson_num}.{lesson_title}.{mistake_text[:100]}")
            
            if content_hash not in self.tracked_hashes:
                self.log_lesson_addition(
                    lesson_type='mistake',
                    content=lesson_content[:500],
                    source_file=str(file_path.relative_to(GLOBAL_COMMANDS)),
                    source_type='repeated_mistakes',
                    metadata={'lesson_number': lesson_num, 'title': lesson_title, 'date_added': date_added}
                )
                self.tracked_hashes.add(content_hash)
    
    def _scan_quick_fixes(self, file_path: Path):
        """Scan quick-fixes.md for patterns"""
        import re
        content = file_path.read_text()
        
        # Extract pattern entries (### Pattern Title ...)
        pattern_pattern = r'### (.*?)\n(.*?)(?=\n### |\Z)'
        matches = re.finditer(pattern_pattern, content, re.DOTALL)
        
        for match in matches:
            pattern_title = match.group(1).strip()
            pattern_content = match.group(2)
            
            content_hash = self._calculate_content_hash(f"pattern.{pattern_title}")
            
            if content_hash not in self.tracked_hashes:
                self.log_lesson_addition(
                    lesson_type='pattern',
                    content=pattern_content[:500],
                    source_file=str(file_path.relative_to(GLOBAL_COMMANDS)),
                    source_type='quick_fixes',
                    metadata={'title': pattern_title}
                )


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Learning Folder Audit Logger')
    parser.add_argument('--scan', action='store_true', help='Scan existing learning files')
    parser.add_argument('--report', action='store_true', help='Generate audit report')
    parser.add_argument('--start-date', help='Start date for report (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for report (YYYY-MM-DD)')
    parser.add_argument('--type', help='Filter by lesson type')
    args = parser.parse_args()
    
    logger = LearningAuditLogger()
    
    if args.scan:
        print("🔍 Scanning existing learning files...")
        logger.scan_existing_learning_files()
        print(f"✅ Scan complete. Total entries: {len(logger.audit_log)}")
    
    if args.report:
        report = logger.get_audit_report(
            start_date=args.start_date,
            end_date=args.end_date,
            lesson_type=args.type
        )
        
        print("\n📊 Learning Folder Audit Report")
        print("=" * 60)
        print(f"Total Entries: {report['total_entries']}")
        print(f"Date Range: {report['date_range']['start']} to {report['date_range']['end']}")
        print("\nBy Type:")
        for lesson_type, count in report['by_type'].items():
            print(f"  {lesson_type}: {count}")
        print("\nBy Source:")
        for source, count in report['by_source'].items():
            print(f"  {source}: {count}")
        print("\nBy Date:")
        for date, count in sorted(report['by_date'].items()):
            print(f"  {date}: {count}")
        
        if report['recent_entries']:
            print("\nRecent Entries (last 10):")
            for entry in report['recent_entries'][-10:]:
                metadata = entry.get('metadata', {})
                title = metadata.get('title', metadata.get('lesson_number', 'Unknown'))
                print(f"  [{entry['timestamp'][:10]}] {entry['lesson_type']}: {title} - {entry['content'][:50]}...")


if __name__ == "__main__":
    main()

