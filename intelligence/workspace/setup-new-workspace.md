---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "INT-WS-001"
component_name: "Workspace Setup System"
layer: "intelligence"
domain: "workspace_management"
type: "deployment_system"
status: "active"
created: "2025-10-28T00:00:00Z"
updated: "2025-01-27T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: ["ENV-LD-001"]
integrates_with: ["FND-LG-002", "EXE-API-001", "EXE-VAL-001"]
api_endpoints: ["/api/v1/workspace/setup", "/api/v1/workspace/validate"]
data_sources: ["environment/master-config.json", "foundation/logic/rule-registry.json"]
outputs: ["workspace/.cursorrules", "workspace/.cursor-commands/", "workspace/.suite6-config.json"]

# === OPERATIONAL METADATA ===
execution_mode: "manual"
monitoring_required: false
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Make Suite 6 governance system available in ANY Cursor workspace with one command"
summary: "Universal workspace deployment system that creates governance-enabled development environments"
business_value: "Enables rapid governance adoption across all development projects"
success_metrics: ["setup_success_rate >= 99%", "setup_time < 30s", "workspace_compliance = 100%"]

# === INTEGRATION METADATA ===
suite_2_origin: "SETUP_NEW_WORKSPACE.md"
migration_notes: "Enhanced with Suite 6 structure, Python environment manager, and automated governance deployment"

# === TAGS & CLASSIFICATION ===
tags: ["workspace_setup", "deployment", "governance_enablement", "cursor_integration"]
keywords: ["workspace", "setup", "deployment", "governance", "cursor"]
related_components: ["ENV-LD-001", "FND-LG-002", "EXE-API-001", "EXE-VAL-001"]
---

# Setup New Workspace - Suite 6 Quick Guide

**Purpose:** Make Suite 6 governance & learning system available in ANY Cursor workspace

---

## STEP 1: Preflight Check

**Before starting, verify:**

```bash
# 1. Check if Suite 6 exists
test -d "/Users/ib-mac/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9)" && echo "✅ Suite 6 found" || echo "❌ Suite 6 not found"

# 2. Check Python 3 installed
python3 --version
# Expected: Python 3.8 or higher

# 3. Check required Python packages
python3 -c "import yaml" 2>&1 && echo "✅ yaml installed" || echo "❌ yaml missing - will install"

# 4. Verify you're in your workspace
pwd
# Should be: /path/to/your/workspace
```

**If yaml missing:**
```bash
python3 -m pip install pyyaml
```

**✅ Success Check**: All commands return ✅ or show expected output

---

## STEP 1.5: Load All Learning Files (MANDATORY)

**⚠️ CRITICAL: At EVERY session start, read ALL files in `.cursor-commands/learning/` (GlobalCommands learning folder) recursively:**

```bash
# Discover all learning files recursively from GlobalCommands
find .cursor-commands/learning/ -type f -name "*.md" | sort

# Expected structure (GlobalCommands learning folder - Suite 6 v6.0):
# .cursor-commands/learning/credentials-policy.md
# .cursor-commands/learning/failures/repeated-mistakes.md
# .cursor-commands/learning/l9-ai-agent-patterns.md
# .cursor-commands/learning/l9_lessons_learned/Recursive_Self_Check_Protocol.md
# .cursor-commands/learning/patterns/quick-fixes.md
# .cursor-commands/learning/solutions/authentication-fixes.md
# .cursor-commands/learning/solutions/json-issues.md
# Expected: 7+ files across organized subdirectories
```

**MANDATORY Session Initialization Sequence:**

```
1. READ: .cursorrules (workspace root) AND @.cursor-commands/templates/.cursorrules
   └─ Purpose: Core governance rules and standards (workspace-specific AND GlobalCommands template)
   └─ Duration: 1 minute (both files)
   └─ Skip: NEVER
   └─ Note: Read BOTH files to ensure complete governance coverage

2. READ: ALL files in .cursor-commands/learning/ folder (recursive, GlobalCommands)
   └─ Purpose: Load ALL learning files from GlobalCommands (failures, patterns, solutions, L9 lessons)
   └─ Method: Read every .md file found recursively in .cursor-commands/learning/
   └─ Duration: 2-3 minutes (all files)
   └─ Skip: NEVER
   └─ Note: This is the GlobalCommands learning folder (via symlink)

3. CHECK: .suite6-config.json
   └─ Purpose: Verify governance enabled
   └─ Duration: 5 seconds
   └─ Skip: Only if checked in last 10 minutes

4. READ: @.cursor-commands/profiles/reasoning_l9.md
   └─ Purpose: Enable L9-specific reasoning capabilities
   └─ Mode Type: Reasoning
   └─ Component: INT-RSN-001
   └─ Duration: 2 minutes
   └─ Skip: NEVER
   └─ Use For: Building/debugging L9 orchestration, selecting L9 tools

5. READ: @.cursor-commands/profiles/reasoning_docs.md
   └─ Purpose: Enable strategic document reasoning capabilities
   └─ Mode Type: Reasoning
   └─ Component: INT-RSN-002
   └─ Duration: 2 minutes
   └─ Skip: NEVER
   └─ Use For: Document analysis, gap detection, strategic insights

6. READ: @.cursor-commands/profiles/reasoning_technical_operations.md
   └─ Purpose: Enable technical operations reasoning capabilities
   └─ Mode Type: Reasoning
   └─ Component: INT-RSN-003
   └─ Duration: 2 minutes
   └─ Skip: NEVER
   └─ Use For: Tool selection, API integration, architecture decisions

7. READ: @.cursor-commands/profiles/ynp_mode.md
   └─ Purpose: Enable YNP (Your Next Prompt) Mode - strategic co-pilot operation
   └─ Mode Type: YNP
   └─ Component: CMD-001
   └─ Duration: 1 minute
   └─ Skip: NEVER

8. READ: @.cursor-commands/profiles/dev_mode.md
   └─ Purpose: Enable Development Automation Mode - code analysis, module management, testing
   └─ Mode Type: Dev Mode
   └─ Component: CMD-003
   └─ Duration: 1 minute
   └─ Skip: NEVER

9. READ: @.cursor-commands/profiles/orchestrator.md
   └─ Purpose: Enable governance orchestration and coordination
   └─ Mode Type: Orchestration
   └─ Component: INT-ORC-001
   └─ Duration: 30 seconds
   └─ Skip: NEVER

10. READ: @.cursor-commands/commands/reasoning.md
   └─ Purpose: Enable /reasoning slash command - L9 Multi-Modal Reasoning
   └─ Mode Type: Command
   └─ Component: CMD-002
   └─ Duration: 2 minutes
   └─ Skip: NEVER
   └─ Use For: Activating reasoning mode with /reasoning command

11. READ: @.cursor-commands/commands/forge.md
   └─ Purpose: Enable /forge slash command - Heavy Forge Mode
   └─ Mode Type: Command
   └─ Component: CMD-004
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: Autonomous high-velocity execution with /forge command

12. READ: @.cursor-commands/commands/consolidate.md
   └─ Purpose: Enable /consolidate slash command
   └─ Mode Type: Command
   └─ Component: CMD-005
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: File consolidation and organization

13. READ: @.cursor-commands/commands/analyze-toolkit.md
   └─ Purpose: Enable /analyze-toolkit slash command
   └─ Mode Type: Command
   └─ Component: CMD-006
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: Complete toolkit analysis

14. READ: @.cursor-commands/commands/evaluate- Comprehensive Project Evaluation.md
   └─ Purpose: Enable /evaluate slash command
   └─ Mode Type: Command
   └─ Component: CMD-007
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: Comprehensive project evaluation

15. READ: @.cursor-commands/profiles/workflow-governance.md
   └─ Purpose: Enable L9 orchestration governance (referenced by orchestrator and reasoning profiles)
   └─ Mode Type: Validation
   └─ Component: EXE-WF-001
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: L9 orchestration validation and governance

16. READ: @.cursor-commands/profiles/operational-health.md
   └─ Purpose: System health monitoring (referenced by orchestrator and reasoning profiles)
   └─ Mode Type: Monitoring
   └─ Component: EXE-OP-001
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: Operational health checks and monitoring

17. READ: @.cursor-commands/intelligence/standards/production-quality-standards.md
   └─ Purpose: Production quality standards and verification directives (MANDATORY)
   └─ Mode Type: Quality Standards
   └─ Component: INT-QS-001
   └─ Duration: 3 minutes
   └─ Skip: NEVER
   └─ Use For: All builds, all code, all deliverables - defines quality baseline

18. READ: @.cursor-commands/intelligence/meta-learning/meta-learning-log.md
   └─ Purpose: Meta-learning log (enabled in .suite6-config.json: meta_learning: true)
   └─ Mode Type: Learning System
   └─ Component: INT-ML-001
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: Capturing patterns, insights, and learning from interactions

19. READ: @.cursor-commands/intelligence/reasoning/cursor-native-reasoning.md
   └─ Purpose: 10-step reasoning framework (enabled in .suite6-config.json: cursor_native_reasoning: true)
   └─ Mode Type: Reasoning Engine
   └─ Component: INT-RE-001
   └─ Duration: 2 minutes
   └─ Skip: NEVER
   └─ Use For: Structured technical evaluation and decision-making framework

20. READ: @.cursor-commands/foundation/logic/probabilistic_engine.py
   └─ Purpose: Probabilistic governance reasoning engine (NEW in v6.1.0)
   └─ Mode Type: Inference Engine
   └─ Component: FND-PE-001
   └─ Duration: 2 minutes
   └─ Skip: NEVER
   └─ Use For: Risk assessment, calibrated decisions, uncertainty quantification

21. READ: @.cursor-commands/foundation/logic/universal-kernel.md
   └─ Purpose: Formal logic validation kernel (enabled in .suite6-config.json: formal_logic_validation: true)
   └─ Mode Type: Kernel
   └─ Component: FND-LG-002
   └─ Duration: 1 minute
   └─ Skip: NEVER
   └─ Use For: Governance rule enforcement and formal logic validation

22. READ: @.cursor-commands/foundation/logic/rule-registry.json
   └─ Purpose: Rule registry for formal validation (enabled in .suite6-config.json: formal_logic_validation: true)
   └─ Mode Type: Registry
   └─ Component: FND-LG-003 (v6.1.0 - includes probabilistic models and thresholds)
   └─ Duration: 30 seconds
   └─ Skip: NEVER
   └─ Use For: Governance rules, validation rules, and probabilistic model configuration
```

**Verification**: Post confirmation after loading
```
✅ Session initialized
   - Governance rules loaded (.cursorrules workspace root AND GlobalCommands template)
   - ALL GlobalCommands learning files loaded (.cursor-commands/learning/ - recursive)
   - Production Quality Standards LOADED (INT-QS-001 - 24 directives active)
   - Reasoning Mode ENABLED (L9, docs, technical operations)
   - YNP Mode ENABLED (strategic co-pilot)
   - Dev Mode ENABLED (development automation)
   - Orchestrator ENABLED (governance coordination)
   - Slash Commands ENABLED (/reasoning, /forge, /consolidate, /analyze-toolkit, /evaluate)
   - Supporting Profiles ENABLED (workflow-governance, operational-health)
   - Feature Files ENABLED (meta-learning, cursor-native-reasoning, formal-logic-validation, probabilistic-reasoning)
   - Suite 6 governance: ACTIVE (v6.1.0 with probabilistic reasoning)
```

**✅ Success Check**: All learning files from GlobalCommands read and accessible

---

## STEP 1.6: Load Standard Operating Modes (MANDATORY)

**⚠️ CRITICAL: At EVERY session start, load reasoning profiles and standard operating modes:**

### Reasoning Profiles (Enable Advanced Reasoning Capabilities)

**These three profiles enable domain-specific reasoning:**

1. **reasoning_l9.md** - L9 Agent Reasoning Profile
   - **When to use:** Building L9 orchestration, debugging agents, selecting L9 tools
   - **Capabilities:** Workflow design, node selection, MCP tool selection protocol
   - **Component:** INT-RSN-001

2. **reasoning_docs.md** - Strategic Document Reasoning Profile
   - **When to use:** Analyzing documents, finding gaps, generating strategic insights
   - **Capabilities:** Chain-of-thought analysis, pattern recognition, coherence checking
   - **Component:** INT-RSN-002

3. **reasoning_technical_operations.md** - Technical Operations Reasoning Profile
   - **When to use:** Tool selection, API integration, architecture decisions
   - **Capabilities:** Tool evaluation, API assessment, infrastructure decisions
   - **Component:** INT-RSN-003

### Standard Operating Modes

**These modes enable core operational capabilities:**

4. **ynp_mode.md** - YNP Mode (Your Next Prompt)
   - **Purpose:** Strategic co-pilot operation with autonomous next-prompt generation
   - **Component:** CMD-001

5. **dev_mode.md** - Dev Mode
   - **Purpose:** Development automation for code analysis, module management, testing
   - **Component:** CMD-003

6. **orchestrator.md** - Governance Orchestrator
   - **Purpose:** Central coordination for all governance layers
   - **Component:** INT-ORC-001

**✅ Success Check**: All reasoning profiles and operating modes loaded and accessible

---

## STEP 2: Installation

**From your workspace directory, run:**

```bash
# Navigate to your workspace
cd /path/to/your/workspace

# Run Suite 6 setup (use actual path - Suite 6 (L9), not Suite 6 (L9 + Suite 6))
python3 "/Users/ib-mac/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9)/environment/env-manager.py" sync "$(pwd)"
```

**Expected Output:**
```
🔄 Syncing configuration to workspace: /path/to/your/workspace
✅ Workspace configuration synced: /path/to/your/workspace/.suite6-config.json
```

**✅ Success Check**: `.suite6-config.json` file created in workspace root

---

## STEP 3: Configuration

**Create symlinks to governance files:**

```bash
# Create .cursor-commands symlink (use Dropbox GlobalCommands, not Library)
bash "/Users/ib-mac/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9)/ops/scripts/setup_workspace_symlinks.sh"
```

**Expected Output:**
```
🔧 Setting up workspace symlinks...
✅ SUCCESS! Symlink created
📁 You can now access:
   @.cursor-commands/learning/failures/repeated-mistakes.md
   @.cursor-commands/profiles/reasoning.md
```

**Verify symlink points to correct location:**
```bash
ls -la .cursor-commands
# Expected: .cursor-commands -> ~/.cursor-governance
```

**⚠️ IMPORTANT**: Governance SSOT is `~/.cursor-governance` (Dropbox is legacy fallback, not Library)
- ✅ Correct: `~/.cursor-governance`
- ❌ Wrong: `~/Library/Application Support/Cursor/GlobalCommands`

**If symlink points to wrong location:**
```bash
# Remove incorrect symlink
rm .cursor-commands

# Create correct symlink to the SSOT
ln -s ~/.cursor-governance .cursor-commands

# Verify
ls -la .cursor-commands
```

**✅ Success Check**: Symlink points to the SSOT `~/.cursor-governance` (not Library)

---

## STEP 3.5: Activate Learning System

**Trigger the learning system to process any existing chat exports:**

```bash
# Run the learning processor manually to activate the system
bash ~/.cursor-governance/ops/scripts/process_learnings.sh
```

**Expected Output:**
```
[Date Time] ========================================
[Date Time] Starting Learning Processing Pipeline
[Date Time] Step 1/2: Running Memory Aggregator...
🚀 Memory Aggregator v2.0.0 - Starting...

📂 Found X chat export directories
✅ Processing complete! Total learnings: X

[Date Time] Step 2/3: Updating Learning Files...
📚 Learning File Updater v1.0.0 - Starting...
✅ No pending learnings to apply

[Date Time] Step 3/3: Syncing to .cursorrules...
🔄 Syncing repeated mistakes to .cursorrules...
✅ Synced X mistakes to .cursorrules
📝 File: /Users/ib-mac/.cursorrules
[Date Time] Learning Processing Pipeline Complete
[Date Time] ========================================
```

**What This Does:**
- ✅ Processes all existing chat exports from Cursor
- ✅ Extracts learnings (mistakes, solutions, patterns)
- ✅ Updates learning files in `.cursor-commands/learning/`
- ✅ Syncs repeated mistakes to `.cursorrules` for AI auto-loading
- ✅ Creates/updates `ops/logs/memory_index.json`

**Verify Learning System Status:**
```bash
# Check if LaunchAgents are running (automatic hourly processing)
launchctl list | grep -E "tenx|learning|chat"

# Expected output:
# -    0    com.tenx.learning-processor
# -    0    com.tenx.chat-export

# View recent learning activity
tail -30 .cursor-commands/ops/logs/learning_processing.log

# Check learning statistics
cat .cursor-commands/ops/logs/memory_index.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Exports: {d[\"stats\"][\"total_exports_processed\"]}'); print(f'Conversations: {d[\"stats\"][\"total_conversations\"]}'); print(f'Learnings: {d[\"stats\"][\"total_learnings_extracted\"]}');"
```

**Learning System Components:**

| Component | Status | Schedule | Purpose | Location |
|-----------|--------|----------|---------|----------|
| **Chat Export** (OPS-EXP-001) | ✅ Hourly | Every 3600s | Exports Cursor chat data | ops/scripts/export_chats.sh |
| **Learning Processor** (OPS-LEA-001) | ✅ Hourly | Every 3600s | Extracts patterns & learnings | ops/scripts/process_learnings.sh |
| **Memory Aggregator** (OPS-AGG-001) | ✅ Auto | On-demand | Parses chat exports | ops/scripts/memory_aggregator.py |
| **Learning Updater** (OPS-UPD-001) | ✅ Auto | On-demand | Updates learning files | ops/scripts/learning_updater.py |
| **Cursorrules Sync** (OPS-SYN-001) | ✅ Auto | On-demand | Syncs to .cursorrules | ops/scripts/sync_mistakes_to_cursorrules.py |

**Utility Scripts (Suite 6 Compliant):**
| Component | ID | Purpose | Location |
|-----------|-----|---------|----------|
| **MCP Cleanup** | OPS-MCP-001 | Remove stale l9-mcp containers | ops/scripts/cleanup_mcp_containers.sh |
| **MCP Config Fix** | OPS-MCP-002 | Repair MCP configuration | ops/scripts/fix_mcp_config.sh |
| **Docker Verify** | OPS-MCP-003 | Verify Docker setup | ops/scripts/verify_docker.sh |

**✅ Success Check**: 
- Learning pipeline completes without errors
- LaunchAgents show status code `0` (running)
- Learning files updated in `.cursor-commands/learning/`
- Memory index created/updated

---

## STEP 4: Validation

**Quick Verification Script:**
```bash
# Run automated startup file verification
bash .cursor-commands/ops/scripts/verify-startup-files.sh
```

**Expected Output:**
```
✅ ALL REQUIRED STARTUP FILES VERIFIED
All 20 required files are accessible and ready for startup.
```

**Manual Verification - Verify governance files are accessible:**

```bash
# Check Suite 6 config
cat .suite6-config.json | grep -E "(governance_enabled|intelligence_active)"
# Expected: "governance_enabled": true, "intelligence_active": true

# Check symlink access
ls .cursor-commands/profiles
# Expected: List of profile files (reasoning_l9.md, orchestrator.md, etc.)

# Check learning files (GlobalCommands learning folder)
ls .cursor-commands/learning
# Expected: failures/, patterns/, solutions/, l9_lessons_learned/, etc.

# Count ALL learning files recursively (MANDATORY)
find .cursor-commands/learning/ -type f -name "*.md" 2>/dev/null | wc -l
# Expected: 7+ files (all .md files in GlobalCommands learning folder with Suite 6 structure)

# Verify specific governance files
test -f ".cursor-commands/profiles/session-startup-protocol.md" && echo "✅ Session startup protocol accessible" || echo "❌ Missing"

# Verify GlobalCommands learning files exist (all subdirectories - Suite 6 v6.0 structure)
test -f ".cursor-commands/learning/credentials-policy.md" && echo "✅ Credentials policy accessible" || echo "❌ Missing"
test -f ".cursor-commands/learning/l9-ai-agent-patterns.md" && echo "✅ L9 patterns accessible" || echo "❌ Missing"
test -d ".cursor-commands/learning/failures" && test -f ".cursor-commands/learning/failures/repeated-mistakes.md" && echo "✅ Failures learning accessible" || echo "❌ Missing"
test -d ".cursor-commands/learning/patterns" && test -f ".cursor-commands/learning/patterns/quick-fixes.md" && echo "✅ Patterns learning accessible" || echo "❌ Missing"
test -d ".cursor-commands/learning/solutions" && echo "✅ Solutions folder accessible (2+ files)" || echo "❌ Missing"
test -d ".cursor-commands/learning/l9_lessons_learned" && test -f ".cursor-commands/learning/l9_lessons_learned/Recursive_Self_Check_Protocol.md" && echo "✅ L9 lessons folder accessible (1 file)" || echo "❌ Missing"

# Verify reasoning profiles are accessible (MANDATORY for session startup)
test -f ".cursor-commands/profiles/reasoning_l9.md" && echo "✅ L9 reasoning profile accessible" || echo "❌ Missing"
test -f ".cursor-commands/profiles/reasoning_docs.md" && echo "✅ Docs reasoning profile accessible" || echo "❌ Missing"
test -f ".cursor-commands/profiles/reasoning_technical_operations.md" && echo "✅ Technical operations reasoning profile accessible" || echo "❌ Missing"

# Verify standard operating modes are accessible
test -f ".cursor-commands/profiles/ynp_mode.md" && echo "✅ YNP Mode accessible" || echo "❌ Missing"
test -f ".cursor-commands/profiles/dev_mode.md" && echo "✅ Dev Mode accessible" || echo "❌ Missing"
test -f ".cursor-commands/profiles/orchestrator.md" && echo "✅ Orchestrator accessible" || echo "❌ Missing"

# Verify slash commands are accessible (MANDATORY for command availability)
test -f ".cursor-commands/commands/reasoning.md" && echo "✅ /reasoning command accessible" || echo "❌ Missing"
test -f ".cursor-commands/commands/forge.md" && echo "✅ /forge command accessible" || echo "❌ Missing"
test -f ".cursor-commands/commands/consolidate.md" && echo "✅ /consolidate command accessible" || echo "❌ Missing"
test -f ".cursor-commands/commands/analyze-toolkit.md" && echo "✅ /analyze-toolkit command accessible" || echo "❌ Missing"
test -f ".cursor-commands/commands/evaluate- Comprehensive Project Evaluation.md" && echo "✅ /evaluate command accessible" || echo "❌ Missing"

# Verify supporting profiles are accessible (referenced by loaded files)
test -f ".cursor-commands/profiles/workflow-governance.md" && echo "✅ Workflow governance accessible" || echo "❌ Missing"
test -f ".cursor-commands/profiles/operational-health.md" && echo "✅ Operational health accessible" || echo "❌ Missing"

# Verify feature files are accessible (enabled in .suite6-config.json)
test -f ".cursor-commands/intelligence/meta-learning/meta-learning-log.md" && echo "✅ Meta-learning log accessible" || echo "❌ Missing"
test -f ".cursor-commands/intelligence/reasoning/cursor-native-reasoning.md" && echo "✅ Cursor native reasoning accessible" || echo "❌ Missing"
test -f ".cursor-commands/foundation/logic/universal-kernel.md" && echo "✅ Universal kernel accessible" || echo "❌ Missing"
test -f ".cursor-commands/foundation/logic/rule-registry.json" && echo "✅ Rule registry accessible" || echo "❌ Missing"
```

**✅ Success Check**: All files return ✅ accessible

---

## STEP 5: Test Workflow

**Test governance system with minimal workflow:**

```bash
# Test 1: Access governance file
cat .cursor-commands/profiles/orchestrator.md | head -5
# Expected: Should display orchestrator.md content

# Test 2: Verify Suite 6 configuration
python3 -c "import json; f=open('.suite6-config.json'); d=json.load(f); print(f'Governance: {d[\"governance_enabled\"]}'); print(f'Intelligence: {d[\"intelligence_active\"]}'); f.close()"
# Expected: Governance: True, Intelligence: True
```

**In Cursor IDE:**
```
1. Open Cursor in this workspace
2. Type: @.cursor-commands/profiles/session-startup-protocol.md
3. Verify: File should be accessible via autocomplete
4. Check: Cursor should suggest the file
```

**✅ Success Check**: All tests pass, files accessible in Cursor

---

## STEP 6: Troubleshooting

### Issue 1: "No module named 'yaml'"
**Symptom**: Python error when running env-manager.py
**Fix**:
```bash
python3 -m pip install pyyaml
```

### Issue 2: Symlink points to wrong location
**Symptom**: `.cursor-commands` points to Library instead of the SSOT
**Root Cause**: Governance SSOT is `~/.cursor-governance`, not Library/Application Support
**Fix**:
```bash
# Remove wrong symlink
rm .cursor-commands

# Create correct symlink to the SSOT (where governance actually is)
ln -s ~/.cursor-governance .cursor-commands

# Verify correct target
ls -la .cursor-commands
# Expected: -> ~/.cursor-governance
```

### Issue 3: Suite 6 directory not found
**Symptom**: "No such file or directory: Suite 6 (L9 + Suite 6)"
**Fix**: Use correct path:
```bash
# Correct path is:
"/Users/ib-mac/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9)"

# NOT:
"/Users/ib-mac/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9 + Suite 6)"
```

### Issue 4: Governance files not accessible
**Symptom**: `@.cursor-commands/` files not found in Cursor
**Diagnosis**:
```bash
# Check if symlink exists
test -L .cursor-commands && echo "Symlink exists" || echo "Symlink missing"

# Check symlink target
readlink .cursor-commands

# Check target directory contents
ls "$(readlink .cursor-commands)"
```
**Fix**: Recreate symlink with correct path (see Issue 2)

### Issue 5: .cursorrules not deployed
**Symptom**: No `.cursorrules` file in workspace
**Note**: This is optional - governance works via `.suite6-config.json` and `.cursor-commands/`
**Optional Fix**: Copy template manually:
```bash
cp .cursor-commands/templates/.cursorrules .cursorrules
```

---

## STEP 7: Final Confirmation

**✅ Setup Complete Checklist:**

**Option 1: Automated Verification (Recommended)**
```bash
# Run comprehensive startup file verification
bash .cursor-commands/ops/scripts/verify-startup-files.sh
```

**Option 2: Manual Verification**

Run this verification:
```bash
echo "=== GOVERNANCE STATUS CHECK ===" && \
test -f ".suite6-config.json" && echo "✅ Suite 6 config exists" || echo "❌ Missing" && \
test -L ".cursor-commands" && echo "✅ Symlink exists" || echo "❌ Missing" && \
readlink .cursor-commands && \
test -d ".cursor-commands/profiles" && echo "✅ Profiles accessible" || echo "❌ Missing" && \
test -d ".cursor-commands/learning" && echo "✅ GlobalCommands learning accessible" || echo "❌ Missing" && \
find .cursor-commands/learning/ -type f -name "*.md" 2>/dev/null | wc -l | xargs -I {} echo "✅ GlobalCommands learning files: {}" && \
test -f ".cursor-commands/profiles/reasoning_l9.md" && echo "✅ Reasoning profiles accessible" || echo "❌ Missing reasoning profiles" && \
test -f ".cursor-commands/profiles/ynp_mode.md" && echo "✅ Operating modes accessible" || echo "❌ Missing operating modes" && \
test -f ".cursor-commands/commands/reasoning.md" && echo "✅ Slash commands accessible" || echo "❌ Missing slash commands" && \
test -f ".cursor-commands/intelligence/meta-learning/meta-learning-log.md" && echo "✅ Feature files accessible" || echo "❌ Missing feature files" && \
echo "=== SETUP COMPLETE ==="
```

**Expected Output:**
```
=== GOVERNANCE STATUS CHECK ===
✅ Suite 6 config exists
✅ Symlink exists
~/.cursor-governance
✅ Profiles accessible
✅ GlobalCommands learning accessible
✅ GlobalCommands learning files: 7
=== SETUP COMPLETE ===
```

**You're ready when:**
- ✅ `.suite6-config.json` shows governance_enabled: true
- ✅ `.cursor-commands` symlink points to Dropbox GlobalCommands
- ✅ All governance files accessible via `@.cursor-commands/`
- ✅ GlobalCommands learning folder (`.cursor-commands/learning/`) accessible with all files
- ✅ Reasoning profiles accessible (reasoning_l9.md, reasoning_docs.md, reasoning_technical_operations.md)
- ✅ Standard operating modes accessible (ynp_mode.md, dev_mode.md, orchestrator.md)
- ✅ Slash commands accessible (/reasoning, /forge, /consolidate, /analyze-toolkit, /evaluate)
- ✅ Supporting profiles accessible (workflow-governance.md, operational-health.md)
- ✅ Feature files accessible (meta-learning-log.md, cursor-native-reasoning.md, universal-kernel.md, rule-registry.json)
- ✅ **Learning system activated** (process_learnings.sh completed successfully)
- ✅ **LaunchAgents running** (chat-export and learning-processor showing status 0)
- ✅ **Memory index created** (ops/logs/memory_index.json exists)
- ✅ Cursor IDE autocomplete suggests governance files
- ✅ No errors in verification commands

---

## What You Get in Your Workspace:

```
workspace/
├── .cursorrules ✅ Auto-loaded by Cursor (Suite 6 enhanced)
├── .cursor-commands/ ✅ Symlink to Suite 6 governance
│   ├── intelligence/
│   │   ├── meta-learning/meta-learning-log.md
│   │   ├── reasoning/cursor-native-reasoning.md
│   │   └── workspace/setup-new-workspace.md
│   ├── foundation/
│   │   ├── logic/
│   │   │   ├── dsl-compiler.md
│   │   │   ├── universal-kernel.md
│   │   │   └── rule-registry.json
│   │   └── agents/
│   │       ├── constellation-linter.md
│   │       └── escalation-router.md
│   ├── execution/
│   │   ├── api/governance-api.py
│   │   ├── monitoring/governance-monitor.py
│   │   └── validation/governance-validator.py
│   ├── operations/
│   │   ├── ops/operational-oversight.md
│   │   ├── pipeline/pipeline-orchestration.md
│   │   └── security/security-audit.md
│   └── environment/
│       ├── env-loader.py
│       └── rules.json
├── .cursor/
│   └── commands/ ✅ Symlink to GlobalCommands/commands (slash commands)
└── .suite6-config.json ✅ Workspace-specific configuration

Note: `.cursor-commands/learning/` ✅ Symlink to GlobalCommands/learning (MANDATORY to read ALL files at session start)
  ├── credentials-policy.md
  ├── l9-ai-agent-patterns.md
  ├── failures/
  │   └── repeated-mistakes.md
  ├── l9_lessons_learned/
  │   └── Recursive_Self_Check_Protocol.md
  ├── patterns/
  │   └── quick-fixes.md
  └── solutions/
      ├── authentication-fixes.md
      └── json-issues.md
```

## You Can Then Use:

### Intelligence Layer Access
```
@.cursor-commands/intelligence/reasoning/cursor-native-reasoning.md
@.cursor-commands/intelligence/meta-learning/meta-learning-log.md
```

### Reasoning Profiles Access (MANDATORY at Session Startup)
```
@.cursor-commands/profiles/reasoning_l9.md
   └─ Use for: L9 orchestration development, debugging, tool selection
   └─ Component: INT-RSN-001

@.cursor-commands/profiles/reasoning_docs.md
   └─ Use for: Strategic document analysis, gap detection, insights
   └─ Component: INT-RSN-002

@.cursor-commands/profiles/reasoning_technical_operations.md
   └─ Use for: Tool selection, API integration, architecture decisions
   └─ Component: INT-RSN-003
```

### Standard Operating Modes Access (MANDATORY at Session Startup)
```
@.cursor-commands/profiles/ynp_mode.md
   └─ YNP Mode: Strategic co-pilot with next-prompt generation
   └─ Component: CMD-001

@.cursor-commands/profiles/dev_mode.md
   └─ Dev Mode: Code analysis, module management, testing automation
   └─ Component: CMD-003

@.cursor-commands/profiles/orchestrator.md
   └─ Orchestrator: Governance coordination and task delegation
   └─ Component: INT-ORC-001
```

### Foundation Layer Access
```
@.cursor-commands/foundation/logic/rule-registry.json
@.cursor-commands/foundation/agents/constellation-linter.md
```

### Slash Commands Access
```
/forge - Heavy Forge mode (autonomous execution)
/ynp - YNP Mode (strategic co-pilot)
/evaluate - Comprehensive project evaluation
/consolidate - File consolidation & organization
/analyze-toolkit - Complete toolkit analysis
```

**Command Reference:** `@.cursor/commands/COMMANDS_REGISTRY.md`

## Suite 6 Enhanced Features

### Automatic Governance
- Real-time compliance checking
- Canonical header validation
- Cross-layer integration monitoring
- Autonomous rule enforcement

### Intelligence Integration
- Meta-learning from workspace interactions
- Cursor-native reasoning framework
- Preference extraction and adaptation
- Pattern recognition and optimization

### Performance Monitoring
- API response time tracking
- Resource usage monitoring
- Compliance rate measurement
- Error detection and alerting

## Workspace Configuration

The setup creates a `.suite6-config.json` file:

```json
{
  "suite_version": "6.0.0",
  "workspace_id": "auto-generated-uuid",
  "governance_enabled": true,
  "intelligence_active": true,
  "monitoring_level": "standard",
  "compliance_required": true,
  "created": "2025-10-28T00:00:00Z",
  "last_validated": "2025-10-28T00:00:00Z"
}
```

## Validation Commands

### Check Workspace Health
```bash
# Via API (if governance server running)
curl http://localhost:8080/governance/health

# Via direct validation
python3 @.cursor-commands/execution/validation/governance-validator.py --workspace-check
```

### Update Governance Rules
```bash
# Pull latest rules from Suite 6
python @.cursor-commands/environment/env-manager.py sync "$(pwd)"
```

### Monitor Compliance
```bash
# Real-time monitoring
python3 @.cursor-commands/execution/monitoring/governance-monitor.py --workspace-mode
```

## Troubleshooting

### Common Issues

1. **Symlink Creation Failed**
   - Check permissions on target directory
   - Ensure Suite 6 path is accessible
   - Run with appropriate user permissions
   - Verify Suite 6 directory exists: `/Users/ib-mac/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9 + Suite 6)`

2. **Governance API Not Responding**
   - Check if governance server is running
   - Verify port 8080 is available
   - Check firewall settings

3. **Compliance Validation Errors**
   - Review canonical headers in workspace files
   - Check rule registry accessibility
   - Validate environment configuration

### Support Commands

```bash
# Check workspace health
python @.cursor-commands/execution/validation/governance-validator.py --workspace-check

# Get environment status
python @.cursor-commands/environment/env-manager.py status

# Validate environment
python @.cursor-commands/environment/env-manager.py validate
```

## STEP 8: Final Alignment Verification (MANDATORY)

**Run the comprehensive alignment test to ensure everything is correctly set up:**

```bash
# Run the Suite 6 Setup Alignment Verification
bash .cursor-commands/ops/scripts/verify-setup-alignment.sh
```

**Expected Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   SUITE 6 SETUP ALIGNMENT VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 GlobalCommands: /path/to/GlobalCommands

1️⃣  Learning Files Discovery:
   Found: 7 files (Expected: 7+)
   ✅ PASS

2️⃣  Learning Subdirectory Structure:
   ✅ learning/failures/ exists
   ✅ learning/patterns/ exists
   ✅ learning/solutions/ exists
   ✅ learning/l9_lessons_learned/ exists

3️⃣  Core Learning Files:
   ✅ failures/repeated-mistakes.md exists
   ✅ patterns/quick-fixes.md exists
   ✅ solutions/authentication-fixes.md exists
   ✅ solutions/json-issues.md exists
   ✅ credentials-policy.md exists
   ✅ l9-ai-agent-patterns.md exists
   ✅ l9_lessons_learned/Recursive_Self_Check_Protocol.md exists

4️⃣  Learning System Scripts:
   ✅ export_chats.sh exists
   ✅ process_learnings.sh exists
   ✅ memory_aggregator.py exists
   ✅ learning_updater.py exists
   ✅ sync_mistakes_to_cursorrules.py exists

5️⃣  Utility Scripts (MCP):
   ✅ cleanup_mcp_containers.sh exists
   ✅ fix_mcp_config.sh exists
   ✅ verify_docker.sh exists

6️⃣  Suite 6 Headers Compliance:
   Found: 10 scripts with headers (Expected: 8+)
   ✅ PASS

7️⃣  LaunchAgent Services:
   Active services: 2 (Expected: 2)
   ✅ PASS (chat-export + learning-processor)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   VERIFICATION RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   ✅ Tests Passed: 7 / 7

   🟢 SETUP ALIGNMENT: PERFECT

   All components verified:
   • 7 learning files in organized structure
   • 5 learning system scripts with Suite 6 headers
   • 3 utility scripts with Suite 6 headers
   • 2 LaunchAgent services running
   • All verification commands will execute successfully

   ✅ setup-new-workspace.md is 100% aligned!
```

**What This Verifies:**
- ✅ Learning folder has correct Suite 6 v6.0 structure (7 files)
- ✅ All 4 subdirectories present (failures, patterns, solutions, l9_lessons_learned)
- ✅ All 7 core learning files accessible
- ✅ All 5 learning system scripts present
- ✅ All 3 utility scripts present (MCP cleanup, config fix, Docker verify)
- ✅ All 8+ scripts have Suite 6 canonical headers
- ✅ Both LaunchAgent services running (hourly chat export + learning processor)

**✅ Success Check**: 
- Exit code: 0 (success)
- All 7 tests pass
- Message: "SETUP ALIGNMENT: PERFECT"
- Green status indicator shown

**If any test fails:**
- Script will exit with code 1
- Failed tests will be highlighted in red
- Specific missing components will be listed

---

## Next Steps After Setup

1. **Verify Installation**: ✅ Already done via verify-setup-alignment.sh
2. **Test Governance**: Create a test file with canonical header
3. **Start Monitoring**: Enable real-time compliance monitoring
4. **Configure Preferences**: Set workspace-specific governance preferences
5. **Enable Learning**: ✅ Already activated via process_learnings.sh in STEP 3.5
