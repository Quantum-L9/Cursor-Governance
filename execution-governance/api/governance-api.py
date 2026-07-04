#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "EXE-API-001"
component_name: "Governance API Server"
layer: "execution"
domain: "api_services"
type: "rest_api"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

dependencies: ["FND-LG-001", "FND-LG-002", "EXE-VAL-001", "EXE-MON-001"]
integrates_with: ["INT-RE-001", "OPS-OPS-001", "TEL-LOG-001"]
api_endpoints: ["/governance/status", "/governance/validate", "/governance/rules", "/governance/metrics"]

suite_3_origin: "56_Governance_API_v3.0.py"
migration_notes: "Enhanced with Suite 6 integration, formal logic endpoints, and canonical headers"

Governance API Server v6.0
REST API for governance dashboard and external integrations with Suite 6 enhancements
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
import sys
from datetime import datetime
import sqlite3
from pathlib import Path

# Suite 6 imports - updated paths with importlib for hyphenated filenames
import importlib.util

l9_governance_root = Path(__file__).parent.parent.parent

# Import governance-validator.py (hyphenated filename)
validator_path = l9_governance_root / 'execution' / 'validation' / 'governance-validator.py'
spec = importlib.util.spec_from_file_location('governance_validator', validator_path)
governance_validator_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(governance_validator_module)
GovernanceValidator = governance_validator_module.GovernanceValidator

# Import governance-monitor.py (hyphenated filename)
monitor_path = l9_governance_root / 'execution' / 'monitoring' / 'governance-monitor.py'
spec = importlib.util.spec_from_file_location('governance_monitor', monitor_path)
governance_monitor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(governance_monitor_module)
GovernanceMonitor = governance_monitor_module.GovernanceMonitor

# Try to import chat learning extractor (optional)
try:
    extractor_path = l9_governance_root / 'intelligence' / 'learning' / 'chat-learning-extractor.py'
    if extractor_path.exists():
        spec = importlib.util.spec_from_file_location('chat_learning_extractor', extractor_path)
        chat_extractor_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(chat_extractor_module)
        ChatLearningExtractor = chat_extractor_module.ChatLearningExtractor
    else:
        ChatLearningExtractor = None
except Exception:
    ChatLearningExtractor = None

app = Flask(__name__)
CORS(app)  # Enable CORS for dashboard access

# Initialize governance components with Suite 6 paths
validator = GovernanceValidator(l9_governance_root)
monitor = GovernanceMonitor(l9_governance_root)
chat_extractor = ChatLearningExtractor(l9_governance_root) if ChatLearningExtractor else None

@app.route('/governance/status', methods=['GET'])
def get_status():
    """Get current governance system status"""
    try:
        metrics = monitor.collect_metrics()
        return jsonify({
            'status': 'online',
            'suite': 'Cursor Governance Suite 6 (Unified)',
            'version': '6.0.0',
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'compliance_rate': metrics.compliance_rate,
                'total_files': metrics.total_files,
                'compliant_files': metrics.compliant_files,
                'violation_count': metrics.violation_count,
                'validation_time': metrics.validation_time,
                'memory_usage': metrics.memory_usage,
                'cpu_usage': metrics.cpu_usage
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/governance/validate', methods=['POST'])
def validate_governance():
    """Run governance validation"""
    try:
        is_compliant = validator.enforce_compliance()
        report = validator.get_compliance_report()
        
        return jsonify({
            'compliant': is_compliant,
            'report': report,
            'timestamp': datetime.now().isoformat(),
            'suite_version': '6.0.0'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/governance/rules', methods=['GET'])
def get_rules():
    """Get current governance rules from rule registry"""
    try:
        rules_path = l9_governance_root / 'foundation' / 'logic' / 'rule-registry.json'
        with open(rules_path, 'r') as f:
            rules_data = json.load(f)
        
        return jsonify({
            'rules': rules_data,
            'timestamp': datetime.now().isoformat(),
            'source': 'Suite 6 Rule Registry'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/governance/rules', methods=['POST'])
def add_rule():
    """Add new governance rule (Suite 6 enhancement)"""
    try:
        rule_data = request.get_json()
        
        # Validate rule format
        required_fields = ['id', 'description', 'fol', 'type', 'priority']
        if not all(field in rule_data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Load current rules
        rules_path = l9_governance_root / 'foundation' / 'logic' / 'rule-registry.json'
        with open(rules_path, 'r') as f:
            rules_registry = json.load(f)
        
        # Add new rule with Suite 6 metadata
        new_rule = {
            **rule_data,
            'enforced_by': 'Universal Governance Kernel v6.0',
            'created': datetime.now().isoformat(),
            'last_validated': datetime.now().isoformat()
        }
        
        rules_registry['rules'].append(new_rule)
        
        # Save updated registry
        with open(rules_path, 'w') as f:
            json.dump(rules_registry, f, indent=2)
        
        return jsonify({
            'success': True,
            'rule_id': rule_data['id'],
            'message': 'Rule added successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/governance/metrics', methods=['GET'])
def get_metrics():
    """Get detailed governance metrics"""
    try:
        metrics = monitor.get_detailed_metrics()
        return jsonify({
            'metrics': metrics,
            'timestamp': datetime.now().isoformat(),
            'suite': 'Suite 6 Enhanced Metrics'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/governance/health', methods=['GET'])
def health_check():
    """Suite 6 health check endpoint"""
    try:
        health_status = {
            'api': 'healthy',
            'validator': 'healthy' if validator else 'unhealthy',
            'monitor': 'healthy' if monitor else 'unhealthy',
            'rule_registry': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'suite_version': '6.0.0'
        }
        
        # Check rule registry accessibility
        try:
            rules_path = l9_governance_root / 'foundation' / 'logic' / 'rule-registry.json'
            with open(rules_path, 'r') as f:
                json.load(f)
        except:
            health_status['rule_registry'] = 'unhealthy'
        
        overall_health = all(status == 'healthy' for status in health_status.values() if isinstance(status, str))
        health_status['overall'] = 'healthy' if overall_health else 'degraded'
        
        return jsonify(health_status), 200 if overall_health else 503
    except Exception as e:
        return jsonify({'error': str(e), 'overall': 'unhealthy'}), 503

@app.route('/governance/learning/extract', methods=['POST'])
def extract_learning():
    """Extract learning patterns from conversation text"""
    try:
        data = request.get_json()
        if not data or 'conversation' not in data:
            return jsonify({'error': 'conversation text required'}), 400
        
        conversation_text = data['conversation']
        conversation_id = data.get('conversation_id', f"api_{int(datetime.now().timestamp())}")
        
        # Extract patterns
        if not chat_extractor:
            return jsonify({'error': 'Chat learning extractor not available'}), 503
        patterns = chat_extractor.extract_from_conversation(conversation_text, conversation_id)
        
        # Update meta-learning log
        if patterns:
            success = chat_extractor.update_meta_learning_log(patterns)
            
            return jsonify({
                'status': 'success',
                'patterns_extracted': len(patterns),
                'meta_log_updated': success,
                'patterns': [
                    {
                        'id': p.pattern_id,
                        'summary': p.learning_summary,
                        'confidence': p.confidence_score,
                        'implications_count': len(p.implications)
                    } for p in patterns
                ]
            })
        else:
            return jsonify({
                'status': 'success',
                'patterns_extracted': 0,
                'message': 'No learning patterns detected'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/governance/learning/auto-process', methods=['POST'])
def auto_process_current():
    """Automatically process current conversation context for learning"""
    try:
        # This would integrate with Cursor's chat context in a real implementation
        # For now, we'll use the request data or a placeholder
        data = request.get_json() or {}
        conversation_text = data.get('conversation', "Current conversation context placeholder")
        
        if not chat_extractor:
            return jsonify({'error': 'Chat learning extractor not available'}), 503
        patterns = chat_extractor.process_current_conversation(conversation_text)
        
        return jsonify({
            'status': 'success',
            'auto_extraction': True,
            'patterns_found': len(patterns),
            'message': f"Automatically extracted {len(patterns)} learning patterns"
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Suite 6 Governance API Server...")
    print(f"📊 Dashboard integration: Enhanced")
    print(f"🔗 Rule registry: {l9_governance_root / 'foundation' / 'logic' / 'rule-registry.json'}")
    print(f"🌐 Health check: http://localhost:8080/governance/health")
    
    app.run(host='0.0.0.0', port=8080, debug=False)
