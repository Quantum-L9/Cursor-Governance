# Lane G1: `.github` native generators and ruleset evidence (CTO session)

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `G1`. Executor: the CTO session, one
  `Quantum-L9/.github` worktree. A pool agent never clones, branches or pushes this repository.
- Base: fetched `origin/main` (`c788b991` on 2026-11-20).
- Findings: T12. Supports `L9-CI-CORE-006` evidence.

## OBJECTIVE

Read the live enforcement boundary and the two governed generators, and change `.github` only where
the harvest proves a delta that belongs to its existing sources.

## NON-GOALS

- No new global invariant, no new global ADR, no CI recipe added to `semantics/`.
- No ruleset, branch-protection or bypass-actor change.
- No edit to `policies/ORG_INVARIANTS.yaml`. Its 4.1.0 text calls itself a candidate.
- No hand edit of a rendered file. No file that open pull request #274 changes.
- No CodeRabbit central-repository creation: that is the operator's task under `.github` ADR-0020.

## ASSETS USED

- This pack: `HARVEST.md` owner table, `CODERABBIT_ACTIVATION.md`, `OTHER_TOOLS_EVIDENCE.md` T12,
  `PROOF.md` P0, P4, P12; `09_EXECUTION_BINDING.md` B07, B15, B19.
- `.github`: `rulesets/l9-canonical-ci-required.json`, `ops/render-coderabbit.js`,
  `ops/render-dependabot.js`, `.coderabbit.yaml`, `docs/adr/0020-coderabbit-central-config-seeded.md`,
  `docs/adr/ADR-010-ownership-boundaries-no-recipes.md`, `semantics/invariants.yaml`.

## WORKFLOW

1. **Ruleset read.** Read the organization ruleset if the token allows, otherwise the repository
   ruleset route. Record enforcement, target, included and excluded repositories, required check name,
   workflow ref, strict policy and bypass actors. Compare with the committed JSON and record drift.
   This read does not prove a bad pull request cannot merge.
2. **Coverage ledger.** For each of the six `Quantum-L9` campaign repositories record whether the
   required workflow evaluated its current head, with the run. `cryptoxdog/IB-Odoo_19` is a separate
   row fed by lane H1.
3. **T12.** From the renderer and one rendered consumer file, list ecosystems, ignores and
   major-version behavior. Record gaps. Dependabot alert state is a G0 item.
4. **CodeRabbit.** Record the rendered source revision and which consumers lack inheritance. Publish
   nothing while P5 is unanswered.
5. **Write only on a proven delta.** Change the renderer source, regenerate, and publish one pull
   request from a dedicated worktree. Otherwise this lane ends with no pull request.

## CONSTRAINTS

- Publish with `PR_REMEDIATE=0 OPEN_PR=1 make -C "$HOME/.cursor-governance" pr WS="$PWD"`.
- The CTO authors this lane and coordinates it. The operator's merge review is the independent check;
  no second swarm review is claimed.
- The managed authority pin `$HOME/.l9/authority/.github` is never the worktree.

## DONE-CRITERIA

- Ruleset observation with every field above, or Unknown with the failed route named.
- Six-row coverage ledger plus the Odoo row.
- T12 has a disposition.
- A pull request exists only if a delta was proven, and is ready to merge.

## ACTIVATION

Runs in the CTO session alongside S0, after the bootstrap sitting.
