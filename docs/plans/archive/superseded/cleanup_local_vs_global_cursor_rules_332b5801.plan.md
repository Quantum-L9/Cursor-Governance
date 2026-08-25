---
name: Cleanup local vs global Cursor rules
overview: Restore this repo's `.cursor/rules` from a broken symlink (currently duplicating global governance rules) back into a real local PlasticOS/Odoo overlay directory, relocate misplaced files in both directions, delete dead cruft, patch the shared wiring script (target-aware, fail-closed) with a regression test, and regenerate the manifest from final disk state.
todos:
  - id: restore-local-dir
    content: Remove .cursor/rules symlink, restore 24 tracked files via git restore --source=HEAD
    status: pending
  - id: move-to-global
    content: "Copy/verify/remove (no cross-repo git mv): move 05-recursive-execution-kernel.mdc and 96-output-discipline.mdc from local .cursor/rules to ~/.cursor-governance/rules"
    status: pending
  - id: move-to-local
    content: "Copy/verify/remove: move 30-odoo-native.mdc, 95-plasticos-equipment-policy.mdc, 98-odoo-sh-staging.mdc from ~/.cursor-governance/rules into local .cursor/rules"
    status: pending
  - id: delete-cruft
    content: Delete fastapi-python-microservices-serverless-cursor-rules.mdc
    status: pending
  - id: fix-wiring-script
    content: Patch setup_workspace_symlinks.sh with target-aware, fail-closed .cursor/rules logic (only repair the known legacy symlink target; stop on anything unexpected)
    status: pending
  - id: add-wiring-regression-test
    content: Add a small regression test script covering the 6 .cursor/rules states (missing / real dir / legacy symlink / unexpected symlink / non-dir file / already correct)
    status: pending
  - id: split-test-fix-policy
    content: Strip Odoo-specific content out of global 95-test-fix-policy.mdc, fold missing fixture rows into local 95-plasticos-test-fix-policy.mdc overlay
    status: pending
  - id: regenerate-manifest
    content: Regenerate RULES-MANIFEST.json/.md from the final governance rules/ directory listing (not incremental hand-edits)
    status: pending
  - id: verify
    content: Run validate_governance_symlinks.sh, directory listings, and git status --short in both repos to confirm final state
    status: pending
isProject: false
---

# Cleanup local vs global Cursor rules

## Root cause

`.cursor/rules` in this repo is currently a **symlink** to `/Users/macm2/.cursor-governance/rules` — the exact same target as `.cursor-commands` (which symlinks to `/Users/macm2/.cursor-governance`, the governance root). That's the literal duplication: `.cursor/rules` and `.cursor-commands/rules` now resolve to the identical folder.

This overwrote a real, git-tracked local overlay directory. `git status` shows 24 files under `.cursor/rules/*.mdc` as deleted from the working tree, but they still exist in git history (`git show HEAD:.cursor/rules/<file>`) — nothing is lost.

Cause: [ops/scripts/setup_workspace_symlinks.sh](file:///Users/macm2/.cursor-governance/ops/scripts/setup_workspace_symlinks.sh) unconditionally runs:

```
link_or_update "$WORKSPACE_DIR/.cursor/rules" "$GLOBAL_COMMANDS/rules" ".cursor/rules"
```

This forces every repo's `.cursor/rules` into a symlink, which contradicts this repo's own [.cursor/rules/01-cursor-governance-law.mdc](file:///Users/macm2/Library/CloudStorage/Dropbox/Repo_Dropbox_IB/IB-Odoo_19-1/.cursor/rules/01-cursor-governance-law.mdc) ("`rules/` — PlasticOS overlay") and the validator [validate_governance_symlinks.sh](file:///Users/macm2/.cursor-governance/ops/scripts/validate_governance_symlinks.sh), which already expects `.cursor/rules` to be a **real directory** (`pass ".cursor/rules/ (repo overlay)"` — it never requires a symlink there). It also matches Cursor's own documented convention: project rules live in `.cursor/rules`; shared/global rules are meant to be delivered as individual copies or symlinks *into* that directory, not by replacing the whole directory with one symlink.

## File-count reconciliation

- 24 files currently tracked under `.cursor/rules/` (in git HEAD, working tree currently shows them as deleted because of the symlink)
- − 2 moved out to global (`05-recursive-execution-kernel.mdc`, `96-output-discipline.mdc`)
- − 1 deleted (`fastapi-python-microservices-serverless-cursor-rules.mdc`)
- = **21 files retained** in the local overlay unchanged
- + 3 moved in from global (`30-odoo-native.mdc`, `95-plasticos-equipment-policy.mdc`, `98-odoo-sh-staging.mdc`)
- = **24 files in the final local `.cursor/rules/` directory**

## Cleanup matrix

**Restore — real local overlay directory (this repo), 21 files, no content changes:**

- `00-plasticos-master-context.mdc`, `01-cursor-governance-law.mdc`, `02-context7-auto-invoke.mdc`, `10-plasticos-workspace-kernel.mdc`, `30-plasticos-deploy-validation.mdc`, `35-plasticos-first-order-execution.mdc`, `40-plasticos-zero-stub-law.mdc`, `50-plasticos-web-lead-guard.mdc`, `70-github-api-commit.mdc`, `71-plasticos-security-model.mdc`, `75-plasticos-xml-data-rules.mdc`, `80-plasticos-testing-rules.mdc`, `81-ci-manifest-contract.mdc`, `82-ci-module-wiring.mdc`, `83-ci-phantom-enum.mdc`, `84-ci-odoo19-patterns.mdc`, `85-ci-naming-ruff.mdc`, `86-ci-github-actions.mdc`, `87-plasticos-code-graph-rag.mdc`, `88-plasticos-odoo-python-tooling.mdc`, `95-plasticos-test-fix-policy.mdc`
- All confirmed PlasticOS/Odoo-repo-scoped (globs on `plasticos_*/**`, `tests/**`, manifest/CI files, etc.)

**Move out — local to this repo → global governance rules, 2 files (domain-agnostic, no PlasticOS content):**

- `05-recursive-execution-kernel.mdc` — generic convergence/no-drift/provenance discipline for any artifact
- `96-output-discipline.mdc` — generic terse-output formatting rule. Kept as `alwaysApply: true` (unchanged behavior) — a suggestion to demote it to agent-requested or fold into Cursor User Rules was raised but not decided; deferred, not part of this pass.
- Destination: `/Users/macm2/.cursor-governance/rules/` (no filename collisions with existing global files)
- **Method (not `git mv` — these are two separate git repositories):** for each file, `cp` into the destination repo, `cmp -s` to verify byte-identical, then `rm` the source. Git will show this as an addition in the governance repo and a deletion in this repo — that is expected and correct.

**Move in — global governance rules → local to this repo, 3 files (Odoo/PlasticOS-specific, mis-filed in global):**

- `30-odoo-native.mdc` — "Scope: All `plasticos_*` modules in this repository"
- `95-plasticos-equipment-policy.mdc` — "Scope: `plasticos_facility_profile` module"
- `98-odoo-sh-staging.mdc` — hardcoded staging URL for this repo's Odoo.sh build
- Source: `/Users/macm2/.cursor-governance/rules/` → destination `.cursor/rules/` (no filename collisions with existing local files)
- Same copy → `cmp -s` verify → remove-source discipline, in the opposite direction.

**Delete — dead cruft, 1 file:**

- `fastapi-python-microservices-serverless-cursor-rules.mdc` — `alwaysApply: false`, `globs: []`, self-described as "not applicable... retained for reference only." Never triggers, adds no value. Recoverable from git history if ever needed.

**Fix — shared wiring script bug, 1 file (separate repo: `~/.cursor-governance`):**

Replace the unconditional `link_or_update .cursor/rules -> $GLOBAL_COMMANDS/rules` with **target-aware, fail-closed** logic — only repair the known legacy whole-directory symlink; never touch an unexpected symlink target, and never clobber a real directory:

```bash
ensure_local_rules_overlay() {
  local dir="$WORKSPACE_DIR/.cursor/rules"
  local legacy_target="$GLOBAL_COMMANDS/rules"

  if [ -L "$dir" ]; then
    local actual_target expected_target
    actual_target="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$dir")"
    expected_target="$(python3 -c "import os,sys; print(os.path.realpath(sys.argv[1]))" "$legacy_target")"
    if [ "$actual_target" = "$expected_target" ]; then
      rm "$dir"
      mkdir -p "$dir"
      echo "FIXED: .cursor/rules was a symlink to global rules -- converted to local overlay dir"
    else
      echo "ERROR: .cursor/rules is a symlink to an unexpected target ($actual_target) -- not touching it" >&2
      return 1
    fi
  elif [ -d "$dir" ]; then
    echo "OK: .cursor/rules/ (repo overlay)"
  elif [ -e "$dir" ]; then
    echo "ERROR: .cursor/rules exists but is neither a directory nor a symlink" >&2
    return 1
  else
    mkdir -p "$dir"
    echo "CREATED: .cursor/rules/ (empty repo overlay)"
  fi
}
```

Note: uses `python3 -c "os.path.realpath(...)"` rather than the `realpath` binary — `realpath` is GNU coreutils and is not present on stock macOS. The rest of `setup_workspace_symlinks.sh` already uses this same python3 pattern elsewhere (see `link_or_update`), so this stays consistent with the existing script style. Quoting is applied throughout so paths with spaces are handled correctly.

No changes needed to `validate_governance_symlinks.sh` or `check_governance_wiring.sh` — both already treat `.cursor/rules` as a directory, not a symlink.

**Add — regression test for the wiring fix, 1 new file (separate repo: `~/.cursor-governance`):**

A small bash test script (e.g. `ops/scripts/test_ensure_local_rules_overlay.sh`) that runs `ensure_local_rules_overlay` (or the patched script) against a `mktemp -d` workspace for each of these states, asserting the expected outcome and never touching a real repo:

1. `.cursor/rules` missing entirely → real empty directory created
2. `.cursor/rules` already a real directory with content → left untouched, content preserved
3. `.cursor/rules` is a symlink to the legacy global rules target → converted to a real empty directory
4. `.cursor/rules` is a symlink to some other, unexpected target → script exits non-zero, symlink left alone
5. `.cursor/rules` exists as a regular file (not a dir or symlink) → script exits non-zero, file left alone
6. `.cursor/rules` is already a real directory that used to be a symlink (idempotency) → running the fix twice is a no-op the second time

**Split — Odoo-specific content embedded inside a global file, 1 file (separate repo: `~/.cursor-governance`):**

- [rules/95-test-fix-policy.mdc](file:///Users/macm2/.cursor-governance/rules/95-test-fix-policy.mdc) (global) contains a full `## Odoo 19 Specific Notes` section (product `type='consu'` migration, Odoo 18-vs-19 table) plus a "Common Fixtures" table built from Odoo model names (`account.journal`, `account.move`, `res.company`, `res.partner`, `product.product`) — this is Odoo domain knowledge, not L9-generic.
- The local overlay [.cursor/rules/95-plasticos-test-fix-policy.mdc](file:///Users/macm2/Library/CloudStorage/Dropbox/Repo_Dropbox_IB/IB-Odoo_19-1/.cursor/rules/95-plasticos-test-fix-policy.mdc) already declares itself the Odoo-specific addendum ("Base policy is global 95-test-fix-policy") and already duplicates most of this content (product type table, 3 of 7 fixture rows) — the separation was intended but never finished.
- Action: remove the `## Odoo 19 Specific Notes` section and the Odoo-flavored "Common Fixtures" table from the global file, leaving only the generic "never skip tests, fix fixtures" principle, anti-pattern/correct-pattern examples (reworded to a domain-neutral fixture example), exception list, and enforcement checklist.
- Fold any fixture rows not already in the local overlay (Bank Journal, Company, Currency, Product) into `95-plasticos-test-fix-policy.mdc`'s fixture table so no information is lost.
- After editing, verify by grep: the global file must contain zero occurrences of `Odoo`, `PlasticOS`, `account.journal`, `account.move`, `res.company`, `product.product`; the local overlay must still state it extends the global rule.

## Manifest handling

`RULES-MANIFEST.json` / `RULES-MANIFEST.md` are regenerated **once, at the end**, from the actual final contents of `~/.cursor-governance/rules/` — not hand-patched incrementally after each move. For every `.mdc` file in the final directory, recompute: filename, `description`, `alwaysApply`, `globs`, first heading, and whether YAML frontmatter is present (matching the manifest's existing schema). Recompute `total_mdc_files`, `always_apply_true`, `always_apply_false` from the real count. Scan for duplicate filenames and duplicate first-headings across the final set as a sanity check.

(Not adding new manifest fields such as content-hash/digest or a "rule ID" column — that would be a manifest schema change beyond this cleanup's scope. Flagging it here rather than doing it silently.)

## Execution steps

0. Preflight (inline, not persisted to a new report file unless requested): `git status --short`, `readlink .cursor/rules`, `find ~/.cursor-governance/rules -maxdepth 1 -name '*.mdc'` — capture current state for comparison after each stage.
1. `rm .cursor/rules` (the symlink), then `git restore --source=HEAD -- .cursor/rules` to restore the 24 tracked files. Verify: `test -d .cursor/rules && test ! -L .cursor/rules && git status --short .cursor/rules`.
2. For `05-recursive-execution-kernel.mdc` and `96-output-discipline.mdc`: copy to `~/.cursor-governance/rules/`, `cmp -s` verify, remove from this repo's `.cursor/rules/`.
3. For `30-odoo-native.mdc`, `95-plasticos-equipment-policy.mdc`, `98-odoo-sh-staging.mdc`: copy from `~/.cursor-governance/rules/` into this repo's `.cursor/rules/`, `cmp -s` verify, remove from governance repo.
4. Delete `.cursor/rules/fastapi-python-microservices-serverless-cursor-rules.mdc`.
5. Patch `~/.cursor-governance/ops/scripts/setup_workspace_symlinks.sh` with the target-aware `ensure_local_rules_overlay` logic above.
6. Add the regression test script for that function/logic; run it locally against temp directories to confirm all 6 scenarios pass.
7. Edit `~/.cursor-governance/rules/95-test-fix-policy.mdc` to remove Odoo-specific sections; edit `.cursor/rules/95-plasticos-test-fix-policy.mdc` to fold in any missing fixture rows; grep-verify the split.
8. Regenerate `RULES-MANIFEST.json`/`.md` from the final `~/.cursor-governance/rules/` directory listing.
9. Verify: `bash .cursor-commands/ops/scripts/validate_governance_symlinks.sh` (expect `RESULT: PASS`); sorted `find .cursor/rules -maxdepth 1 -name '*.mdc'` and sorted `find ~/.cursor-governance/rules -maxdepth 1 -name '*.mdc'`; `git status --short` in both repos for final review. (Optional manual check for you: open Cursor Settings → Rules and confirm the restored local rules are listed.)

No commits or pushes will be made in either repo (this repo or `~/.cursor-governance`) — changes are left staged/unstaged for explicit review and approval, per standing no-auto-commit policy. This applies across both repositories touched.

## Explicitly out of scope (documented, not implemented, this pass)

- Redesigning how global governance rules get delivered as native Cursor project rules (e.g., symlinking individual global `.mdc` files into `.cursor/rules/` one-by-one) is a real follow-up worth doing later, but is a separate, larger change. Not implemented here — noted so it isn't lost.
- Whether `96-output-discipline.mdc` should be `alwaysApply: true`, agent-requested, or a Cursor User Rule instead of governance MDC — deferred; kept as `alwaysApply: true` (no behavior change) pending an explicit decision.
