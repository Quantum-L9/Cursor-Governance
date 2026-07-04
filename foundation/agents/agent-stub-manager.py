#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "FND-AG-002"
component_name: "Agent Stub Manager"
layer: "foundation"
domain: "agent_governance"
type: "management_system"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"
governance_level: "critical"
purpose: "Manage agent governance profiles and stub validation for L9 Governance components"

# === GOVERNANCE METADATA ===
compliance_required: true
audit_trail: true
security_classification: "restricted"

# === TECHNICAL METADATA ===
dependencies: ["foundation/logic/rule-registry.json", "foundation/logic/universal-kernel.md"]
integrates_with: ["FND-LG-001", "FND-LG-002", "EXE-VAL-001"]
api_endpoints: ["/api/v1/agents/stubs", "/api/v1/agents/validate"]
data_sources: ["foundation/agents/stubs/", "foundation/logic/rule-registry.json"]
outputs: ["telemetry/logs/agent-governance.log", "foundation/agents/stubs/"]

# === OPERATIONAL METADATA ===
execution_mode: "autonomous"
monitoring_required: true
logging_level: "info"
performance_tier: "standard"

# === BUSINESS METADATA ===
business_value: "Provides granular agent-level governance tracking and validation"
success_metrics: ["stub_coverage = 100%", "validation_accuracy > 95%", "response_time < 200ms"]

# === INTEGRATION METADATA ===
constellation_origin: "StubValidatorAgent_LiveService_Bundle"
migration_notes: "Enhanced Constellation stub validation with L9 Governance integration"

# === TAGS & CLASSIFICATION ===
tags: ["agent_governance", "stub_management", "validation", "constellation_integration"]
keywords: ["agent", "stub", "governance", "validation", "management"]
related_components: ["FND-LG-001", "FND-LG-002", "EXE-VAL-001"]
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib
import yaml

class AgentStubManager:
    """
    Agent Stub Management System for L9 Governance
    
    Manages agent governance profiles, validates stub compliance,
    and provides agent-centric governance tracking.
    """
    
    def __init__(self, suite_root: str = None):
        self.suite_root = Path(suite_root) if suite_root else Path(__file__).parent.parent.parent
        self.stubs_dir = self.suite_root / "foundation" / "agents" / "stubs"
        self.rule_registry_path = self.suite_root / "foundation" / "logic" / "rule-registry.json"
        self.stubs_dir.mkdir(parents=True, exist_ok=True)
        
    def create_stub_from_component(self, component_path: str, component_id: str) -> Dict:
        """
        Generate agent stub from L9 Governance component canonical header
        """
        try:
            with open(component_path, 'r') as f:
                content = f.read()
            
            # Extract YAML header
            if content.startswith('---'):
                header_end = content.find('---', 3)
                if header_end != -1:
                    header_yaml = content[3:header_end].strip()
                    header = yaml.safe_load(header_yaml)
                    
                    # Create stub based on header metadata
                    stub = {
                        "agent": header.get("component_name", "Unknown Agent"),
                        "component_id": component_id,
                        "agent_version": header.get("version", "1.0.0"),
                        "governance_kernel": "6.0",
                        "rules_enforced": self._extract_applicable_rules(header),
                        "snapshot_required": header.get("governance_level") in ["critical", "high"],
                        "override_enabled": header.get("governance_level") == "critical",
                        "linter_verified": True,
                        "last_validated": datetime.now().isoformat()[:10],
                        "escalation_path": self._determine_escalation_path(header),
                        "policy_anchor": "universal-kernel.md",
                        "roles_declared": [header.get("domain", "general")],
                        "layer": header.get("layer", "unknown"),
                        "status": header.get("status", "active"),
                        "tags": header.get("tags", [])
                    }
                    
                    return stub
                    
        except Exception as e:
            print(f"Error creating stub for {component_path}: {e}")
            return None
    
    def _extract_applicable_rules(self, header: Dict) -> List[str]:
        """Extract applicable governance rules based on component metadata"""
        rules = ["R004"]  # All components need canonical headers
        
        governance_level = header.get("governance_level", "low")
        if governance_level in ["critical", "high"]:
            rules.extend(["R001", "R003"])  # Critical components need strict rules
            
        layer = header.get("layer", "")
        if layer == "foundation":
            rules.append("R002")  # Foundation layer specific rules
            
        return list(set(rules))  # Remove duplicates
    
    def _determine_escalation_path(self, header: Dict) -> str:
        """Determine escalation path based on component criticality"""
        governance_level = header.get("governance_level", "low")
        
        escalation_map = {
            "critical": "Chair_Override",
            "high": "Roundtable", 
            "medium": "Auto_Snapshot",
            "low": "HumanOperator"
        }
        
        return escalation_map.get(governance_level, "HumanOperator")
    
    def validate_stub(self, stub_path: str) -> Tuple[bool, Dict]:
        """
        Validate agent stub against governance requirements
        Based on Constellation's StubValidatorAgent logic
        """
        try:
            with open(stub_path, 'r') as f:
                stub = json.load(f)
                
            issues = {
                "schema": [],
                "rules": [],
                "staleness": False,
                "kernel": []
            }
            
            # Schema validation
            required_fields = [
                "agent", "component_id", "agent_version", "governance_kernel",
                "rules_enforced", "snapshot_required", "override_enabled",
                "linter_verified", "last_validated"
            ]
            
            for field in required_fields:
                if field not in stub:
                    issues["schema"].append(f"Missing required field: {field}")
            
            # Rule integrity check
            if self.rule_registry_path.exists():
                with open(self.rule_registry_path, 'r') as f:
                    registry = json.load(f)
                    valid_rules = [rule["id"] for rule in registry.get("rules", [])]
                    
                for rule_id in stub.get("rules_enforced", []):
                    if rule_id not in valid_rules:
                        issues["rules"].append(f"Rule {rule_id} not found in registry")
            
            # Kernel compatibility check
            if stub.get("governance_kernel") != "6.0":
                issues["kernel"].append(f"Expected kernel version 6.0, got {stub.get('governance_kernel')}")
            
            # Staleness check (30 days)
            last_validated = stub.get("last_validated", "")
            if last_validated:
                try:
                    validated_date = datetime.fromisoformat(last_validated)
                    if datetime.now() - validated_date > timedelta(days=30):
                        issues["staleness"] = True
                except:
                    issues["schema"].append("Invalid last_validated date format")
            
            # Determine overall status
            has_issues = any([
                issues["schema"],
                issues["rules"], 
                issues["staleness"],
                issues["kernel"]
            ])
            
            result = {
                "agent": stub.get("agent", "Unknown"),
                "component_id": stub.get("component_id", "Unknown"),
                "status": "fail" if has_issues else "pass",
                "issues": issues,
                "last_validated": stub.get("last_validated", ""),
                "recommended_action": self._get_recommended_action(issues) if has_issues else "compliant"
            }
            
            return not has_issues, result
            
        except Exception as e:
            return False, {
                "agent": "Unknown",
                "status": "error", 
                "error": str(e),
                "recommended_action": "fix_stub_format"
            }
    
    def _get_recommended_action(self, issues: Dict) -> str:
        """Determine recommended action based on validation issues"""
        if issues["schema"]:
            return "fix_schema_violations"
        elif issues["rules"]:
            return "update_rule_references"
        elif issues["kernel"]:
            return "upgrade_kernel_version"
        elif issues["staleness"]:
            return "re_validate_and_update"
        else:
            return "general_review_required"
    
    def generate_stubs_for_l9_governance(self) -> Dict[str, bool]:
        """
        Generate stubs for all L9 Governance components
        """
        results = {}
        
        # Scan all layers for components
        layers = ["intelligence", "foundation", "execution", "operations", "environment", "telemetry"]
        
        for layer in layers:
            layer_path = self.suite_root / layer
            if layer_path.exists():
                for file_path in layer_path.rglob("*.md"):
                    if self._has_canonical_header(file_path):
                        component_id = self._extract_component_id(file_path)
                        if component_id:
                            stub = self.create_stub_from_component(str(file_path), component_id)
                            if stub:
                                stub_file = self.stubs_dir / f"{component_id}.stub.json"
                                with open(stub_file, 'w') as f:
                                    json.dump(stub, f, indent=2)
                                results[component_id] = True
                            else:
                                results[component_id] = False
        
        return results
    
    def _has_canonical_header(self, file_path: Path) -> bool:
        """Check if file has L9 Governance canonical header"""
        try:
            with open(file_path, 'r') as f:
                content = f.read(500)  # Read first 500 chars
                return "=== L9 GOVERNANCE CANONICAL HEADER ===" in content
        except:
            return False
    
    def _extract_component_id(self, file_path: Path) -> Optional[str]:
        """Extract component ID from canonical header"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            if content.startswith('---'):
                header_end = content.find('---', 3)
                if header_end != -1:
                    header_yaml = content[3:header_end].strip()
                    header = yaml.safe_load(header_yaml)
                    return header.get("component_id")
        except:
            pass
        return None
    
    def get_governance_coverage(self) -> Dict:
        """
        Analyze governance coverage across L9 Governance components
        """
        coverage = {
            "total_components": 0,
            "components_with_stubs": 0,
            "coverage_percentage": 0,
            "by_layer": {},
            "validation_status": {}
        }
        
        # Count components by layer
        layers = ["intelligence", "foundation", "execution", "operations", "environment", "telemetry"]
        
        for layer in layers:
            layer_path = self.suite_root / layer
            layer_components = 0
            layer_stubs = 0
            
            if layer_path.exists():
                for file_path in layer_path.rglob("*.md"):
                    if self._has_canonical_header(file_path):
                        layer_components += 1
                        component_id = self._extract_component_id(file_path)
                        if component_id:
                            stub_file = self.stubs_dir / f"{component_id}.stub.json"
                            if stub_file.exists():
                                layer_stubs += 1
                                
                                # Validate stub
                                is_valid, validation_result = self.validate_stub(str(stub_file))
                                coverage["validation_status"][component_id] = validation_result
            
            coverage["by_layer"][layer] = {
                "total": layer_components,
                "with_stubs": layer_stubs,
                "coverage": (layer_stubs / layer_components * 100) if layer_components > 0 else 0
            }
            
            coverage["total_components"] += layer_components
            coverage["components_with_stubs"] += layer_stubs
        
        coverage["coverage_percentage"] = (
            coverage["components_with_stubs"] / coverage["total_components"] * 100
        ) if coverage["total_components"] > 0 else 0
        
        return coverage

def main():
    """CLI interface for agent stub management"""
    if len(sys.argv) < 2:
        print("Usage: python agent-stub-manager.py <command> [args]")
        print("Commands:")
        print("  generate - Generate stubs for all L9 Governance components")
        print("  validate <stub_path> - Validate specific stub file")
        print("  coverage - Show governance coverage analysis")
        return
    
    manager = AgentStubManager()
    command = sys.argv[1]
    
    if command == "generate":
        print("Generating stubs for L9 Governance components...")
        results = manager.generate_stubs_for_l9_governance()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f"Generated {success_count}/{total_count} stubs successfully")
        
        for component_id, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {component_id}")
    
    elif command == "validate" and len(sys.argv) > 2:
        stub_path = sys.argv[2]
        is_valid, result = manager.validate_stub(stub_path)
        
        print(f"Validation result for {stub_path}:")
        print(json.dumps(result, indent=2))
    
    elif command == "coverage":
        coverage = manager.get_governance_coverage()
        
        print("Governance Coverage Analysis:")
        print(f"Overall Coverage: {coverage['coverage_percentage']:.1f}% ({coverage['components_with_stubs']}/{coverage['total_components']})")
        print("\nBy Layer:")
        
        for layer, stats in coverage["by_layer"].items():
            print(f"  {layer}: {stats['coverage']:.1f}% ({stats['with_stubs']}/{stats['total']})")
        
        print(f"\nValidation Status: {len(coverage['validation_status'])} stubs validated")
        
        failed_validations = [
            comp_id for comp_id, result in coverage['validation_status'].items()
            if result.get('status') == 'fail'
        ]
        
        if failed_validations:
            print(f"Failed validations: {len(failed_validations)}")
            for comp_id in failed_validations:
                print(f"  ❌ {comp_id}")
    
    else:
        print("Invalid command. Use 'generate', 'validate <path>', or 'coverage'")

if __name__ == "__main__":
    main()
