#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.1.0"
component_id: "OPS-OPS-002"
component_name: "Operational Oversight - Executable Monitor"
layer: "operations"
domain: "autonomous_operations"
type: "monitoring_script"
status: "active"
created: "2025-11-20T00:00:00Z"
updated: "2025-11-20T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["governance-monitor.py", "process_learnings.sh"]
integrates_with: ["OPS-PIP-001", "OPS-SEC-001", "INT-RE-001", "EXE-MON-001"]
api_endpoints: []
data_sources: ["ops/logs/", "learning/failures/", "telemetry/logs/"]
outputs: ["ops/logs/operational_health.log", "ops/logs/dashboard_state.json"]

# === OPERATIONAL METADATA ===
execution_mode: "scheduled"
monitoring_required: true
logging_level: "info"
performance_tier: "realtime"
schedule: "every_30_min"

# === BUSINESS METADATA ===
purpose: "Autonomous operational oversight with real-time anomaly detection and intelligent response"
summary: "Executable implementation of operational-oversight.md providing governance dashboard, memory aggregation, and autonomous anomaly response"
business_value: "Enables hands-off governance operation with intelligent anomaly handling"
success_metrics: ["anomaly_detection_accuracy >= 95%", "response_time < 30s", "false_positive_rate < 5%"]

Operational Oversight - Executable Monitor
Implements the monitoring system described in operational-oversight.md
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

# Add governance-monitor to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from governance_monitor import GovernanceMonitor, GovernanceMetrics
    GOVERNANCE_MONITOR_AVAILABLE = True
except ImportError:
    print("⚠️  Warning: governance-monitor.py not found, governance metrics disabled")
    GOVERNANCE_MONITOR_AVAILABLE = False

@dataclass
class OperationalHealth:
    """Operational health status"""
    timestamp: str
    governance_health: float
    active_alerts: List[str]
    workflow_readiness: str
    reasoning_confidence: float
    memory_insights: int
    autonomous_mode: str
    last_anomaly: Optional[str]

@dataclass
class AnomalyDetection:
    """Detected anomaly"""
    anomaly_type: str
    severity: str  # minor, moderate, critical, security
    detected_at: str
    description: str
    response_action: str
    auto_remediated: bool

class OperationalOversight:
    """
    Autonomous operational oversight system
    Monitors governance health, detects anomalies, triggers responses
    """
    
    def __init__(self, workspace_root: Path = None):
        if workspace_root is None:
            workspace_root = Path.cwd()
        
        self.workspace = Path(workspace_root)
        self.cursor_commands = self.workspace / ".cursor-commands"
        self.logs_dir = self.cursor_commands / "ops" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.logs_dir / "operational_health.log"
        self.dashboard_file = self.logs_dir / "dashboard_state.json"
        
        # Initialize governance monitor if available
        self.governance_monitor = None
        if GOVERNANCE_MONITOR_AVAILABLE:
            try:
                self.governance_monitor = GovernanceMonitor(self.cursor_commands)
            except Exception as e:
                self.log(f"Warning: Could not initialize governance monitor: {e}")
    
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and stdout"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def collect_health_metrics(self) -> OperationalHealth:
        """Collect current operational health metrics"""
        self.log("Collecting operational health metrics...")
        
        # Get governance metrics if available
        governance_health = 100.0
        if self.governance_monitor:
            try:
                metrics = self.governance_monitor.collect_metrics()
                governance_health = metrics.compliance_rate
            except Exception as e:
                self.log(f"Warning: Could not collect governance metrics: {e}", "WARN")
        
        # Check active alerts
        active_alerts = self._check_alerts()
        
        # Check workflow readiness
        workflow_readiness = self._check_workflow_readiness()
        
        # Calculate reasoning confidence (from recent lessons)
        reasoning_confidence = self._calculate_reasoning_confidence()
        
        # Count memory insights
        memory_insights = self._count_memory_insights()
        
        # Get last anomaly
        last_anomaly = self._get_last_anomaly()
        
        health = OperationalHealth(
            timestamp=datetime.now().isoformat(),
            governance_health=governance_health,
            active_alerts=active_alerts,
            workflow_readiness=workflow_readiness,
            reasoning_confidence=reasoning_confidence,
            memory_insights=memory_insights,
            autonomous_mode="nonstop",  # Always nonstop mode
            last_anomaly=last_anomaly
        )
        
        return health
    
    def _check_alerts(self) -> List[str]:
        """Check for active alerts"""
        alerts = []
        
        # Check for repeated mistakes
        repeated_mistakes = self.cursor_commands / "learning" / "failures" / "repeated-mistakes.md"
        if repeated_mistakes.exists():
            with open(repeated_mistakes, 'r') as f:
                content = f.read()
                # Check for HIGH frequency markers
                if "HIGH frequency" in content:
                    alerts.append("High frequency mistakes detected")
        
        # Check for failed LaunchAgents
        try:
            result = subprocess.run(
                ["launchctl", "list"],
                capture_output=True,
                text=True
            )
            if "com.tenx.learning-processor" not in result.stdout:
                alerts.append("Learning processor LaunchAgent not running")
        except:
            pass
        
        return alerts
    
    def _check_workflow_readiness(self) -> str:
        """Check if workflow system is ready"""
        # Check if mandatory files exist
        session_startup = self.cursor_commands / "profiles" / "session-startup-protocol.md"
        reasoning_stack = self.cursor_commands / "startup" / "REASONING_STACK.yaml"
        
        if session_startup.exists() and reasoning_stack.exists():
            return "green"
        elif session_startup.exists() or reasoning_stack.exists():
            return "yellow"
        else:
            return "red"
    
    def _calculate_reasoning_confidence(self) -> float:
        """Calculate reasoning confidence from recent lessons"""
        # Check lessons review log for quality scores
        review_log = self.cursor_commands / "learning" / "failures" / "lessons_review_log.jsonl"
        
        if not review_log.exists():
            return 0.90  # Default high confidence
        
        try:
            with open(review_log, 'r') as f:
                lessons = [json.loads(line) for line in f]
            
            if not lessons:
                return 0.90
            
            # Average quality scores as confidence proxy
            avg_quality = sum(l.get('quality_score', 0.7) for l in lessons) / len(lessons)
            return min(0.95, avg_quality + 0.10)  # Boost and cap at 0.95
        except:
            return 0.90
    
    def _count_memory_insights(self) -> int:
        """Count available memory insights"""
        # Count learning files
        learning_dir = self.cursor_commands / "learning"
        if not learning_dir.exists():
            return 0
        
        md_files = list(learning_dir.rglob("*.md"))
        return len(md_files)
    
    def _get_last_anomaly(self) -> Optional[str]:
        """Get timestamp of last detected anomaly"""
        # Check log file for recent anomalies
        if not self.log_file.exists():
            return None
        
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()
            
            for line in reversed(lines):
                if "ANOMALY" in line or "ALERT" in line:
                    # Extract timestamp
                    if line.startswith('['):
                        timestamp = line.split(']')[0][1:]
                        return timestamp
        except:
            pass
        
        return None
    
    def detect_anomalies(self, health: OperationalHealth) -> List[AnomalyDetection]:
        """Detect anomalies from health metrics"""
        anomalies = []
        
        # Check governance health
        if health.governance_health < 90.0:
            anomalies.append(AnomalyDetection(
                anomaly_type="compliance_violation",
                severity="moderate" if health.governance_health >= 80 else "critical",
                detected_at=datetime.now().isoformat(),
                description=f"Governance health at {health.governance_health:.1f}% (threshold: 90%)",
                response_action="remediation_required",
                auto_remediated=False
            ))
        
        # Check active alerts
        if health.active_alerts:
            for alert in health.active_alerts:
                anomalies.append(AnomalyDetection(
                    anomaly_type="system_alert",
                    severity="moderate",
                    detected_at=datetime.now().isoformat(),
                    description=alert,
                    response_action="investigate",
                    auto_remediated=False
                ))
        
        # Check workflow readiness
        if health.workflow_readiness != "green":
            anomalies.append(AnomalyDetection(
                anomaly_type="workflow_degradation",
                severity="critical" if health.workflow_readiness == "red" else "moderate",
                detected_at=datetime.now().isoformat(),
                description=f"Workflow readiness: {health.workflow_readiness}",
                response_action="check_mandatory_files",
                auto_remediated=False
            ))
        
        # Check reasoning confidence
        if health.reasoning_confidence < 0.85:
            anomalies.append(AnomalyDetection(
                anomaly_type="reasoning_degradation",
                severity="moderate",
                detected_at=datetime.now().isoformat(),
                description=f"Reasoning confidence at {health.reasoning_confidence:.2f} (threshold: 0.85)",
                response_action="review_lessons",
                auto_remediated=False
            ))
        
        return anomalies
    
    def respond_to_anomalies(self, anomalies: List[AnomalyDetection]):
        """Respond to detected anomalies"""
        if not anomalies:
            return
        
        self.log(f"Responding to {len(anomalies)} detected anomalies...")
        
        for anomaly in anomalies:
            self.log(f"ANOMALY: [{anomaly.severity.upper()}] {anomaly.description}", "WARN")
            
            # Auto-remediation based on response action
            if anomaly.response_action == "check_mandatory_files":
                self.log("  → Running verification script...")
                self._run_verification()
            
            elif anomaly.response_action == "review_lessons":
                self.log("  → Triggering learning processor...")
                self._trigger_learning_processor()
            
            elif anomaly.response_action == "remediation_required":
                self.log("  → Manual remediation required - escalating to logs")
            
            else:
                self.log(f"  → Action required: {anomaly.response_action}")
    
    def _run_verification(self):
        """Run verification script"""
        verify_script = self.cursor_commands / "ops" / "scripts" / "verify-startup-files.sh"
        if verify_script.exists():
            try:
                subprocess.run(["bash", str(verify_script)], check=False)
            except:
                self.log("  ✗ Verification script failed", "ERROR")
    
    def _trigger_learning_processor(self):
        """Trigger learning processor manually"""
        try:
            # Find GlobalCommands path
            home = Path.home()
            ssot_path = home / ".cursor-governance"
            dropbox_path = home / "Dropbox/Cursor Governance/GlobalCommands"
            library_path = home / "Library/Application Support/Cursor/GlobalCommands"

            if ssot_path.exists():
                global_commands = ssot_path
            elif dropbox_path.exists():
                global_commands = dropbox_path
            else:
                global_commands = library_path
            
            learning_script = global_commands / "ops" / "scripts" / "process_learnings.sh"
            if learning_script.exists():
                subprocess.run(["bash", str(learning_script)], check=False)
                self.log("  ✓ Learning processor triggered")
        except Exception as e:
            self.log(f"  ✗ Could not trigger learning processor: {e}", "ERROR")
    
    def save_dashboard_state(self, health: OperationalHealth):
        """Save dashboard state to JSON"""
        dashboard_data = asdict(health)
        
        with open(self.dashboard_file, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        self.log(f"Dashboard state saved to {self.dashboard_file}")
    
    def run(self):
        """Execute complete operational oversight cycle"""
        self.log("=" * 60)
        self.log("Starting Operational Oversight Monitor")
        self.log("=" * 60)
        
        # Collect health metrics
        health = self.collect_health_metrics()
        
        # Display health summary
        self.log(f"Governance Health: {health.governance_health:.1f}%")
        self.log(f"Workflow Readiness: {health.workflow_readiness}")
        self.log(f"Reasoning Confidence: {health.reasoning_confidence:.2f}")
        self.log(f"Memory Insights: {health.memory_insights}")
        self.log(f"Active Alerts: {len(health.active_alerts)}")
        
        # Detect anomalies
        anomalies = self.detect_anomalies(health)
        
        if anomalies:
            self.log(f"⚠️  Detected {len(anomalies)} anomalies", "WARN")
            self.respond_to_anomalies(anomalies)
        else:
            self.log("✅ No anomalies detected")
        
        # Save dashboard state
        self.save_dashboard_state(health)
        
        self.log("=" * 60)
        self.log("Operational Oversight Monitor Complete")
        self.log("=" * 60)

if __name__ == '__main__':
    print("🧠 Starting Operational Oversight Monitor...")
    monitor = OperationalOversight()
    monitor.run()

