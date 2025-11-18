#!/usr/bin/env python3
"""
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "FND-SEC-001"
component_name: "Governance Integrity Manager"
layer: "foundation"
domain: "security"
type: "integrity_system"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"
governance_level: "critical"
purpose: "Digital signature and integrity protection for governance files"

# === GOVERNANCE METADATA ===
compliance_required: true
audit_trail: true
security_classification: "restricted"

# === TECHNICAL METADATA ===
dependencies: ["hashlib", "pathlib", "json"]
integrates_with: ["FND-AG-002", "EXE-VAL-001", "FND-LG-001"]
api_endpoints: ["/api/v1/integrity/hash", "/api/v1/integrity/verify"]
data_sources: ["foundation/", "intelligence/", "execution/"]
outputs: ["foundation/security/signatures/", "telemetry/logs/integrity.log"]

# === OPERATIONAL METADATA ===
execution_mode: "autonomous"
monitoring_required: true
logging_level: "info"
performance_tier: "realtime"

# === BUSINESS METADATA ===
business_value: "Ensures governance file integrity and prevents tampering"
success_metrics: ["hash_generation_time < 50ms", "verification_accuracy = 100%", "tamper_detection = 100%"]

# === INTEGRATION METADATA ===
constellation_origin: "GovernanceSnapshotHash.js"
migration_notes: "Ported from JavaScript to Python with enhanced Suite 6 integration"

# === TAGS & CLASSIFICATION ===
tags: ["security", "integrity", "hashing", "digital_signature", "constellation_port"]
keywords: ["hash", "signature", "integrity", "security", "verification"]
related_components: ["FND-AG-002", "EXE-VAL-001"]
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

class GovernanceIntegrityManager:
    """
    Digital Signature and Integrity Protection System for Suite 6
    
    Provides SHA256 hashing, signature generation, and integrity verification
    for all governance files. Based on Constellation's GovernanceSnapshotHash.js
    """
    
    def __init__(self, suite_root: str = None):
        self.suite_root = Path(suite_root) if suite_root else Path(__file__).parent.parent.parent
        self.signatures_dir = self.suite_root / "foundation" / "security" / "signatures"
        self.signatures_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
    def generate_file_hash(self, file_path: str) -> str:
        """
        Generate SHA256 hash for a file
        Based on Constellation's GovernanceSnapshotHash.js
        """
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            hash_obj = hashlib.sha256()
            hash_obj.update(file_content)
            return hash_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"Error generating hash for {file_path}: {e}")
            return None
    
    def create_signature_record(self, file_path: str, signer_id: str = "Suite6_System") -> Dict:
        """
        Create digital signature record for a governance file
        """
        file_hash = self.generate_file_hash(file_path)
        if not file_hash:
            return None
            
        signature_record = {
            "file": os.path.basename(file_path),
            "full_path": str(Path(file_path).resolve()),
            "hash": file_hash,
            "algorithm": "SHA256",
            "signed_by": signer_id,
            "signed_on": datetime.now().isoformat(),
            "suite_version": "6.0.0",
            "file_size": os.path.getsize(file_path),
            "signature_version": "1.0"
        }
        
        return signature_record
    
    def save_signature(self, file_path: str, signature_record: Dict) -> bool:
        """
        Save signature record to signatures directory
        """
        try:
            file_name = os.path.basename(file_path)
            signature_file = self.signatures_dir / f"{file_name}.sig.json"
            
            with open(signature_file, 'w') as f:
                json.dump(signature_record, f, indent=2)
            
            self.logger.info(f"Signature saved for {file_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving signature for {file_path}: {e}")
            return False
    
    def verify_file_integrity(self, file_path: str) -> Tuple[bool, Dict]:
        """
        Verify file integrity against stored signature
        """
        try:
            file_name = os.path.basename(file_path)
            signature_file = self.signatures_dir / f"{file_name}.sig.json"
            
            if not signature_file.exists():
                return False, {
                    "status": "no_signature",
                    "message": f"No signature found for {file_name}",
                    "file": file_name
                }
            
            # Load stored signature
            with open(signature_file, 'r') as f:
                stored_signature = json.load(f)
            
            # Generate current hash
            current_hash = self.generate_file_hash(file_path)
            if not current_hash:
                return False, {
                    "status": "hash_error",
                    "message": f"Could not generate hash for {file_name}",
                    "file": file_name
                }
            
            # Compare hashes
            stored_hash = stored_signature.get("hash", "")
            integrity_valid = current_hash == stored_hash
            
            result = {
                "status": "valid" if integrity_valid else "tampered",
                "file": file_name,
                "stored_hash": stored_hash,
                "current_hash": current_hash,
                "signed_by": stored_signature.get("signed_by", "unknown"),
                "signed_on": stored_signature.get("signed_on", "unknown"),
                "integrity_valid": integrity_valid
            }
            
            if not integrity_valid:
                result["message"] = "File has been modified since signing"
                self.logger.warning(f"Integrity violation detected for {file_name}")
            
            return integrity_valid, result
            
        except Exception as e:
            self.logger.error(f"Error verifying integrity for {file_path}: {e}")
            return False, {
                "status": "verification_error",
                "message": str(e),
                "file": os.path.basename(file_path)
            }
    
    def sign_governance_file(self, file_path: str, signer_id: str = "Suite6_System") -> bool:
        """
        Complete signing process for a governance file
        """
        signature_record = self.create_signature_record(file_path, signer_id)
        if signature_record:
            return self.save_signature(file_path, signature_record)
        return False
    
    def sign_all_governance_files(self, signer_id: str = "Suite6_System") -> Dict[str, bool]:
        """
        Sign all governance files in Suite 6
        """
        results = {}
        
        # Define governance file patterns
        governance_patterns = [
            "**/*.md",  # All markdown files
            "**/*.json",  # All JSON files
            "**/*.py"   # All Python files
        ]
        
        # Scan governance directories
        governance_dirs = [
            "intelligence",
            "foundation", 
            "execution",
            "operations",
            "environment"
        ]
        
        for dir_name in governance_dirs:
            dir_path = self.suite_root / dir_name
            if dir_path.exists():
                for pattern in governance_patterns:
                    for file_path in dir_path.glob(pattern):
                        if file_path.is_file() and self._is_governance_file(file_path):
                            success = self.sign_governance_file(str(file_path), signer_id)
                            results[str(file_path.relative_to(self.suite_root))] = success
        
        return results
    
    def _is_governance_file(self, file_path: Path) -> bool:
        """
        Check if file is a governance file that should be signed
        """
        # Skip certain files
        skip_patterns = [
            ".DS_Store",
            "__pycache__",
            ".pyc",
            ".log",
            ".tmp",
            ".sig.json",  # Don't sign signature files
            "debug-gap-analysis.py",
            "suite6-constellation-integration",
            "cleanup-pre-commit.sh"
        ]
        
        file_name = file_path.name
        for pattern in skip_patterns:
            if pattern in file_name:
                return False
        
        # Check for Suite 6 canonical header (for .md and .py files)
        if file_path.suffix in ['.md', '.py']:
            try:
                with open(file_path, 'r') as f:
                    content = f.read(1000)  # Read first 1000 chars
                    return "=== SUITE 6 CANONICAL HEADER ===" in content
            except:
                return False
        
        # Include all JSON files in governance directories
        if file_path.suffix == '.json':
            return True
            
        return False
    
    def verify_all_signatures(self) -> Dict:
        """
        Verify integrity of all signed governance files
        """
        verification_results = {
            "total_files": 0,
            "valid_files": 0,
            "tampered_files": 0,
            "missing_signatures": 0,
            "verification_errors": 0,
            "details": []
        }
        
        # Check all signature files
        for sig_file in self.signatures_dir.glob("*.sig.json"):
            try:
                with open(sig_file, 'r') as f:
                    signature = json.load(f)
                
                original_file = signature.get("full_path", "")
                if os.path.exists(original_file):
                    is_valid, result = self.verify_file_integrity(original_file)
                    
                    verification_results["total_files"] += 1
                    verification_results["details"].append(result)
                    
                    if result["status"] == "valid":
                        verification_results["valid_files"] += 1
                    elif result["status"] == "tampered":
                        verification_results["tampered_files"] += 1
                    else:
                        verification_results["verification_errors"] += 1
                        
            except Exception as e:
                verification_results["verification_errors"] += 1
                self.logger.error(f"Error processing signature file {sig_file}: {e}")
        
        # Calculate integrity percentage
        if verification_results["total_files"] > 0:
            verification_results["integrity_percentage"] = (
                verification_results["valid_files"] / verification_results["total_files"] * 100
            )
        else:
            verification_results["integrity_percentage"] = 0
        
        return verification_results
    
    def get_signature_status(self, file_path: str) -> Dict:
        """
        Get signature status for a specific file
        """
        file_name = os.path.basename(file_path)
        signature_file = self.signatures_dir / f"{file_name}.sig.json"
        
        if not signature_file.exists():
            return {
                "signed": False,
                "file": file_name,
                "message": "No signature found"
            }
        
        try:
            with open(signature_file, 'r') as f:
                signature = json.load(f)
            
            is_valid, verification = self.verify_file_integrity(file_path)
            
            return {
                "signed": True,
                "file": file_name,
                "signature": signature,
                "verification": verification,
                "integrity_valid": is_valid
            }
            
        except Exception as e:
            return {
                "signed": True,
                "file": file_name,
                "error": str(e),
                "message": "Error reading signature"
            }

def main():
    """CLI interface for governance integrity management"""
    if len(sys.argv) < 2:
        print("Usage: python governance-integrity.py <command> [args]")
        print("Commands:")
        print("  hash <file_path> - Generate SHA256 hash for file")
        print("  sign <file_path> [signer_id] - Sign a governance file")
        print("  verify <file_path> - Verify file integrity")
        print("  sign-all [signer_id] - Sign all governance files")
        print("  verify-all - Verify all signed files")
        print("  status <file_path> - Get signature status for file")
        return
    
    manager = GovernanceIntegrityManager()
    command = sys.argv[1]
    
    if command == "hash" and len(sys.argv) > 2:
        file_path = sys.argv[2]
        file_hash = manager.generate_file_hash(file_path)
        if file_hash:
            print(f"SHA256 Hash for {file_path}: {file_hash}")
        else:
            print(f"Error generating hash for {file_path}")
    
    elif command == "sign" and len(sys.argv) > 2:
        file_path = sys.argv[2]
        signer_id = sys.argv[3] if len(sys.argv) > 3 else "Suite6_System"
        
        success = manager.sign_governance_file(file_path, signer_id)
        if success:
            print(f"✅ Successfully signed {file_path}")
        else:
            print(f"❌ Failed to sign {file_path}")
    
    elif command == "verify" and len(sys.argv) > 2:
        file_path = sys.argv[2]
        is_valid, result = manager.verify_file_integrity(file_path)
        
        status_icon = "✅" if is_valid else "❌"
        print(f"{status_icon} Verification result for {file_path}:")
        print(json.dumps(result, indent=2))
    
    elif command == "sign-all":
        signer_id = sys.argv[2] if len(sys.argv) > 2 else "Suite6_System"
        
        print("Signing all governance files...")
        results = manager.sign_all_governance_files(signer_id)
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        print(f"Signed {success_count}/{total_count} files successfully")
        
        for file_path, success in results.items():
            status = "✅" if success else "❌"
            print(f"  {status} {file_path}")
    
    elif command == "verify-all":
        print("Verifying all signed governance files...")
        results = manager.verify_all_signatures()
        
        print(f"Verification Summary:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Valid: {results['valid_files']} ✅")
        print(f"  Tampered: {results['tampered_files']} ❌")
        print(f"  Errors: {results['verification_errors']} ⚠️")
        print(f"  Integrity: {results['integrity_percentage']:.1f}%")
        
        if results['tampered_files'] > 0:
            print("\nTampered files:")
            for detail in results['details']:
                if detail['status'] == 'tampered':
                    print(f"  ❌ {detail['file']}")
    
    elif command == "status" and len(sys.argv) > 2:
        file_path = sys.argv[2]
        status = manager.get_signature_status(file_path)
        
        print(f"Signature status for {file_path}:")
        print(json.dumps(status, indent=2))
    
    else:
        print("Invalid command or missing arguments")

if __name__ == "__main__":
    main()
