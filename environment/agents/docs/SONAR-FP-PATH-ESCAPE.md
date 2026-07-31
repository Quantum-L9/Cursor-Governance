# SonarCloud false-positive report — LLM/CLI path-escape on render_principals

**Project:** Quantum-L9_Cursor-Governance  
**PR:** https://github.com/Quantum-L9/Cursor-Governance/pull/25  
**Issue:** https://github.com/Quantum-L9/Cursor-Governance/issues/26  
**Rule message:** "LLMs running this code with faulty CLI arguments can escape file system restrictions. Refactor this code to validate the constructed path before accessing the file system."

## Why this is a false positive (after API change)

Cycle 4 changed the CLI so tainted free-form paths are **rejected**:

1. `--root` / `--out-dir` are the only trusted directory bases.
2. `--registry`, `--tokens`, `--out` MUST be relative (no absolute, no `~`, no `..`).
3. Paths are constructed only as `os.path.join(base, rel)` then checked with
   `os.path.realpath` + `os.path.commonpath([base, target]) == base` before
   every `open()` read/write.

This is the Sonar-documented sanitizer pattern for path traversal. Residual
flags after that pattern (pre-cycle-4 absolute CLI paths, and post-cycle-4
join+commonpath sinks) indicate the analyzer does not clear taint through
this helper for Python `Path`/`open` sinks in this rule family.

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
an explicit relative-path / escape error (covered by `test_validators.py`
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
