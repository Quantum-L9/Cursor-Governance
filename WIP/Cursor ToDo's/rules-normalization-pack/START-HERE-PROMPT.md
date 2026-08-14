# Copy-paste prompt for Cursor Agent

Paste into Cursor Agent (Agent mode), repo open, on a fresh branch.

---

```
Read ./rules-normalization-pack/STANDARD.md and ./rules-normalization-pack/NORMALIZE_TASK.md.

Execute STAGE 1 and STAGE 2 only. Stop and report before STAGE 3.

Stage 1 is frontmatter normalization: strip every non-Cursor-native field
from rules/*.mdc, keeping only description, globs, alwaysApply in that order.
Do NOT change any alwaysApply value in Stage 1. Do NOT touch rule bodies.

Stage 2 is the mechanical fixes listed in NORMALIZE_TASK.md Stage 2.

Hard constraints:
- Never change a rule's tier or alwaysApply value in Stage 1 or 2.
  Retiering is Stage 3 and needs my approval per rule.
- Preserve all removed field values in docs/rules-frontmatter-archive.yaml
  before deleting them, so nothing is lost.
- Do not touch CANONICAL_LAW.md, ORG_INVARIANTS.yaml, CODEOWNERS,
  SECURITY.md, .claude/settings.json, or .claude/hooks/**.
- Branch: chore/rules-normalization. Do not commit or push.

Report: files changed, fields removed with counts per field name, the
before/after always-apply byte total, and any file where frontmatter failed
to parse.
```

---

Stage 3 is the retiering in `MIGRATION-MAP.md`. Do that one rule at a time,
reviewing each, because tier changes alter agent behavior.
