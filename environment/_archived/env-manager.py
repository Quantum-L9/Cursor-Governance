#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "ENV-MGR-001"
component_name: "Environment Manager"
layer: "environment"
domain: "configuration_management"
type: "management_system"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "restricted"

dependencies: ["ENV-VAL-001", "ENV-LD-001"]
integrates_with: ["FND-LG-002", "EXE-API-001", "OPS-OPS-001"]

suite_2_origin: "02_env_loader.py, 03_env_validator.py"
migration_notes: "Enhanced with L9 Governance integration and comprehensive environment management"

Environment Manager v6.0
Comprehensive environment configuration management for L9 Governance
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class EnvironmentManager:
    """Comprehensive environment management for L9 Governance"""

    def __init__(self, l9_governance_root: Path = None):
        if l9_governance_root is None:
            l9_governance_root = Path(__file__).parent.parent

        self.l9_governance_root = Path(l9_governance_root)
        self.env_dir = self.l9_governance_root / "environment"
        self.logs_dir = self.env_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Configuration files
        self.master_config = self.env_dir / "master-config.json"
        self.env_file = self.env_dir / "l9_governance.env"
        self.requirements_file = self.l9_governance_root / "requirements.txt"

    def initialize_environment(self) -> dict[str, Any]:
        """Initialize L9 Governance environment configuration"""
        print("🌍 Initializing L9 Governance environment...")

        # Create master configuration
        config = {
            "suite_version": "6.0.0",
            "environment_version": "1.0.0",
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "python_version": self._get_python_version(),
            "dependencies": self._load_requirements(),
            "layers": {
                "intelligence": {"enabled": True, "path": "intelligence/"},
                "foundation": {"enabled": True, "path": "foundation/"},
                "execution": {"enabled": True, "path": "execution/"},
                "operations": {"enabled": True, "path": "operations/"},
                "environment": {"enabled": True, "path": "environment/"},
                "telemetry": {"enabled": True, "path": "telemetry/"},
            },
            "api": {"host": "localhost", "port": 8080, "debug": False, "cors_enabled": True},
            "monitoring": {"enabled": True, "log_level": "INFO", "metrics_retention_days": 30},
            "governance": {
                "compliance_required": True,
                "canonical_headers_required": True,
                "validation_on_startup": True,
            },
        }

        # Save configuration
        with open(self.master_config, "w") as f:
            json.dump(config, f, indent=2)

        print(f"✅ Master configuration created: {self.master_config}")
        return config

    def install_dependencies(self, force: bool = False) -> bool:
        """Install Python dependencies for L9 Governance"""
        print("📦 Installing L9 Governance dependencies...")

        if not self.requirements_file.exists():
            print(f"❌ Requirements file not found: {self.requirements_file}")
            return False

        try:
            # Check if dependencies are already installed
            if not force:
                missing_deps = self._check_missing_dependencies()
                if not missing_deps:
                    print("✅ All dependencies already installed")
                    return True
                print(f"📦 Missing dependencies: {missing_deps}")

            # Install dependencies
            cmd = ["pip3", "install", "-r", str(self.requirements_file)]
            if force:
                cmd.append("--force-reinstall")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Dependencies installed successfully")
                self._log_environment_action("dependencies_installed", {"success": True})
                return True
            else:
                print(f"❌ Failed to install dependencies: {result.stderr}")
                self._log_environment_action("dependencies_failed", {"error": result.stderr})
                return False

        except Exception as e:
            print(f"❌ Error installing dependencies: {e}")
            return False

    def validate_environment(self) -> dict[str, Any]:
        """Validate L9 Governance environment configuration"""
        print("🔍 Validating L9 Governance environment...")

        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "checks": {},
        }

        # Check Python version
        python_version = self._get_python_version()
        validation_results["checks"]["python_version"] = {
            "status": "pass" if python_version >= "3.9" else "fail",
            "value": python_version,
            "requirement": ">=3.9",
        }

        # Check dependencies
        missing_deps = self._check_missing_dependencies()
        validation_results["checks"]["dependencies"] = {
            "status": "pass" if not missing_deps else "fail",
            "missing": missing_deps,
            "total_required": len(self._load_requirements()),
        }

        # Check directory structure
        required_dirs = [
            "intelligence",
            "foundation",
            "execution",
            "operations",
            "environment",
            "telemetry",
        ]
        missing_dirs = [d for d in required_dirs if not (self.l9_governance_root / d).exists()]
        validation_results["checks"]["directory_structure"] = {
            "status": "pass" if not missing_dirs else "fail",
            "missing": missing_dirs,
        }

        # Check configuration files
        config_files = {
            "master_config": self.master_config.exists(),
            "requirements": self.requirements_file.exists(),
            "readme": (self.l9_governance_root / "README.md").exists(),
        }
        validation_results["checks"]["configuration_files"] = {
            "status": "pass" if all(config_files.values()) else "warn",
            "files": config_files,
        }

        # Determine overall status
        failed_checks = [
            k for k, v in validation_results["checks"].items() if v["status"] == "fail"
        ]
        if not failed_checks:
            validation_results["overall_status"] = "pass"
        elif len(failed_checks) <= 1:
            validation_results["overall_status"] = "warn"
        else:
            validation_results["overall_status"] = "fail"

        print(f"📊 Environment validation: {validation_results['overall_status'].upper()}")

        # Log validation results
        self._log_environment_action("environment_validated", validation_results)

        return validation_results

    def sync_workspace_config(self, workspace_path: Path) -> bool:
        """Sync L9 Governance configuration to workspace"""
        print(f"🔄 Syncing configuration to workspace: {workspace_path}")

        try:
            workspace_path = Path(workspace_path)

            # Create workspace configuration
            workspace_config = {
                "suite_version": "6.0.0",
                "workspace_id": f"ws-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                "workspace_path": str(workspace_path),
                "l9_governance_root": str(self.l9_governance_root),
                "governance_enabled": True,
                "intelligence_active": True,
                "monitoring_level": "standard",
                "compliance_required": True,
                "created": datetime.now().isoformat(),
                "last_validated": datetime.now().isoformat(),
                "features": {
                    "meta_learning": True,
                    "cursor_native_reasoning": True,
                    "formal_logic_validation": True,
                    "autonomous_operation": False,
                    "real_time_monitoring": False,
                },
                "api_endpoints": {
                    "governance_api": "http://localhost:8080",
                    "health_check": "http://localhost:8080/governance/health",
                    "validation": "http://localhost:8080/governance/validate",
                },
            }

            # Save workspace configuration
            config_file = workspace_path / ".l9_governance-config.json"
            with open(config_file, "w") as f:
                json.dump(workspace_config, f, indent=2)

            print(f"✅ Workspace configuration synced: {config_file}")
            return True

        except Exception as e:
            print(f"❌ Failed to sync workspace config: {e}")
            return False

    def get_environment_status(self) -> dict[str, Any]:
        """Get current environment status"""
        status = {
            "timestamp": datetime.now().isoformat(),
            "suite_version": "6.0.0",
            "environment_healthy": True,
            "python_version": self._get_python_version(),
            "dependencies_installed": len(self._check_missing_dependencies()) == 0,
            "configuration_valid": self.master_config.exists(),
            "layers_accessible": self._check_layers_accessible(),
            "api_available": self._check_api_available(),
            "last_validation": self._get_last_validation_time(),
        }

        # Determine overall health
        status["environment_healthy"] = all(
            [
                status["dependencies_installed"],
                status["configuration_valid"],
                status["layers_accessible"],
            ]
        )

        return status

    def _get_python_version(self) -> str:
        """Get Python version"""
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    def _load_requirements(self) -> list[str]:
        """Load requirements from requirements.txt"""
        if not self.requirements_file.exists():
            return []

        try:
            with open(self.requirements_file) as f:
                lines = f.readlines()

            requirements = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name (before >= or ==)
                    package = line.split(">=")[0].split("==")[0].strip()
                    requirements.append(package)

            return requirements
        except:
            return []

    def _check_missing_dependencies(self) -> list[str]:
        """Check for missing Python dependencies"""
        requirements = self._load_requirements()
        missing = []

        for package in requirements:
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing.append(package)

        return missing

    def _check_layers_accessible(self) -> bool:
        """Check if all L9 Governance layers are accessible"""
        required_layers = ["intelligence", "foundation", "execution", "operations"]
        return all((self.l9_governance_root / layer).exists() for layer in required_layers)

    def _check_api_available(self) -> bool:
        """Check if governance API is available"""
        api_file = self.l9_governance_root / "execution" / "api" / "governance-api.py"
        return api_file.exists()

    def _get_last_validation_time(self) -> str | None:
        """Get timestamp of last validation"""
        log_file = self.logs_dir / "env-activity.log"
        if not log_file.exists():
            return None

        try:
            with open(log_file) as f:
                lines = f.readlines()

            for line in reversed(lines):
                if "environment_validated" in line:
                    # Extract timestamp from log line
                    parts = line.split(" - ")
                    if len(parts) >= 2:
                        return parts[0]

            return None
        except:
            return None

    def _log_environment_action(self, action: str, data: dict[str, Any]):
        """Log environment management actions"""
        log_file = self.logs_dir / "env-activity.log"

        log_entry = {"timestamp": datetime.now().isoformat(), "action": action, "data": data}

        with open(log_file, "a") as f:
            f.write(f"{log_entry['timestamp']} - {action} - {json.dumps(data)}\n")


def main():
    """Main environment management CLI"""
    import sys

    env_manager = EnvironmentManager()

    if len(sys.argv) < 2:
        print("Usage: python env-manager.py [init|install|validate|status|sync]")
        return 1

    command = sys.argv[1]

    if command == "init":
        config = env_manager.initialize_environment()
        print(f"Environment initialized with {len(config['layers'])} layers")

    elif command == "install":
        force = "--force" in sys.argv
        success = env_manager.install_dependencies(force=force)
        return 0 if success else 1

    elif command == "validate":
        results = env_manager.validate_environment()
        return 0 if results["overall_status"] == "pass" else 1

    elif command == "status":
        status = env_manager.get_environment_status()
        print(f"Environment Status: {'HEALTHY' if status['environment_healthy'] else 'UNHEALTHY'}")
        for key, value in status.items():
            if key != "environment_healthy":
                print(f"  {key}: {value}")

    elif command == "sync":
        if len(sys.argv) < 3:
            print("Usage: python env-manager.py sync <workspace_path>")
            return 1

        workspace_path = Path(sys.argv[2])
        success = env_manager.sync_workspace_config(workspace_path)
        return 0 if success else 1

    else:
        print(f"Unknown command: {command}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
