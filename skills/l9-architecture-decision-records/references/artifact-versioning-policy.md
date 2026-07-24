<!-- L9_META
l9_schema: 1
parent: l9-architecture-decision-records
origin: migrated-from profiles/versioning.md
sources: [profiles/versioning.md]
tags: [versioning, semver, governance-artifacts, archival]
status: active
/L9_META -->

# Artifact Versioning Policy

Versioning for **governance artifacts** — rules, skills, references, commands, kernels. For code,
follow the repo's own release convention; this covers the governance tree.

## Semantic versioning

`MAJOR.MINOR.PATCH`

| Bump | When |
|---|---|
| MAJOR | A rule's meaning changes such that previously-compliant behavior is now a violation |
| MINOR | New guidance, new section, new capability — additive |
| PATCH | Clarification, typo, link repair, formatting — no behavioral change |

The test for MAJOR is behavioral, not structural: *would an agent that followed the old version be
wrong under the new one?* If yes, MAJOR. Reorganizing a document without changing what it requires is
a PATCH regardless of how many lines moved.

## Where the version lives

In the artifact's `L9_META` header, when it carries a version field. Do not maintain a parallel
version registry — a version that can disagree with the file is worse than no version.

## Archival

When an artifact is retired rather than edited:

- Move it under `_archived/`, do not delete it. Archived paths are excluded from live vocabulary and
  reference checks by design.
- State in the archived file what replaced it, so the trail is followable forward.
- Preserve the history documents that explain a migration. Erasing the record of why a change happened
  destroys the reason future readers need most.

## Change discipline

Governance edits are edits: show the change and wait for approval before committing. A version bump
does not authorize a commit.

## Not implemented

The original profile described auto-incrementing versions on structural change, `manifest.json`
updates on every validated commit, and `version_audit.json` diff reports. None exists. Versioning is
**manual and judgment-based** — apply the MAJOR test above rather than expecting automation.
