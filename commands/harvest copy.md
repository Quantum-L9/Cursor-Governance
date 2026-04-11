---
name: harvest
version: "3.0.0"
description: "Extract code from documents using sed — NEVER write/type code manually"
auto_chain: use-harvest
dag_executor: .cursor-commands/workflows/harvest_executor.py
---

# /harvest — Code Extraction (v3.0.0)

## 🚨 ABSOLUTE RULE: sed ONLY — NEVER WRITE CODE MANUALLY

**Harvest = mechanical extraction.** The agent MUST use `sed` (or equivalent line-range extraction) to pull code blocks out of source documents. The agent MUST NOT:

- ❌ Read the code and re-type it into a `Write` tool call
- ❌ Copy code into the assistant message and then write it to a file
- ❌ "Rewrite" or "reproduce" code from the document
- ❌ Use any tool that involves the agent generating/typing the code content

The agent MUST:

- ✅ Use `grep -n` to find code fence boundaries (` ```python `, ` ``` `)
- ✅ Use `sed -n 'START,ENDp'` to extract the exact lines from the source file
- ✅ Redirect `sed` output directly to the target file path
- ✅ Validate with `py_compile` after extraction

**Why:** The agent typing code wastes tokens, introduces transcription errors, and violates the "Copy Complete Code, Don't Rewrite" learned lesson. `sed` is instant, exact, and zero-error.

---

## EXECUTION STEPS (MANDATORY ORDER)

### Step 1: Find code block boundaries

```bash
grep -n '```python\|```makefile\|```$' "path/to/document.md"
```

This gives you line numbers for every code fence open/close.

### Step 2: Map blocks to target files

Read the document headers (e.g., `### File: tools/foo/bar.py`) to determine where each block goes. Build a mapping:

| Block | Source Lines | Target Path |
|-------|-------------|-------------|
| 1 | 28-454 | `tools/type_coverage/track_mypy_progress.py` |
| 2 | 465-812 | `tools/code_index/build_semantic_index.py` |

### Step 3: Create target directories

```bash
mkdir -p tools/type_coverage tools/code_index
```

### Step 4: Extract with sed

```bash
sed -n '28,454p' "path/to/document.md" > tools/type_coverage/track_mypy_progress.py
sed -n '465,812p' "path/to/document.md" > tools/code_index/build_semantic_index.py
```

**CRITICAL:** The line range EXCLUDES the ` ```python ` and ` ``` ` fence lines themselves. Extract only the code content between fences.

### Step 5: Validate syntax

```bash
python3 -m py_compile tools/type_coverage/track_mypy_progress.py && echo "✅ OK" || echo "❌ FAIL"
```

### Step 6: Verify first/last lines

```bash
head -1 tools/type_coverage/track_mypy_progress.py  # Should be #!/usr/bin/env python3 or import
tail -1 tools/type_coverage/track_mypy_progress.py  # Should be code, not ```
```

If first line is ` ```python ` or last line is ` ``` `, your line range is wrong. Adjust +1/-1.

### Step 7: Run the extracted tool

```bash
python3 tools/type_coverage/track_mypy_progress.py --help
```

---

## VIOLATION DETECTION

If the agent does ANY of the following during `/harvest`, it is a **governance violation**:

1. Opens a `Write` tool call with code content copied from the document
2. Uses `StrReplace` to insert code that came from reading the document
3. Generates code in the assistant response and then writes it to a file
4. Says "Let me write this file" instead of "Let me sed-extract this file"

**Correct language:** "Let me find the line ranges and sed them out."
**Wrong language:** "Let me write/create this file with the code from the document."

---

## MULTIPLE DOCUMENTS

When harvesting from multiple source documents, process each document independently:

```bash
# Document 1
grep -n '```python\|```$' "doc1.md"
sed -n '28,454p' "doc1.md" > target1.py

# Document 2
grep -n '```python\|```$' "doc2.md"
sed -n '13,460p' "doc2.md" > target2.py
```

---

## OUTPUT

After extraction, report a summary table:

| # | File | Source | Lines | Syntax | Run |
|---|------|--------|-------|--------|-----|
| 1 | `target/path.py` | doc.md:28-454 | 427 | ✅ | ✅ |

---

## NEXT STEP

After harvest completes, run `/use-harvest` or:
```bash
python3 .cursor-commands/workflows/use_harvest_executor.py {harvest_dir}
```

---

## LESSON HISTORY

- **2026-02-13:** Agent used `Write` tool to manually type code from documents instead of `sed`. User corrected twice. This v3.0.0 update makes the `sed`-only rule explicit and enforceable.
