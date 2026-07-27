#!/usr/bin/env bash
# L9_META
#   l9_schema: 1
#   artifact_type: orchestrator
#   component: learning_processing_pipeline
#   tags: [learning, pipeline, orchestration, automation, intelligence]
#   retrieval: on_demand
#   status: active
#
# Orchestrate learning extraction from chat exports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/learning_processing.log"
LAST_RUN_FILE="$SCRIPT_DIR/../logs/learning_processing.lastrun"

# Check if we should run (catch-up logic for missed scheduled runs)
SHOULD_RUN=true
if [ -f "$LAST_RUN_FILE" ]; then
    LAST_RUN=$(cat "$LAST_RUN_FILE")
    CURRENT_TIME=$(date +%s)
    TIME_SINCE_LAST_RUN=$((CURRENT_TIME - LAST_RUN))
    HOURS_SINCE_LAST_RUN=$((TIME_SINCE_LAST_RUN / 3600))
    
    # Only run if it's been more than 20 hours since last run (allows for daily schedule)
    if [ "$HOURS_SINCE_LAST_RUN" -lt 20 ]; then
        SHOULD_RUN=false
        echo "[$(date)] Skipping run - last run was $HOURS_SINCE_LAST_RUN hours ago (less than 20 hours)" >> "$LOG_FILE"
    fi
fi

if [ "$SHOULD_RUN" = false ]; then
    exit 0
fi

echo "[$(date)] ========================================" >> "$LOG_FILE"
echo "[$(date)] Starting Learning Processing Pipeline" >> "$LOG_FILE"

# Step 1: Run Memory Aggregator
echo "[$(date)] Step 1/7: Running Memory Aggregator..." >> "$LOG_FILE"
python3 "$SCRIPT_DIR/memory_aggregator.py" >> "$LOG_FILE" 2>&1

# Step 2: Apply learnings to files
echo "[$(date)] Step 2/7: Updating Learning Files..." >> "$LOG_FILE"
python3 "$SCRIPT_DIR/learning_updater.py" >> "$LOG_FILE" 2>&1

# Step 3: Sync to meta-learning log (NEW - CRITICAL)
echo "[$(date)] Step 3/7: Syncing to Meta-Learning Log..." >> "$LOG_FILE"
python3 "$SCRIPT_DIR/sync_to_meta_learning.py" >> "$LOG_FILE" 2>&1

# Step 4: Sync to .cursorrules for auto-loading
echo "[$(date)] Step 4/7: Syncing to .cursorrules..." >> "$LOG_FILE"
python3 "$SCRIPT_DIR/sync_mistakes_to_cursorrules.py" >> "$LOG_FILE" 2>&1

# Step 5: Refresh pre-execution checker cache (NEW - Recursive Learning)
echo "[$(date)] Step 5/7: Refreshing Pre-Execution Checker Cache..." >> "$LOG_FILE"
python3 "$SCRIPT_DIR/pre_execution_checker.py" >> "$LOG_FILE" 2>&1 || echo "[$(date)] Warning: Pre-execution checker refresh failed" >> "$LOG_FILE"

# Step 6: Update memory compounding weights (NEW - Recursive Learning)
echo "[$(date)] Step 6/7: Updating Memory Compounding Weights..." >> "$LOG_FILE"
python3 "$SCRIPT_DIR/memory_compounding.py" --evolve >> "$LOG_FILE" 2>&1 || echo "[$(date)] Warning: Memory compounding update failed" >> "$LOG_FILE"

# Step 7: Scan and audit learning folder additions (NEW - Audit)
echo "[$(date)] Step 7/7: Auditing Learning Folder Additions..." >> "$LOG_FILE"
python3 "$SCRIPT_DIR/intelligence_audit_logger.py" --scan >> "$LOG_FILE" 2>&1 || echo "[$(date)] Warning: Learning audit scan failed" >> "$LOG_FILE"

echo "[$(date)] Learning Processing Pipeline Complete" >> "$LOG_FILE"
echo "[$(date)] ========================================" >> "$LOG_FILE"

# Record successful run timestamp
date +%s > "$LAST_RUN_FILE"

