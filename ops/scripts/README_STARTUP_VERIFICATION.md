---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "6.0.0"
component_id: "OPS-VER-001"
component_name: "Startup Verification Script Documentation"
layer: "operations"
domain: "verification"
type: "script_documentation"
status: "active"
created: "2025-11-17T22:06:00Z"
updated: "2025-11-17T22:06:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "high"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["INT-SSP-001"]
api_endpoints: []
data_sources: ["setup-new-workspace.md", "session-startup-protocol.md"]
outputs: ["verification_report", "startup_status"]

# === OPERATIONAL METADATA ===
execution_mode: "on-demand"
monitoring_required: false
logging_level: "info"
performance_tier: "batch"

# === BUSINESS METADATA ===
purpose: "Documentation for startup file verification script"
summary: "Guide for using verify-startup-files.sh to check all required startup files"
business_value: "Ensures all governance files are accessible before session start"
success_metrics: ["verification_accuracy = 100%", "false_positive_rate = 0%"]

# === INTEGRATION METADATA ===
suite_2_origin: "README_STARTUP_VERIFICATION.md v1.0.0"
migration_notes: "Initial documentation for startup verification script"

# === TAGS & CLASSIFICATION ===
tags: ["verification", "startup", "script", "documentation"]
keywords: ["verification", "startup", "files", "check", "script"]
related_components: ["INT-SSP-001"]
startup_required: false
mode_type: "verification"
---

# Startup File Verification Script

## 🎯 Purpose

The `verify-startup-files.sh` script verifies that all 20 files required at session startup are accessible and ready to be loaded.

## 📋 What It Checks

### Core Governance (3 files)
1. `.cursorrules` (optional)
2. `.cursor-commands/learning/` directory (all .md files)
3. `.suite6-config.json`

### Reasoning Profiles (3 files)
4. `profiles/reasoning_n8n.md`
5. `profiles/reasoning_docs.md`
6. `profiles/reasoning_technical_operations.md`

### Operating Modes (3 files)
7. `profiles/ynp_mode.md`
8. `profiles/dev_mode.md`
9. `profiles/orchestrator.md`

### Slash Commands (5 files)
10. `commands/reasoning.md`
11. `commands/forge.md`
12. `commands/consolidate.md`
13. `commands/analyze-toolkit.md`
14. `commands/evaluate- Comprehensive Project Evaluation.md`

### Supporting Profiles (2 files)
15. `profiles/workflow-governance.md`
16. `profiles/operational-health.md`

### Feature Files (4 files)
17. `intelligence/meta-learning/meta-learning-log.md`
18. `intelligence/reasoning/cursor-native-reasoning.md`
19. `foundation/logic/universal-kernel.md`
20. `foundation/logic/rule-registry.json`

## 🚀 Usage

### Basic Usage
```bash
bash .cursor-commands/ops/scripts/verify-startup-files.sh
```

### From Workspace Root
```bash
cd /path/to/workspace
bash .cursor-commands/ops/scripts/verify-startup-files.sh
```

## 📊 Output Format

### Success Output
```
✅ ALL REQUIRED STARTUP FILES VERIFIED
All 20 required files are accessible and ready for startup.
```

### Partial Success (Optional Files Missing)
```
✅ ALL REQUIRED STARTUP FILES VERIFIED
Some optional files are missing, but all required files are present.
```

### Failure Output
```
❌ STARTUP VERIFICATION FAILED
X critical file(s) are missing. Please check the paths above.
```

## 🔍 Exit Codes

- **0**: All required files verified ✅
- **1**: Critical files missing ❌

## 📝 Integration

### Use in CI/CD
```bash
#!/bin/bash
if ! bash .cursor-commands/ops/scripts/verify-startup-files.sh; then
    echo "Startup verification failed - aborting"
    exit 1
fi
```

### Use Before Session Start
```bash
# Run verification before starting work
bash .cursor-commands/ops/scripts/verify-startup-files.sh && echo "Ready to start!" || echo "Fix missing files first"
```

## 🛠️ Troubleshooting

### Issue: Script reports files missing but they exist
**Solution:** Check file paths are relative to workspace root, not absolute paths

### Issue: Learning directory shows 0 files
**Solution:** Verify `.cursor-commands` symlink points to correct GlobalCommands location

### Issue: .cursorrules marked as optional but you want it required
**Solution:** Edit script and change `check_file ".cursorrules" ... "true"` to `"false"`

## 📈 Expected Results

**Minimum Success:**
- 19/20 files loaded (if .cursorrules is optional)
- 100% of required files present

**Perfect Success:**
- 20/20 files loaded
- All files accessible

---

**Last Updated:** 2025-11-17  
**Status:** Active & Ready for Use

