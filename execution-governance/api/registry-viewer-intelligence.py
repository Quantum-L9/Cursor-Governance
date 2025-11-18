#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "EXE-API-002"
component_name: "Registry Viewer Intelligence"
layer: "execution"
domain: "api_services"
type: "intelligent_query_engine"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"
governance_level: "high"
purpose: "Intelligent governance registry querying with natural language support"

# === GOVERNANCE METADATA ===
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["json", "pathlib", "datetime", "re"]
integrates_with: ["FND-LG-001", "FND-AG-002", "EXE-API-001"]
api_endpoints: ["/api/v1/registry/query", "/api/v1/registry/agents", "/api/v1/registry/coverage"]
data_sources: ["foundation/logic/rule-registry.json", "foundation/agents/stubs/"]
outputs: ["execution/api/query-cache/", "telemetry/logs/registry-queries.log"]

# === OPERATIONAL METADATA ===
execution_mode: "service"
monitoring_required: true
logging_level: "info"
performance_tier: "standard"

# === BUSINESS METADATA ===
business_value: "Enables natural language querying of governance registries for audit and analysis"
success_metrics: ["query_response_time < 500ms", "query_accuracy > 90%", "cache_hit_rate > 70%"]

# === INTEGRATION METADATA ===
constellation_origin: "RegistryViewerAgent.md"
migration_notes: "Enhanced Constellation registry viewer with intelligent querying and Suite 6 integration"

# === TAGS & CLASSIFICATION ===
tags: ["registry", "intelligence", "querying", "natural_language", "governance"]
keywords: ["registry", "viewer", "intelligence", "query", "governance"]
related_components: ["FND-LG-001", "FND-AG-002", "EXE-API-001"]
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

class RegistryViewerIntelligence:
    """
    Intelligent Governance Registry Query Engine for Suite 6
    
    Provides natural language querying capabilities for governance registries,
    agent stubs, and compliance data. Based on Constellation's RegistryViewerAgent.
    """
    
    def __init__(self, suite_root: str = None):
        self.suite_root = Path(suite_root) if suite_root else Path(__file__).parent.parent.parent
        self.rule_registry_path = self.suite_root / "foundation" / "logic" / "rule-registry.json"
        self.stubs_dir = self.suite_root / "foundation" / "agents" / "stubs"
        self.cache_dir = self.suite_root / "execution" / "api" / "query-cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Load registries
        self.rule_registry = self._load_rule_registry()
        self.agent_stubs = self._load_agent_stubs()
        
        # Query patterns for natural language processing
        self.query_patterns = {
            "agents_enforcing_rule": [
                r"which agents enforce (\w+)",
                r"agents using rule (\w+)",
                r"who enforces (\w+)",
                r"components with rule (\w+)"
            ],
            "agents_by_kernel": [
                r"agents using kernel ([\d.]+)",
                r"components with kernel ([\d.]+)",
                r"kernel version ([\d.]+) agents"
            ],
            "stale_agents": [
                r"stale agents",
                r"outdated validations",
                r"agents not validated in (\d+) days",
                r"old validations"
            ],
            "agents_by_layer": [
                r"(\w+) layer agents",
                r"agents in (\w+) layer",
                r"(\w+) components"
            ],
            "rule_coverage": [
                r"rule coverage",
                r"which rules are enforced",
                r"rule usage",
                r"coverage analysis"
            ],
            "escalation_paths": [
                r"escalation paths",
                r"agents with (\w+) escalation",
                r"escalation to (\w+)"
            ]
        }
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def _load_rule_registry(self) -> Dict:
        """Load governance rule registry"""
        try:
            if self.rule_registry_path.exists():
                with open(self.rule_registry_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading rule registry: {e}")
        return {"rules": []}
    
    def _load_agent_stubs(self) -> Dict[str, Dict]:
        """Load all agent stubs"""
        stubs = {}
        try:
            if self.stubs_dir.exists():
                for stub_file in self.stubs_dir.glob("*.stub.json"):
                    with open(stub_file, 'r') as f:
                        stub_data = json.load(f)
                        component_id = stub_data.get("component_id", stub_file.stem)
                        stubs[component_id] = stub_data
        except Exception as e:
            self.logger.error(f"Error loading agent stubs: {e}")
        return stubs
    
    def parse_natural_language_query(self, query: str) -> Tuple[str, Dict]:
        """
        Parse natural language query and determine intent
        """
        query_lower = query.lower().strip()
        
        for intent, patterns in self.query_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    params = {"matches": match.groups()} if match.groups() else {}
                    return intent, params
        
        # Default to general search if no pattern matches
        return "general_search", {"query": query}
    
    def query_agents_enforcing_rule(self, rule_id: str) -> Dict:
        """
        Find agents that enforce a specific rule
        """
        enforcing_agents = []
        
        for component_id, stub in self.agent_stubs.items():
            rules_enforced = stub.get("rules_enforced", [])
            if rule_id.upper() in rules_enforced:
                enforcing_agents.append({
                    "component_id": component_id,
                    "agent_name": stub.get("agent", "Unknown"),
                    "layer": stub.get("layer", "unknown"),
                    "last_validated": stub.get("last_validated", "unknown"),
                    "escalation_path": stub.get("escalation_path", "unknown")
                })
        
        # Get rule details
        rule_details = None
        for rule in self.rule_registry.get("rules", []):
            if rule.get("id") == rule_id.upper():
                rule_details = rule
                break
        
        return {
            "query_type": "agents_enforcing_rule",
            "rule_id": rule_id.upper(),
            "rule_details": rule_details,
            "enforcing_agents": enforcing_agents,
            "total_agents": len(enforcing_agents),
            "timestamp": datetime.now().isoformat()
        }
    
    def query_agents_by_kernel_version(self, kernel_version: str) -> Dict:
        """
        Find agents using specific kernel version
        """
        matching_agents = []
        
        for component_id, stub in self.agent_stubs.items():
            if stub.get("governance_kernel") == kernel_version:
                matching_agents.append({
                    "component_id": component_id,
                    "agent_name": stub.get("agent", "Unknown"),
                    "layer": stub.get("layer", "unknown"),
                    "agent_version": stub.get("agent_version", "unknown"),
                    "last_validated": stub.get("last_validated", "unknown")
                })
        
        return {
            "query_type": "agents_by_kernel",
            "kernel_version": kernel_version,
            "matching_agents": matching_agents,
            "total_agents": len(matching_agents),
            "timestamp": datetime.now().isoformat()
        }
    
    def query_stale_agents(self, days_threshold: int = 30) -> Dict:
        """
        Find agents with stale validation dates
        """
        stale_agents = []
        threshold_date = datetime.now() - timedelta(days=days_threshold)
        
        for component_id, stub in self.agent_stubs.items():
            last_validated = stub.get("last_validated", "")
            if last_validated:
                try:
                    validated_date = datetime.fromisoformat(last_validated)
                    if validated_date < threshold_date:
                        days_old = (datetime.now() - validated_date).days
                        stale_agents.append({
                            "component_id": component_id,
                            "agent_name": stub.get("agent", "Unknown"),
                            "layer": stub.get("layer", "unknown"),
                            "last_validated": last_validated,
                            "days_old": days_old,
                            "escalation_path": stub.get("escalation_path", "unknown")
                        })
                except:
                    # Invalid date format
                    stale_agents.append({
                        "component_id": component_id,
                        "agent_name": stub.get("agent", "Unknown"),
                        "layer": stub.get("layer", "unknown"),
                        "last_validated": "invalid_date",
                        "days_old": "unknown",
                        "escalation_path": stub.get("escalation_path", "unknown")
                    })
        
        # Sort by days old (oldest first)
        stale_agents.sort(key=lambda x: x.get("days_old", 0) if isinstance(x.get("days_old"), int) else 0, reverse=True)
        
        return {
            "query_type": "stale_agents",
            "days_threshold": days_threshold,
            "stale_agents": stale_agents,
            "total_stale": len(stale_agents),
            "timestamp": datetime.now().isoformat()
        }
    
    def query_agents_by_layer(self, layer_name: str) -> Dict:
        """
        Find agents in specific layer
        """
        layer_agents = []
        
        for component_id, stub in self.agent_stubs.items():
            if stub.get("layer", "").lower() == layer_name.lower():
                layer_agents.append({
                    "component_id": component_id,
                    "agent_name": stub.get("agent", "Unknown"),
                    "agent_version": stub.get("agent_version", "unknown"),
                    "governance_kernel": stub.get("governance_kernel", "unknown"),
                    "rules_enforced": stub.get("rules_enforced", []),
                    "last_validated": stub.get("last_validated", "unknown"),
                    "status": stub.get("status", "unknown")
                })
        
        return {
            "query_type": "agents_by_layer",
            "layer_name": layer_name,
            "layer_agents": layer_agents,
            "total_agents": len(layer_agents),
            "timestamp": datetime.now().isoformat()
        }
    
    def query_rule_coverage(self) -> Dict:
        """
        Analyze rule coverage across all agents
        """
        rule_usage = {}
        total_agents = len(self.agent_stubs)
        
        # Count rule usage
        for component_id, stub in self.agent_stubs.items():
            rules_enforced = stub.get("rules_enforced", [])
            for rule_id in rules_enforced:
                if rule_id not in rule_usage:
                    rule_usage[rule_id] = {
                        "rule_id": rule_id,
                        "enforcing_agents": [],
                        "usage_count": 0
                    }
                rule_usage[rule_id]["enforcing_agents"].append(component_id)
                rule_usage[rule_id]["usage_count"] += 1
        
        # Add rule details and calculate coverage
        coverage_analysis = []
        for rule in self.rule_registry.get("rules", []):
            rule_id = rule.get("id")
            usage = rule_usage.get(rule_id, {"usage_count": 0, "enforcing_agents": []})
            
            coverage_percentage = (usage["usage_count"] / total_agents * 100) if total_agents > 0 else 0
            
            coverage_analysis.append({
                "rule_id": rule_id,
                "description": rule.get("description", ""),
                "type": rule.get("type", ""),
                "priority": rule.get("priority", ""),
                "usage_count": usage["usage_count"],
                "coverage_percentage": round(coverage_percentage, 1),
                "enforcing_agents": usage["enforcing_agents"]
            })
        
        # Sort by usage count (most used first)
        coverage_analysis.sort(key=lambda x: x["usage_count"], reverse=True)
        
        return {
            "query_type": "rule_coverage",
            "total_rules": len(self.rule_registry.get("rules", [])),
            "total_agents": total_agents,
            "coverage_analysis": coverage_analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    def query_escalation_paths(self, escalation_target: str = None) -> Dict:
        """
        Analyze escalation paths across agents
        """
        escalation_analysis = {}
        
        for component_id, stub in self.agent_stubs.items():
            escalation_path = stub.get("escalation_path", "unknown")
            
            if escalation_target and escalation_path.lower() != escalation_target.lower():
                continue
            
            if escalation_path not in escalation_analysis:
                escalation_analysis[escalation_path] = {
                    "escalation_path": escalation_path,
                    "agents": [],
                    "count": 0
                }
            
            escalation_analysis[escalation_path]["agents"].append({
                "component_id": component_id,
                "agent_name": stub.get("agent", "Unknown"),
                "layer": stub.get("layer", "unknown"),
                "governance_level": stub.get("governance_level", "unknown")
            })
            escalation_analysis[escalation_path]["count"] += 1
        
        escalation_paths = list(escalation_analysis.values())
        escalation_paths.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "query_type": "escalation_paths",
            "escalation_target": escalation_target,
            "escalation_paths": escalation_paths,
            "total_paths": len(escalation_paths),
            "timestamp": datetime.now().isoformat()
        }
    
    def execute_query(self, query: str) -> Dict:
        """
        Execute natural language query against governance registries
        """
        try:
            # Parse query intent
            intent, params = self.parse_natural_language_query(query)
            
            # Execute appropriate query
            if intent == "agents_enforcing_rule" and params.get("matches"):
                rule_id = params["matches"][0]
                return self.query_agents_enforcing_rule(rule_id)
            
            elif intent == "agents_by_kernel" and params.get("matches"):
                kernel_version = params["matches"][0]
                return self.query_agents_by_kernel_version(kernel_version)
            
            elif intent == "stale_agents":
                days = 30
                if params.get("matches") and params["matches"][0].isdigit():
                    days = int(params["matches"][0])
                return self.query_stale_agents(days)
            
            elif intent == "agents_by_layer" and params.get("matches"):
                layer_name = params["matches"][0]
                return self.query_agents_by_layer(layer_name)
            
            elif intent == "rule_coverage":
                return self.query_rule_coverage()
            
            elif intent == "escalation_paths":
                escalation_target = None
                if params.get("matches"):
                    escalation_target = params["matches"][0]
                return self.query_escalation_paths(escalation_target)
            
            else:
                # General search - return summary
                return self.get_governance_summary()
        
        except Exception as e:
            self.logger.error(f"Error executing query '{query}': {e}")
            return {
                "query_type": "error",
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_governance_summary(self) -> Dict:
        """
        Get overall governance summary
        """
        total_agents = len(self.agent_stubs)
        total_rules = len(self.rule_registry.get("rules", []))
        
        # Layer distribution
        layer_distribution = {}
        for stub in self.agent_stubs.values():
            layer = stub.get("layer", "unknown")
            layer_distribution[layer] = layer_distribution.get(layer, 0) + 1
        
        # Kernel version distribution
        kernel_distribution = {}
        for stub in self.agent_stubs.values():
            kernel = stub.get("governance_kernel", "unknown")
            kernel_distribution[kernel] = kernel_distribution.get(kernel, 0) + 1
        
        # Recent validation status
        recent_validations = 0
        stale_validations = 0
        threshold_date = datetime.now() - timedelta(days=30)
        
        for stub in self.agent_stubs.values():
            last_validated = stub.get("last_validated", "")
            if last_validated:
                try:
                    validated_date = datetime.fromisoformat(last_validated)
                    if validated_date >= threshold_date:
                        recent_validations += 1
                    else:
                        stale_validations += 1
                except:
                    stale_validations += 1
        
        return {
            "query_type": "governance_summary",
            "total_agents": total_agents,
            "total_rules": total_rules,
            "layer_distribution": layer_distribution,
            "kernel_distribution": kernel_distribution,
            "validation_status": {
                "recent_validations": recent_validations,
                "stale_validations": stale_validations,
                "validation_rate": round((recent_validations / total_agents * 100) if total_agents > 0 else 0, 1)
            },
            "timestamp": datetime.now().isoformat()
        }

def main():
    """CLI interface for registry viewer intelligence"""
    if len(sys.argv) < 2:
        print("Usage: python registry-viewer-intelligence.py <query>")
        print("Example queries:")
        print("  'Which agents enforce R001?'")
        print("  'Agents using kernel 6.0'")
        print("  'Stale agents'")
        print("  'Foundation layer agents'")
        print("  'Rule coverage'")
        print("  'Escalation paths'")
        return
    
    query = " ".join(sys.argv[1:])
    
    viewer = RegistryViewerIntelligence()
    result = viewer.execute_query(query)
    
    print(f"Query: {query}")
    print("=" * 50)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
