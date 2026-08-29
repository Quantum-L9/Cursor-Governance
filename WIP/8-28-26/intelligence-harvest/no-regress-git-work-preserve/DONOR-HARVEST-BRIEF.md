# Donor Harvest Brief — /Users/ib-mac/Cursor-Governance/docs/plans/novel_remainder_no-regress_0429bc04.plan.md → skills/l9-git-work-preserve [portable leftover-work no-regression invariants]

## Executive Picture
Status: PARTIAL. Highest-leverage nugget: c-path-union-not-cherry-pick.

## Source Identity
```json
{'bytes': 13617, 'file_count': 1, 'inventory_status': 'PASS', 'kind': 'file', 'note': 'Untracked plan at inventory time; no git blob sha.', 'path': '/Users/ib-mac/Cursor-Governance/docs/plans/novel_remainder_no-regress_0429bc04.plan.md', 'ref': None, 'remote': None, 'sha256': '971845994af946b1fb39f0496e4b8a5a639d193f88a6fc04f41b51d77e90b2df'}
```

## Inventory
- docs/plans/novel_remainder_no-regress_0429bc04.plan.md | canonical

## System Reconstruction
```json
{'control_flow': [{'from': 'classify unique vs baseline', 'relation': 'feeds', 'to': 'allowlist JSON'}, {'from': 'allowlist JSON', 'relation': 'gates copy set; empty is stop', 'to': 'dedicated baseline worktree'}, {'from': 'path-union extract', 'relation': 'must complete before', 'to': 'prune-execute'}], 'dependencies': [{'name': 'git cat-file / worktree / pathspecs', 'used_by': 'path-absent copy and extract'}, {'name': 'ops/scripts/agent_worktree_start.sh', 'used_by': 'dedicated baseline worktree'}, {'name': 'ops/scripts/sync_generated_artifacts.py GENERATED_PATH_PREFIXES', 'used_by': 'generated skip and regen-not-copy'}], 'identity': 'A leftover-work remainder system: reclassify unique bytes against a fetched baseline, emit a copy/skip allowlist, port only path-absent layout-native paths onto a dedicated baseline worktree, publish by theme, then prune only patch-id-absorbed refs.', 'must_not_own': ['donor census counts, SHAs, branch names, and named file lists', 'l9-repo-sync /ff parking', 'surface-profile push/merge authorization', 'live SSOT vs bak clone selection', 'implementation edits under skills/l9-git-work-preserve'], 'ownership_boundaries': [{'owner': 'skills/l9-git-work-preserve harvest classifier', 'owns': 'porcelain dirty/untracked path classes vs baseline'}, {'owner': 'skills/l9-git-work-preserve extract-workflow', 'owns': 'one-ref local extract; currently cherry-pick or path-limited commits'}, {'owner': 'skills/l9-git-work-preserve prune-policy', 'owns': 'delete authority: prune_candidate and archive_ref with patch_id only'}, {'owner': 'skills/l9-repo-sync', 'owns': 'in-place catch-up and parking of unique work; does not harvest or prune'}, {'owner': 'this harvest', 'owns': 'transfer semantics and acceptance tests only; no skill mutation'}], 'workflows': [{'evidence_ids': ['e-donor-classifier', 'e-donor-allowlist-empty', 'e-donor-path-union', 'e-donor-prune-last'], 'id': 'no-regress-remainder', 'steps': ['re-inventory and re-diagnose vs fetched baseline', 'emit copy/skip/reason allowlist; stop if copy set empty', 'spawn dedicated worktree from fetched baseline', 'copy path-union of unique paths through the allowlist', 'regen generated artifacts from copied sources only', 'publish one theme per PR on the stack; no merge', 're-diagnose; prune-execute patch-id absorbed refs last']}]}
```

## Surface / Target Graph
- no-regression classifier | docs/plans/novel_remainder_no-regress_0429bc04.plan.md | plan-prose
- allowlist gate | docs/plans/novel_remainder_no-regress_0429bc04.plan.md | plan-todo-T2
- path-union extract | docs/plans/novel_remainder_no-regress_0429bc04.plan.md | plan-todo-T5
- themed publish | docs/plans/novel_remainder_no-regress_0429bc04.plan.md | plan-todo-T8
- prune-last | docs/plans/novel_remainder_no-regress_0429bc04.plan.md | plan-todo-T9

## Duplicate and Drift Register
- Porcelain harvest classifies dirty/untracked paths with cat-file against baseline, but does not scan unique committed paths on keep_push or preserve tips. | path-absent copy applied to diagnosed ref trees as well as porcelain | Donor is stronger on committed leftover trees; beneficiary already owns the porcelain case.
- Extract workflow still allows cherry-pick of a whole diagnosed ref; donor forbids whole-branch cherry-pick because mixed refs carry baseline overwrites and deletes. | path-union through the allowlist | Port path-union; keep cherry-pick only when the diagnosis receipt proves the commit range is path-limited and add-only.
- already_on_baseline is a hard skip; donor allows an add-only exception when the dirty diff deletes zero lines that still exist on baseline. | default skip with explicit add-only exception | Port the exception as hardening, not as a default overwrite.

## Nugget Register
- c-path-union-not-cherry-pick | Path-union extract, never whole-branch cherry-pick | PORT_WITH_HARDENING | leverage=5 | destination=skills/l9-git-work-preserve/references/extract-workflow.md
- c-path-absent-copy | Copy iff path absent on baseline | PORT_WITH_HARDENING | leverage=5 | destination=skills/l9-git-work-preserve/scripts/harvest_worktree_dirt.py classify_path plus extract of diagnosed leftover trees
- c-allowlist-gate | Durable copy/skip allowlist; empty copy set is stop | PORT_WITH_HARDENING | leverage=4 | destination=skills/l9-git-work-preserve harvest then extract handoff
- c-add-only-dirty-on-baseline | Add-only exception for dirty-on-baseline paths | PORT_WITH_HARDENING | leverage=4 | destination=skills/l9-git-work-preserve/scripts/harvest_worktree_dirt.py already_on_baseline handling
- c-layout-native-prefixes | Copy only layout-native prefixes | CONFIGURE | leverage=4 | destination=skills/l9-git-work-preserve harvest classifier declarative prefix/generated/secret config
- c-named-dangling-recover | Recover dangling objects only when named and allowlisted | PORT_WITH_HARDENING | leverage=3 | destination=skills/l9-git-work-preserve extract optional dangling recover
- c-bytes-before-delete | Committed copy before unique-path delete | PORT_WITH_HARDENING | leverage=3 | destination=skills/l9-git-work-preserve harvest unique_plans execute notes
- c-themed-stacked-publish | One theme per PR on the stack, no merge | MERGE_WITH_EXISTING | leverage=3 | destination=skills/l9-git-work-preserve/references/harvest-workflow.md Publish
- c-prune-after-extract | Prune last; patch-id only; keep keep_push | MERGE_WITH_EXISTING | leverage=4 | destination=skills/l9-git-work-preserve/references/prune-policy.md plus compact workflow step 5
- c-regen-generated-not-copy | Regen generated artifacts; never copy stale generated | MERGE_WITH_EXISTING | leverage=3 | destination=skills/l9-git-work-preserve/references/harvest-workflow.md Execute step 6
- c-dedicated-worktree | Dedicated baseline worktree; never scoop shared dirty clone | MERGE_WITH_EXISTING | leverage=3 | destination=skills/l9-git-work-preserve/references/harvest-workflow.md Execute

## Beneficiary Fit
- c-path-union-not-cherry-pick | PORT_WITH_HARDENING | skills/l9-git-work-preserve/references/extract-workflow.md
- c-path-absent-copy | PORT_WITH_HARDENING | skills/l9-git-work-preserve/scripts/harvest_worktree_dirt.py classify_path plus extract of diagnosed leftover trees
- c-allowlist-gate | PORT_WITH_HARDENING | skills/l9-git-work-preserve harvest then extract handoff
- c-add-only-dirty-on-baseline | PORT_WITH_HARDENING | skills/l9-git-work-preserve/scripts/harvest_worktree_dirt.py already_on_baseline handling
- c-layout-native-prefixes | CONFIGURE | skills/l9-git-work-preserve harvest classifier declarative prefix/generated/secret config
- c-named-dangling-recover | PORT_WITH_HARDENING | skills/l9-git-work-preserve extract optional dangling recover
- c-bytes-before-delete | PORT_WITH_HARDENING | skills/l9-git-work-preserve harvest unique_plans execute notes
- c-themed-stacked-publish | MERGE_WITH_EXISTING | skills/l9-git-work-preserve/references/harvest-workflow.md Publish
- c-prune-after-extract | MERGE_WITH_EXISTING | skills/l9-git-work-preserve/references/prune-policy.md plus compact workflow step 5
- c-regen-generated-not-copy | MERGE_WITH_EXISTING | skills/l9-git-work-preserve/references/harvest-workflow.md Execute step 6
- c-dedicated-worktree | MERGE_WITH_EXISTING | skills/l9-git-work-preserve/references/harvest-workflow.md Execute

## Safety and Portability Audit
- CONFIRMED | Donor plan was inventoried and read, not executed. No harvest/extract/prune scripts were run against leftover refs.
- CONFIRMED | No files under skills/l9-git-work-preserve were created or edited.
- CONFIRMED | Donor kernel filenames, plan filenames, SHAs, branch names, and census counts were classified REJECT, not PORT.
- CONFIRMED | Secret globs and Legal Defense paths were not copied into transferable contracts.

## Concept Acceptance Tests
- c-path-union-not-cherry-pick | Given a keep_push ref whose commit range both adds a path absent from baseline and deletes a path present on baseline | When extract runs | Then only the path-absent allowlisted paths appear on the extract branch | Must not cherry-pick the whole ref or apply the baseline delete
- c-path-absent-copy | Given a unique blob whose bytes do not appear on baseline but whose path already exists at baseline | When harvest classify and extract run | Then the path is skipped as already on baseline | Must not overwrite the baseline path because the blob looks novel
- c-path-absent-copy | Given a unique blob on a keep_push tip at a path that fails cat-file on baseline | When extract runs after allowlist | Then that path is eligible to copy | Must not ignore committed leftover trees solely because porcelain is clean
- c-allowlist-gate | Given classifier output whose unique copy set is empty | When extract is considered | Then extract stops successfully and copies nothing | Must not treat empty unique as failure or copy skipped paths
- c-allowlist-gate | Given an allowlist with copy and skip rows each carrying a reason | When extract runs | Then only copy-set paths are copied | Must not copy a skipped path because it appeared in harvestable earlier
- c-add-only-dirty-on-baseline | Given a dirty file whose path exists on baseline and whose diff deletes a line that still exists on baseline | When harvest classify runs | Then the path is skipped | Must not overwrite or delete any baseline line
- c-add-only-dirty-on-baseline | Given a dirty file whose path exists on baseline and whose diff adds lines and deletes zero baseline-still-present lines | When extract is allowed the add-only exception | Then only the added lines may be appended | Must not rewrite the baseline file wholesale
- c-layout-native-prefixes | Given a unique path whose first directory is absent from the fetched baseline tree layout | When classify runs | Then the path is skipped as foreign overlay | Must not copy it because it is path-absent
- c-layout-native-prefixes | Given a unique path matching the live generated-prefix SSOT | When classify and extract run | Then the path is skipped and later regen may recreate it from copied sources | Must not copy the stale generated file from a behind tree
- c-named-dangling-recover | Given a dangling blob with no recoverable path name | When extract considers dangling recover | Then the blob is left dangling | Must not write it to a guessed path on the extract branch
- c-named-dangling-recover | Given a dangling blob whose recovered path fails the allowlist | When extract considers dangling recover | Then the blob is left dangling | Must not copy it because the object is unique
- c-bytes-before-delete | Given a unique path that harvest intends to remove from the donor location | When the remove is considered | Then a committed copy already exists at the destination path | Must not delete the unique path while it is the only copy
- c-themed-stacked-publish | Given harvestable unique_plans and unrelated unique_product paths | When publish runs | Then they land on separate PRs on the default stack and none are merged by harvest | Must not mix the themes in one PR or stack onto an unrelated open PR
- c-prune-after-extract | Given a leftover ref still classified keep_push after extract | When prune-execute is considered | Then the ref is kept | Must not delete keep_push or content_superset refs
- c-prune-after-extract | Given unique paths have not yet been extracted | When prune-execute is considered | Then prune is refused | Must not delete a ref whose unique paths are not yet on an extract branch
- c-regen-generated-not-copy | Given a leftover tree containing both a unique source and a generated manifest | When extract runs | Then the source may copy and generated files are regenerated from the SSOT if needed | Must not copy the leftover generated manifest
- c-dedicated-worktree | Given a dirty shared primary checkout and leftover unique paths | When harvest extract runs | Then copies land on a dedicated worktree started from fetched baseline | Must not stage, checkout, or apply on the shared dirty clone, or apply a behind-baseline dirty tree wholesale
- c-skip-ssot-bak | Given this harvest | When beneficiary fit is applied | Then SSOT/bak skip stays local to this machine's clone map | Must not add bak-clone skip lists to l9-git-work-preserve
- c-plan-is-push-auth | Given a proposal to treat harvest completion as push authorization | When beneficiary fit is applied | Then the concept is rejected and publish stays ask-first unless the surface profile already authorizes it | Must not record plan-build as harvest skill authority
- c-hardcoded-instances | Given harvest.json after qualification | When nugget semantic contracts and acceptance tests are inspected | Then they speak in baseline/cat-file/allowlist/path-union language | Must not name donor kernel files, plan filenames, SHAs, branch names, or census counts as the contract

## Rejected and Local Concepts
- c-skip-ssot-bak | KEEP_LOCAL | Skip live SSOT and bak clones unless path missing from workspace extract
- c-plan-is-push-auth | REJECT | Plan-build as push authorization
- c-hardcoded-instances | REJECT | Donor filenames, SHAs, census, and theme counts

## Highest-Leverage Next Action
c-path-union-not-cherry-pick

## UNKNOWNs
- Whether keep_push path-union should be a new script or extract-workflow prose only.
- Whether layout-native prefixes belong in harvest-workflow.md or a YAML config beside the classifier.
- Whether the add-only dirty-on-baseline exception should be an explicit classifier class or remain default-skip with a documented override.
