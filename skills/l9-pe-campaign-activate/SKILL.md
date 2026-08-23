---
name: l9-pe-campaign-activate
description: invoke make campaign INTENT= as the only live PE campaign front door. use when the user asks to activate a campaign, run a pe campaign, compile campaign source, emit campaign seeds, or take a brief through verified local commits. the run ends at verified local commits, so publication stays PR_REMEDIATE=0 make pr and merge stays /l9-pr-remediation. do not call pec, the intent compiler, or inner compile/accept scripts as a substitute.
disable-model-invocation: true
metadata:
  skill_schema: 1
  layer: control_plane
  role: skill_entrypoint
  tags: [l9, program-execution, campaign, compiler, activate, merge]
  owner: igor_beylin
  status: active
  version: 1.2.0
  updated: 2026-08-23
---

# PE Campaign Activation

## Purpose

Run the single live Program Execution front door from operator intent through
Blueprint, Program Lock, bounded Peer Execution, Controller verification, and
**local commits only**.

```bash
make -C "$HOME/.cursor-governance" campaign INTENT=<brief.md|activate.yaml>
```

## Authority law

- Program Execution owns design projection, readiness, leases, worktrees,
  provider-neutral execution, independent verification, evidence, and local commits.
- Program Execution **never** pushes, opens/updates a PR, writes merge authority,
  or merges. `L9_PE_RELEASE_AUTHORIZED` cannot widen this boundary.
- Publication is a later root operation: `PR_REMEDIATE=0 make pr`.
- Merge belongs only to `/l9-pr-remediation` under exact approval. Invoking this
  skill is **not** merge authorization.

## Live path

```text
operator intent
  → make campaign
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
target lineage mutation remains serialized by the canonical concurrency policy.

## Stop conditions

Stop and report on Program Lock drift, blocked capability probe, missing runtime
binding, provider failure, verification failure, scheduler dead-end, lease expiry,
or any attempted remote publication from PE. Never bypass the tunnel with direct
PEC mutation commands.

## After PE

A successful PE run hands off verified local commits. Remote publication and merge
are separate operations with separate authority:

```text
PE local handoff → PR_REMEDIATE=0 make pr → /l9-pr-remediation
```

## Resource map

The emit contract is unchanged and still enforced by the compiler:

- [references/file-set.md](references/file-set.md) — allowed vs forbidden emitted files
- [references/source-contract.md](references/source-contract.md) — intent + seed fields
- [references/pipeline.md](references/pipeline.md) — stage order inside the runner
- [references/merge-authority.md](references/merge-authority.md) — where merge authority lives
- [scripts/compile_brief.py](scripts/compile_brief.py) — memo `.md` → activate seed
- [scripts/compile_activation_files.py](scripts/compile_activation_files.py) — the compiler
- PLAN window owner: `skills/l9-pe-nuggets/` (not this pack)
