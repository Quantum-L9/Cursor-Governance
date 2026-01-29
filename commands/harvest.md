---
name: harvest
version: "1.3.0"
description: "Harvest code from documents — READ source, WRITE to target, NO rewriting"
auto_chain: ynp
---

# /harvest — Pattern Harvesting

## WHAT IT DOES

Extract code blocks from source documents into target files.
**READ the source lines → WRITE to target file. That's it.**

---

## 🚨 CRITICAL RULE

**USE FILE TOOLS TO COPY CODE DIRECTLY.**

1. **Read** the source file at the exact line range
2. **Write** that content to the target file
3. **DO NOT TYPE THE CODE YOURSELF**

The Write tool IS copy-paste. Use it.

---

## INSTRUCTIONS

**Target folder or file:** `<TARGET>`

1. **Identify patterns/line range list** for complete files in source
2. **Locate filenames** from the source document headers (e.g., `**File**: filename.py`)
3. **For each pattern/file:**
   - Open `<TARGET>` source document
   - Go to the line range listed
   - Copy the code block (inside the triple backticks)
   - Paste into target file using same filename in `harvested-files/` subfolder of TARGET folder

---

## HARVEST TABLE FORMAT

Before extracting, catalog what you'll harvest:

```markdown
| # | Pattern | Source | Lines | Target |
|---|---------|--------|-------|--------|
| 1 | `ClassName` | doc.md | 100-250 | `1_file.py` |
| 2 | `AnotherClass` | doc.md | 300-450 | `2_file.py` |
```

Then execute the extractions.

---

## EXTRACTION COMMANDS

Use `sed` to extract code blocks directly (removes the triple backtick lines):

```bash
# Extract lines 859-1453 from source, strip first/last lines (backticks), write to target
sed -n '859,1453p' "source.md" | sed '1d' | sed '$d' > "harvested-files/1_semantic_discovery.py"

# Another example
sed -n '2342,2481p' "source.md" | sed '1d' | sed '$d' > "harvested-files/7_benchmarks.py"

# And another
sed -n '2492,2564p' "source.md" | sed '1d' | sed '$d' > "harvested-files/8_observability.py"
```

**Pattern:** `sed -n 'START,ENDp' "SOURCE" | sed '1d' | sed '$d' > "TARGET"`

- `sed -n 'START,ENDp'` — extracts lines START to END
- `sed '1d'` — removes first line (opening triple backticks)
- `sed '$d'` — removes last line (closing triple backticks)

---

## VERIFICATION

After extraction, verify files exist with content:

```bash
ls -la "harvested-files/" && wc -l "harvested-files/"*
```

Expected output shows files with line counts:

```
-rw-r--r--  1 user  staff  21271 Jan 25 10:36 1_semantic_discovery.py
-rw-r--r--  1 user  staff   8596 Jan 25 10:36 2_anthropic_tool_search.py
...
     593 harvested-files/1_semantic_discovery.py
     262 harvested-files/2_anthropic_tool_search.py
```

---

## COMPLETE EXAMPLE

**Source:** `Tool Discovery-2.md`
**Target folder:** `Tool Discovery/harvested-files/`

### Step 1: Identify patterns

| # | Pattern | Lines | Target |
|---|---------|-------|--------|
| 1 | `DynamicToolDiscoveryService` | 859-1453 | `1_semantic_discovery.py` |
| 2 | `AnthropicToolSearchAdapter` | 1465-1728 | `2_anthropic_tool_search.py` |
| 3 | `PromptCachingStrategy` | 1740-1977 | `3_prompt_caching.py` |

### Step 2: Execute extractions

```bash
sed -n '859,1453p' "Tool Discovery-2.md" | sed '1d' | sed '$d' > "harvested-files/1_semantic_discovery.py"
sed -n '1465,1728p' "Tool Discovery-2.md" | sed '1d' | sed '$d' > "harvested-files/2_anthropic_tool_search.py"
sed -n '1740,1977p' "Tool Discovery-2.md" | sed '1d' | sed '$d' > "harvested-files/3_prompt_caching.py"
```

### Step 3: Verify

```bash
ls -la "harvested-files/" && wc -l "harvested-files/"*
```

---

## ANTI-PATTERNS

❌ **DON'T** manually type out code you see in the source
❌ **DON'T** regenerate code from memory
❌ **DON'T** "write" by composing the code yourself
❌ **DON'T** give "instructions" to copy-paste — just DO IT with tools

✅ **DO** use `sed` to extract exact content
✅ **DO** verify with `ls -la` and `wc -l`
✅ **DO** strip backtick lines with `sed '1d' | sed '$d'`

---

## LESSON LEARNED (2026-01-25)

> "Don't write them, PASTE them. The Write tool IS paste.
> Read the lines, Write to file. That simple.
> Stop being a speed bump on the dumbest thing."

---

## GOVERNANCE REFERENCE

From `92-learned-lessons.mdc`:

> **🔴 CRITICAL: Copy Complete Code, Don't Rewrite**
> If code exists, COPY it. Rewriting existing code is a governance violation.

**Copying via tools = sed extraction. Use it.**

→ **Auto-chains to /ynp**
