# SonarCloud false-positive report — LLM/CLI path-escape on render_principals

**Project:** Quantum-L9_Cursor-Governance  
**PR:** https://github.com/Quantum-L9/Cursor-Governance/pull/25  
**Issue:** https://github.com/Quantum-L9/Cursor-Governance/issues/26  
**Rule message:** "LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path before accessing the file system."

## Resolution (basename-only API — issue #26)

Issue #26 / Sonar S6396 is addressed by narrowing the CLI contract further:

1. `--root` / `--out-dir` remain the only trusted directory bases.
2. `--registry`, `--tokens`, `--out` MUST be **basenames only** (a single path
   segment — no directories, no `..`, no absolute paths, no `~`, no `/` or `\`).
3. Paths are constructed only as `os.path.join(base, basename)` then checked with
   `os.path.realpath` + `os.path.commonpath([base, target]) == base` before
   every `open()` read/write.

Free-form relative escapes under trusted roots are no longer accepted, so the
taint source Sonar flagged cannot reach a traversable path. See
`require_basename` / `under_root` in `render_principals.py` and tests T3b/T3c.

## Reproduction

```bash
python3 environment/agents/tools/render_principals.py \
  --root environment/agents \
  --out-dir /tmp/l9test \
  --registry agent_registry.yaml \
  --tokens agent_tokens.local.json \
  --out auth_tokens.json
```

Absolute `--tokens /etc/passwd` or `--out ../escape.json` exit non-zero with
an explicit basename / escape error (covered by `test_validators.py`
T3b / T3c).

## Ask

Please confirm whether `os.path.commonpath([base, target]) == base` after
`join(base, relative)` is a recognized sanitizer for this LLM/CLI path-escape
rule on Python. If yes, treat prior findings on `render_principals.py` as FP.
If the rule requires a different API (e.g. basename-only), document that so
operators can comply without NOSONAR.

## Filing

Paste this report at:
https://community.sonarsource.com/c/help/sc/9
(or mark the issue False Positive in the SonarCloud UI for PR #25).
