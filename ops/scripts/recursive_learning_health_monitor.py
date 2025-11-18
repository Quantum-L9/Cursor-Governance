#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "OPS-HM-001"
component_name: "Recursive Learning Health Monitor"
layer: "operations"
domain: "monitoring"
type: "monitor"
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
dependencies: ["python3", "subprocess", "json", "pathlib"]
integrates_with: ["OPS-PEC-001", "OPS-PET-001", "OPS-CLI-001", "OPS-MCS-001"]
data_sources: ["launchctl", "log_files"]
outputs: ["health_status", "auto_recovery_log"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "background"

# === BUSINESS METADATA ===
purpose: "Monitor health of all recursive learning components and auto-recover on failure"
summary: "Health checker that verifies component status and automatically restarts failed components"
business_value: "Ensures recursive learning system reliability and availability"
"""

import subprocess
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Component LaunchAgent names
COMPONENTS = {
    'pre-execution-checker': 'com.cursor.pre-execution-checker',
    'prevention-effectiveness-tracker': 'com.cursor.prevention-effectiveness-tracker',
    'closed-loop-improvement': 'com.cursor.closed-loop-improvement',
    'memory-compounding': 'com.cursor.memory-compounding',
    'recursive-learning-orchestrator': 'com.cursor.recursive-learning-orchestrator',
    'formal-lesson-extractor': 'com.cursor.formal-lesson-extractor',
    'weekly-meta-insights': 'com.cursor.weekly-meta-insights'
}

# Get LOG_DIR from GlobalCommands path (use $HOME)
def get_log_dir():
    """Get log directory using $HOME-based path"""
    global_commands = get_global_commands_path()
    return global_commands / "ops/logs"

# RECOVERY_LOG will be resolved dynamically using get_global_commands_path()
RECOVERY_LOG = None  # Will be set in methods that use it


class HealthMonitor:
    """Health monitor for recursive learning components"""
    
    def check_launchagent_status(self, agent_name: str) -> Dict[str, Any]:
        """Check if LaunchAgent is running"""
        try:
            result = subprocess.run(
                ['launchctl', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            is_running = agent_name in result.stdout
            
            return {
                'name': agent_name,
                'running': is_running,
                'status': 'healthy' if is_running else 'stopped'
            }
        except Exception as e:
            return {
                'name': agent_name,
                'running': False,
                'status': 'error',
                'error': str(e)
            }
    
    def check_log_freshness(self, log_file: Path, max_age_hours: int = 2) -> Dict[str, Any]:
        """Check if log file is fresh (recently updated)"""
        if not log_file.exists():
            return {
                'file': str(log_file),
                'exists': False,
                'fresh': False,
                'status': 'missing'
            }
        
        mtime = log_file.stat().st_mtime
        age_hours = (datetime.now().timestamp() - mtime) / 3600
        
        return {
            'file': str(log_file),
            'exists': True,
            'fresh': age_hours < max_age_hours,
            'age_hours': age_hours,
            'status': 'fresh' if age_hours < max_age_hours else 'stale'
        }
    
    def check_all_components(self) -> Dict[str, Any]:
        """Check health of all components"""
        # Resolve LOG_DIR dynamically
        log_dir = get_global_commands_path() / "ops/logs"
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'components': {},
            'overall_health': 'unknown',
            'healthy_count': 0,
            'unhealthy_count': 0
        }
        
        for component_name, agent_name in COMPONENTS.items():
            # Check LaunchAgent status
            agent_status = self.check_launchagent_status(agent_name)
            
            # Check log freshness (if applicable)
            log_file = log_dir / f"{component_name.replace('-', '_')}.log"
            log_status = self.check_log_freshness(log_file)
            
            component_health = {
                'agent_status': agent_status,
                'log_status': log_status,
                'overall': 'healthy' if agent_status['running'] and log_status['fresh'] else 'unhealthy'
            }
            
            health_status['components'][component_name] = component_health
            
            if component_health['overall'] == 'healthy':
                health_status['healthy_count'] += 1
            else:
                health_status['unhealthy_count'] += 1
        
        # Determine overall health
        total = len(COMPONENTS)
        healthy_ratio = health_status['healthy_count'] / total if total > 0 else 0
        
        if healthy_ratio >= 0.9:
            health_status['overall_health'] = 'healthy'
        elif healthy_ratio >= 0.7:
            health_status['overall_health'] = 'degraded'
        else:
            health_status['overall_health'] = 'unhealthy'
        
        return health_status
    
    def auto_recover_component(self, component_name: str, agent_name: str) -> bool:
        """Attempt to auto-recover a failed component"""
        plist_file = Path.home() / f"Library/LaunchAgents/{agent_name}.plist"
        
        if not plist_file.exists():
            self._log_recovery(f"❌ Cannot recover {component_name}: plist file not found")
            return False
        
        try:
            # Unload and reload
            subprocess.run(['launchctl', 'unload', str(plist_file)], 
                         capture_output=True, timeout=5)
            time.sleep(1)
            subprocess.run(['launchctl', 'load', str(plist_file)], 
                         capture_output=True, timeout=5)
            
            # Verify recovery
            time.sleep(2)
            status = self.check_launchagent_status(agent_name)
            
            if status['running']:
                self._log_recovery(f"✅ Recovered {component_name}")
                return True
            else:
                self._log_recovery(f"❌ Recovery failed for {component_name}")
                return False
        except Exception as e:
            self._log_recovery(f"❌ Recovery error for {component_name}: {e}")
            return False
    
    def _log_recovery(self, message: str):
        """Log recovery attempt"""
        # Resolve recovery log path dynamically
        recovery_log = get_global_commands_path() / "ops/logs/health_monitor_recovery.log"
        recovery_log.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(recovery_log, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def run_health_check(self):
        """Run health check and auto-recover if needed"""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running health check...")
        
        health_status = self.check_all_components()
        
        print(f"Overall Health: {health_status['overall_health']}")
        print(f"Healthy: {health_status['healthy_count']}/{len(COMPONENTS)}")
        
        # Auto-recover unhealthy components
        recovered = 0
        for component_name, component_data in health_status['components'].items():
            if component_data['overall'] == 'unhealthy':
                agent_name = COMPONENTS[component_name]
                print(f"⚠️  {component_name} is unhealthy, attempting recovery...")
                if self.auto_recover_component(component_name, agent_name):
                    recovered += 1
        
        if recovered > 0:
            print(f"✅ Recovered {recovered} component(s)")
        else:
            print("✅ All components healthy")


def main():
    """Main execution"""
    import time
    
    monitor = HealthMonitor()
    monitor.run_health_check()


if __name__ == "__main__":
    main()

