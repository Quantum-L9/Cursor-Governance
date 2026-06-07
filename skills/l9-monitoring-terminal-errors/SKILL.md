---
name: l9-monitoring-terminal-errors
description: watch running terminal processes for crashes and stack traces. when an error appears, navigate to the failing file and line, diagnose, and fix it automatically. use when a dev server, watcher, or test process is running and may emit runtime errors to fix live.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, terminal, errors, monitoring, debugging]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
---

# Monitoring Terminal Errors

## Purpose

Continuously watch a running dev server, test runner, or build process for errors; navigate to failing files from stack traces; fix and confirm recovery via terminal output.

## Core Contract

| Step | Action | Stop condition |
|------|--------|----------------|
| Identify | Find terminal running target process | Process located |
| Read | Scan for error patterns | Stack trace extracted |
| Fix | Patch root cause at file:line | Hot reload / rebuild clean |
| Loop | Re-read terminal | Clean output or 5 failed attempts |

## Authority Order

1. Terminal output and stack trace — primary error source.
2. Failing file at cited line — fix target.
3. Cascading errors — fix first/root error first.
4. This skill's workflow below.
5. `Unknown` — report to user after 5 unresolved fix attempts.

## Workflow

### 1. Identify the Terminal

List terminal files and find the one running the target process:

```bash
head -n 10 <terminals_folder>/*.txt
```

Look for terminals running dev servers (`npm run dev`, `pnpm dev`, `python manage.py runserver`, etc.).

### 2. Read Terminal Output

Read the full terminal file content. Search for error patterns:

- **Stack traces**: `at <function> (<file>:<line>:<col>)`
- **Node.js**: `Error:`, `TypeError:`, `ReferenceError:`, `ENOENT`, `ECONNREFUSED`
- **Python**: `Traceback (most recent call last):` followed by `File "<path>", line <n>`
- **React/Next.js**: `Unhandled Runtime Error`, `Error: ...`, `Module not found`
- **Build errors**: `ERROR in`, `Failed to compile`, `SyntaxError`
- **Vite**: `[vite] Internal server error:`
- **TypeScript**: `error TS\d+:`

### 3. Extract the Source Location

From the stack trace, extract:
- File path
- Line number
- Error message

For Node.js: `at functionName (/path/to/file.ts:42:10)`
For Python: `File "/path/to/file.py", line 42, in function_name`

### 4. Navigate and Fix

1. Read the identified file around the error line
2. Understand the error (missing import, type mismatch, undefined variable, etc.)
3. Apply the fix
4. Re-read the terminal file to confirm the server recovered (hot reload should pick it up)

### 5. Loop

If the server is still showing errors after the fix, repeat from step 2. Stop when:
- The terminal shows a clean "compiled successfully" or equivalent
- No new errors appear in the output
- You've made 5 attempts without resolution (report to user)

## Tips

- Check for `exit_code` in the terminal file footer — if present, the process has crashed entirely and needs a restart
- Some errors cascade — fix the first/root error and the rest often disappear
- For HMR errors, the fix might just be saving the file again to trigger a rebuild

## Resource Map

No `references/` folder — error patterns and loop discipline live in this file.

## Validation

Fix MUST target the root stack frame when identifiable. Terminal MUST be re-read after each fix to confirm recovery. Process crash (`exit_code` in terminal footer) MUST trigger restart recommendation — not infinite fix loops.

## Failure Handling

- Process crashed → check `exit_code`; restart before continuing fixes.
- No stack trace → search terminal for first `Error:` or build failure line.
- Same error after 5 attempts → STOP; report findings and ask user.
- Multiple terminals → identify correct process via command in terminal metadata.
