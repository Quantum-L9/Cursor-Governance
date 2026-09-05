---
description: Name the authority chain and locate its rungs, because the two highest are not in context.
---

# Authority chain — and where to read the parts you cannot see

## The chain

Highest first. A lower rung never overrides a higher one.

| # | Rung | Where |
|---|---|---|
| 1 | **Constitution** | `CANONICAL_LAW.md` |
| 2 | **Autonomy Surface Profile** | `ops/autonomy/surface_profile.yaml` |
| 3 | **Operating instructions** | `AGENTS.md` |
| 4 | **Task procedures** | `skills/l9-*/SKILL.md`, invoked by name |
| 5 | **Agent-invented contracts** | none — it belongs in a rung above, in a PR |

## Rungs 1 and 3 are NOT in your context

`CANONICAL_LAW.md` (~47 KB) and `AGENTS.md` (~60 KB) are not agent memory files
on any surface. They do not load. What loads is this rule and the other
always-apply rules beside it — roughly a third of the rule corpus, the rest
being glob-scoped and attached only when a matching file is open.

So a `CANONICAL_LAW §N` or `AGENTS.md §N` cited in a rule, a skill, a commit
message, or a PR description is a **pointer to a file on disk**, not a quotation
you have already read. Read it before relying on it. Do not reconstruct a
section from its number, its title, or another rule's summary of it.

## Both documents are base + amendments

`CANONICAL_LAW.md` carries dated sections after §14 that **supersede** earlier
ones, and `AGENTS.md` carries its own after §20. A heading reading
`## 6.2.4 … (2026-08-21) — supersedes §6.2 push-denial phrasing` means §6.2 as
written is no longer the law.

Therefore: after reading a section, scan the tail of the file for a later dated
section naming it. Reading §6.2 alone and acting on it is how a retracted rule
gets enforced.

## Section index — so you read 40 lines, not 47 KB

**`CANONICAL_LAW.md`** — §1 SSOT · §2 IDE adapter model · §3 user-level config ·
§4 naming · §5 GitHub SSOT · §6 repository wiring · §6.1 autonomy velocity ·
§6.2 L4 local autonomy · §7 anti-patterns · §8 memory layer · §9 intelligence
mining · §10 governance enforcement · §11 diagnose-first · §12 mandatory pre-PR
local gate · §13 integration branch · §14 Openclaw PAT authority.

**`AGENTS.md`** — §1 mission · §2 activation · §3 autonomy and merge · §4 publish
path · §5 interpreter · §6 toolchain pins · §7 Graphiti · §8 secrets · §9 SSOT
files · §10 symlink law · §11 workspace kinds · §12 change policy · §13 PE
adapter · §14 root files are append-only · §15 WIP corpus · §16 SessionStart
plan audit · §17 stack-safe merge · §18 pre-commit "files were modified" ·
§19 guidance for AI agents · §20 final principle.

## What this rule is not

It is not a summary of either document and must never grow into one — a summary
in the always-apply plane becomes a competing SSOT that drifts from the law it
paraphrases, which is the failure `00-global` already forbids. Its whole job is
to make the invisible rungs findable, and to stop a section number being
mistaken for something you have read.

<!-- generated-from: rules/01-authority-chain.mdc; do-not-edit -->
