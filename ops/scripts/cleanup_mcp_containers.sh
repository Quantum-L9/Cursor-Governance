#!/bin/bash
# === L9 GOVERNANCE CANONICAL HEADER ===
# suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
# version: "6.0.0"
# component_id: "OPS-MCP-001"
# component_name: "MCP Container Cleanup Script"
# layer: "operations"
# domain: "infrastructure"
# type: "utility"
# status: "active"
# created: "2025-11-04T20:18:00Z"
# updated: "2025-11-08T00:00:00Z"
# author: "Igor Beylin"
# maintainer: "Igor Beylin"
#
# === GOVERNANCE METADATA ===
# governance_level: "medium"
# compliance_required: false
# audit_trail: false
# security_classification: "internal"
#
# === TECHNICAL METADATA ===
# dependencies: ["docker", "bash"]
# integrates_with: ["docker", "n8n-mcp"]
# data_sources: ["docker_ps"]
# outputs: ["terminal_output"]
#
# === OPERATIONAL METADATA ===
# execution_mode: "manual"
# monitoring_required: false
# logging_level: "info"
# performance_tier: "utility"
#
# === BUSINESS METADATA ===
# purpose: "Remove stale n8n-mcp Docker containers that may interfere with MCP tools"
# summary: "Cleanup script for n8n-mcp Docker containers"
# business_value: "Prevents MCP configuration issues caused by stale containers"
# success_metrics: ["cleanup_success_rate >= 95%", "no_active_containers_removed"]
#
# === TAGS & CLASSIFICATION ===
# tags: ["docker", "mcp", "cleanup", "utility", "infrastructure"]
# keywords: ["docker", "n8n-mcp", "cleanup", "containers"]
# related_components: ["OPS-MCP-002", "OPS-MCP-003"]

echo "🧹 Cleaning up old n8n-mcp containers..."
echo ""

# Find all n8n-mcp containers
CONTAINERS=$(docker ps -a --filter "ancestor=ghcr.io/czlonkowski/n8n-mcp:latest" --format "{{.ID}} {{.Status}}")

if [ -z "$CONTAINERS" ]; then
    echo "✅ No n8n-mcp containers found"
    exit 0
fi

echo "Found containers:"
echo "$CONTAINERS"
echo ""

# Stop and remove containers
echo "$CONTAINERS" | while read id status; do
    if [ ! -z "$id" ]; then
        echo "Stopping container: $id ($status)"
        docker stop "$id" 2>/dev/null
        docker rm "$id" 2>/dev/null
        echo "  ✅ Removed"
    fi
done

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "⚠️  Please restart Cursor completely (Cmd+Q, wait 5 seconds, reopen)"
echo "   Cursor will start fresh containers with correct configuration"

