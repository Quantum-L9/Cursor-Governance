#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-RE-003"
component_name: "Reasoning Snapshot Generator"
layer: "intelligence"
domain: "reasoning"
type: "generator"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"
governance_level: "high"
purpose: "Automated generation of structured reasoning snapshots for governance decisions"

# === GOVERNANCE METADATA ===
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["datetime", "pathlib", "json", "yaml"]
integrates_with: ["INT-RE-001", "INT-RE-002", "FND-SEC-001"]
api_endpoints: ["/api/v1/reasoning/snapshot"]
data_sources: ["foundation/logic/rule-registry.json", "foundation/agents/stubs/"]
outputs: ["intelligence/reasoning/snapshots/"]

# === OPERATIONAL METADATA ===
execution_mode: "autonomous"
monitoring_required: true
logging_level: "info"
performance_tier: "standard"

# === BUSINESS METADATA ===
business_value: "Automates governance decision documentation for audit compliance"
success_metrics: ["snapshot_generation_time < 100ms", "completeness = 100%", "audit_compliance = 100%"]

# === INTEGRATION METADATA ===
constellation_origin: "ReasoningSnapshot_Template.md + SnapshotEnforcer.md"
migration_notes: "Enhanced Constellation snapshot generation with Suite 6 automation"

# === TAGS & CLASSIFICATION ===
tags: ["reasoning", "snapshot", "generator", "automation", "governance"]
keywords: ["snapshot", "reasoning", "generator", "automation", "governance"]
related_components: ["INT-RE-001", "INT-RE-002", "FND-SEC-001"]
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

class ReasoningSnapshotGenerator:
    """
    Automated Reasoning Snapshot Generator for Suite 6
    
    Generates structured reasoning snapshots for governance decisions,
    integrating Constellation's snapshot format with Suite 6's 10-step framework.
    """
    
    def __init__(self, suite_root: str = None):
        self.suite_root = Path(suite_root) if suite_root else Path(__file__).parent.parent.parent
        self.snapshots_dir = self.suite_root / "intelligence" / "reasoning" / "snapshots"
        self.template_path = self.suite_root / "intelligence" / "reasoning" / "reasoning-snapshot-template.md"
        
        # Create snapshots directory structure
        self._setup_snapshot_directories()
    
    def _setup_snapshot_directories(self):
        """Create directory structure for snapshots"""
        current_year = datetime.now().year
        current_month = datetime.now().month
        current_day = datetime.now().day
        
        snapshot_path = self.snapshots_dir / str(current_year) / f"{current_month:02d}" / f"{current_day:02d}"
        snapshot_path.mkdir(parents=True, exist_ok=True)
    
    def generate_snapshot_id(self, component_id: str, decision_type: str) -> str:
        """Generate unique snapshot ID"""
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        return f"SNAP-{timestamp}-{component_id}-{decision_type}"
    
    def create_governance_snapshot(self, 
                                 component_id: str,
                                 component_name: str,
                                 decision_type: str,
                                 rule_applied: str,
                                 rule_id: str,
                                 observation: str,
                                 conclusion: str,
                                 verdict: str,
                                 reasoning_steps: Dict = None,
                                 evidence: Dict = None,
                                 initiated_by: str = "System",
                                 priority_level: str = "medium") -> Dict:
        """
        Create a structured governance reasoning snapshot
        """
        snapshot_id = self.generate_snapshot_id(component_id, decision_type)
        timestamp = datetime.now().isoformat()
        
        # Default reasoning steps if not provided
        if not reasoning_steps:
            reasoning_steps = {
                "objective": "Governance decision required",
                "context": "Standard governance validation",
                "system_analysis": "Component evaluation",
                "strategy": "Apply governance rules",
                "analysis": "Rule compliance check",
                "decision": conclusion,
                "validation": "Standard validation process",
                "documentation": "Automated snapshot generation",
                "risk_assessment": "Standard governance risk",
                "maintainability": "Standard maintenance requirements"
            }
        
        # Default evidence if not provided
        if not evidence:
            evidence = {
                "data_sources": ["governance-validator.py", "rule-registry.json"],
                "key_findings": [observation],
                "constraints": ["Must comply with Suite 6 governance"],
                "assumptions": ["Standard governance assumptions"]
            }
        
        # Determine escalation path based on verdict and priority
        escalation_path = self._determine_escalation_path(verdict, priority_level)
        
        snapshot = {
            "metadata": {
                "snapshot_id": snapshot_id,
                "component_id": component_id,
                "component_name": component_name,
                "decision_type": decision_type,
                "initiated_by": initiated_by,
                "priority_level": priority_level,
                "timestamp": timestamp,
                "kernel_version": "6.0"
            },
            "governance_framework": {
                "rule_applied": rule_applied,
                "rule_id": rule_id,
                "escalation_path": escalation_path
            },
            "reasoning_process": reasoning_steps,
            "evidence": evidence,
            "outcome": {
                "observation": observation,
                "conclusion": conclusion,
                "verdict": verdict,
                "confidence_level": self._determine_confidence_level(verdict, evidence),
                "next_actions": self._determine_next_actions(verdict, escalation_path)
            },
            "audit_trail": {
                "generated_by": "reasoning-snapshot-generator.py",
                "validation_status": "Generated",
                "digital_signature": None,  # Will be added by integrity system
                "related_snapshots": []
            }
        }
        
        return snapshot
    
    def _determine_escalation_path(self, verdict: str, priority_level: str) -> str:
        """Determine appropriate escalation path"""
        if verdict in ["FAIL", "ESCALATE"]:
            if priority_level == "critical":
                return "Chair_Override"
            elif priority_level == "high":
                return "Roundtable"
            else:
                return "Auto_Snapshot"
        else:
            return "None"
    
    def _determine_confidence_level(self, verdict: str, evidence: Dict) -> str:
        """Determine confidence level based on verdict and evidence quality"""
        if verdict in ["PASS", "FAIL"] and len(evidence.get("data_sources", [])) >= 2:
            return "High"
        elif verdict in ["PASS", "FAIL"]:
            return "Medium"
        else:
            return "Low"
    
    def _determine_next_actions(self, verdict: str, escalation_path: str) -> List[str]:
        """Determine next actions based on verdict and escalation"""
        actions = []
        
        if verdict == "PASS":
            actions.append("Proceed with normal operations")
        elif verdict == "FAIL":
            actions.append("Address governance violations")
            if escalation_path != "None":
                actions.append(f"Route to {escalation_path}")
        elif verdict == "ESCALATE":
            actions.append(f"Escalate to {escalation_path}")
            actions.append("Await higher-level decision")
        elif verdict == "DEFER":
            actions.append("Collect additional information")
            actions.append("Re-evaluate after conditions change")
        
        return actions
    
    def save_snapshot(self, snapshot: Dict) -> str:
        """Save snapshot to file system"""
        try:
            # Generate file path
            timestamp = datetime.now()
            year_month_day = f"{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}"
            snapshot_dir = self.snapshots_dir / year_month_day
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            snapshot_id = snapshot["metadata"]["snapshot_id"]
            filename = f"{snapshot_id}.md"
            file_path = snapshot_dir / filename
            
            # Generate markdown content
            markdown_content = self._generate_markdown_content(snapshot)
            
            # Save file
            with open(file_path, 'w') as f:
                f.write(markdown_content)
            
            return str(file_path)
            
        except Exception as e:
            print(f"Error saving snapshot: {e}")
            return None
    
    def _generate_markdown_content(self, snapshot: Dict) -> str:
        """Generate markdown content from snapshot data"""
        metadata = snapshot["metadata"]
        governance = snapshot["governance_framework"]
        reasoning = snapshot["reasoning_process"]
        evidence = snapshot["evidence"]
        outcome = snapshot["outcome"]
        audit = snapshot["audit_trail"]
        
        content = f"""# Suite 6 Reasoning Snapshot

## Decision Context
- **Component**: {metadata['component_id']} - {metadata['component_name']}
- **Decision Type**: {metadata['decision_type']}
- **Initiated By**: {metadata['initiated_by']}
- **Priority Level**: {metadata['priority_level']}
- **Timestamp**: {metadata['timestamp']}

## Governance Framework
- **Rule Applied**: {governance['rule_applied']}
- **Rule ID**: {governance['rule_id']}
- **Kernel Version**: {metadata['kernel_version']}
- **Escalation Path**: {governance['escalation_path']}

## 10-Step Reasoning Process
1. **Objective**: {reasoning.get('objective', 'Not specified')}
2. **Context**: {reasoning.get('context', 'Not specified')}
3. **System Analysis**: {reasoning.get('system_analysis', 'Not specified')}
4. **Strategy**: {reasoning.get('strategy', 'Not specified')}
5. **Analysis**: {reasoning.get('analysis', 'Not specified')}
6. **Decision**: {reasoning.get('decision', 'Not specified')}
7. **Validation**: {reasoning.get('validation', 'Not specified')}
8. **Documentation**: {reasoning.get('documentation', 'Not specified')}
9. **Risk Assessment**: {reasoning.get('risk_assessment', 'Not specified')}
10. **Maintainability**: {reasoning.get('maintainability', 'Not specified')}

## Observation & Evidence
- **Data Sources**: {', '.join(evidence.get('data_sources', []))}
- **Key Findings**: {', '.join(evidence.get('key_findings', []))}
- **Constraints**: {', '.join(evidence.get('constraints', []))}
- **Assumptions**: {', '.join(evidence.get('assumptions', []))}

## Decision Outcome
- **Observation**: {outcome['observation']}
- **Conclusion**: {outcome['conclusion']}
- **Verdict**: {outcome['verdict']}
- **Confidence Level**: {outcome['confidence_level']}
- **Next Actions**: 
{chr(10).join(f"  - {action}" for action in outcome['next_actions'])}

## Audit Trail
- **Snapshot ID**: {metadata['snapshot_id']}
- **Generated By**: {audit['generated_by']}
- **Validation Status**: {audit['validation_status']}
- **Digital Signature**: {audit.get('digital_signature', 'Pending')}
- **Related Snapshots**: {', '.join(audit.get('related_snapshots', [])) or 'None'}
"""
        
        return content
    
    def create_validation_snapshot(self, component_id: str, component_name: str, 
                                 validation_result: Dict) -> Optional[str]:
        """
        Create snapshot for governance validation results
        """
        # Determine verdict based on validation result
        if validation_result.get("compliant", False):
            verdict = "PASS"
            conclusion = "Component meets all governance requirements"
            observation = "All validation checks passed successfully"
        else:
            verdict = "FAIL"
            violations = validation_result.get("violations", [])
            conclusion = f"Component has {len(violations)} governance violations"
            observation = f"Violations detected: {', '.join(violations)}"
        
        # Create snapshot
        snapshot = self.create_governance_snapshot(
            component_id=component_id,
            component_name=component_name,
            decision_type="governance_validation",
            rule_applied="∀f. GovernanceFile(f) → HasCanonicalHeader(f)",
            rule_id="R004",
            observation=observation,
            conclusion=conclusion,
            verdict=verdict,
            priority_level="high" if verdict == "FAIL" else "medium"
        )
        
        # Save snapshot
        return self.save_snapshot(snapshot)
    
    def create_escalation_snapshot(self, component_id: str, component_name: str,
                                 failure_type: str, escalation_target: str) -> Optional[str]:
        """
        Create snapshot for escalation routing decisions
        """
        snapshot = self.create_governance_snapshot(
            component_id=component_id,
            component_name=component_name,
            decision_type="escalation_routing",
            rule_applied="∃x. Chair(x) ∧ Override(x) → CanChangeAgent(y)",
            rule_id="R003",
            observation=f"Governance failure detected: {failure_type}",
            conclusion=f"Escalation required to {escalation_target}",
            verdict="ESCALATE",
            priority_level="critical",
            reasoning_steps={
                "objective": "Route governance failure to appropriate authority",
                "context": f"Failure type: {failure_type}",
                "system_analysis": "Escalation routing system evaluation",
                "strategy": "Apply escalation hierarchy rules",
                "analysis": f"Failure severity requires {escalation_target} intervention",
                "decision": f"Route to {escalation_target}",
                "validation": "Escalation path validated against governance rules",
                "documentation": "Escalation decision documented",
                "risk_assessment": "High risk if not escalated properly",
                "maintainability": "Standard escalation maintenance"
            }
        )
        
        return self.save_snapshot(snapshot)
    
    def list_snapshots(self, component_id: str = None, days: int = 30) -> List[Dict]:
        """
        List recent snapshots, optionally filtered by component
        """
        snapshots = []
        
        # Search recent snapshot directories
        for snapshot_file in self.snapshots_dir.rglob("SNAP-*.md"):
            try:
                # Parse snapshot ID to get component info
                filename = snapshot_file.stem
                parts = filename.split("-")
                
                if len(parts) >= 4:
                    file_component_id = parts[2]
                    
                    # Filter by component if specified
                    if component_id and file_component_id != component_id:
                        continue
                    
                    # Get file stats
                    stat = snapshot_file.stat()
                    
                    snapshots.append({
                        "snapshot_id": filename,
                        "component_id": file_component_id,
                        "file_path": str(snapshot_file),
                        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "size": stat.st_size
                    })
                    
            except Exception as e:
                print(f"Error processing snapshot {snapshot_file}: {e}")
        
        # Sort by creation time (newest first)
        snapshots.sort(key=lambda x: x["created"], reverse=True)
        
        return snapshots

def main():
    """CLI interface for reasoning snapshot generation"""
    if len(sys.argv) < 2:
        print("Usage: python reasoning-snapshot-generator.py <command> [args]")
        print("Commands:")
        print("  create <component_id> <component_name> <decision_type> <rule_id> <observation> <conclusion> <verdict>")
        print("  validation <component_id> <component_name> <compliant:true/false> [violations...]")
        print("  escalation <component_id> <component_name> <failure_type> <escalation_target>")
        print("  list [component_id] - List recent snapshots")
        return
    
    generator = ReasoningSnapshotGenerator()
    command = sys.argv[1]
    
    if command == "create" and len(sys.argv) >= 9:
        component_id = sys.argv[2]
        component_name = sys.argv[3]
        decision_type = sys.argv[4]
        rule_id = sys.argv[5]
        observation = sys.argv[6]
        conclusion = sys.argv[7]
        verdict = sys.argv[8]
        
        snapshot = generator.create_governance_snapshot(
            component_id=component_id,
            component_name=component_name,
            decision_type=decision_type,
            rule_applied=f"Rule {rule_id} applied",
            rule_id=rule_id,
            observation=observation,
            conclusion=conclusion,
            verdict=verdict
        )
        
        file_path = generator.save_snapshot(snapshot)
        if file_path:
            print(f"✅ Snapshot created: {file_path}")
        else:
            print("❌ Failed to create snapshot")
    
    elif command == "validation" and len(sys.argv) >= 5:
        component_id = sys.argv[2]
        component_name = sys.argv[3]
        compliant = sys.argv[4].lower() == "true"
        violations = sys.argv[5:] if len(sys.argv) > 5 else []
        
        validation_result = {
            "compliant": compliant,
            "violations": violations
        }
        
        file_path = generator.create_validation_snapshot(component_id, component_name, validation_result)
        if file_path:
            print(f"✅ Validation snapshot created: {file_path}")
        else:
            print("❌ Failed to create validation snapshot")
    
    elif command == "escalation" and len(sys.argv) >= 6:
        component_id = sys.argv[2]
        component_name = sys.argv[3]
        failure_type = sys.argv[4]
        escalation_target = sys.argv[5]
        
        file_path = generator.create_escalation_snapshot(component_id, component_name, failure_type, escalation_target)
        if file_path:
            print(f"✅ Escalation snapshot created: {file_path}")
        else:
            print("❌ Failed to create escalation snapshot")
    
    elif command == "list":
        component_id = sys.argv[2] if len(sys.argv) > 2 else None
        snapshots = generator.list_snapshots(component_id)
        
        print(f"Recent snapshots{f' for {component_id}' if component_id else ''}:")
        for snapshot in snapshots[:10]:  # Show last 10
            print(f"  📸 {snapshot['snapshot_id']} ({snapshot['created']})")
    
    else:
        print("Invalid command or missing arguments")

if __name__ == "__main__":
    main()
