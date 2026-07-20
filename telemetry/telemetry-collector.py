#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "TEL-COL-001"
component_name: "Telemetry Collector"
layer: "telemetry"
domain: "metrics_collection"
type: "collector_system"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

dependencies: ["EXE-MON-001", "EXE-API-001"]
integrates_with: ["OPS-OPS-001", "INT-ML-001", "ENV-MGR-001"]

purpose: "Comprehensive telemetry collection system for L9 Governance governance monitoring"
summary: "Collects, aggregates, and stores metrics from all L9 Governance components for analysis and monitoring"
business_value: "Enables data-driven governance optimization and proactive issue detection"
success_metrics: ["collection_accuracy >= 99%", "data_retention >= 30_days", "query_performance < 100ms"]

Telemetry Collector v6.0
Comprehensive metrics collection and aggregation for L9 Governance
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import threading
import queue
import psutil
import os

class TelemetryCollector:
    """Comprehensive telemetry collection system for L9 Governance"""
    
    def __init__(self, l9_governance_root: Path = None):
        if l9_governance_root is None:
            l9_governance_root = Path(__file__).parent.parent
        
        self.l9_governance_root = Path(l9_governance_root)
        self.telemetry_dir = self.l9_governance_root / "telemetry"
        self.logs_dir = self.telemetry_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Database for metrics storage
        self.db_path = self.logs_dir / "telemetry.db"
        self.init_database()
        
        # Collection queue for async processing
        self.metrics_queue = queue.Queue()
        self.collection_active = False
        self.collection_thread = None
        
    def init_database(self):
        """Initialize telemetry database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                component_id TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                metric_unit TEXT,
                tags TEXT,
                metadata TEXT
            )
        ''')
        
        # Events table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                component_id TEXT NOT NULL,
                event_data TEXT,
                severity TEXT DEFAULT 'info'
            )
        ''')
        
        # Performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                component_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                duration_ms REAL,
                success BOOLEAN,
                error_message TEXT
            )
        ''')
        
        # System metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_usage_percent REAL,
                network_io TEXT,
                process_count INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def start_collection(self):
        """Start continuous telemetry collection"""
        if self.collection_active:
            return
        
        print("🚀 Starting L9 Governance telemetry collection...")
        self.collection_active = True
        
        # Start collection thread
        self.collection_thread = threading.Thread(target=self._collection_worker, daemon=True)
        self.collection_thread.start()
        
        # Start system metrics collection
        system_thread = threading.Thread(target=self._system_metrics_worker, daemon=True)
        system_thread.start()
        
        print("✅ Telemetry collection started")
    
    def stop_collection(self):
        """Stop telemetry collection"""
        print("🛑 Stopping telemetry collection...")
        self.collection_active = False
        
        if self.collection_thread:
            self.collection_thread.join(timeout=5)
        
        print("✅ Telemetry collection stopped")
    
    def collect_metric(self, component_id: str, metric_name: str, value: float, 
                      unit: str = None, tags: Dict[str, str] = None, 
                      metadata: Dict[str, Any] = None):
        """Collect a metric from a L9 Governance component"""
        metric_data = {
            'timestamp': datetime.now().isoformat(),
            'component_id': component_id,
            'metric_name': metric_name,
            'value': value,
            'unit': unit or '',
            'tags': json.dumps(tags or {}),
            'metadata': json.dumps(metadata or {})
        }
        
        # Add to queue for async processing
        self.metrics_queue.put(('metric', metric_data))
    
    def collect_event(self, component_id: str, event_type: str, event_data: Dict[str, Any], 
                     severity: str = 'info'):
        """Collect an event from a L9 Governance component"""
        event_data_obj = {
            'timestamp': datetime.now().isoformat(),
            'component_id': component_id,
            'event_type': event_type,
            'event_data': json.dumps(event_data),
            'severity': severity
        }
        
        self.metrics_queue.put(('event', event_data_obj))
    
    def collect_performance(self, component_id: str, operation: str, duration_ms: float,
                          success: bool, error_message: str = None):
        """Collect performance metrics from a L9 Governance component"""
        perf_data = {
            'timestamp': datetime.now().isoformat(),
            'component_id': component_id,
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success,
            'error_message': error_message or ''
        }
        
        self.metrics_queue.put(('performance', perf_data))
    
    def get_metrics(self, component_id: str = None, metric_name: str = None,
                   start_time: datetime = None, end_time: datetime = None,
                   limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve metrics from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM metrics WHERE 1=1"
        params = []
        
        if component_id:
            query += " AND component_id = ?"
            params.append(component_id)
        
        if metric_name:
            query += " AND metric_name = ?"
            params.append(metric_name)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dictionaries
        columns = [description[0] for description in cursor.description]
        metrics = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        return metrics
    
    def get_events(self, component_id: str = None, event_type: str = None,
                  severity: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve events from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if component_id:
            query += " AND component_id = ?"
            params.append(component_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        events = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        return events
    
    def get_performance_summary(self, component_id: str = None, 
                              hours: int = 24) -> Dict[str, Any]:
        """Get performance summary for the last N hours"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = datetime.now() - timedelta(hours=hours)
        
        query = """
            SELECT 
                component_id,
                operation,
                COUNT(*) as operation_count,
                AVG(duration_ms) as avg_duration,
                MIN(duration_ms) as min_duration,
                MAX(duration_ms) as max_duration,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
            FROM performance 
            WHERE timestamp >= ?
        """
        
        params = [start_time.isoformat()]
        
        if component_id:
            query += " AND component_id = ?"
            params.append(component_id)
        
        query += " GROUP BY component_id, operation"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        columns = [description[0] for description in cursor.description]
        performance_data = [dict(zip(columns, row)) for row in rows]
        
        conn.close()
        
        # Calculate summary statistics
        summary = {
            'period_hours': hours,
            'total_operations': sum(p['operation_count'] for p in performance_data),
            'avg_duration_ms': sum(p['avg_duration'] * p['operation_count'] for p in performance_data) / 
                              max(sum(p['operation_count'] for p in performance_data), 1),
            'success_rate': sum(p['success_count'] for p in performance_data) / 
                           max(sum(p['operation_count'] for p in performance_data), 1),
            'by_component': {}
        }
        
        # Group by component
        for perf in performance_data:
            comp_id = perf['component_id']
            if comp_id not in summary['by_component']:
                summary['by_component'][comp_id] = []
            summary['by_component'][comp_id].append(perf)
        
        return summary
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get latest system metrics
        cursor.execute("""
            SELECT * FROM system_metrics 
            ORDER BY timestamp DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            latest_metrics = dict(zip(columns, row))
        else:
            latest_metrics = {}
        
        # Get recent error count
        cursor.execute("""
            SELECT COUNT(*) FROM events 
            WHERE severity IN ('error', 'critical') 
            AND timestamp >= ?
        """, [(datetime.now() - timedelta(hours=1)).isoformat()])
        
        error_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': latest_metrics,
            'recent_errors': error_count,
            'database_size_mb': self._get_database_size(),
            'collection_active': self.collection_active
        }
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up telemetry data older than specified days"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clean up old metrics
        cursor.execute("DELETE FROM metrics WHERE timestamp < ?", [cutoff_time.isoformat()])
        metrics_deleted = cursor.rowcount
        
        # Clean up old events
        cursor.execute("DELETE FROM events WHERE timestamp < ?", [cutoff_time.isoformat()])
        events_deleted = cursor.rowcount
        
        # Clean up old performance data
        cursor.execute("DELETE FROM performance WHERE timestamp < ?", [cutoff_time.isoformat()])
        perf_deleted = cursor.rowcount
        
        # Clean up old system metrics
        cursor.execute("DELETE FROM system_metrics WHERE timestamp < ?", [cutoff_time.isoformat()])
        system_deleted = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        print(f"🧹 Cleaned up telemetry data older than {days} days:")
        print(f"   Metrics: {metrics_deleted}")
        print(f"   Events: {events_deleted}")
        print(f"   Performance: {perf_deleted}")
        print(f"   System: {system_deleted}")
    
    def _collection_worker(self):
        """Background worker for processing telemetry data"""
        while self.collection_active:
            try:
                # Process queued items
                while not self.metrics_queue.empty():
                    item_type, data = self.metrics_queue.get(timeout=1)
                    self._store_data(item_type, data)
                
                time.sleep(1)  # Brief pause between processing cycles
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in telemetry collection worker: {e}")
    
    def _system_metrics_worker(self):
        """Background worker for collecting system metrics"""
        while self.collection_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                system_data = {
                    'timestamp': datetime.now().isoformat(),
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'disk_usage_percent': (disk.used / disk.total) * 100,
                    'network_io': json.dumps(dict(psutil.net_io_counters()._asdict())),
                    'process_count': len(psutil.pids())
                }
                
                self.metrics_queue.put(('system', system_data))
                
                # Sleep for 60 seconds before next collection
                time.sleep(60)
                
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                time.sleep(60)
    
    def _store_data(self, item_type: str, data: Dict[str, Any]):
        """Store telemetry data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if item_type == 'metric':
                cursor.execute('''
                    INSERT INTO metrics 
                    (timestamp, component_id, metric_name, metric_value, metric_unit, tags, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['timestamp'], data['component_id'], data['metric_name'],
                    data['value'], data['unit'], data['tags'], data['metadata']
                ))
            
            elif item_type == 'event':
                cursor.execute('''
                    INSERT INTO events 
                    (timestamp, event_type, component_id, event_data, severity)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    data['timestamp'], data['event_type'], data['component_id'],
                    data['event_data'], data['severity']
                ))
            
            elif item_type == 'performance':
                cursor.execute('''
                    INSERT INTO performance 
                    (timestamp, component_id, operation, duration_ms, success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data['timestamp'], data['component_id'], data['operation'],
                    data['duration_ms'], data['success'], data['error_message']
                ))
            
            elif item_type == 'system':
                cursor.execute('''
                    INSERT INTO system_metrics 
                    (timestamp, cpu_percent, memory_percent, disk_usage_percent, network_io, process_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data['timestamp'], data['cpu_percent'], data['memory_percent'],
                    data['disk_usage_percent'], data['network_io'], data['process_count']
                ))
            
            conn.commit()
            
        except Exception as e:
            print(f"Error storing telemetry data: {e}")
        finally:
            conn.close()
    
    def _get_database_size(self) -> float:
        """Get database size in MB"""
        try:
            size_bytes = os.path.getsize(self.db_path)
            return size_bytes / (1024 * 1024)  # Convert to MB
        except:
            return 0.0

def main():
    """Main telemetry collector CLI"""
    import sys
    
    collector = TelemetryCollector()
    
    if len(sys.argv) < 2:
        print("Usage: python telemetry-collector.py [start|stop|status|cleanup]")
        return 1
    
    command = sys.argv[1]
    
    if command == "start":
        collector.start_collection()
        print("Telemetry collection started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            collector.stop_collection()
    
    elif command == "stop":
        collector.stop_collection()
    
    elif command == "status":
        health = collector.get_system_health()
        print(f"Collection Active: {health['collection_active']}")
        print(f"Database Size: {health['database_size_mb']:.2f} MB")
        print(f"Recent Errors: {health['recent_errors']}")
    
    elif command == "cleanup":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        collector.cleanup_old_data(days)
    
    else:
        print(f"Unknown command: {command}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
