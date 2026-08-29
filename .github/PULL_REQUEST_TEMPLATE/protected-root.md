<!-- L9_PROTECTED_ROOT_PR -->
<!--
  REQUIRED when this PR touches any additive_only root file
  (ops/config/root-file-protection.json): Makefile, AGENTS.md,
  CANONICAL_LAW.md, pyproject.toml, requirements.txt, conftest.py,
  .pre-commit-config.yaml, .gitleaks.toml, .mcp.json, CODEOWNERS,
  LICENSE, SECURITY.md, ORG_INVARIANTS.yaml.

  make pr injects this template. The Root-file append-only gate fails
  CI if the stamp above is missing from the PR body.

  Prefer append-only edits. A rewrite/deletion also needs a commit line:
    ALLOW-ROOT-DELETION: <path> — <reason with proof of necessity>
-->

## Protected-root PR

This PR touches additive-only repository-root files. Default template is not enough.

### Paths

<!-- One path per line. Must match the diff. -->

- ` `

### Edit mode (pick one per path)

- [ ] **Append-only** — existing lines kept; only new lines added (no `ALLOW-ROOT-DELETION`)
- [ ] **Justified rewrite** — commit contains `ALLOW-ROOT-DELETION: <path> — <reason>`

### Why a root file

<!-- What cannot be done in a non-root path. -->

### Proof of necessity (rewrites only)

<!-- Issue, failing gate, or law citation. Empty if every path is append-only. -->

## Problem

<!-- Symptom / failing gate this change fixes. -->

## Fix

## Risk

- [ ] Low — additive, reversible
- [ ] Medium — shared contract
- [ ] High — law / Makefile / lock / CI contract

## Evidence

```
$ make pr
```

## Reviewer focus

<!-- Especially: did this stay append-only? If not, is the marker exact? -->
