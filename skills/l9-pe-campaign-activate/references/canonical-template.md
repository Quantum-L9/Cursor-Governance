<!--
--- L9_META ---
l9_schema: 1
parent: l9-pe-campaign-activate
layer: reference
role: canonical_campaign_source_template
source_of_truth: environment/program-execution/templates/campaign-source-v2
artifacts: [CAMPAIGN_SOURCE.yaml, README.md]
tags: [campaign, campaign-source-v2, template, blueprint, pec]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-13
--- /L9_META ---
-->

# Canonical direct campaign-source.v2 template

Use the source-of-truth assets at
`environment/program-execution/templates/campaign-source-v2/` for a complete,
operator-authored direct campaign input. Do not duplicate the template in this
skill; the repository template is the single source of truth and its compiler
regression test verifies preflight and native Blueprint validation.

| Artifact | Use | Ownership |
|---|---|---|
| `CAMPAIGN_SOURCE.yaml` | Copy to a working authoring location, replace verified campaign facts, and pass it to `make campaign`. | Operator-authored immutable source after intake. |
| `README.md` | Read for artifact boundaries and the cleanup-safe Blueprint-only test command. | Template operational guide. |
| `source-integrity-receipt.json` | Do not author. | Runner-generated in the isolated campaign worktree. |
| Blueprint directory | Do not author by hand. | Campaign compiler-generated and template-validated. |
| PEC workspace | Do not commit. | PEC-generated mutable runtime state. |

## Direct-source shaping rules

Keep `metadata.campaign_id` equal to `program.id`. Replace the example campaign
and program facts, owner, target repository, expected revision, scope,
authorities, evidence, workstreams, waves, dependency edges, task paths,
validation commands, gates, risks, and rollback rules with verified facts. Retain
all explicit remote-action ceilings as `false`.

A `repo_local` task with `local_write: true` needs explicit writable paths and an
admissible single-operation terminal validation command. Express task ordering
only with top-level `dependency_edges`; do not add task-local dependency fields.
Do not leave `REPLACE_WITH_*` or `{{TOKEN}}` markers. Do not create a compile
allowlist: campaign IDs are admitted by valid source semantics, not
preregistration. Retired v1 source or pack documents belong only in the
immutable `environment/program-execution/archive/campaign-input-v1/` evidence
boundary and must never be resubmitted to activation.

## Validate before live execution

```bash
repo_root="${L9_REPO:-$HOME/.cursor-governance}"
make -C "$repo_root" campaign-check-input INTENT=path/to/CAMPAIGN_SOURCE.yaml
```

Use the template guide's cleanup-safe command only to test the direct route
through Blueprint generation. It requires `L9_CAMPAIGN_UNTIL_DEBUG=1` and stops
before Blueprint acceptance, PEC bootstrap, task execution, publication, merge,
release, or deployment. For the live path, invoke only:

```bash
make -C "$repo_root" campaign INTENT=path/to/CAMPAIGN_SOURCE.yaml
```

If preflight or the runner fails, stop and report the output. Do not call
`pec bootstrap`, `compile_campaign_source.py`, or inner acceptance scripts as a
live-path substitute.
