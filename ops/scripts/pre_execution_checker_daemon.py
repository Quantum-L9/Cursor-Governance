#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-PEC-DAEMON-001"
component_name: "Pre-Execution Checker Daemon"
layer: "operations"
domain: "learning"
type: "daemon"
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
dependencies: ["python3", "watchdog", "json", "pathlib"]
integrates_with: ["OPS-PEC-001"]
data_sources: ["learning/failures/repeated-mistakes.md"]
outputs: ["pattern_cache_updates"]

# === OPERATIONAL METADATA ===
execution_mode: "daemon"
monitoring_required: true
logging_level: "info"
performance_tier: "real-time"

# === BUSINESS METADATA ===
purpose: "Background daemon for real-time pre-execution checking and cache refresh"
summary: "Monitors lesson file changes and refreshes pattern cache automatically"
business_value: "Ensures pre-execution checker always has latest patterns"
"""

import time
import os
from datetime import datetime
from pathlib import Path
import sys

# Add script directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("⚠️  watchdog not available - using polling mode")

from pre_execution_checker import PreExecutionChecker, get_global_commands_path

GLOBAL_COMMANDS = get_global_commands_path()
REPEATED_MISTAKES_FILE = GLOBAL_COMMANDS / "learning/failures/repeated-mistakes.md"


class LessonFileHandler(FileSystemEventHandler):
    """Handler for lesson file changes"""
    
    def __init__(self, checker: PreExecutionChecker):
        self.checker = checker
        self.last_modified = 0
    
    def on_modified(self, event):
        """Handle file modification"""
        if event.is_directory:
            return
        
        if str(event.src_path) == str(REPEATED_MISTAKES_FILE):
            # Throttle: only refresh if file changed more than 5 seconds ago
            current_time = time.time()
            if current_time - self.last_modified > 5:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Lesson file modified, refreshing cache...")
                self.checker.refresh_cache()
                self.last_modified = current_time


def run_daemon():
    """Run pre-execution checker daemon"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pre-Execution Checker Daemon starting...")
    
    checker = PreExecutionChecker()
    
    if WATCHDOG_AVAILABLE:
        # Use file system watcher
        event_handler = LessonFileHandler(checker)
        observer = Observer()
        observer.schedule(event_handler, str(REPEATED_MISTAKES_FILE.parent), recursive=False)
        observer.start()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Watching for lesson file changes...")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Daemon running (Press Ctrl+C to stop)")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Daemon stopping...")
        
        observer.join()
    else:
        # Fallback: polling mode
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Using polling mode (watchdog not available)")
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Polling every 60 seconds...")
        
        last_mtime = REPEATED_MISTAKES_FILE.stat().st_mtime if REPEATED_MISTAKES_FILE.exists() else 0
        
        try:
            while True:
                time.sleep(60)
                
                if REPEATED_MISTAKES_FILE.exists():
                    current_mtime = REPEATED_MISTAKES_FILE.stat().st_mtime
                    if current_mtime > last_mtime:
                        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Lesson file changed, refreshing cache...")
                        checker.refresh_cache()
                        last_mtime = current_mtime
        except KeyboardInterrupt:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Daemon stopping...")


if __name__ == "__main__":
    run_daemon()

