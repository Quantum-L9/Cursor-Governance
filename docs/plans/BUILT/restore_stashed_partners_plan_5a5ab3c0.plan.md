---
name: Restore stashed partners plan
overview: Restore only the later stashed Partners-first plan into its original path,
  then add the logistics BRS ownership section. Do not pop either stash.
todos:
- id: restore-plan-file
  content: Write only the stash@{4} untracked blob of the Partners-first plan back
    to docs/campaigns/11-03-26/, without popping the stash.
  status: completed
- id: add-logistics-section
  content: 'Insert the logistics BRS ownership section immediately before ## Out of
    scope in the restored plan.'
  status: completed
isProject: false
built: true
status: built
---

# Restore the stashed Partners-first plan

The file is not in the working tree. It is an untracked blob in two stashes created on `fix/merged-stack-material-contracts`. The current branch is `fix/documents-loop-query-batch`.

- `stash@{4}` — "hold concurrent edits during second publication attempt". This is the later copy: 654 lines, blob `2e5bc7b0`. Use this one.
- `stash@{5}` — "hold unrelated tree during stacked publication". Earlier 681-line copy, blob `bb7b1340`, plus the rest of the native-opportunity campaign pack.

Do not `git stash pop` or `git stash apply`. `stash@{4}` also contains logistics and documents model edits, a baseline deletion, and other plan JSON. Those stay in the stash.

## Restore one file

Write the later blob to [docs/campaigns/11-03-26/PLAN Partners First Native Opportunity Matching Canonical Revision.md](docs/campaigns/11-03-26/PLAN%20Partners%20First%20Native%20Opportunity%20Matching%20Canonical%20Revision.md) without staging it and without switching branches:

```bash
git show "stash@{4}^3:docs/campaigns/11-03-26/PLAN Partners First Native Opportunity Matching Canonical Revision.md" \
  > "docs/campaigns/11-03-26/PLAN Partners First Native Opportunity Matching Canonical Revision.md"
```

Leave both stashes in place.

## Add the logistics section

Insert this section in that restored file immediately before `## Out of scope` (currently the heading near line 425). Do not rewrite the opportunity-matching todos or the machine stub.

```markdown
## What belongs with logistics and is not installed

BRS-POS-10 is the Native-First chapter whose owner is plasticos_logistics plus Odoo Mail. All 16 of its rules are out of Documents scope. Eight are EXTERNAL_OWNER_OUT_OF_SCOPE, eight are cross-domain references. There is no BRS-POS-10-*.md anywhere in the tree. Logistics only cites those IDs from the crosswalk.

BRS-POS-09 was kept inside Documents even though its owner line includes Linda external mail. The rules that are actually Linda behavior are the single external reminder writer, the supplier/carrier/buyer clocks, the one-touch-per-day rule, and quiet hours (BRS-POS-09-R006 through R012). Documents OWNERSHIP_AND_INTEROP.md already says only Linda sends the external chase.

These should not move into logistics:

- BRS-POS-04 is commercial weight, owned by transaction/commercial.
- BRS-POS-05 is native stock, owned by Inventory, Purchase, and Sales.
- BRS-POS-06 through BRS-POS-08 are purchase, sales, claims, and accounting.
- BRS-POS-11 and BRS-POS-12 are security and sequencing.
```

The restored file will be untracked on `fix/documents-loop-query-batch`. It will not be committed unless you ask.

## Build evidence (auto)

- detected_at: `2026-11-05T15:35:38Z`
- conversation_id: `3daa1fcf-bcbe-4111-b358-32762565f298`
- generation_id: `b033b6be-587f-4f86-b7fb-421665b532ac`
- transcript: `/Users/ib-mac/.cursor/projects/Users-ib-mac-IB-Odoo-19-LOCAL-IB-Odoo-19/agent-transcripts/3daa1fcf-bcbe-4111-b358-32762565f298/3daa1fcf-bcbe-4111-b358-32762565f298.jsonl`
- todos at build time:
- `restore-plan-file`: completed
- `add-logistics-section`: completed
