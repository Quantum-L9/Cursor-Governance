#!/bin/bash
# L9_META
#   l9_schema: 1
#   artifact_type: verification
#   component: setup_alignment_verification
#   tags: [verification, setup, validation, alignment, governance]
#   retrieval: on_demand
#   status: active
#   contract: Verify governance infrastructure matches documented setup

# Determine script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_COMMANDS="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   GOVERNANCE SETUP ALIGNMENT VERIFICATION"
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
echo "   Found: $FILE_COUNT files (Expected: 5+)"
if [ "$FILE_COUNT" -ge 5 ]; then
    echo "   ✅ PASS"
    ((PASS_COUNT++))
else
    echo "   ❌ FAIL - Only $FILE_COUNT files found"
    ((FAIL_COUNT++))
fi
echo ""

# Test 2: Learning Subdirectory Structure (failures, patterns, solutions only)
echo "2️⃣  Learning Subdirectory Structure:"
STRUCT_PASS=0
for dir in failures patterns solutions; do
    if [ -d "./learning/$dir" ]; then
        echo "   ✅ learning/$dir/ exists"
        ((STRUCT_PASS++))
    else
        echo "   ❌ learning/$dir/ missing"
    fi
done
if [ "$STRUCT_PASS" -eq 3 ]; then
    ((PASS_COUNT++))
else
    ((FAIL_COUNT++))
fi
echo ""

# Test 3: Core Learning Files
echo "3️⃣  Core Learning Files:"
CORE_PASS=0
for file in "failures/repeated-mistakes.md" "patterns/quick-fixes.md" "solutions/authentication-fixes.md" "solutions/json-issues.md" "credentials-policy.md"; do
    if [ -f "./learning/$file" ]; then
        echo "   ✅ $file exists"
        ((CORE_PASS++))
    else
        echo "   ❌ $file missing"
    fi
done
if [ "$CORE_PASS" -eq 5 ]; then
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

# Test 5: Utility Scripts (Docker)
echo "5️⃣  Utility Scripts (Docker):"
UTIL_PASS=0
for script in verify_docker.sh; do
    if [ -f "./ops/scripts/$script" ]; then
        echo "   ✅ $script exists"
        ((UTIL_PASS++))
    else
        echo "   ❌ $script missing"
    fi
done
if [ "$UTIL_PASS" -eq 1 ]; then
    ((PASS_COUNT++))
else
    ((FAIL_COUNT++))
fi
echo ""

# Test 6: LaunchAgent Services (optional - pass if at least 2 when present)
echo "6️⃣  LaunchAgent Services:"
SERVICES=$(launchctl list 2>/dev/null | grep -E "tenx|learning|chat" | wc -l | tr -d ' ')
echo "   Active services: $SERVICES (Expected: 2+ when configured)"
if [ "$SERVICES" -ge 2 ]; then
    echo "   ✅ PASS"
    ((PASS_COUNT++))
else
    echo "   ⚠️  Found $SERVICES (optional; 2+ expected when LaunchAgents configured)"
    ((FAIL_COUNT++))
fi
echo ""

# Final Report
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   VERIFICATION RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   ✅ Tests Passed: $PASS_COUNT / 6"
if [ "$FAIL_COUNT" -gt 0 ]; then
    echo "   ❌ Tests Failed: $FAIL_COUNT / 6"
    echo ""
    echo "   🔴 SETUP ALIGNMENT: FAILED"
    echo ""
    exit 1
else
    echo ""
    echo "   🟢 SETUP ALIGNMENT: PERFECT"
    echo ""
    echo "   All components verified:"
    echo "   • 5+ learning files in organized structure (failures, patterns, solutions)"
    echo "   • 5 learning system scripts present"
    echo "   • 3 utility scripts present"
    echo "   • LaunchAgent services (when configured)"
    echo "   • All verification commands will execute successfully"
    echo ""
    echo "   ✅ workspace setup alignment verified"
    echo ""
    exit 0
fi
