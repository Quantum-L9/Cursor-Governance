---
name: l9-pe-campaign-activate
description: Run the only live Program Execution campaign front door, `make campaign INTENT=`, from a complete direct campaign-source.v2, architecture intent, activate seed, plan, or brief through verified local commits. Use when the user asks to author from the canonical campaign template, activate a campaign, run a PE campaign, compile campaign source, emit campaign seeds, or take a brief through Program Execution. Do not call PEC, inner compile/accept scripts, PR publication, or merge as substitutes.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, program-execution, campaign, campaign-source-v2, compiler, activate, merge]
  owner: igor_beylin
  status: active
  version: 1.4.0
  updated: 2026-09-13
---

# PE Campaign Activation

## Use the canonical direct-source template

For a fully specified campaign, start with the repository canonical source, not a
historical three-file pack, an `INTENT.yaml`, or a hand-assembled Blueprint:

```text
environment/program-execution/templates/campaign-source-v2/CAMPAIGN_SOURCE.yaml
```

Read [references/canonical-template.md](references/canonical-template.md) before
editing a direct source. Copy the template to a working authoring location,
replace its verified campaign facts, then run the read-only preflight. Do **not**
put a hand-authored campaign directory under `environment/program-execution/campaigns/`;
the runner serializes the accepted source and generated integrity receipt into an
isolated worktree.

```bash
repo_root="${L9_REPO:-$HOME/.cursor-governance}"
make -C "$repo_root" campaign-check-input INTENT=path/to/CAMPAIGN_SOURCE.yaml
make -C "$repo_root" campaign INTENT=path/to/CAMPAIGN_SOURCE.yaml
```

The direct source is the only operator-authored artifact required by this route.
`source-integrity-receipt.json`, the Blueprint, and the PEC workspace are
runner- or controller-generated artifacts. PEC consumes the validated Blueprint;
it is not a live campaign front door.

## Purpose

Run the single live Program Execution front door from operator input through
Blueprint, Program Lock, bounded Peer Execution, Controller verification, and
**local commits only**.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<path>
```

The front door classifies direct `campaign-source.v2`, declared or classified
architecture intent, activate seeds, plans, and briefs before selecting a
compiler. Use a direct source when the campaign already has complete semantics.
Do not flatten rich architecture prose through brief → activate just because it
lacks frontmatter.

## Authority law

- Program Execution owns design projection, readiness, leases, worktrees,
  provider-neutral execution, independent verification, evidence, and local commits.
- Program Execution **never** pushes, opens or updates a PR, writes merge
  authority, or merges. `L9_PE_RELEASE_AUTHORIZED` cannot widen this boundary.
- Publication is a later root operation: `PR_REMEDIATE=0 make pr`.
- Merge belongs only to `/l9-pr-remediation` under exact approval. Invoking this
  skill is **not** merge authorization.

## Live path

```text
operator input
  → make campaign
  → deterministic input classification
  → campaign-source.v2 (direct or compiled)
  → Blueprint / Program Lock / Controller
  → PE runtime binding + execution profile
  → fresh capability probe
  → canonical context manifest
  → Peer Execution Core → thin provider
  → typed attempt receipt
  → Controller verify
  → local commit
  → STOP / handoff
```

The Controller remains the Program state owner. Peer Execution owns the
provider-neutral execution lifecycle only. The bounded scheduler may overlap only
non-conflicting ready provider lanes and must harvest every child result; same
target-lineage mutation remains serialized by the canonical concurrency policy.

## Stop conditions

Stop and report on input-preflight failure, Program Lock drift, blocked capability
probe, missing runtime binding, provider failure, verification failure, scheduler
dead-end, lease expiry, or any attempted remote publication from PE. Never bypass
the tunnel with direct PEC mutation commands. Do not invent missing direct-source
facts, placeholder tokens, task ordering, writable paths, or terminal validation.

## After PE

A successful PE run hands off verified local commits. Remote publication and merge
are separate operations with separate authority:

```text
PE local handoff → PR_REMEDIATE=0 make pr → /l9-pr-remediation
```

## Resource map

- [references/canonical-template.md](references/canonical-template.md) — current direct-source template, copy rules, and validation commands
- [references/file-set.md](references/file-set.md) — emitted files and runner-owned registrations
- [references/source-contract.md](references/source-contract.md) — accepted input forms and direct-source contract
- [references/pipeline.md](references/pipeline.md) — stage order inside the runner
- [references/merge-authority.md](references/merge-authority.md) — where merge authority lives
- [scripts/compile_brief.py](scripts/compile_brief.py) — only classifier-selected brief `.md` → activate seed
- [scripts/compile_activation_files.py](scripts/compile_activation_files.py) — activate-seed compiler and host registration helpers
- `environment/program-execution/scripts/compile_architecture_intent.py` — classifier-selected architecture prose → campaign-source.v2
- `environment/program-execution/templates/campaign-source-v2/` — canonical source-of-truth template assets
- PLAN window owner: `skills/l9-pe-nuggets/` (not this pack)
