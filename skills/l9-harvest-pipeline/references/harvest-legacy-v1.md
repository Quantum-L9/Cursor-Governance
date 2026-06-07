<!--
--- SKILL_META ---
skill_schema: 1
origin: l9-harvest-pipeline
layer: reference
role: harvest_legacy_protocol
tags: [l9, harvest, deprecated, legacy]
owner: igor_beylin
status: deprecated
version: 1.3.0
updated: 2026-06-06
superseded_by: references/harvest-extraction.md
--- /SKILL_META ---
-->

# /harvest — Pattern Harvesting (DEPRECATED v1.3)

> **DEPRECATED:** Superseded by harvest-extraction.md v3.2. Retained for reference only. Do not use Write-tool copy pattern for new harvests — use sed extraction.

## WHAT IT DID

Extract code blocks from source documents into target files.
**READ the source lines → WRITE to target file.**

## CRITICAL RULE (v1.3)

**USE FILE TOOLS TO COPY CODE DIRECTLY.**

1. **Read** the source file at the exact line range
2. **Write** that content to the target file
3. **DO NOT TYPE THE CODE YOURSELF**

## HARVEST TABLE FORMAT

```markdown
| # | Pattern | Source | Lines | Target |
|---|---------|--------|-------|--------|
| 1 | `ClassName` | doc.md | 100-250 | `1_file.py` |
| 2 | `AnotherClass` | doc.md | 300-450 | `2_file.py` |
```

## EXTRACTION COMMANDS (sed — still valid)

```bash
sed -n '859,1453p' "source.md" | sed '1d' | sed '$d' > "harvested-files/1_semantic_discovery.py"
```

**Pattern:** `sed -n 'START,ENDp' "SOURCE" | sed '1d' | sed '$d' > "TARGET"`

## VERIFICATION

```bash
ls -la "harvested-files/" && wc -l "harvested-files/"*
```

## LESSON LEARNED (2026-01-25)

> "Don't write them, PASTE them. The Write tool IS paste.
> Read the lines, Write to file. That simple.
> Stop being a speed bump on the dumbest thing."

→ **Auto-chained to /ynp** in v1.3; current pipeline chains to `/use-harvest`.
