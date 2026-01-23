#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-RLS-001"
component_name: "Recursive Learning System Orchestrator"
layer: "operations"
domain: "learning"
type: "orchestrator"
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
integrates_with: ["OPS-PEC-001", "OPS-PET-001", "OPS-CLI-001", "OPS-MCS-001"]
data_sources: ["ops/logs/recursive_learning_status.json"]
outputs: ["ops/logs/recursive_learning_status.json"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Coordinate all recursive learning components"
summary: "Orchestrates pre-execution checker, effectiveness tracker, closed-loop improvement, and memory compounding"
business_value: "Ensures all recursive learning components work together seamlessly"
success_metrics: ["orchestration_success_rate >= 95%", "component_health >= 90%", "coordination_latency < 5s"]

# === TAGS & CLASSIFICATION ===
tags: ["learning", "orchestration", "recursive", "coordination"]
keywords: ["orchestrator", "recursive", "learning", "coordination", "system"]
related_components: ["OPS-PEC-001", "OPS-PET-001", "OPS-CLI-001", "OPS-MCS-001"]
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

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
[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]   Script: recursive_learning_orchestrator.py
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
STATUS_FILE = GLOBAL_COMMANDS / "ops/logs/recursive_learning_status.json"
SCRIPT_DIR = GLOBAL_COMMANDS / "ops/scripts"


class RecursiveLearningOrchestrator:
    """Orchestrates all recursive learning components"""
    
    def __init__(self):
        self.components = {
            'pre_execution_checker': {
                'script': 'pre_execution_checker.py',
                'required': True,
                'status': 'unknown'
            },
            'prevention_effectiveness_tracker': {
                'script': 'prevention_effectiveness_tracker.py',
                'required': True,
                'status': 'unknown'
            },
            'closed_loop_improvement': {
                'script': 'closed_loop_improvement.py',
                'required': True,
                'status': 'unknown'
            },
            'memory_compounding': {
                'script': 'memory_compounding.py',
                'required': True,
                'status': 'unknown'
            }
        }
        self.status = self._load_status()
    
    def _load_status(self) -> Dict[str, Any]:
        """Load system status"""
        if STATUS_FILE.exists():
            try:
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        return {
            'last_run': None,
            'component_health': {},
            'overall_health': 'unknown',
            'success_rate': 0.0
        }
    
    def _save_status(self):
        """Save system status"""
        STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.status['last_run'] = datetime.now().isoformat()
        with open(STATUS_FILE, 'w') as f:
            json.dump(self.status, f, indent=2)
    
    def check_component_health(self, component_name: str) -> Dict[str, Any]:
        """Check health of a component"""
        component = self.components.get(component_name, {})
        script_path = SCRIPT_DIR / component.get('script', '')
        
        health = {
            'component': component_name,
            'script_exists': script_path.exists(),
            'last_check': datetime.now().isoformat(),
            'status': 'healthy' if script_path.exists() else 'missing'
        }
        
        # Check if script is executable
        if script_path.exists():
            health['executable'] = os.access(script_path, os.X_OK)
            health['status'] = 'healthy' if health['executable'] else 'not_executable'
        
        return health
    
    def check_all_components(self) -> Dict[str, Any]:
        """Check health of all components"""
        component_health = {}
        
        for component_name in self.components.keys():
            health = self.check_component_health(component_name)
            component_health[component_name] = health
        
        # Calculate overall health
        healthy_count = len([h for h in component_health.values() if h['status'] == 'healthy'])
        total_count = len(component_health)
        overall_health = 'healthy' if healthy_count == total_count else 'degraded' if healthy_count > 0 else 'unhealthy'
        
        self.status['component_health'] = component_health
        self.status['overall_health'] = overall_health
        self.status['health_percentage'] = (healthy_count / total_count * 100) if total_count > 0 else 0.0
        
        return component_health
    
    def coordinate_components(self):
        """Coordinate execution of all components"""
        print("🎯 Recursive Learning System Orchestrator v1.0.0\n")
        print("=" * 60)
        
        # Step 1: Refresh pre-execution checker cache
        print("\n1️⃣  Refreshing Pre-Execution Checker Cache...")
        try:
            from pre_execution_checker import PreExecutionChecker
            checker = PreExecutionChecker()
            checker.refresh_cache()
            print("   ✅ Cache refreshed")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
        
        # Step 2: Calculate effectiveness metrics
        print("\n2️⃣  Calculating Prevention Effectiveness Metrics...")
        try:
            result = subprocess.run(
                ['python3', str(SCRIPT_DIR / 'prevention_effectiveness_tracker.py'), '--calculate'],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print("   ✅ Metrics calculated")
            else:
                print(f"   ⚠️  Error: {result.stderr[:100]}")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
        
        # Step 3: Run closed-loop improvement cycle
        print("\n3️⃣  Running Closed-Loop Improvement Cycle...")
        try:
            result = subprocess.run(
                ['python3', str(SCRIPT_DIR / 'closed_loop_improvement.py'), '--cycle'],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                print("   ✅ Improvement cycle complete")
            else:
                print(f"   ⚠️  Error: {result.stderr[:100]}")
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
        
        # Step 4: Check component health
        # Note: Memory compounding is handled by learning processing pipeline (nightly)
        print("\n4️⃣  Checking Component Health...")
        component_health = self.check_all_components()
        
        healthy_count = len([h for h in component_health.values() if h['status'] == 'healthy'])
        print(f"   ✅ {healthy_count}/{len(component_health)} components healthy")
        
        # Save status
        self._save_status()
        
        print("\n" + "=" * 60)
        print("✅ Orchestration Complete")
        print(f"   Overall Health: {self.status['overall_health']}")
        print(f"   Health Percentage: {self.status['health_percentage']:.1f}%")
        print("=" * 60)


def main():
    """Main execution"""
    orchestrator = RecursiveLearningOrchestrator()
    orchestrator.coordinate_components()


if __name__ == "__main__":
    main()

