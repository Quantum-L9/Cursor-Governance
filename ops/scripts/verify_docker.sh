#!/bin/bash
# L9_META
#   l9_schema: 1
#   artifact_type: utility
#   component: docker_verification_script
#   tags: [docker, verification, mcp, utility, infrastructure]
#   retrieval: on_demand
#   status: active
#
# Verify Docker is properly configured for n8n-mcp integration

echo "🔍 Docker Verification for n8n-mcp"
echo "=================================="
echo ""

# Check Docker version
echo "1. Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ Docker is installed: $DOCKER_VERSION"
else
    echo "❌ Docker is NOT installed"
    echo "   Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo ""

# Check if Docker daemon is running
echo "2. Checking Docker daemon status..."
if docker ps &> /dev/null; then
    echo "✅ Docker daemon is running"
    CONTAINER_COUNT=$(docker ps -q | wc -l | tr -d ' ')
    echo "   Active containers: $CONTAINER_COUNT"
else
    echo "❌ Docker daemon is NOT running"
    echo "   Please start Docker Desktop application"
    echo "   Then verify with: docker ps"
    exit 1
fi

echo ""

# Check Docker info
echo "3. Checking Docker system info..."
if docker info &> /dev/null; then
    echo "✅ Docker system is accessible"
    DOCKER_SERVER_VERSION=$(docker info 2>/dev/null | grep "Server Version" | awk '{print $3}')
    if [ ! -z "$DOCKER_SERVER_VERSION" ]; then
        echo "   Server Version: $DOCKER_SERVER_VERSION"
    fi
else
    echo "⚠️  Could not retrieve Docker system info"
fi

echo ""

# Test n8n-mcp Docker image pull
echo "4. Testing n8n-mcp Docker image availability..."
if docker pull ghcr.io/czlonkowski/n8n-mcp:latest &> /dev/null; then
    echo "✅ n8n-mcp Docker image is accessible"
else
    echo "⚠️  Could not pull n8n-mcp image (may need network connection)"
    echo "   This is OK if image is already cached locally"
fi

echo ""

# Check if image exists locally
echo "5. Checking for n8n-mcp image locally..."
if docker images | grep -q "czlonkowski/n8n-mcp"; then
    echo "✅ n8n-mcp image found locally"
    docker images | grep "czlonkowski/n8n-mcp"
else
    echo "⚠️  n8n-mcp image not found locally"
    echo "   It will be pulled automatically when first used"
fi

echo ""

# Test Docker run command (dry run)
echo "6. Testing Docker run command syntax..."
docker run --rm --help &> /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Docker run command is functional"
else
    echo "❌ Docker run command failed"
    exit 1
fi

echo ""

# Verify MCP config file exists
echo "7. Checking MCP configuration file..."
CONFIG_FILE="$HOME/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ MCP config file exists: $CONFIG_FILE"
    
    # Check if n8n-mcp is in config
    if grep -q "n8n-mcp" "$CONFIG_FILE"; then
        echo "✅ n8n-mcp is configured in MCP settings"
    else
        echo "❌ n8n-mcp NOT found in MCP config"
    fi
else
    echo "❌ MCP config file not found: $CONFIG_FILE"
    echo "   Configure MCP in Cursor settings (or recreate the Cline MCP settings file)."
fi

echo ""
echo "=================================="
echo "✅ Docker Verification Complete!"
echo ""
echo "Next steps:"
echo "1. Ensure Docker Desktop is running (check menu bar)"
echo "2. Restart Cursor completely (Cmd+Q, wait 5s, reopen)"
echo "3. Test MCP tools in a new Cursor chat"
echo ""

