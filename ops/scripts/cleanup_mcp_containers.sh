#!/bin/bash
# L9_META
#   l9_schema: 1
#   artifact_type: utility
#   component: mcp_container_cleanup_script
#   tags: [docker, mcp, cleanup, utility, infrastructure]
#   retrieval: on_demand
#   status: active
#
# Remove stale n8n-mcp Docker containers that may interfere with MCP tools

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

