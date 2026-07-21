#!/usr/bin/env bash
# L9_META
#   l9_schema: 1
#   repo: Quantum-L9/L9-Graphite-Memory
#   layer: scripts
#   owner: platform
#   status: active
#   created: 2026-07-05
#   contract: Activate memory gate hooks in a target repo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
    echo "Usage: activate_gate.sh <target_repo_path> [--hooks-only] [--dry-run]"
    echo ""
    echo "Activates L9 Graphite Memory gate hooks in a target repository."
    echo ""
    echo "What it does:"
    echo "  1. Copies graphiti-*.sh hooks to target repo's .cursor/hooks/"
    echo "  2. Copies .cursorrules memory integration rules"
    echo "  3. Registers the repo in group_registry.yaml"
    echo "  4. Runs autoseed-check to verify graph connectivity"
    echo ""
    echo "Options:"
    echo "  --hooks-only  Only install hooks, skip registry and autoseed"
    echo "  --dry-run     Show what would be done without making changes"
    exit 1
}

[ $# -lt 1 ] && usage

TARGET_REPO="$1"
HOOKS_ONLY=false
DRY_RUN=false

shift
while [ $# -gt 0 ]; do
    case "$1" in
        --hooks-only) HOOKS_ONLY=true ;;
        --dry-run) DRY_RUN=true ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
    shift
done

if [ ! -d "$TARGET_REPO" ]; then
    echo "ERROR: Target repo not found: $TARGET_REPO"
    exit 1
fi

TARGET_REPO="$(cd "$TARGET_REPO" && pwd)"
REPO_NAME="$(basename "$TARGET_REPO")"

echo "╔══════════════════════════════════════════════════════╗"
echo "║  L9 Graphite Memory — Gate Activation               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Target: $TARGET_REPO"
echo "  Repo:   $REPO_NAME"
echo ""

# Step 1: Install hooks
echo "→ Step 1: Installing memory hooks..."
HOOKS_SRC="$REPO_ROOT/hooks"
HOOKS_DST="$TARGET_REPO/.cursor/hooks"

if [ "$DRY_RUN" = true ]; then
    echo "  [DRY RUN] Would copy hooks from $HOOKS_SRC to $HOOKS_DST"
else
    mkdir -p "$HOOKS_DST"
    if [ -d "$HOOKS_SRC" ] && [ "$(ls -A "$HOOKS_SRC" 2>/dev/null)" ]; then
        cp -v "$HOOKS_SRC"/graphiti-*.sh "$HOOKS_DST/" 2>/dev/null || true
        chmod +x "$HOOKS_DST"/graphiti-*.sh 2>/dev/null || true
        echo "  ✓ Hooks installed"
    else
        echo "  ⚠ No hooks found in $HOOKS_SRC"
    fi
fi
echo ""

# Step 2: Install rules
echo "→ Step 2: Installing memory rules..."
RULES_SRC="$REPO_ROOT/rules"
RULES_DST="$TARGET_REPO/.cursor/rules"

if [ "$DRY_RUN" = true ]; then
    echo "  [DRY RUN] Would copy rules from $RULES_SRC to $RULES_DST"
else
    mkdir -p "$RULES_DST"
    if [ -d "$RULES_SRC" ] && [ "$(ls -A "$RULES_SRC" 2>/dev/null)" ]; then
        cp -v "$RULES_SRC"/*.mdc "$RULES_DST/" 2>/dev/null || true
        echo "  ✓ Rules installed"
    else
        echo "  ⚠ No rules found in $RULES_SRC"
    fi
fi
echo ""

if [ "$HOOKS_ONLY" = true ]; then
    echo "  ✓ Hooks-only mode — skipping registry and autoseed"
    exit 0
fi

# Step 3: Register in group registry
echo "→ Step 3: Registering in group registry..."
REGISTRY="$REPO_ROOT/config/group_registry.yaml"

if [ "$DRY_RUN" = true ]; then
    echo "  [DRY RUN] Would add '$REPO_NAME' to $REGISTRY"
else
    if [ -f "$REGISTRY" ]; then
        if grep -q "^  $REPO_NAME:" "$REGISTRY" 2>/dev/null; then
            echo "  ✓ Already registered"
        else
            echo "  Adding $REPO_NAME to registry..."
            cat >> "$REGISTRY" << EOF

  $REPO_NAME:
    github: "$(cd "$TARGET_REPO" && git remote get-url origin 2>/dev/null || echo 'UNKNOWN')"
    integrates_with: []
EOF
            echo "  ✓ Registered"
        fi
    else
        echo "  ⚠ Registry not found at $REGISTRY"
    fi
fi
echo ""

# Step 4: Autoseed check
echo "→ Step 4: Running autoseed check..."
if [ "$DRY_RUN" = true ]; then
    echo "  [DRY RUN] Would run: l9-memory autoseed-check --group-id $REPO_NAME"
else
    if command -v l9-memory &>/dev/null; then
        cd "$TARGET_REPO"
        l9-memory autoseed-check --group-id "$REPO_NAME" 2>/dev/null || echo "  ⚠ Autoseed check returned non-zero (may need bootstrap)"
    else
        echo "  ⚠ l9-memory CLI not in PATH — skip autoseed"
    fi
fi
echo ""

echo "╔══════════════════════════════════════════════════════╗"
echo "║  ✓ Gate activation complete for: $REPO_NAME"
echo "╚══════════════════════════════════════════════════════╝"
