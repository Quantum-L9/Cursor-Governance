#!/usr/bin/env bash
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: scripts
#   owner: platform
#   status: active
#   created: 2026-07-05
#   contract: Pre-flight validation — 8 gates must pass before server start
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
FAIL=0
WARN=0

gate_pass() { echo -e "  ${GREEN}✓${NC} Gate $1: $2"; PASS=$((PASS + 1)); }
gate_fail() { echo -e "  ${RED}✗${NC} Gate $1: $2"; FAIL=$((FAIL + 1)); }
gate_warn() { echo -e "  ${YELLOW}⚠${NC} Gate $1: $2"; WARN=$((WARN + 1)); }

echo "╔══════════════════════════════════════════════════════╗"
echo "║  L9 Graphite Memory — Pre-flight Check (8 Gates)    ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Gate 1: Python version
echo "Gate 1: Python Environment"
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        gate_pass 1 "Python $PY_VER (>=3.10 required)"
    else
        gate_fail 1 "Python $PY_VER is too old (>=3.10 required)"
    fi
else
    gate_fail 1 "python3 not found"
fi

# Gate 2: Package installed
echo "Gate 2: Package Installation"
if python3 -c "import l9_graphite_memory" 2>/dev/null; then
    gate_pass 2 "l9_graphite_memory importable"
else
    gate_fail 2 "l9_graphite_memory not installed (run: pip install -e .)"
fi

# Gate 3: Infisical bootstrap vars
echo "Gate 3: Infisical Bootstrap Variables"
INFISICAL_OK=true
for var in INFISICAL_CLIENT_ID INFISICAL_CLIENT_SECRET INFISICAL_PROJECT_ID; do
    if [ -z "${!var:-}" ]; then
        INFISICAL_OK=false
    fi
done
if [ "$INFISICAL_OK" = true ]; then
    gate_pass 3 "All Infisical bootstrap vars set"
else
    # Check if ZEP_API_KEY is set directly (bypass mode)
    if [ -n "${ZEP_API_KEY:-}" ]; then
        gate_warn 3 "Infisical vars missing but ZEP_API_KEY set directly (bypass mode)"
    else
        gate_fail 3 "Missing INFISICAL_CLIENT_ID, INFISICAL_CLIENT_SECRET, or INFISICAL_PROJECT_ID"
    fi
fi

# Gate 4: Transport selection
echo "Gate 4: Transport Configuration"
TRANSPORT="${GRAPHITI_TRANSPORT:-zep}"
if [ "$TRANSPORT" = "zep" ]; then
    if [ -n "${ZEP_API_KEY:-}" ] || [ "$INFISICAL_OK" = true ]; then
        gate_pass 4 "Transport=zep (key available or Infisical will provide)"
    else
        gate_fail 4 "Transport=zep but no ZEP_API_KEY and no Infisical"
    fi
elif [ "$TRANSPORT" = "http" ]; then
    gate_pass 4 "Transport=http (legacy MCP)"
else
    gate_warn 4 "Unknown transport '$TRANSPORT' — will fall back to http"
fi

# Gate 5: Zep Python SDK
echo "Gate 5: Zep Python SDK"
if python3 -c "import zep_python" 2>/dev/null; then
    gate_pass 5 "zep-python installed"
else
    if [ "$TRANSPORT" = "zep" ]; then
        gate_fail 5 "zep-python not installed (run: pip install l9-graphite-memory[zep])"
    else
        gate_warn 5 "zep-python not installed (not needed for http transport)"
    fi
fi

# Gate 6: Infisical Python SDK
echo "Gate 6: Infisical Python SDK"
if python3 -c "import infisical_client" 2>/dev/null; then
    gate_pass 6 "infisical-python installed"
else
    if [ "$INFISICAL_OK" = true ]; then
        gate_fail 6 "infisical-python not installed but Infisical vars are set"
    else
        gate_warn 6 "infisical-python not installed (using direct env vars)"
    fi
fi

# Gate 7: Group registry
echo "Gate 7: Group Registry"
REGISTRY_PATHS=(
    "./config/group_registry.yaml"
    "../config/group_registry.yaml"
    "$HOME/.cursor/graphiti/group_registry.yaml"
)
FOUND_REGISTRY=false
for rp in "${REGISTRY_PATHS[@]}"; do
    if [ -f "$rp" ]; then
        FOUND_REGISTRY=true
        gate_pass 7 "Group registry found at $rp"
        break
    fi
done
if [ "$FOUND_REGISTRY" = false ]; then
    gate_warn 7 "No group_registry.yaml found (will use defaults)"
fi

# Gate 8: Server dry-run
echo "Gate 8: Server Import Check"
if python3 -c "from l9_graphite_memory.server import TOOL_DEFINITIONS; print(f'{len(TOOL_DEFINITIONS)} tools registered')" 2>/dev/null; then
    gate_pass 8 "Server module loads successfully"
else
    gate_fail 8 "Server module failed to import"
fi

# Summary
echo ""
echo "══════════════════════════════════════════════════════"
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${YELLOW}${WARN} warnings${NC}, ${RED}${FAIL} failed${NC}"
echo "══════════════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    echo -e "  ${RED}PREFLIGHT FAILED${NC} — resolve failures before starting server"
    exit 1
elif [ "$WARN" -gt 0 ]; then
    echo -e "  ${YELLOW}PREFLIGHT PASSED WITH WARNINGS${NC} — server may start in degraded mode"
    exit 0
else
    echo -e "  ${GREEN}PREFLIGHT PASSED${NC} — all gates clear"
    exit 0
fi
