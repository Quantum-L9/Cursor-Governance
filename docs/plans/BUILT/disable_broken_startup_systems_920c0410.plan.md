---
name: Disable Broken Startup Systems
overview: "Remove non-functional systems from workspace setup YAML: Operating Modes, Feature Files, Memory Context, and Intelligence Systems. Disable LaunchAgents for the old learning pipeline."
todos:
  - id: remove-operating-modes
    content: Remove operating_modes section (lines 297-301) from setup YAML
    status: completed
  - id: remove-feature-files
    content: Remove features section (lines 357-362) from setup YAML
    status: completed
  - id: remove-memory-context
    content: Remove memory_context section (lines 186-243) from setup YAML
    status: completed
  - id: remove-intelligence
    content: Remove intelligence section (lines 367-376) from setup YAML
    status: completed
  - id: remove-supporting-profiles
    content: Remove supporting section (lines 352-355) from setup YAML
    status: completed
  - id: disable-launchagents
    content: Unload LaunchAgents for learning-processor, context.processor, governance-monitor
    status: completed
  - id: update-verification
    content: Update verification section to remove launchagent checks and update counts
    status: completed
  - id: update-success-message
    content: Update success message to reflect simplified startup
    status: completed
---

# Disable Broken Startup Systems

## What Gets Removed from Setup YAML

### 1. Operating Modes (3 files) - REMOVE

- `profiles/ynp_mode.md`
- `profiles/dev_mode.md`
- `profiles/orchestrator.md`

**Location in YAML:** Lines 297-301 (`operating_modes:` section)

### 2. Feature Files (4 files) - REMOVE

- `intelligence/meta-learning/meta-learning-log.md`
- `intelligence/reasoning/cursor-native-reasoning.md`
- `foundation/logic/universal-kernel.md`
- `foundation/logic/rule-registry.json`

**Location in YAML:** Lines 357-362 (`features:` section)

### 3. Memory Context - REMOVE

- Entire `memory_context:` section (Lines 186-243)
- Auto /mem READ phase that doesn't work

### 4. Intelligence Systems - REMOVE

- Entire `intelligence:` section (Lines 367-376)
- Learning pipeline activation
- Context processor activation
- Governance monitor activation
- Operational oversight activation

### 5. Supporting Profiles (2 files) - REMOVE

- `profiles/workflow-governance.md` (N8N deprecated)
- `profiles/operational-health.md` (no actual monitoring)

**Location in YAML:** Lines 352-355 (`supporting:` section)

---

## LaunchAgents to Disable

Unload these LaunchAgents (they run the broken intelligence systems):

```bash
launchctl unload ~/Library/LaunchAgents/com.tenx.learning-processor.plist
launchctl unload ~/Library/LaunchAgents/com.cursor.context.processor.plist
launchctl unload ~/Library/LaunchAgents/com.cursor.governance-monitor.plist
```

---

## Files to Edit

| File | Action |

|------|--------|

| [.cursor-commands/setup-new-workspace.yaml](.cursor-commands/setup-new-workspace.yaml) | Remove 5 sections |

---

## What STAYS in Setup YAML

- Preflight checks (4)
- Installation (symlinks)
- Python Governance Modules (Phase 1) - these actually work
- Workflow State (Phase 2) - `workflow_state.md`
- Repo Index Refresh (Phase 2.5) - useful
- Dead Code Audit (Phase 2.55) - useful
- Reasoning Stack (Phase 3) - reference only but harmless
- Reference Learning Files (Phase 4) - will update to point to Python modules
- Startup Files (5) - keep for now or remove?
- Reasoning Profiles (2) - keep for now or remove?
- Slash Commands (26) - these work
- Verification - update to reflect removals

---

## Verification Updates

Update `verification.manual.counts` to reflect removed items:

- Remove `launchagents` check for disabled agents
- Update file counts
