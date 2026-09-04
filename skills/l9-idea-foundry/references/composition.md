<!-- L9_META
l9_schema: 1
parent: l9-idea-foundry
layer: reference
role: composition
tags: [foundry, harvest, plan-simple, repo-template]
owner: igor_beylin
status: active
version: 1.0.0
updated: 2026-09-02
/L9_META -->

# Foundry capability composition

Foundry is an orchestrator and product-realization owner. Compose existing L9 semantic owners instead of copying them.

## Contents

- [Call graph](#call-graph)
- [Single-ingress law](#single-ingress-law)
- [l9-intelligence-harvest boundary](#l9-intelligence-harvest-boundary)
- [l9-plan-simple boundary](#l9-plan-simple-boundary)
- [GAR boundary](#gar-boundary)
- [l9-repo-template boundary](#l9-repo-template-boundary)
- [Upstream-first rule](#upstream-first-rule)
- [Compounding-leverage rule](#compounding-leverage-rule)

## Call graph

```text
idea pack
  |
  v
Foundry inventory + authority map
  |
  v
beneficiary profile + L9 reuse scan
  |
  +--> l9-intelligence-harvest (conditional, read-only semantic transfer)
  |          |
  |          v
  |      harvest.json + harvest-receipt.json
  |
  +--> l9-global-architect (when explicitly active for architecture judgment)
  |          |
  |          v
  |      architecture decision evidence
  |
  v
IMPLEMENTATION_BLUEPRINT.yaml  <- pre-code single ingress
  |
  v
l9-plan-simple (implementation plan compiler)
  |
  v
validated PLAN_DOCUMENT
  |
  v
Foundry code realization + exact-state validation
  |
  v
FOUNDRY_INDEX.json             <- post-realization single ingress
  |
  v
l9-repo-template birth compiler + birth engine
```

## Single-ingress law

Foundry has two justified ingress surfaces, each at a different lifecycle boundary:

1. `IMPLEMENTATION_BLUEPRINT.yaml` is the accepted **pre-code semantic ingress**. After acceptance, Plan Simple and code realization consume it. They may follow its evidence refs into the raw pack, but must not independently reinterpret the whole pack and create a second product specification.
2. `FOUNDRY_INDEX.json` is the deterministic **post-realization resume ingress**. It indexes origin artifacts, semantic digests, plan binding, and current Foundry state for later agents and recompile decisions.

Do not add a third active ingress unless a verified consumer cannot use either existing boundary. More entrypoints are not more leverage.

After remote birth, the index becomes origin evidence. Current repository ground truth and repo-local law win over stale origin material.

## l9-intelligence-harvest boundary

Use Harvest only for a genuine donor-to-beneficiary semantic transfer problem.

Donor examples:

- an idea pack containing prior system designs, kernels, playbooks, or reusable architecture
- a named existing repository the new product should learn from
- multiple historical implementations whose portable semantics must be separated from incidental machinery

Beneficiary is the intended newborn product/repository profile, including verified upstream L9 owners.

Harvest owns semantic mining, fit comparison, transfer disposition, portability closure, and acceptance-test derivation. Foundry must not copy Harvest schemas or implement its DAG.

Harvest outputs are **evidence**, not source authority. If a nugget conflicts with canonical idea-pack law or a stronger beneficiary owner, reject or adapt the nugget according to Harvest's own disposition semantics.

Do not use Harvest for literal code extraction or to manufacture missing product requirements.

## l9-plan-simple boundary

Foundry requires Plan Simple for nontrivial implementation planning because it already owns:

- planning doctrine and depth routing
- repo-grounded decomposition
- plan stress testing
- first-order leverage analysis
- `PLAN_DOCUMENT` schema
- plan validation
- plan projection

Foundry does not copy those mechanisms.

### Handoff-mode negotiation

Probe the current Plan Simple contract before planning.

**Preferred:** when current evidence proves first-class embedded mode exists, invoke it and record:

```yaml
plan_handoff: EMBEDDED
mode_evidence_ref: <observed Plan Simple contract or emitted plan>
compatibility_fallback: false
```

This mode must stop after validated planning artifacts and return control to Foundry. It grants no Build, commit, PR, PE, GMP, or deployment authority.

**Compatibility fallback:** when current Plan Simple lacks first-class embedded mode, consume only its validated planning surface and record:

```yaml
plan_handoff: EMBEDDED_PRE_BIRTH
compatibility_fallback: true
fallback_reason: "current l9-plan-simple lacks first-class embedded mode"
```

Do not claim Plan Simple's normal stacked-PR completion or PR URL in this compatibility path.

Never select embedded merely because host execution or publication capability is missing. If Plan Simple cannot produce a validated plan under an authorized mode, emit `PLANNING_CAPABILITY_BLOCKED`.

### Plan reuse boundary

A previously validated plan may be reused only when:

- compiled intent is unchanged by semantic digest,
- Plan Simple's own baseline/preconditions still hold against the current staging state,
- its validation evidence is still applicable,
- no explicit current operator change invalidates it.

The Foundry index can prove content identity; it cannot overrule Plan Simple's own baseline law.

## GAR boundary

GAR owns architecture judgment when explicitly active. Foundry supplies objective, authority map, beneficiary/reuse map, Harvest evidence, and known constraints; GAR decides architecture direction, constellation alignment, first-order fit, ownership coherence, and complexity legitimacy.

Foundry may record equivalent lightweight answers only when GAR is not active. It must not label those answers as GAR evidence.

## l9-repo-template boundary

The template owns birth. Foundry supplies an authoritative product payload and evidence. The template decides how that payload becomes a governed repository.

Never duplicate:

- birth state machine
- payload ownership rules
- org birth profile application
- provenance stamping
- CI enrollment logic
- remote attestation

## Upstream-first rule

Before creating a new shared capability locally:

1. search verified L9 owners,
2. determine whether an existing owner already satisfies or nearly satisfies the responsibility,
3. use Harvest when semantic fit is nontrivial,
4. prefer dependency, contract, adapter, or port over copied policy or copied state,
5. create a new local owner only when the responsibility is genuinely product-specific or no existing owner fits.

A newborn product may adapt an upstream contract. It must not become a shadow authority for a constellation-wide responsibility.

## Compounding-leverage rule

Foundry owns cross-repository leverage selection, not implementation-todo ranking.

Before accepting a new shared abstraction, automation, or contract, require at least one of:

- two or more verified consumers,
- one recurring operation whose repeated manual cost is already demonstrated,
- a verified shared failure mode that one canonical boundary removes.

Prefer, in order:

1. reuse or strengthen an existing owner,
2. remove duplicate responsibility,
3. add a narrow contract at an existing seam,
4. automate a repeated deterministic operation,
5. create a new abstraction only when the above cannot solve the recurring problem.

Record rejected speculative abstractions in the blueprint when that rejection prevents likely future drift.
