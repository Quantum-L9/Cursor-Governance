#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "LRN-VT-001"
component_name: "Violation Tracker"
layer: "learning"
domain: "feedback"
type: "tracker"
status: "active"
created: "2026-01-02T06:13:53Z"
updated: "2026-01-02T06:13:53Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["argparse", "json", "re", "datetime", "pathlib", "typing", "httpx"]
integrates_with: ["LRN-RM-001", "OPS-FL-001", "MCP-MEMORY"]
api_endpoints: []
data_sources: ["repeated-mistakes.md", "violations.jsonl", "audit_log.jsonl"]
outputs: ["violations.jsonl", "audit_log.jsonl", "mcp_memory_entries"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: true
logging_level: "info"
performance_tier: "realtime"

# === BUSINESS METADATA ===
purpose: "Log and track lesson violations to close the learning feedback loop"
summary: "CLI tool for logging violations, auto-detecting patterns, viewing stats, and syncing to MCP Memory"
business_value: "Enables enforcement of learned lessons and cross-session memory of mistakes"
success_metrics: ["violation_log_success = 1.0", "mcp_sync_latency < 500ms"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "feedback", "violations", "mcp-memory", "tracking"]
keywords: ["violation", "lesson", "feedback", "tracking", "enforcement"]
related_components: ["LRN-RM-001", "OPS-FL-001"]

# === DESCRIPTION ===
L9 Violation Tracker - Logs lesson violations to local audit log and MCP Memory.

Usage:
    python3 violation_tracker.py --lesson-id lesson-015-investigate-first --context "..."
    python3 violation_tracker.py --detect-file output.md
    python3 violation_tracker.py --list-violations
    python3 violation_tracker.py --stats
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import os

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# Path configuration
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
LESSONS_FILE = WORKSPACE_ROOT / ".cursor-commands/learning/failures/repeated-mistakes.md"
AUDIT_LOG = WORKSPACE_ROOT / ".cursor-commands/learning/failures/audit_log.jsonl"
VIOLATIONS_LOG = WORKSPACE_ROOT / ".cursor-commands/learning/failures/violations.jsonl"
CONFIG_FILE = WORKSPACE_ROOT / ".cursor-commands/ops/feedback_loop_config.yaml"

# MCP Memory configuration
MCP_MEMORY_URL = os.environ.get("MCP_MEMORY_URL", "https://l9.quantumaipartners.com/mcp")
MCP_MEMORY_ENABLED = os.environ.get("MCP_MEMORY_ENABLED", "true").lower() == "true"


def sync_to_mcp_memory(entry: dict[str, Any]) -> bool:
    """
    Sync a violation entry to MCP Memory for cross-session persistence.
    
    Args:
        entry: The violation entry to sync
        
    Returns:
        True if sync succeeded, False otherwise
    """
    if not MCP_MEMORY_ENABLED:
        return False
    
    if not HAS_HTTPX:
        print("⚠️  httpx not installed, skipping MCP sync")
        return False
    
    try:
        # Format for MCP Memory save_memory tool
        memory_payload = {
            "content": f"VIOLATION: {entry['lesson_id']} - {entry['context'][:200]}",
            "metadata": {
                "kind": "lesson_violation",
                "lesson_id": entry["lesson_id"],
                "severity": entry["severity"],
                "timestamp": entry["timestamp_utc"],
                "trigger_source": entry.get("trigger_source", "unknown"),
            },
        }
        
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                f"{MCP_MEMORY_URL}/tools/save_memory",
                json=memory_payload,
            )
            
            if response.status_code == 200:
                print("✅ Synced to MCP Memory")
                return True
            else:
                print(f"⚠️  MCP sync failed: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"⚠️  MCP sync error: {e}")
        return False


# Violation detection patterns (from feedback_loop_config.yaml)
VIOLATION_PATTERNS = [
    {
        "pattern": r"may not be fully implemented",
        "lesson_id": "lesson-015-investigate-first",
        "severity": "critical",
    },
    {
        "pattern": r"likely generated",
        "lesson_id": "lesson-015-investigate-first",
        "severity": "critical",
    },
    {
        "pattern": r"probably exists",
        "lesson_id": "lesson-015-investigate-first",
        "severity": "critical",
    },
    {
        "pattern": r"/Users/ib-mac/",
        "lesson_id": "lesson-013-use-home-variable",
        "severity": "critical",
    },
    {
        "pattern": r"docker-compose\.yaml",
        "lesson_id": "lesson-014-root-docker-compose",
        "severity": "critical",
    },
    {
        "pattern": r"Library/Application Support/Cursor",
        "lesson_id": "lesson-012-dropbox-not-library",
        "severity": "ultra-critical",
    },
]


def log_violation(
    lesson_id: str,
    context: str,
    severity: str = "critical",
    trigger_source: str = "violation_command",
) -> dict[str, Any]:
    """
    Log a lesson violation to local files and optionally MCP Memory.
    
    Args:
        lesson_id: The MCP-ID of the violated lesson (e.g., lesson-015-investigate-first)
        context: Description of what happened
        severity: critical, high, medium, low, ultra-critical
        trigger_source: What triggered this violation log
    
    Returns:
        The violation entry that was logged
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    entry = {
        "timestamp_utc": timestamp,
        "change_type": "lesson_violation",
        "trigger_source": trigger_source,
        "lesson_id": lesson_id,
        "context": context,
        "severity": severity,
        "outcome": "pending",
    }
    
    # Append to violations log
    VIOLATIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(VIOLATIONS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    
    # Append to audit log
    audit_entry = {
        "timestamp_utc": timestamp,
        "change_type": "lesson_violation",
        "trigger_source": trigger_source,
        "outcome": "pending",
        "next_steps": f"Review lesson {lesson_id} and reinforce prevention",
        "lesson_id": lesson_id,
    }
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(audit_entry) + "\n")
    
    print(f"✅ Violation logged: {lesson_id}")
    print(f"   Context: {context[:100]}..." if len(context) > 100 else f"   Context: {context}")
    print(f"   Severity: {severity}")
    print(f"   Logged to: {VIOLATIONS_LOG}")
    
    # Sync to MCP Memory for cross-session persistence
    sync_to_mcp_memory(entry)
    
    return entry


def detect_violations(text: str) -> list[dict[str, Any]]:
    """
    Auto-detect potential violations in text using pattern matching.
    
    Args:
        text: The text to scan for violations
    
    Returns:
        List of detected violation patterns
    """
    violations = []
    
    for pattern_def in VIOLATION_PATTERNS:
        pattern = pattern_def["pattern"]
        if re.search(pattern, text, re.IGNORECASE):
            violations.append({
                "pattern": pattern,
                "lesson_id": pattern_def["lesson_id"],
                "severity": pattern_def["severity"],
            })
    
    return violations


def list_violations(limit: int = 20) -> list[dict[str, Any]]:
    """
    List recent violations from the violations log.
    
    Args:
        limit: Maximum number of violations to return
    
    Returns:
        List of violation entries
    """
    if not VIOLATIONS_LOG.exists():
        return []
    
    violations = []
    with open(VIOLATIONS_LOG, "r") as f:
        for line in f:
            if line.strip():
                violations.append(json.loads(line))
    
    # Return most recent first
    return list(reversed(violations[-limit:]))


def get_stats() -> dict[str, Any]:
    """
    Get violation statistics.
    
    Returns:
        Dict with violation counts by lesson_id and severity
    """
    if not VIOLATIONS_LOG.exists():
        return {"total": 0, "by_lesson": {}, "by_severity": {}}
    
    by_lesson: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    total = 0
    
    with open(VIOLATIONS_LOG, "r") as f:
        for line in f:
            if line.strip():
                entry = json.loads(line)
                total += 1
                
                lesson_id = entry.get("lesson_id", "unknown")
                by_lesson[lesson_id] = by_lesson.get(lesson_id, 0) + 1
                
                severity = entry.get("severity", "unknown")
                by_severity[severity] = by_severity.get(severity, 0) + 1
    
    return {
        "total": total,
        "by_lesson": dict(sorted(by_lesson.items(), key=lambda x: x[1], reverse=True)),
        "by_severity": by_severity,
    }


def main():
    parser = argparse.ArgumentParser(
        description="L9 Violation Tracker - Log and track lesson violations"
    )
    
    parser.add_argument(
        "--lesson-id",
        type=str,
        help="MCP-ID of the violated lesson (e.g., lesson-015-investigate-first)",
    )
    parser.add_argument(
        "--context",
        type=str,
        default="",
        help="Description of what happened",
    )
    parser.add_argument(
        "--severity",
        type=str,
        choices=["ultra-critical", "critical", "high", "medium", "low"],
        default="critical",
        help="Severity of the violation",
    )
    parser.add_argument(
        "--detect-file",
        type=str,
        help="Path to file to scan for potential violations",
    )
    parser.add_argument(
        "--detect-text",
        type=str,
        help="Text to scan for potential violations",
    )
    parser.add_argument(
        "--list-violations",
        action="store_true",
        help="List recent violations",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show violation statistics",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit for list operations",
    )
    
    args = parser.parse_args()
    
    if args.list_violations:
        violations = list_violations(args.limit)
        if not violations:
            print("No violations logged yet.")
            return
        
        print(f"📋 Recent Violations ({len(violations)}):\n")
        for v in violations:
            print(f"  [{v.get('severity', 'unknown').upper()}] {v.get('lesson_id', 'unknown')}")
            print(f"      Time: {v.get('timestamp_utc', 'unknown')}")
            context = v.get("context", "")
            if context:
                print(f"      Context: {context[:80]}...")
            print()
        return
    
    if args.stats:
        stats = get_stats()
        print("📊 Violation Statistics:\n")
        print(f"  Total violations: {stats['total']}")
        print("\n  By Lesson:")
        for lesson_id, count in stats["by_lesson"].items():
            print(f"    {lesson_id}: {count}")
        print("\n  By Severity:")
        for severity, count in stats["by_severity"].items():
            print(f"    {severity}: {count}")
        return
    
    if args.detect_file:
        file_path = Path(args.detect_file)
        if not file_path.exists():
            print(f"❌ File not found: {file_path}")
            sys.exit(1)
        
        text = file_path.read_text()
        violations = detect_violations(text)
        
        if not violations:
            print("✅ No violations detected in file.")
            return
        
        print(f"⚠️  Detected {len(violations)} potential violation(s):\n")
        for v in violations:
            print(f"  [{v['severity'].upper()}] Pattern: {v['pattern']}")
            print(f"      Lesson: {v['lesson_id']}")
            print()
        return
    
    if args.detect_text:
        violations = detect_violations(args.detect_text)
        
        if not violations:
            print("✅ No violations detected in text.")
            return
        
        print(f"⚠️  Detected {len(violations)} potential violation(s):\n")
        for v in violations:
            print(f"  [{v['severity'].upper()}] Pattern: {v['pattern']}")
            print(f"      Lesson: {v['lesson_id']}")
            print()
        return
    
    if args.lesson_id:
        if not args.context:
            print("❌ --context is required when logging a violation")
            sys.exit(1)
        
        log_violation(
            lesson_id=args.lesson_id,
            context=args.context,
            severity=args.severity,
        )
        return
    
    # No action specified
    parser.print_help()


if __name__ == "__main__":
    main()

