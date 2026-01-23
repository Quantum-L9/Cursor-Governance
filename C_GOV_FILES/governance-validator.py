#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "EXE-VAL-001"
component_name: "Governance Validator"
layer: "execution"
domain: "validation"
type: "validator_system"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

dependencies: ["FND-LG-002", "INT-RE-001"]
integrates_with: ["EXE-API-001", "EXE-MON-001", "OPS-OPS-001"]

suite_3_origin: "50_Governance_Validator_v3.0.py"
migration_notes: "Enhanced with Suite 6 canonical header validation and formal logic integration"

Governance Validator v6.0
Runtime enforcement mechanism for Suite 6 governance compliance
"""

import os
import re
import json
import hashlib
import yaml
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path

class GovernanceValidator:
    """Validates Suite 6 governance compliance at runtime"""
    
    def __init__(self, suite6_root: Path = None):
        if suite6_root is None:
            suite6_root = Path(__file__).parent.parent.parent
        
        self.suite6_root = Path(suite6_root)
        self.governance_path = self.suite6_root
        self.violations = []
        self.log_file = self.suite6_root / "telemetry" / "logs" / "governance-violations.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Suite 6 canonical header requirements
        self.required_header_fields = [
            'suite', 'version', 'component_id', 'component_name', 'layer',
            'status', 'created', 'author', 'governance_level', 'purpose'
        ]
        
        self.valid_layers = ['intelligence', 'foundation', 'execution', 'operations', 'environment', 'telemetry', 'docs']
        self.valid_statuses = ['active', 'deprecated', 'experimental', 'archived']
        self.component_id_pattern = r'^(INT|FND|EXE|OPS|ENV|TEL|DOC)-[A-Z]{2,3}-\d{3}$'
    
    def validate_all_files(self) -> Dict[str, bool]:
        """Validate all Suite 6 governance files for compliance"""
        results = {}
        
        # Scan all layers for governance files
        for layer in self.valid_layers:
            layer_path = self.suite6_root / layer
            if layer_path.exists():
                for file_path in layer_path.rglob('*'):
                    if file_path.is_file() and file_path.suffix in ['.md', '.py', '.json', '.yaml']:
                        relative_path = str(file_path.relative_to(self.suite6_root))
                        results[relative_path] = self.validate_file(file_path)
        
        return results
    
    def validate_file(self, filepath: Path) -> bool:
        """Validate a single file for Suite 6 governance compliance"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            violations = []
            
            # Check for Suite 6 canonical header
            if not self._has_canonical_header(content, filepath):
                violations.append(f"Missing Suite 6 canonical header in {filepath.name}")
            
            # Validate header content if present
            header_violations = self._validate_header_content(content, filepath)
            violations.extend(header_violations)
            
            # Check kebab-case naming convention
            if not self._is_kebab_case(filepath.name):
                violations.append(f"File name should use kebab-case format: {filepath.name}")
            
            # Log violations
            if violations:
                self.violations.extend(violations)
                self._log_violations(filepath, violations)
                return False
            
            return True
            
        except Exception as e:
            violation = f"Error validating {filepath}: {str(e)}"
            self.violations.append(violation)
            self._log_violations(filepath, [violation])
            return False
    
    def _has_canonical_header(self, content: str, filepath: Path) -> bool:
        """Check if file has Suite 6 canonical header"""
        # Python files: check for header in docstring
        if filepath.suffix == '.py':
            return '# === SUITE 6 CANONICAL HEADER ===' in content
        
        # Markdown files: check for YAML header
        if filepath.suffix == '.md':
            return content.startswith('---') and '# === SUITE 6 CANONICAL HEADER ===' in content
        
        # JSON files: check for metadata section
        if filepath.suffix == '.json':
            try:
                data = json.loads(content)
                return 'metadata' in data and 'suite' in data.get('metadata', {})
            except:
                return False
        
        return True  # Other file types don't require headers
    
    def _validate_header_content(self, content: str, filepath: Path) -> List[str]:
        """Validate canonical header content"""
        violations = []
        
        try:
            if filepath.suffix == '.md':
                # Extract YAML header
                if content.startswith('---'):
                    yaml_end = content.find('---', 3)
                    if yaml_end != -1:
                        yaml_content = content[3:yaml_end]
                        header = yaml.safe_load(yaml_content)
                        violations.extend(self._check_header_fields(header, filepath))
            
            elif filepath.suffix == '.json':
                # Check JSON metadata
                data = json.loads(content)
                if 'metadata' in data:
                    violations.extend(self._check_header_fields(data['metadata'], filepath))
            
            elif filepath.suffix == '.py':
                # Extract header from docstring
                header_match = re.search(r'# === SUITE 6 CANONICAL HEADER ===.*?"""', content, re.DOTALL)
                if header_match:
                    # For Python files, we expect key-value pairs in comments
                    header_content = header_match.group(0)
                    if 'suite: "Cursor Governance Suite 6 (L9 + Suite 6)"' not in header_content:
                        violations.append("Invalid suite name in Python file header")
                    if 'version: "6.0.0"' not in header_content:
                        violations.append("Invalid version in Python file header")
        
        except Exception as e:
            violations.append(f"Error parsing header: {str(e)}")
        
        return violations
    
    def _check_header_fields(self, header: Dict, filepath: Path) -> List[str]:
        """Check required header fields"""
        violations = []
        
        # Check required fields
        for field in self.required_header_fields:
            if field not in header:
                violations.append(f"Missing required header field: {field}")
        
        # Validate suite name
        if header.get('suite') != 'Cursor Governance Suite 6 (L9 + Suite 6)':
            violations.append('Invalid suite name in header')
        
        # Validate version format
        version = header.get('version', '')
        if not re.match(r'^6\.\d+\.\d+$', version):
            violations.append('Invalid version format (must be 6.x.x)')
        
        # Validate component ID
        component_id = header.get('component_id', '')
        if component_id and not re.match(self.component_id_pattern, component_id):
            violations.append('Invalid component_id format')
        
        # Validate layer
        if header.get('layer') not in self.valid_layers:
            violations.append(f'Invalid layer: {header.get("layer")}')
        
        # Validate status
        if header.get('status') not in self.valid_statuses:
            violations.append(f'Invalid status: {header.get("status")}')
        
        return violations
    
    def _is_kebab_case(self, filename: str) -> bool:
        """Check if filename follows kebab-case convention"""
        # Remove extension
        name_without_ext = Path(filename).stem
        
        # Check kebab-case pattern (lowercase letters, numbers, hyphens)
        kebab_pattern = r'^[a-z0-9]+(-[a-z0-9]+)*$'
        return re.match(kebab_pattern, name_without_ext) is not None
    
    def _log_violations(self, filepath: Path, violations: List[str]):
        """Log violations to file"""
        timestamp = datetime.now().isoformat()
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n[{timestamp}] Violations in {filepath}:\n")
            for violation in violations:
                f.write(f"  - {violation}\n")
    
    def enforce_compliance(self) -> bool:
        """Enforce governance compliance across Suite 6"""
        self.violations = []  # Reset violations
        
        print("🔍 Enforcing Suite 6 governance compliance...")
        
        results = self.validate_all_files()
        compliant_files = sum(1 for is_compliant in results.values() if is_compliant)
        total_files = len(results)
        
        compliance_rate = (compliant_files / total_files * 100) if total_files > 0 else 100.0
        
        print(f"📊 Compliance Results:")
        print(f"   Total files: {total_files}")
        print(f"   Compliant files: {compliant_files}")
        print(f"   Compliance rate: {compliance_rate:.1f}%")
        print(f"   Violations: {len(self.violations)}")
        
        if self.violations:
            print(f"\n🚨 Violations found:")
            for violation in self.violations[:10]:  # Show first 10
                print(f"   - {violation}")
            
            if len(self.violations) > 10:
                print(f"   ... and {len(self.violations) - 10} more violations")
        
        return len(self.violations) == 0
    
    def get_compliance_report(self) -> Dict:
        """Generate detailed compliance report"""
        results = self.validate_all_files()
        compliant_files = sum(1 for is_compliant in results.values() if is_compliant)
        total_files = len(results)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'suite_version': '6.0.0',
            'total_files': total_files,
            'compliant_files': compliant_files,
            'violation_count': len(self.violations),
            'compliance_rate': (compliant_files / total_files * 100) if total_files > 0 else 100.0,
            'violations': self.violations,
            'file_results': results
        }
    
    def validate_workspace(self, workspace_path: Path) -> Dict:
        """Validate workspace governance setup"""
        workspace_path = Path(workspace_path)
        
        # Check for required workspace files
        required_files = [
            '.cursorrules',
            '.cursor-commands',
            '.suite6-config.json'
        ]
        
        missing_files = []
        for required_file in required_files:
            if not (workspace_path / required_file).exists():
                missing_files.append(required_file)
        
        # Check symlink integrity
        cursor_commands = workspace_path / '.cursor-commands'
        symlink_valid = cursor_commands.is_symlink() and cursor_commands.exists()
        
        # Check configuration
        config_valid = False
        try:
            config_path = workspace_path / '.suite6-config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    config_valid = config.get('suite_version') == '6.0.0'
        except:
            pass
        
        return {
            'workspace_path': str(workspace_path),
            'missing_files': missing_files,
            'symlink_valid': symlink_valid,
            'config_valid': config_valid,
            'governance_enabled': len(missing_files) == 0 and symlink_valid and config_valid,
            'timestamp': datetime.now().isoformat()
        }

if __name__ == '__main__':
    import sys
    
    print("🚀 Suite 6 Governance Validator")
    print("=" * 50)
    
    validator = GovernanceValidator()
    
    if '--workspace-check' in sys.argv:
        workspace_path = Path.cwd()
        if len(sys.argv) > 2:
            workspace_path = Path(sys.argv[2])
        
        print(f"🔍 Validating workspace: {workspace_path}")
        result = validator.validate_workspace(workspace_path)
        
        print(f"📊 Workspace Validation Results:")
        print(f"   Governance enabled: {result['governance_enabled']}")
        print(f"   Missing files: {result['missing_files']}")
        print(f"   Symlink valid: {result['symlink_valid']}")
        print(f"   Config valid: {result['config_valid']}")
    else:
        # Standard compliance check
        is_compliant = validator.enforce_compliance()
        
        if is_compliant:
            print("\n✅ Suite 6 governance compliance: PASSED")
            sys.exit(0)
        else:
            print("\n❌ Suite 6 governance compliance: FAILED")
            sys.exit(1)
