# Archived Noise Entries from repeated-mistakes.md
# Archived: 2026-01-01
# Reason: Low-quality auto-generated entries with "Unknown pattern" and duplicates
# Original entries 14-124 from repeated-mistakes.md

---

## Archive Summary

- **Total entries archived:** 111 (entries 14-124)
- **Categories:**
  - "Pattern detected: Unknown pattern..." - ~50 entries
  - "User correction required..." - ~30 entries
  - Duplicate entries - ~20 entries
  - "n8n workflow or node configuration..." - ~12 entries (deprecated platform)

---

## Why These Were Archived

1. **"Unknown pattern" entries**: The pattern detection fell through to a generic fallback. These have no actionable prevention rules.

2. **Duplicate entries**: Same lessons repeated multiple times with identical content.

3. **n8n references**: n8n was deprecated 2026-01-01. These patterns are now obsolete.

4. **Vague "User correction" entries**: Generic correction detection without specific mistake identification.

---

## Sample of Archived Content

### Pattern Types Found:

```
- "Pattern detected: Unknown pattern..." (50+ occurrences)
- "User correction required - misunderstanding or incorrect assumption made" (43+ occurrences)
- "Authentication method incorrect or not following best practices" (20+ occurrences)
- "n8n workflow or node configuration issue detected" (12+ occurrences)
- "Data format parsing issue..." (5+ occurrences)
- "Successful solution pattern detected..." (39+ occurrences - mislabeled as mistakes)
```

### Example Entries:

**Entry 14:**
```
Mistake: Pattern detected: Unknown pattern
Impact: Occurred 33 time(s) | Date range: 2025-10-10 to 2025-11-15
Prevention: Review pattern context before proceeding
```

**Entry 27:**
```
Mistake: User correction required - misunderstanding or incorrect assumption made
Impact: Occurred 43 time(s) | Date range: 2025-10-10 to 2025-11-17
Prevention: Ask clarifying questions BEFORE starting
```

---

## Lessons Learned from This Archive

1. **Pattern detection needs improvement**: Too many patterns fall through to "Unknown"
2. **Deduplication missing**: Same patterns repeated dozens of times
3. **Category confusion**: "Successful solution" was being logged as a "mistake"
4. **Platform-specific patterns**: n8n patterns are now obsolete, need filtering

---

## Future Improvements

To prevent this noise accumulation:

1. **Better pattern categorization** in `memory_aggregator.py`
2. **Deduplication logic** based on content hash
3. **Confidence threshold** - only store lessons with confidence > 0.8
4. **Platform filtering** - exclude deprecated platforms (n8n, supabase legacy)

---

*This archive is kept for analysis purposes only. These entries should NOT be migrated to MCP-Memory.*

