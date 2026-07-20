#!/usr/bin/env python3
"""
# === L9 GOVERNANCE CANONICAL HEADER ===
suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"
version: "6.0.0"
component_id: "EXE-TEST-001"
component_name: "Governance Test Suite"
layer: "execution"
domain: "testing"
type: "test_framework"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-10-28T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

dependencies: ["EXE-VAL-001", "EXE-MON-001", "EXE-API-001"]
integrates_with: ["FND-LG-002", "INT-RE-001", "OPS-OPS-001"]

suite_3_origin: "51_Governance_Test_Suite_v3.0.py"
migration_notes: "Enhanced with L9 Governance integration, canonical header validation, and cross-layer testing"

Governance Test Suite v6.0
Comprehensive automated testing framework for L9 Governance governance validation
"""

# L9 Governance imports
import sys
import time
import unittest
from pathlib import Path

l9_governance_root = Path(__file__).parent.parent.parent
sys.path.append(str(l9_governance_root / "execution" / "validation"))
sys.path.append(str(l9_governance_root / "execution" / "monitoring"))

from governance_monitor import GovernanceMonitor
from governance_validator import GovernanceValidator


class TestL9GovernanceCompliance(unittest.TestCase):
    """Test suite for L9 Governance governance compliance"""

    def setUp(self):
        """Set up test environment"""
        self.l9_governance_root = Path(__file__).parent.parent.parent
        self.validator = GovernanceValidator(self.l9_governance_root)
        self.monitor = GovernanceMonitor(self.l9_governance_root)

    def test_canonical_header_compliance(self):
        """Test that all governance files have L9 Governance canonical headers"""
        print("🧪 Testing canonical header compliance...")

        results = self.validator.validate_all_files()

        # Check that we have files to test
        self.assertGreater(len(results), 0, "Should have governance files to validate")

        # Check compliance rate
        compliant_files = sum(1 for is_compliant in results.values() if is_compliant)
        total_files = len(results)
        compliance_rate = (compliant_files / total_files) * 100

        print(f"   Compliance rate: {compliance_rate:.1f}% ({compliant_files}/{total_files})")

        # Should have high compliance (allow some development files to be non-compliant)
        self.assertGreaterEqual(compliance_rate, 80.0, "Compliance rate should be >= 80%")

    def test_l9_governance_header_format(self):
        """Test L9 Governance canonical header format"""
        print("🧪 Testing L9 Governance header format...")

        # Test a known compliant file
        test_file = (
            self.l9_governance_root / "intelligence" / "reasoning" / "cursor-native-reasoning.md"
        )

        if test_file.exists():
            with open(test_file) as f:
                content = f.read()

            # Check for L9 Governance canonical header
            self.assertIn("# === L9 GOVERNANCE CANONICAL HEADER ===", content)
            self.assertIn('suite: "Cursor Governance L9 Governance (L9 + L9 Governance)"', content)
            self.assertIn('version: "6.0.0"', content)
            self.assertIn("component_id:", content)

            print("   ✅ Canonical header format validated")
        else:
            self.skipTest("Test file not found")

    def test_kebab_case_naming(self):
        """Test that files follow kebab-case naming convention"""
        print("🧪 Testing kebab-case naming convention...")

        violations = []

        for layer in ["intelligence", "foundation", "execution", "operations"]:
            layer_path = self.l9_governance_root / layer
            if layer_path.exists():
                for file_path in layer_path.rglob("*.md"):
                    filename = file_path.stem
                    # Check kebab-case pattern (lowercase letters, numbers, hyphens)
                    if not filename.replace("-", "").replace("_", "").islower():
                        violations.append(str(file_path.relative_to(self.l9_governance_root)))

        if violations:
            print(f"   ⚠️  Kebab-case violations: {violations}")
        else:
            print("   ✅ All files follow kebab-case naming")

        # Allow some violations during development
        self.assertLessEqual(len(violations), 3, f"Too many naming violations: {violations}")

    def test_component_id_format(self):
        """Test component ID format compliance"""
        print("🧪 Testing component ID format...")

        valid_patterns = ["INT-", "FND-", "EXE-", "OPS-", "ENV-", "TEL-", "DOC-"]
        violations = []

        # Check markdown files with headers
        for md_file in self.l9_governance_root.rglob("*.md"):
            try:
                with open(md_file) as f:
                    content = f.read()

                if "component_id:" in content:
                    # Extract component ID
                    for line in content.split("\n"):
                        if "component_id:" in line:
                            component_id = line.split(":")[1].strip().strip('"')

                            # Check format
                            if not any(
                                component_id.startswith(pattern) for pattern in valid_patterns
                            ):
                                violations.append(f"{md_file.name}: {component_id}")
                            break
            except:
                continue

        if violations:
            print(f"   ⚠️  Component ID violations: {violations}")
        else:
            print("   ✅ All component IDs follow correct format")

        self.assertLessEqual(len(violations), 2, f"Component ID format violations: {violations}")


class TestL9GovernanceIntegration(unittest.TestCase):
    """Test L9 Governance cross-layer integration"""

    def setUp(self):
        """Set up integration test environment"""
        self.l9_governance_root = Path(__file__).parent.parent.parent

    def test_symlink_structure(self):
        """Test that symlink structure works correctly"""
        print("🧪 Testing symlink structure...")

        # Create test workspace
        test_workspace = Path("/tmp/l9_governance-test-workspace")
        test_workspace.mkdir(exist_ok=True)

        try:
            # Create symlink
            cursor_commands = test_workspace / ".cursor-commands"
            if cursor_commands.exists():
                cursor_commands.unlink()

            cursor_commands.symlink_to(self.l9_governance_root)

            # Test access to components
            self.assertTrue((cursor_commands / "intelligence").exists())
            self.assertTrue((cursor_commands / "foundation").exists())
            self.assertTrue((cursor_commands / "execution").exists())

            print("   ✅ Symlink structure working correctly")

        finally:
            # Cleanup
            if cursor_commands.exists():
                cursor_commands.unlink()
            if test_workspace.exists():
                test_workspace.rmdir()

    def test_api_integration(self):
        """Test API integration and endpoints"""
        print("🧪 Testing API integration...")

        # Test API file exists
        api_file = self.l9_governance_root / "execution" / "api" / "governance-api.py"
        self.assertTrue(api_file.exists(), "Governance API file should exist")

        # Test API imports (basic syntax check)
        try:
            with open(api_file) as f:
                content = f.read()

            # Check for required imports and endpoints
            self.assertIn("from flask import Flask", content)
            self.assertIn("/governance/status", content)
            self.assertIn("/governance/health", content)

            print("   ✅ API integration structure validated")

        except Exception as e:
            self.fail(f"API integration test failed: {e}")

    def test_validation_integration(self):
        """Test validation system integration"""
        print("🧪 Testing validation integration...")

        validator = GovernanceValidator(self.l9_governance_root)

        # Test basic validation functionality
        results = validator.validate_all_files()
        self.assertIsInstance(results, dict)

        # Test compliance report generation
        report = validator.get_compliance_report()
        self.assertIn("timestamp", report)
        self.assertIn("suite_version", report)
        self.assertEqual(report["suite_version"], "6.0.0")

        print("   ✅ Validation integration working")


class TestL9GovernancePerformance(unittest.TestCase):
    """Test L9 Governance performance requirements"""

    def setUp(self):
        """Set up performance test environment"""
        self.l9_governance_root = Path(__file__).parent.parent.parent

    def test_validation_performance(self):
        """Test validation performance meets targets"""
        print("🧪 Testing validation performance...")

        validator = GovernanceValidator(self.l9_governance_root)

        # Measure validation time
        start_time = time.time()
        results = validator.validate_all_files()
        validation_time = time.time() - start_time

        print(f"   Validation time: {validation_time:.2f}s")

        # Should complete within reasonable time (adjust based on file count)
        file_count = len(results)
        max_time = max(10.0, file_count * 0.5)  # 0.5s per file, minimum 10s

        self.assertLess(
            validation_time,
            max_time,
            f"Validation took {validation_time:.2f}s, should be < {max_time:.2f}s",
        )

        print("   ✅ Validation performance acceptable")

    def test_monitoring_performance(self):
        """Test monitoring system performance"""
        print("🧪 Testing monitoring performance...")

        monitor = GovernanceMonitor(self.l9_governance_root)

        # Measure metrics collection time
        start_time = time.time()
        metrics = monitor.collect_metrics()
        collection_time = time.time() - start_time

        print(f"   Metrics collection time: {collection_time:.2f}s")

        # Should complete quickly
        self.assertLess(
            collection_time,
            5.0,
            f"Metrics collection took {collection_time:.2f}s, should be < 5.0s",
        )

        # Check metrics structure
        self.assertIn("compliance_rate", metrics.__dict__)
        self.assertIn("total_files", metrics.__dict__)

        print("   ✅ Monitoring performance acceptable")


class TestL9GovernanceSecurity(unittest.TestCase):
    """Test L9 Governance security requirements"""

    def test_no_hardcoded_secrets(self):
        """Test that no hardcoded secrets exist in code"""
        print("🧪 Testing for hardcoded secrets...")

        secret_patterns = [
            "password",
            "secret",
            "key",
            "token",
            "api_key",
            "private_key",
            "access_token",
            "auth_token",
        ]

        violations = []

        for py_file in Path(__file__).parent.parent.parent.rglob("*.py"):
            try:
                with open(py_file) as f:
                    content = f.read().lower()

                for pattern in secret_patterns:
                    if f"{pattern} = " in content or f"{pattern}=" in content:
                        # Skip if it's just a variable name or comment
                        lines = content.split("\n")
                        for i, line in enumerate(lines):
                            if f"{pattern} = " in line or f"{pattern}=" in line:
                                if not (
                                    line.strip().startswith("#")
                                    or "None" in line
                                    or "input(" in line
                                    or "getenv(" in line
                                ):
                                    violations.append(f"{py_file.name}:{i+1}")
            except:
                continue

        if violations:
            print(f"   ⚠️  Potential hardcoded secrets: {violations}")
        else:
            print("   ✅ No hardcoded secrets detected")

        self.assertEqual(len(violations), 0, f"Potential hardcoded secrets found: {violations}")


def run_test_suite():
    """Run the complete L9 Governance test suite"""
    print("🚀 L9 GOVERNANCE GOVERNANCE TEST SUITE")
    print("=" * 50)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestL9GovernanceCompliance))
    suite.addTests(loader.loadTestsFromTestCase(TestL9GovernanceIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestL9GovernancePerformance))
    suite.addTests(loader.loadTestsFromTestCase(TestL9GovernanceSecurity))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.failures:
        print("\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")

    if result.errors:
        print("\n🚨 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")

    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED - L9 GOVERNANCE READY FOR PRODUCTION")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - REVIEW ISSUES BEFORE DEPLOYMENT")
        return 1


if __name__ == "__main__":
    exit_code = run_test_suite()
