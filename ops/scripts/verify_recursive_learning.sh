#!/bin/bash
#
# === SUITE 6 CANONICAL HEADER ===
# suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
# version: "1.0.0"
# component_id: "OPS-VER-RLS-001"
# component_name: "Recursive Learning System Verification"
# layer: "operations"
# domain: "verification"
# type: "verification_script"
# status: "active"
# created: "2025-11-17T22:06:00Z"
# updated: "2025-11-17T22:06:00Z"
# author: "Igor Beylin"
# maintainer: "Igor Beylin"
#
# === BUSINESS METADATA ===
# purpose: "Verify recursive learning system components are installed and running"
# summary: "Checks LaunchAgent status, verifies scripts exist, validates system health"
# business_value: "Ensures recursive learning system is operational at startup"
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GLOBAL_COMMANDS="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Component LaunchAgent names
COMPONENTS=(
    "com.cursor.pre-execution-checker:Pre-Execution Checker Daemon"
    "com.cursor.prevention-effectiveness-tracker:Prevention Effectiveness Tracker"
    "com.cursor.closed-loop-improvement:Closed-Loop Improvement"
    "com.cursor.memory-compounding:Memory Compounding"
    "com.cursor.recursive-learning-orchestrator:Recursive Learning Orchestrator"
    "com.cursor.recursive-learning-health-monitor:Health Monitor"
    "com.cursor.formal-lesson-extractor:Formal Lesson Extractor"
    "com.cursor.weekly-meta-insights:Weekly Meta-Insights"
)

# Required scripts
SCRIPTS=(
    "pre_execution_checker.py"
    "pre_execution_checker_daemon.py"
    "prevention_effectiveness_tracker.py"
    "closed_loop_improvement.py"
    "memory_compounding.py"
    "recursive_learning_orchestrator.py"
    "recursive_learning_health_monitor.py"
    "adaptive_reasoning.py"
)

echo "🔍 Recursive Learning System Verification"
echo "=========================================="
echo ""

# Check LaunchAgents
echo "📋 LaunchAgent Status:"
echo "----------------------"
ALL_RUNNING=true
MISSING_COUNT=0
STOPPED_COUNT=0

for component in "${COMPONENTS[@]}"; do
    IFS=':' read -r agent_name display_name <<< "$component"
    
    if launchctl list | grep -q "$agent_name"; then
        status=$(launchctl list | grep "$agent_name" | awk '{print $1}')
        if [ "$status" = "0" ] || [ -n "$status" ]; then
            echo "  ✅ $display_name: Running"
        else
            echo "  ⚠️  $display_name: Installed but stopped"
            STOPPED_COUNT=$((STOPPED_COUNT + 1))
            ALL_RUNNING=false
        fi
    else
        echo "  ❌ $display_name: NOT INSTALLED"
        MISSING_COUNT=$((MISSING_COUNT + 1))
        ALL_RUNNING=false
    fi
done

echo ""

# Check scripts exist
echo "📜 Script Verification:"
echo "----------------------"
ALL_SCRIPTS_EXIST=true
MISSING_SCRIPTS=()

for script in "${SCRIPTS[@]}"; do
    script_path="$GLOBAL_COMMANDS/ops/scripts/$script"
    if [ -f "$script_path" ]; then
        if [ -x "$script_path" ]; then
            echo "  ✅ $script: Exists and executable"
        else
            echo "  ⚠️  $script: Exists but not executable"
            chmod +x "$script_path" 2>/dev/null && echo "     → Fixed permissions"
        fi
    else
        echo "  ❌ $script: MISSING"
        MISSING_SCRIPTS+=("$script")
        ALL_SCRIPTS_EXIST=false
    fi
done

echo ""

# Check install scripts
echo "🔧 Install Script Verification:"
echo "-------------------------------"
INSTALL_SCRIPTS=(
    "install_pre_execution_checker.sh"
    "install_prevention_effectiveness_tracker.sh"
    "install_closed_loop_improvement.sh"
    "install_memory_compounding.sh"
    "install_recursive_learning_orchestrator.sh"
    "install_health_monitor.sh"
)

ALL_INSTALL_EXIST=true
for install_script in "${INSTALL_SCRIPTS[@]}"; do
    install_path="$GLOBAL_COMMANDS/ops/scripts/$install_script"
    if [ -f "$install_path" ]; then
        if [ -x "$install_path" ]; then
            echo "  ✅ $install_script: Ready"
        else
            echo "  ⚠️  $install_script: Not executable"
            chmod +x "$install_path" 2>/dev/null && echo "     → Fixed permissions"
        fi
    else
        echo "  ❌ $install_script: MISSING"
        ALL_INSTALL_EXIST=false
    fi
done

echo ""

# Check critical files
echo "📁 Critical Files:"
echo "-----------------"
CRITICAL_FILES=(
    "learning/failures/repeated-mistakes.md"
    "ops/logs/memory_index.json"
    "ops/logs/pattern_weights.json"
)

for file in "${CRITICAL_FILES[@]}"; do
    file_path="$GLOBAL_COMMANDS/$file"
    if [ -f "$file_path" ]; then
        echo "  ✅ $file: Exists"
    else
        echo "  ⚠️  $file: Missing (will be created on first run)"
    fi
done

echo ""

# Summary
echo "═══════════════════════════════════════════════════"
echo "📊 Verification Summary:"
echo "═══════════════════════════════════════════════════"

if [ "$ALL_RUNNING" = true ] && [ "$ALL_SCRIPTS_EXIST" = true ] && [ "$ALL_INSTALL_EXIST" = true ]; then
    echo "✅ ALL SYSTEMS OPERATIONAL"
    echo ""
    echo "   LaunchAgents: All running"
    echo "   Scripts: All present and executable"
    echo "   Install Scripts: All ready"
    echo ""
    echo "🎯 Recursive Learning System is READY"
    exit 0
else
    echo "⚠️  ISSUES DETECTED"
    echo ""
    
    if [ "$MISSING_COUNT" -gt 0 ]; then
        echo "   ❌ $MISSING_COUNT LaunchAgent(s) not installed"
        echo "      Run install scripts to fix:"
        echo "      cd \"$GLOBAL_COMMANDS\""
        echo "      bash ops/scripts/install_pre_execution_checker.sh"
        echo "      bash ops/scripts/install_prevention_effectiveness_tracker.sh"
        echo "      bash ops/scripts/install_closed_loop_improvement.sh"
        echo "      bash ops/scripts/install_memory_compounding.sh"
        echo "      bash ops/scripts/install_recursive_learning_orchestrator.sh"
        echo "      bash ops/scripts/install_health_monitor.sh"
        echo ""
    fi
    
    if [ "$STOPPED_COUNT" -gt 0 ]; then
        echo "   ⚠️  $STOPPED_COUNT LaunchAgent(s) stopped"
        echo "      Reload with: launchctl load ~/Library/LaunchAgents/com.cursor.*.plist"
        echo ""
    fi
    
    if [ ${#MISSING_SCRIPTS[@]} -gt 0 ]; then
        echo "   ❌ Missing scripts: ${MISSING_SCRIPTS[*]}"
        echo ""
    fi
    
    echo "🔧 To install all components:"
    echo "   cd \"$GLOBAL_COMMANDS\""
    echo "   bash ops/scripts/install_pre_execution_checker.sh"
    echo "   bash ops/scripts/install_prevention_effectiveness_tracker.sh"
    echo "   bash ops/scripts/install_closed_loop_improvement.sh"
    echo "   bash ops/scripts/install_memory_compounding.sh"
    echo "   bash ops/scripts/install_recursive_learning_orchestrator.sh"
    echo "   bash ops/scripts/install_health_monitor.sh"
    echo ""
    
    exit 1
fi

