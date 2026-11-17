---
name: Invariant citation map
overview: Update root INVARIANTS.md citations and the Claude invariants pointer so later rule work can follow version 2.2.0 without reading deleted workflows. Normative rule text stays.
todos:
  - id: status-block
    content: Add the v2.2.0 status block to INVARIANTS.md without changing version or conflict-row rule text
    status: pending
  - id: enforcement-map
    content: Retarget the enforcement map and deleted-workflow citations to checks that exist in ci.yml
    status: pending
  - id: claude-pointer
    content: Replace the 18 CI-enforced count in .claude/rules/invariants.md with a pointer to the root file
    status: pending
  - id: citation-test
    content: Add the citation pytest and run it with the external-intelligence contract test
    status: pending
isProject: false
---

# Invariant citation map

Bind this change to live [INVARIANTS.md](INVARIANTS.md) version 2.2.0. [docs/campaigns/INVARIANT_ALIGNMENT_AND_IRREDUCIBILITY.md](docs/campaigns/INVARIANT_ALIGNMENT_AND_IRREDUCIBILITY.md) is the reason `POS-INV-21` and later stay unadmitted. That receipt is on `origin/Staging` as of `#403` (`29bc7ca0`). [docs/campaigns/future-add-ons/PlasticOS_Export/GOVERNANCE/V2_2_TO_V3_1_PRELIMINARY_MAPPING.md](docs/campaigns/future-add-ons/PlasticOS_Export/GOVERNANCE/V2_2_TO_V3_1_PRELIMINARY_MAPPING.md) is the preserve-versus-conflict split. Neither draft is copied into the root file. Do not edit those campaign files, `.cursor/rules/`, `AGENTS.md`, or `CLAUDE.md`.

`INVARIANTS.md` is `managed` in [ops/config/root-file-protection.json](ops/config/root-file-protection.json). No `ALLOW-ROOT-DELETION` marker.

## Baseline

Re-read on 2026-11-08 against `origin/Staging` `29bc7ca080b5d90f5bd11658e575a5c27c54887c` (`fix(rehearsal): run the sync on this checkout (#403)`). The previous pin `209bf83c` is an ancestor, not the branch point. Between those commits the only plan input that changed is the alignment receipt landing on Staging. `INVARIANTS.md` is still Constitutional version 2.2.0, last updated 2026-08-30, and still cites `test-quality.yml`, `odoo-audit.yml`, and `pr-gate.yml`. [.claude/rules/invariants.md](.claude/rules/invariants.md) still says “18 CI-enforced invariants.” The `ci.yml` steps this plan names are still present, including `ci/check_name_literal.py`, `ci/check_no_local_intelligence.py`, `ci/check_pipeline_v2_guard.py`, `ci/check_acl_completeness.py`, and `ci/check_banned_identifier.py`.

Branch from `origin/Staging` at `29bc7ca0`. Do not branch from `fix/sudo-authorization-markers` or from `fix/rehearsal-evidence-20261108` (that checkout is nine commits ahead of Staging). Publish later with `make pr` into `Staging`.

## Status block

Insert a short block under the version line. Keep `Version: 2.2.0`. Do not renumber.

- Version 2.2.0 remains the constitution.
- Rows with a named check below are enforced by that check in [.github/workflows/ci.yml](.github/workflows/ci.yml).
- Invariants 4, 5, 7, and 8 are open conflicts. Their current sentences stay in force until a later pull request replaces that sentence in this file.
- `POS-INV-21` and later are not admitted. Domain thresholds stay in the owning BRS.

The block must keep the phrases `tests/contracts/test_external_intelligence_authority.py` already requires in the invariant 19 section: `Single External Intelligence Authority`, `ADR-003-single-external-intelligence-authority`, and `not architectural authority`.

## Enforcement map

Replace the sentence that says every invariant has an automated tool. The map lists a check only when that check exists. Conflict rows 4, 5, 7, and 8 stay in the map as citations only. Their rule sections are not rewritten.

Preserve rows, pointed at current jobs:

- 1 and 3: pre-commit `odoo-patterns`, job `static-checks`, `scripts/check_odoo_patterns.sh`. Also retarget the invariant 1 **Enforcement** line that still names `test-quality.yml` and `odoo-audit.yml` to `static-checks` in `ci.yml`. Leave the forbidden-pattern list.
- 2: pre-commit `module-wiring` and `circular-deps`, `scripts/check_module_wiring.py` and `ci/check_circular_deps.py`, job `static-checks`.
- 9: pre-commit `orphan-model-refs`, `ci/check_orphan_model_refs.py`, job `static-checks`.
- 10 and 14: no `ci.yml` check. Keep “code review”. Do not invent a script. Invariant 10’s `odoo_test` sentence stays.
- 12: job `static-checks`, `python3 ci/check_name_literal.py` (the step at `ci.yml` “_name string literal enforcement”). Replace `odoo-audit.yml` in the invariant 12 detection line and in the forbidden parenthetical. The prohibition `_name` must be a string literal stays.
- 13: pre-commit `field-integrity` and `automation-field-refs`, `ci/check_field_integrity.py`, job `static-checks`.
- 15: pre-commit `cron-invariants`, `tools/cron_invariant_check.py`, and `tests/test_cron_invariants.py` under job `pure-python-tests`.
- 16: do not keep `ci/check_pipeline_v2_guard.py` as this row’s check. That script only fences `pipeline_v2` imports. Record “no dedicated ci.yml check; code review.” Leave the lazy-import rule text, including its example.
- 17: pre-commit `package-init` and `module-wiring`, `ci/check_package_init.py` and `scripts/check_module_wiring.py`, job `static-checks`.
- 18: pre-commit `odoo19-xml` and `xpath-stability`, `ci/check_odoo19_xml.py` and `ci/check_xpath_stability.py`, job `static-checks`.
- 19: add the missing map row from the section that already names `ci/check_no_local_intelligence.py` and the two contract tests. That script already runs in `static-checks`. Do not edit the invariant 19 rule.
- 20 / BAN001: pre-commit `banned-identifier`, `ci/check_banned_identifier.py`, job `static-checks`. Leave the BAN001 section byte-for-byte except where a deleted workflow name appears outside it.

Conflict-row citations already inside the map, script names only:

- 5: `ci/check_pipeline_v2_guard.py` does run in `static-checks`. Point the workflow column at `static-checks`. Do not rewrite the graph-isolation rule.
- 8: `ci/check_acl_completeness.py` runs in `static-checks`, and the pre-commit hook is warn-only. Replace the workflow value `audit`. Do not rewrite the ACL formula.

Other dead citations in the same file, names only:

- False-positive row that says excluded in `pr-gate.yml`: say the ruff exclusion lives in `pyproject.toml`. Do not drop or add module names in that row.
- Enforcement Strategy: `ci.yml` jobs `lint`, `static-checks`, `pure-python-tests`, `gate-sdk-tests`, `secret-scan`, and `audit-baseline` run in parallel, then `ci-gate-result` (`needs` those six). Delete the “11 workflow files” count and the sequential `lint → static-checks → pure-python-tests` claim. Pre-commit hook names that still exist in [.pre-commit-config.yaml](.pre-commit-config.yaml) stay.

## Claude pointer

In [.claude/rules/invariants.md](.claude/rules/invariants.md), delete “18 CI-enforced invariants.” State that root `INVARIANTS.md` is the authority and the count is the set of sections in that file. Keep the path globs, the meta-rule, the quick-gate commands, and the three overlay-rule pointers.

## Proof

Add `tests/test_invariants_enforcement_citations.py`. It reads only `INVARIANTS.md` and `.claude/rules/invariants.md`. It asserts version 2.2.0, the four open conflict numbers in the status block, that `POS-INV-21` is named as not admitted, that `odoo-audit.yml`, `pr-gate.yml`, `test-quality.yml`, and `module-check.yml` do not appear in `INVARIANTS.md`, and that the Claude pointer does not say “18 CI-enforced”. Run `python3 -m pytest tests/test_invariants_enforcement_citations.py tests/contracts/test_external_intelligence_authority.py -q`.

## Out of scope

Layer diagrams, universal `noupdate`, the blanket ACL formula, local-matcher rule deletions, `AGENTS.md`, `CLAUDE.md`, admitting `POS-INV-21` through `POS-INV-26`, and any edit under `docs/campaigns/`.
