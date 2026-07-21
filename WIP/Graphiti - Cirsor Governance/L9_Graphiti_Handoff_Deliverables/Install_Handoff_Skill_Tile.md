---
description: "Approval Tile: System-Wide Installation of AI-to-AI Handoff Skill"
author: "L9 Systems Analyst"
date: "2026-07-04"
---

# 🚀 SYSTEM-WIDE SKILL INSTALLATION REQUIRED

The **L9 AI-to-AI Handoff Skill** has been successfully extracted and validated. To enable seamless context transfer and cross-agent learning across all workspaces, this skill must be installed system-wide.

## What this does:
1.  Installs the 6-phase handoff prompt sequence into the global `.cursor/rules/` directory.
2.  Enables the `CrossAgentLearningEngine` pattern discovery API.
3.  Allows Claude, Cursor, and Copilot to share validated "proven_best_practice" patterns automatically.

## ⚠️ Approval Required

Tap below to authorize the system-wide installation of this skill.

```bash
# TAP TO APPROVE & INSTALL
mkdir -p ~/.cursor/skills/ai-to-ai-handoff && cp -r /home/ubuntu/handoff-skill/l9-ai-to-ai-handoff-skill/* ~/.cursor/skills/ai-to-ai-handoff/ && echo "✅ Handoff Skill Installed System-Wide"
```
