# CI canary fixtures — DO NOT MERGE

Disposable witnesses for campaign L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1,
lane CG-CUTOVER item 4 (CURSOR_CANARY Gate 3). This directory exists only on
the canary branch. Each file is a deliberate known-good or known-bad input:

| File | Expected central result |
|---|---|
| `central_rule_bad.py` | SDK baseline `subprocess-shell-true` fires (known-bad) |
| `central_rule_good.py` | no finding (known-good) |
| `override_nosemgrep.py` | same defect with an inline `# nosemgrep`: a consumer suppression must not lower central coverage, so the central rule fires here |
| `biome_bad.json` | Biome format violation: central Biome (blocking) and the SDK Biome job must both fail |
| `override_ignored_dir/central_rule_bad_ignored.py` | same defect under a path the consumer's `.semgrepignore` excludes; the central rule still fires |
