# 🚀 Suite 6 Workspace Setup - Quick Start

**Version:** 7.0.0 | **Enforcement:** 200% | **Duration:** ~15 minutes

---

## ⚡ ONE-COMMAND SETUP

```bash
# From your workspace directory:
python3 "$HOME/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9)/environment/env-manager.py" sync "$(pwd)" && \
bash "$HOME/Dropbox/Cursor Governance/Cursor Governance Suite 6 (L9)/ops/scripts/setup_workspace_symlinks.sh" && \
bash .cursor-commands/ops/scripts/verify-startup-files.sh
```

**Expected:** ✅ All checks pass, Suite 6 active

---

## 📋 WHAT GETS LOADED (23 Files)

### **Core Protocol (1 file)**
- `session-startup-protocol.md` - Master checklist

### **Governance (2 files)**
- `.cursorrules` (workspace + GlobalCommands template)

### **Reasoning Stack (1 file)**
- `REASONING_STACK.yaml` - Activates all reasoning capabilities

### **Learning Files (12 files)**
- `credentials-policy.md`
- `failures/repeated-mistakes.md`
- `n8n-ai-agent-patterns.md`
- `n8n-configs/` (2 files: Email, Supabase)
- `patterns/quick-fixes.md`
- `solutions/` (2 files: auth, JSON)
- `n8n_lessons_learned/` (3 files: validation, research, execution)

### **n8n Start-Up Kit (7 files)**
- Complete MCP validation system
- 5-phase workflow creation
- Context7 integration
- Architecture patterns

### **Startup Files (5 files)**
- System capabilities
- Probabilistic governance
- Production speed pack
- Pre-build questions
- Quality standards

### **Reasoning Profiles (3 files)**
- n8n reasoning
- Document reasoning
- Technical operations

### **Operating Modes (3 files)**
- YNP Mode
- Dev Mode
- Orchestrator

### **Slash Commands (6 files)**
- `/reasoning`, `/ynp`, `/forge`
- `/consolidate`, `/analyze`, `/evaluate`

### **Supporting (2 files)**
- Workflow governance
- Operational health

### **Feature Files (4 files)**
- Meta-learning log
- Cursor native reasoning
- Universal kernel
- Rule registry

---

## ✅ VERIFICATION

```bash
# Quick check
bash .cursor-commands/ops/scripts/verify-startup-files.sh

# Expected output:
✅ ALL REQUIRED STARTUP FILES VERIFIED
All 23 required files are accessible and ready for startup.
```

---

## 🔧 TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| YAML missing | `python3 -m pip install pyyaml` |
| Wrong symlink | `rm .cursor-commands && ln -s "$HOME/Dropbox/Cursor Governance/GlobalCommands" .cursor-commands` |
| Verify symlink | `readlink .cursor-commands` |

---

## 📊 ENFORCEMENT: 200%

**What 200% means:**
- ✅ 100% = All mandatory files must be loaded
- ✅ +100% = System actively prevents skipping + auto-verifies + blocks on failure

**Enforcement Rules:**
- ❌ Cannot skip files marked `skip: never`
- ❌ Cannot proceed with missing files
- ❌ Cannot bypass verification
- ✅ Must complete all 23 file loads
- ✅ Must pass all verification checks

---

## 📖 FULL SPEC

**Complete protocol:** `setup-new-workspace.yaml` (250 lines, script-parseable)  
**Archived verbose version:** `_archived/setup-archive-20251118/setup-new-workspace-v6.0-verbose.md`

---

**Ready to setup a new workspace? Run the one-command setup above!** 🎯

