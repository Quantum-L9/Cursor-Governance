# NORMALIZE_TASK - skills

Four stages. Stages 1-3 are safe. Stage 4 changes routing behavior.

## STAGE 1 - Nest non-native frontmatter (lossless)

### 1.1 Archive first

Write `docs/skills-frontmatter-archive.yaml` capturing every skill's original
frontmatter verbatim before any edit. This is the undo record.

### 1.2 Nest, do not strip

For every `skills/**/SKILL.md`, move every key that is not `name`,
`description`, `paths`, or `disable-model-invocation` under `metadata:`.

Expected movers based on the audit: `skill_schema`, `layer`, `role`, `tags`.
If a key named `metadata` already exists, merge into it rather than replacing.

Emit field order: `name`, `description`, `paths`,
`disable-model-invocation`, `metadata`.

Do not alter any value. Do not touch `description` text. Do not add `paths`.

### 1.3 Verify name/folder agreement

`name` must equal the parent directory name. Report every mismatch. Do not
auto-rename either side - a rename breaks `/skill-name` invocation and any
reference in `AUTONOMY_MANIFEST.yaml`.

### 1.4 Check the manifest coupling

`skills/AUTONOMY_MANIFEST.yaml` is 22.5 KB and may index skills by the fields
just moved. Grep it for `skill_schema`, `layer`, `role`, and `tags`. If it
reads them from SKILL.md frontmatter, update its accessor paths to the nested
location. Report the finding either way. Do not proceed to Stage 2 with a
broken manifest.

## STAGE 2 - Archived skill lockdown

### 2.1 Enumerate

List every skill under `skills/_archived/` with its
`disable-model-invocation` value.

### 2.2 Lock

Add `disable-model-invocation: true` to any archived skill missing it. Known
gap: `_archived/l9-pr-analysis`.

### 2.3 Recommend relocation

Report whether `_archived/` sits inside the discovered skills tree. If it does,
recommend moving it to `docs/archived-skills/` and state exactly which
references would need updating. Do not perform the move in this run.

## STAGE 3 - Audit report (measure only)

Write `docs/skills-inventory.md` containing:

### 3.1 Inventory table

`skill | description chars | paths set | disable-model-invocation | non-native keys | body lines`

### 3.2 Discovery footprint

- count of live skills
- total bytes of `name` + `description` across live skills
- estimated tokens (bytes / 4)
- comparison against the 16,384-byte budget

### 3.3 Description flags

- descriptions under 150 chars - triggers likely missing
- descriptions over 500 chars - body leaking into frontmatter
- descriptions with no `use when` clause
- descriptions with no negative trigger, for the overlap clusters named in
  STANDARD.md Section 3

### 3.4 Collision check

For each overlap cluster, quote the competing descriptions side by side so a
human can judge whether an agent could distinguish them. Do not rewrite.

## STOP and report

## STAGE 4 - `paths` scoping (per-skill approval)

Work `PATHS-PROPOSAL.md`. One skill per commit.

For each proposed scoping:

1. State the glob and the exact set of files it currently matches in this repo.
2. Confirm that set is non-empty. An empty match means the skill is now dead.
3. Confirm agreement with any overlapping rule glob (see PATHS-PROPOSAL.md
   verification section).
4. Test by opening a matching file and confirming the skill appears; then open
   a non-matching file and confirm it does not.
5. Re-run `make skills-check`.

Never scope a skill listed as deliberately unscoped without arguing why the
trigger is actually file-detectable.
