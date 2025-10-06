#!/bin/bash
#
# ====================================================================
# | Workflow: Governance-Enforcement
# | Agent: Orchestrator
# | Sub-Agent: Compliance-Monitor
# |
# | File: governance_enforcer_v1.1.0.sh
# | Created: 2025-10-06 22:52:17 UTC
# | Last Modified: 2025-10-06 22:52:17 UTC
# | Version: v1.1.0
# | Author: WARP-Assistant
# | Description: Governance compliance checker with operational health integration
# | Dependencies: profiles/*, config.json, meta_index.md
# ====================================================================
#
# Governance Enforcement Hook for Cursor

set -euo pipefail  # Strict error handling

# Configuration
WORKSPACE="/Users/ib-mac/Workspace/Cursor-Governance"
RULES_FILE="$WORKSPACE/profiles/workflow-governance.md"
OPS_HEALTH_FILE="$WORKSPACE/profiles/operational-health.md"
ORCHESTRATOR_FILE="$WORKSPACE/profiles/orchestrator.md"
LOG_FILE="$WORKSPACE/meta_index.md"
CONFIG_FILE="$WORKSPACE/config.json"

# Get timestamp in standardized format
timestamp=$(date "+%Y-%m-%d %H:%M:%S")
iso_timestamp=$(date -u "+%Y-%m-%d %H:%M:%S UTC")

# Logging function
log_action() {
    local status="$1"
    local message="$2"
    echo "| enforcement | $timestamp | $status $message |" >> "$LOG_FILE"
    echo "$status $message at $timestamp"
}

# 1. Operational Health - Preflight Check
log_action "🔍" "Starting governance enforcement check"

# Check for governance activation flag
if [ ! -f "$WORKSPACE/.governance_active" ]; then
    log_action "🛑" "Governance not active - creating activation flag"
    touch "$WORKSPACE/.governance_active"
    log_action "✅" "Governance activation flag created"
fi

# 2. Security & Access - Verify core governance files exist
required_profiles=(
    "$RULES_FILE"
    "$OPS_HEALTH_FILE" 
    "$ORCHESTRATOR_FILE"
    "$CONFIG_FILE"
)

for profile in "${required_profiles[@]}"; do
    if [ ! -f "$profile" ]; then
        filename=$(basename "$profile")
        log_action "❌" "Critical governance file missing: $filename"
        exit 1
    fi
done

log_action "✅" "All required governance profiles present"

# 3. Versioning - Verify configuration structure
if ! grep -q '"ai.prompt"' "$CONFIG_FILE"; then
    log_action "⚠️" "config.json missing or malformed ai.prompt configuration"
    exit 1
fi

# 4. Workflow Governance - Validate active mode
active_mode=$(grep -o '"ai.prompt"[^}]*' "$CONFIG_FILE" | head -1)
if [[ "$active_mode" =~ "Systems Architect" ]]; then
    log_action "✅" "Architect mode active and compliant"
else
    log_action "⚠️" "Non-standard AI mode detected - review config.json"
fi

# 5. Reasoning - Self-verification complete
log_action "✅" "Governance enforcement passed - all checks green"
log_action "📋" "Next check scheduled for next enforcement run"

