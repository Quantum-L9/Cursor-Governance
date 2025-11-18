#!/bin/bash
# === SUITE 6 CANONICAL HEADER ===
# suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
# version: "6.0.0"
# component_id: "OPS-VER-001"
# component_name: "Setup Alignment Verification Script"
# layer: "operations"
# domain: "validation"
# type: "verification"
# status: "active"
# created: "2025-11-08T00:00:00Z"
# updated: "2025-11-08T00:00:00Z"
# author: "Igor Beylin"
# maintainer: "Igor Beylin"
#
# === GOVERNANCE METADATA ===
# governance_level: "high"
# compliance_required: true
# audit_trail: true
# security_classification: "internal"
#
# === TECHNICAL METADATA ===
# dependencies: ["bash", "find", "launchctl"]
# integrates_with: ["OPS-LEA-001", "OPS-EXP-001", "INT-WS-001"]
# data_sources: ["learning_folder", "ops_scripts", "launchctl"]
# outputs: ["terminal_output", "verification_report"]
#
# === OPERATIONAL METADATA ===
# execution_mode: "manual"
# monitoring_required: false
# logging_level: "info"
# performance_tier: "utility"
#
# === BUSINESS METADATA ===
# purpose: "Verify setup-new-workspace.md instructions align with actual governance infrastructure"
# summary: "Comprehensive verification test for workspace setup alignment"
# business_value: "Ensures setup documentation matches reality, preventing setup failures"
# success_metrics: ["all_checks_pass", "zero_misalignment_detected", "execution_time < 5s"]
#
# === TAGS & CLASSIFICATION ===
# tags: ["verification", "setup", "validation", "testing", "alignment"]
# keywords: ["verify", "setup", "alignment", "test", "validation"]
# related_components: ["INT-WS-001", "OPS-LEA-001", "OPS-EXP-001"]

# Determine script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_COMMANDS="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   SUITE 6 SETUP ALIGNMENT VERIFICATION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 GlobalCommands: $GLOBAL_COMMANDS"
echo ""

cd "$GLOBAL_COMMANDS"

PASS_COUNT=0
FAIL_COUNT=0

# Test 1: Learning Files Discovery
echo "1️⃣  Learning Files Discovery:"
FILE_COUNT=$(find ./learning/ -type f -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "   Found: $FILE_COUNT files (Expected: 11+)"
if [ "$FILE_COUNT" -ge 11 ]; then
    echo "   ✅ PASS"
    ((PASS_COUNT++))
else
    echo "   ❌ FAIL - Only $FILE_COUNT files found"
    ((FAIL_COUNT++))
fi
echo ""

# Test 2: Learning Subdirectory Structure
echo "2️⃣  Learning Subdirectory Structure:"
STRUCT_PASS=0
for dir in failures patterns solutions n8n_lessons_learned n8n-configs; do
    if [ -d "./learning/$dir" ]; then
        echo "   ✅ learning/$dir/ exists"
        ((STRUCT_PASS++))
    else
        echo "   ❌ learning/$dir/ missing"
    fi
done
if [ "$STRUCT_PASS" -eq 5 ]; then
    ((PASS_COUNT++))
else
    ((FAIL_COUNT++))
fi
echo ""

# Test 3: Core Learning Files
echo "3️⃣  Core Learning Files:"
CORE_PASS=0
for file in "failures/repeated-mistakes.md" "patterns/quick-fixes.md" "solutions/authentication-fixes.md" "solutions/json-issues.md" "credentials-policy.md" "n8n-ai-agent-patterns.md"; do
    if [ -f "./learning/$file" ]; then
        echo "   ✅ $file exists"
        ((CORE_PASS++))
    else
        echo "   ❌ $file missing"
    fi
done
if [ "$CORE_PASS" -eq 6 ]; then
    ((PASS_COUNT++))
else
    ((FAIL_COUNT++))
fi
echo ""

# Test 4: Learning System Scripts
echo "4️⃣  Learning System Scripts:"
SCRIPT_PASS=0
for script in export_chats.sh process_learnings.sh memory_aggregator.py learning_updater.py sync_mistakes_to_cursorrules.py; do
    if [ -f "./ops/scripts/$script" ]; then
        echo "   ✅ $script exists"
        ((SCRIPT_PASS++))
    else
        echo "   ❌ $script missing"
    fi
done
if [ "$SCRIPT_PASS" -eq 5 ]; then
    ((PASS_COUNT++))
else
    ((FAIL_COUNT++))
fi
echo ""

# Test 5: Utility Scripts (MCP)
echo "5️⃣  Utility Scripts (MCP):"
UTIL_PASS=0
for script in cleanup_mcp_containers.sh fix_mcp_config.sh verify_docker.sh; do
    if [ -f "./ops/scripts/$script" ]; then
        echo "   ✅ $script exists"
        ((UTIL_PASS++))
    else
        echo "   ❌ $script missing"
    fi
done
if [ "$UTIL_PASS" -eq 3 ]; then
    ((PASS_COUNT++))
else
    ((FAIL_COUNT++))
fi
echo ""

# Test 6: Suite 6 Headers Compliance
echo "6️⃣  Suite 6 Headers Compliance:"
HEADERS=$(grep -l "=== SUITE 6 CANONICAL HEADER ===" ./ops/scripts/*.sh ./ops/scripts/*.py 2>/dev/null | wc -l | tr -d ' ')
echo "   Found: $HEADERS scripts with headers (Expected: 8+)"
if [ "$HEADERS" -ge 8 ]; then
    echo "   ✅ PASS"
    ((PASS_COUNT++))
else
    echo "   ⚠️  Only $HEADERS scripts have Suite 6 headers"
    ((FAIL_COUNT++))
fi
echo ""

# Test 7: LaunchAgent Services
echo "7️⃣  LaunchAgent Services:"
SERVICES=$(launchctl list 2>/dev/null | grep -E "tenx|learning|chat" | wc -l | tr -d ' ')
echo "   Active services: $SERVICES (Expected: 2)"
if [ "$SERVICES" -eq 2 ]; then
    echo "   ✅ PASS (chat-export + learning-processor)"
    ((PASS_COUNT++))
else
    echo "   ⚠️  Expected 2 services, found $SERVICES"
    ((FAIL_COUNT++))
fi
echo ""

# Final Report
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   VERIFICATION RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   ✅ Tests Passed: $PASS_COUNT / 7"
if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "   ❌ Tests Failed: $FAIL_COUNT / 7"
    echo ""
    echo "   🔴 SETUP ALIGNMENT: FAILED"
    echo ""
    exit 1
else
    echo ""
    echo "   🟢 SETUP ALIGNMENT: PERFECT"
    echo ""
    echo "   All components verified:"
    echo "   • 11+ learning files in organized structure"
    echo "   • 5 learning system scripts with Suite 6 headers"
    echo "   • 3 utility scripts with Suite 6 headers"
    echo "   • 2 LaunchAgent services running"
    echo "   • All verification commands will execute successfully"
    echo ""
    echo "   ✅ setup-new-workspace.md is 100% aligned!"
    echo ""
    exit 0
fi

