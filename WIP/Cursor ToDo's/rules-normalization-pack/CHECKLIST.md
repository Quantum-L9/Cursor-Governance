# Rules Normalization Checklist

## Stage 1 - frontmatter (no behavior change)
- [ ] `docs/rules-frontmatter-archive.yaml` created before any edit
- [ ] Only `description`, `globs`, `alwaysApply` remain, in that order
- [ ] `activation:` removed - count: ____
- [ ] `authority:` removed - count: ____
- [ ] `context_cost:` removed - count: ____
- [ ] Stable-ID keys removed - count: ____
- [ ] `globs` dropped from all `alwaysApply: true` rules
- [ ] Empty `globs: []` removed (`05-ask-mode`)
- [ ] All globs converted to comma-separated string form
- [ ] Missing descriptions backfilled or flagged as intentionally manual
- [ ] No `alwaysApply` value changed in this stage

## Stage 2 - mechanical
- [ ] `93-perplexity-research-protocol` renamed `.md` -> `.mdc`
- [ ] Compliant frontmatter added to the resurrected rule
- [ ] References updated in `RULES-MANIFEST.yaml`
- [ ] Rule discovery mechanism to `.cursor/rules` identified: ____________
- [ ] Explicit component paths declared in `.cursor-plugin/plugin.json`
- [ ] `RULES-MANIFEST.json` and `.md` added to `.cursorignore`
- [ ] Regeneration make target added
- [ ] `tools/check_rules_standard.py` wired to Makefile + pre-commit
- [ ] Ratchet threshold set to measured baseline

## Stage 3 - retiering (one commit each)
- [ ] `92-learned-lessons` moved out (~7,339 tok/turn saved)
- [ ] `99-incident-report` moved to commands (~3,648 tok/turn saved)
- [ ] `00-global` split and trimmed under 4 KB
- [ ] `02-slash-commands` -> agent-selected
- [ ] `60-anti-patterns` -> agent-selected
- [ ] `30-memory.mdc` merge complete with precedence section
- [ ] `10-write-authority.mdc` merge complete with authority table
- [ ] `87-cursor-subagent-orchestration` -> `agents/`
- [ ] All 7 glob-scoping conversions done
- [ ] Prefix collisions resolved to zero
- [ ] `make rules-check` green at target budget

## Sign-off

| Field | Value |
|---|---|
| Operator | |
| Date | |
| Always-apply before | 182,427 B / ~45,606 tok |
| Always-apply after | |
| Rules count before / after | 65 / |
