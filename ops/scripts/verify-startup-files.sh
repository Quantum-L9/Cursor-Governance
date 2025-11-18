#!/bin/bash

# === SUITE 6 STARTUP FILE VERIFICATION SCRIPT ===
# Purpose: Verify all files required at startup are accessible
# Usage: bash .cursor-commands/ops/scripts/verify-startup-files.sh

# Don't exit on error - continue checking all files
set +e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_FILES=0
LOADED_FILES=0
MISSING_FILES=0

# Results arrays
LOADED=()
MISSING=()

echo -e "${BLUE}=== SUITE 6 STARTUP FILE VERIFICATION ===${NC}"
echo ""

# Function to check file
check_file() {
    local file_path="$1"
    local description="$2"
    local component="${3:-N/A}"
    local optional="${4:-false}"
    
    TOTAL_FILES=$((TOTAL_FILES + 1))
    
    if [ -f "$file_path" ]; then
        LOADED_FILES=$((LOADED_FILES + 1))
        LOADED+=("✅ $description")
        echo -e "${GREEN}✅${NC} $description"
        echo "   Path: $file_path"
        echo "   Component: $component"
        if [ "$optional" = "true" ]; then
            echo "   Status: OPTIONAL (present)"
        fi
        echo ""
        return 0
    else
        MISSING_FILES=$((MISSING_FILES + 1))
        if [ "$optional" = "true" ]; then
            MISSING+=("⚠️  $description (OPTIONAL)")
            echo -e "${YELLOW}⚠️${NC}  $description (OPTIONAL)"
            echo "   Path: $file_path"
            echo "   Component: $component"
            echo "   Status: OPTIONAL - not required"
        else
            MISSING+=("❌ $description")
            echo -e "${RED}❌${NC} $description"
            echo "   Path: $file_path"
            echo "   Component: $component"
            echo "   Status: MISSING"
        fi
        echo ""
        return 1
    fi
}

# Function to check directory
check_directory() {
    local dir_path="$1"
    local description="$2"
    
    TOTAL_FILES=$((TOTAL_FILES + 1))
    
    if [ -d "$dir_path" ]; then
        LOADED_FILES=$((LOADED_FILES + 1))
        LOADED+=("✅ $description")
        echo -e "${GREEN}✅${NC} $description"
        echo "   Path: $dir_path"
        
        # Count files in directory
        local file_count=$(find "$dir_path" -type f -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
        echo "   Files found: $file_count"
        echo ""
        return 0
    else
        MISSING_FILES=$((MISSING_FILES + 1))
        MISSING+=("❌ $description")
        echo -e "${RED}❌${NC} $description"
        echo "   Path: $dir_path"
        echo "   Status: MISSING"
        echo ""
        return 1
    fi
}

echo -e "${BLUE}--- CORE GOVERNANCE FILES ---${NC}"
echo ""

# Step 1: .cursorrules (optional - governance works via .suite6-config.json)
check_file ".cursorrules" "Core governance rules" "Core" "true"

# Step 2: Learning files directory
check_directory ".cursor-commands/learning" "Learning files directory (GlobalCommands)"

# Step 3: .suite6-config.json
check_file ".suite6-config.json" "Suite 6 configuration" "Config"

# Step 4: CAPABILITIES.md
check_file ".cursor-commands/startup/system_capabilities.md" "System Capabilities Manifest" "DOC-CAP-001"

echo -e "${BLUE}--- REASONING PROFILES ---${NC}"
echo ""

# Step 5: reasoning_n8n.md
check_file ".cursor-commands/profiles/reasoning_n8n.md" "n8n Reasoning Profile" "INT-RSN-001"

# Step 6: reasoning_docs.md
check_file ".cursor-commands/profiles/reasoning_docs.md" "Document Reasoning Profile" "INT-RSN-002"

# Step 7: reasoning_technical_operations.md
check_file ".cursor-commands/profiles/reasoning_technical_operations.md" "Technical Operations Reasoning Profile" "INT-RSN-003"

echo -e "${BLUE}--- OPERATING MODES ---${NC}"
echo ""

# Step 8: ynp_mode.md
check_file ".cursor-commands/profiles/ynp_mode.md" "YNP Mode Profile" "CMD-001"

# Step 9: dev_mode.md
check_file ".cursor-commands/profiles/dev_mode.md" "Dev Mode Profile" "CMD-003"

# Step 10: orchestrator.md
check_file ".cursor-commands/profiles/orchestrator.md" "Orchestrator Profile" "INT-ORC-001"

echo -e "${BLUE}--- SLASH COMMANDS ---${NC}"
echo ""

# Step 11: reasoning.md
check_file ".cursor-commands/commands/reasoning.md" "/reasoning Command" "CMD-002"

# Step 12: forge.md
check_file ".cursor-commands/commands/forge.md" "/forge Command" "CMD-004"

# Step 13: consolidate.md
check_file ".cursor-commands/commands/consolidate.md" "/consolidate Command" "CMD-005"

# Step 14: analyze.md
check_file ".cursor-commands/commands/analyze.md" "/analyze Command" "CMD-006"

# Step 15: evaluate command
check_file ".cursor-commands/commands/evaluate.md" "/evaluate Command" "CMD-007"

echo -e "${BLUE}--- SUPPORTING PROFILES ---${NC}"
echo ""

# Step 16: workflow-governance.md
check_file ".cursor-commands/profiles/workflow-governance.md" "Workflow Governance Profile" "EXE-WF-001"

# Step 17: operational-health.md
check_file ".cursor-commands/profiles/operational-health.md" "Operational Health Profile" "EXE-OP-001"

echo -e "${BLUE}--- FEATURE FILES (from .suite6-config.json) ---${NC}"
echo ""

# Step 18: meta-learning-log.md
check_file ".cursor-commands/intelligence/meta-learning/meta-learning-log.md" "Meta-Learning Log" "INT-ML-001"

# Step 19: cursor-native-reasoning.md
check_file ".cursor-commands/intelligence/reasoning/cursor-native-reasoning.md" "Cursor Native Reasoning Framework" "INT-RE-001"

# Step 20: universal-kernel.md
check_file ".cursor-commands/foundation/logic/universal-kernel.md" "Universal Kernel" "FND-LG-002"

# Step 21: rule-registry.json
check_file ".cursor-commands/foundation/logic/rule-registry.json" "Rule Registry" "FND-LG-001"

echo -e "${BLUE}--- INTELLIGENCE SYSTEMS ---${NC}"
echo ""

# Step 22: Context-memory system
check_file ".cursor-commands/intelligence/context-memory/context-extractor.py" "Context Memory Extractor" "INT-CTX-001"

# Step 23: Context memory README
check_file ".cursor-commands/intelligence/context-memory/README.md" "Context Memory Documentation" "INT-CTX-001"

# Step 24: Process context script
check_file ".cursor-commands/ops/scripts/process_context.sh" "Context Processing Script" "OPS-CTX-001"

# Step 25: Show context script
check_file ".cursor-commands/ops/scripts/show_context.sh" "Context Display Script" "OPS-CTX-001"

echo ""
echo -e "${BLUE}=== VERIFICATION SUMMARY ===${NC}"
echo ""
echo "Total files checked: $TOTAL_FILES"
echo -e "${GREEN}Loaded: $LOADED_FILES${NC}"
echo -e "${RED}Missing: $MISSING_FILES${NC}"
echo ""

# Calculate percentage
if [ $TOTAL_FILES -gt 0 ]; then
    PERCENTAGE=$((LOADED_FILES * 100 / TOTAL_FILES))
    echo "Success rate: ${PERCENTAGE}%"
    echo ""
fi

# Show missing files if any
if [ ${#MISSING[@]} -gt 0 ]; then
    echo -e "${YELLOW}=== FILES STATUS ===${NC}"
    for item in "${MISSING[@]}"; do
        echo "$item"
    done
    echo ""
    
    # Count critical missing files (non-optional)
    CRITICAL_MISSING=0
    for item in "${MISSING[@]}"; do
        if [[ "$item" != *"OPTIONAL"* ]]; then
            CRITICAL_MISSING=$((CRITICAL_MISSING + 1))
        fi
    done
    
    if [ $CRITICAL_MISSING -gt 0 ]; then
        echo -e "${RED}❌ STARTUP VERIFICATION FAILED${NC}"
        echo "$CRITICAL_MISSING critical file(s) are missing. Please check the paths above."
        exit 1
    else
        echo -e "${GREEN}✅ ALL REQUIRED STARTUP FILES VERIFIED${NC}"
        echo "Some optional files are missing, but all required files are present."
        exit 0
    fi
else
    echo -e "${GREEN}✅ ALL STARTUP FILES VERIFIED${NC}"
    echo "All $TOTAL_FILES required files are accessible and ready for startup."
    exit 0
fi

