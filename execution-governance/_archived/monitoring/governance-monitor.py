#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "EXE-MON-001"
component_name: "Governance Monitor"
layer: "execution"
domain: "monitoring"
type: "monitoring_system"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

dependencies: ["EXE-VAL-001", "TEL-LOG-001"]
integrates_with: ["EXE-API-001", "OPS-OPS-001", "INT-ML-001"]

suite_3_origin: "52_Governance_Monitor_v3.0.py"
migration_notes: "Enhanced with L9 Governance integration, autonomous operation, and expanded metrics"

Governance Monitor v6.0
Observability and monitoring tools for L9 Governance governance system
"""

import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import psutil


@dataclass
class GovernanceMetrics:
    """L9 Governance governance system metrics"""

    timestamp: str
    total_files: int
    compliant_files: int
    violation_count: int
    compliance_rate: float
    validation_time: float
    memory_usage: float
    cpu_usage: float
    active_violations: list[str]
    suite_version: str = "6.0.0"


class GovernanceMonitor:
    """Monitor L9 Governance governance system performance and compliance"""

    def __init__(self, l9_governance_root: Path = None):
        if l9_governance_root is None:
            l9_governance_root = Path(__file__).parent.parent.parent

        self.l9_governance_root = Path(l9_governance_root)
        self.governance_path = self.l9_governance_root
        self.db_path = self.l9_governance_root / "telemetry" / "logs" / "governance-metrics.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for metrics storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS governance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_files INTEGER,
                compliant_files INTEGER,
                violation_count INTEGER,
                compliance_rate REAL,
                validation_time REAL,
                memory_usage REAL,
                cpu_usage REAL,
                active_violations TEXT,
                suite_version TEXT DEFAULT '6.0.0'
            )
        """)

        # L9 Governance enhancement: Add performance tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                component_id TEXT,
                operation TEXT,
                duration_ms REAL,
                success BOOLEAN,
                error_message TEXT
            )
        """)

        conn.commit()
        conn.close()

    def collect_metrics(self) -> GovernanceMetrics:
        """Collect current governance metrics"""
        start_time = time.time()

        # Scan L9 Governance structure for governance files
        total_files = 0
        compliant_files = 0
        violations = []

        # Check all layers for compliance
        for layer in ["intelligence", "foundation", "execution", "operations", "environment"]:
            layer_path = self.l9_governance_root / layer
            if layer_path.exists():
                for file_path in layer_path.rglob("*.md"):
                    total_files += 1
                    if self._check_file_compliance(file_path):
                        compliant_files += 1
                    else:
                        violations.append(str(file_path.relative_to(self.l9_governance_root)))

        validation_time = time.time() - start_time
        compliance_rate = (compliant_files / total_files * 100) if total_files > 0 else 100.0

        # System resource usage
        memory_usage = psutil.virtual_memory().percent
        cpu_usage = psutil.cpu_percent(interval=1)

        metrics = GovernanceMetrics(
            timestamp=datetime.now().isoformat(),
            total_files=total_files,
            compliant_files=compliant_files,
            violation_count=len(violations),
            compliance_rate=compliance_rate,
            validation_time=validation_time,
            memory_usage=memory_usage,
            cpu_usage=cpu_usage,
            active_violations=violations[:10],  # Limit to first 10
        )

        self._store_metrics(metrics)
        return metrics

    def _check_file_compliance(self, file_path: Path) -> bool:
        """Check if file has L9 Governance canonical header"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Check for L9 Governance canonical header
            return "# === L9 GOVERNANCE CANONICAL HEADER ===" in content
        except:
            return False

    def _store_metrics(self, metrics: GovernanceMetrics):
        """Store metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO governance_metrics 
            (timestamp, total_files, compliant_files, violation_count, 
             compliance_rate, validation_time, memory_usage, cpu_usage, 
             active_violations, suite_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                metrics.timestamp,
                metrics.total_files,
                metrics.compliant_files,
                metrics.violation_count,
                metrics.compliance_rate,
                metrics.validation_time,
                metrics.memory_usage,
                metrics.cpu_usage,
                json.dumps(metrics.active_violations),
                metrics.suite_version,
            ),
        )

        conn.commit()
        conn.close()

    def get_detailed_metrics(self) -> dict:
        """Get detailed metrics for L9 Governance dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent metrics
        cursor.execute("""
            SELECT * FROM governance_metrics 
            ORDER BY timestamp DESC 
            LIMIT 24
        """)

        recent_metrics = cursor.fetchall()

        # Get performance trends
        cursor.execute("""
            SELECT component_id, AVG(duration_ms) as avg_duration,
                   COUNT(*) as operation_count,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM performance_metrics 
            WHERE timestamp > datetime('now', '-1 day')
            GROUP BY component_id
        """)

        performance_data = cursor.fetchall()
        conn.close()

        return {
            "recent_metrics": [
                dict(zip([col[0] for col in cursor.description], row)) for row in recent_metrics
            ],
            "performance_summary": [
                dict(zip(["component_id", "avg_duration", "operation_count", "success_count"], row))
                for row in performance_data
            ],
            "suite_version": "6.0.0",
            "monitoring_enhanced": True,
        }

    def log_performance(
        self,
        component_id: str,
        operation: str,
        duration_ms: float,
        success: bool,
        error_message: str = None,
    ):
        """Log performance metrics for L9 Governance components"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO performance_metrics 
            (timestamp, component_id, operation, duration_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                datetime.now().isoformat(),
                component_id,
                operation,
                duration_ms,
                success,
                error_message,
            ),
        )

        conn.commit()
        conn.close()

    def get_compliance_report(self) -> dict:
        """Generate comprehensive compliance report"""
        metrics = self.collect_metrics()

        # Check rule registry health
        rule_registry_path = self.l9_governance_root / "foundation" / "logic" / "rule-registry.json"
        rule_registry_healthy = rule_registry_path.exists()

        # Check API health
        api_path = self.l9_governance_root / "execution" / "api" / "governance-api.py"
        api_healthy = api_path.exists()

        return {
            "compliance_summary": {
                "overall_rate": metrics.compliance_rate,
                "total_files": metrics.total_files,
                "compliant_files": metrics.compliant_files,
                "violations": metrics.violation_count,
            },
            "system_health": {
                "rule_registry": "healthy" if rule_registry_healthy else "unhealthy",
                "api_server": "healthy" if api_healthy else "unhealthy",
                "memory_usage": f"{metrics.memory_usage:.1f}%",
                "cpu_usage": f"{metrics.cpu_usage:.1f}%",
            },
            "violations": metrics.active_violations,
            "timestamp": metrics.timestamp,
            "suite_version": "6.0.0",
        }


if __name__ == "__main__":
    print("🔍 Starting L9 Governance Governance Monitor...")
    monitor = GovernanceMonitor()

    print("📊 Collecting initial metrics...")
    metrics = monitor.collect_metrics()

    print(f"✅ Compliance Rate: {metrics.compliance_rate:.1f}%")
    print(f"📁 Total Files: {metrics.total_files}")
    print(f"✅ Compliant Files: {metrics.compliant_files}")
    print(f"⚠️  Violations: {metrics.violation_count}")

    if metrics.active_violations:
        print("🚨 Active Violations:")
        for violation in metrics.active_violations[:5]:
            print(f"   - {violation}")
