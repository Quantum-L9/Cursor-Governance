#!/bin/bash
# L9_META
#   l9_schema: 1
#   artifact_type: utility
#   component: mcp_configuration_fix_script
#   tags: [mcp, configuration, fix, utility, cursor]
#   retrieval: on_demand
#   status: active
#
# Ensure MCP configuration is properly set up for Cursor

CONFIG_DIR="$HOME/Library/Application Support/Cursor/User/globalStorage/saoudrizwan.claude-dev/settings"
CONFIG_FILE="$CONFIG_DIR/cline_mcp_settings.json"

echo "🔧 Fixing MCP Configuration..."
echo ""

# Create directory if missing
mkdir -p "$CONFIG_DIR"
echo "✅ Directory created: $CONFIG_DIR"

# Backup existing config
if [ -f "$CONFIG_FILE" ]; then
    BACKUP_FILE="$CONFIG_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo "✅ Backed up existing config to: $BACKUP_FILE"
fi

# Create/update config file
cat > "$CONFIG_FILE" << 'EOF'
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "MCP_MODE=stdio",
        "-e",
        "LOG_LEVEL=error",
        "-e",
        "DISABLE_CONSOLE_OUTPUT=true",
        "-e",
        "N8N_API_URL=https://ibeylin.app.n8n.cloud/",
        "-e",
        "N8N_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGRkNDc4OC1hYTU4LTRhZDctYTljYS05YmQxOTY4MDUzYTEiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwiaWF0IjoxNzYwMzAzMzg0fQ.5hhJ5zuorxdAtAKfRnACPslF0wDqWZBaEQ92msdqC08",
        "ghcr.io/czlonkowski/n8n-mcp:latest"
      ]
    },
    "n8n-workflows Docs": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://gitmcp.io/Zie619/n8n-workflows"
      ]
    },
    "Context7": {
      "command": "npx",
      "args": [
        "-y",
        "@upstash/context7-mcp"
      ]
    },
    "firecrawl-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "firecrawl-mcp"
      ],
      "env": {
        "FIRECRAWL_API_KEY": "fc-5fd9a72545ae49a787712f1c7e48b142"
      }
    },
    "Playwright": {
      "command": "npx",
      "args": [
        "-y",
        "@playwright/mcp@latest"
      ]
    },
    "supabase": {
      "type": "http",
      "url": "https://mcp.supabase.com/mcp?project_ref=ebprgdlzzeoinrvdcfwx",
      "name": "Supabase MCP (project-scoped)"
    },
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/ib-mac/Dropbox/**Agent Constellation (SM)/Agents/*Logistics Agent - Linda/Freight Rate Sub-Agent copy/Json Files"
      ]
    },
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-github"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_YOUR_TOKEN_HERE"
      }
    },
    "postgres": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres"
      ],
      "env": {
        "DATABASE_URL": "postgresql://postgres:KJP_xam5pvj%2Angd_tkm@db.ebprgdlzzeoinrvdcfwx.supabase.co:5432/postgres"
      }
    }
  }
}
EOF

echo "✅ MCP configuration file created/updated at:"
echo "   $CONFIG_FILE"
echo ""

# Validate JSON syntax
if command -v python3 &> /dev/null; then
    if python3 -m json.tool "$CONFIG_FILE" > /dev/null 2>&1; then
        echo "✅ JSON syntax is valid"
    else
        echo "❌ JSON syntax error detected!"
        exit 1
    fi
fi

echo ""
echo "📋 Verification Checklist:"
echo ""

# Check Docker
if command -v docker &> /dev/null; then
    if docker ps &> /dev/null; then
        echo "✅ Docker is installed and running"
    else
        echo "⚠️  Docker is installed but not running (start Docker Desktop)"
    fi
else
    echo "❌ Docker is not installed (required for n8n-mcp)"
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node.js installed: $NODE_VERSION"
else
    echo "❌ Node.js is not installed (required for most MCP servers)"
fi

# Check npx
if command -v npx &> /dev/null; then
    echo "✅ npx is available"
else
    echo "❌ npx is not available (required for most MCP servers)"
fi

echo ""
echo "⚠️  IMPORTANT: Restart Cursor completely for changes to take effect"
echo "   1. Quit Cursor (Cmd+Q)"
echo "   2. Wait 5 seconds"
echo "   3. Reopen Cursor"
echo "   4. Test MCP tools in a new chat"

