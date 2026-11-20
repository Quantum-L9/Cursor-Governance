# Lane L1: SDK capability closure and lossless evidence

## MANIFEST

- Campaign `L9-CI-UNIFIED-LEVERAGE-2026-11-20-v1.7.1`, lane `L1`, pool slot 1.
- Write: `Quantum-L9/l9-ci-sdk` only. Base: fetched `origin/main` (`ab8a2554` on 2026-11-20).
- Read-only: `Quantum-L9/Enrichment.Inference.Engine`, `Quantum-L9/Cognitive.Engine.Graphs`,
  `Quantum-L9/Cursor-Governance`, `cryptoxdog/IB-Odoo_19`. Attach all four in the bootstrap sitting.
- Absorbs v1.7.0 Lane 1.

## OBJECTIVE

Propose SDK ADR 0020 and invariants `L9-CI-SDK-001` to `005` at their owner with running positive and
negative witnesses, then give Core a complete, deterministic capability inventory and a rulepack
composition that loses no specialized rule.

## NON-GOALS

- No new provider. Biome stays Core-executed (SDK ADR 0017).
- No CodeQL, Sonar, CodeRabbit or any SaaS credential inside the SDK.
- No Assurance verdict from the SDK.
- No edit to a donor repository. No rule retired anywhere.
- Do not mark ADR 0020 Accepted. Do not rewrite ADR 0005, 0016 or 0017.

## ASSETS USED

- This pack: `ADRS.md`, `INVARIANTS.yaml`, `INVARIANTS.md`, `HARVEST.md`, `PROOF.md` P1, P3, P8, P9,
  P10; `candidates/adr/l9-ci-sdk/docs/adr/0020-*.md`, `candidates/sdk-integration-contract.patch`,
  `candidates/sdk-adr-index.patch`; `09_EXECUTION_BINDING.md` B12, B13, B15.
- SDK: `AGENTS.md`, `CLAUDE.md`, `.l9/integration-contract.yaml`, `.l9/architecture.yaml`,
  `INVARIANTS.md` (INV-001 to INV-014 stay), `docs/adr/README.md`,
  `l9_ci/capabilities/detector.py`, `l9_ci/rulesets/semgrep/profiles.yaml`.
- Donors: EIE and CEG `.semgrep/semgrep-rules.yaml` (8 rule IDs each; CEG has `.semgrep/fixtures/`),
  Cursor-Governance `.semgrep/l9-pr.yml` (4), IB-Odoo_19 `.semgrep/odoo-patterns.yml` (39) with
  `.semgrep/tests/`.

## WORKFLOW

1. **PR 1a, decisions.** Copy ADR 0020 to `docs/adr/` unchanged. Apply both patches (they apply
   cleanly at `ab8a2554`). Add one positive and one negative witness test per invariant, named by ID.
   A witness that needs code from step 2 or 3 is written to fail closed and marked with the exact
   missing capability; it is not skipped. Publish.
2. **PR 1b, capability inventory**, stacked on 1a. Every supported language, framework and provider
   prerequisite for one snapshot, with separate states for not applicable, incomplete and failed.
   Fixtures: Python only, TypeScript only, mixed, Odoo Python plus XML, no supported code, malformed
   manifest, unsupported language. Write `CTO-STATUS: interface-freeze <head sha>` naming the public
   symbols Core will call. Publish.
3. **PR 1c, rulepack composition**, stacked on 1b. For each donor rule give one `HARVEST.md`
   disposition with donor head, blob, behavior, good and bad fixture, and a non-target witness. Compare
   the EIE and CEG pairs by behavior, not by ID. Keep Odoo 19 patterns separate from PlasticOS law and
   keep Cursor memory-path rules scoped. Anything unproven is `defer_unknown` and stays at its owner.
   Publish.
4. Report harvest rows in the transcript for the CTO ledger.

## CONSTRAINTS

- SDK `CLAUDE.md` holds: update models, JSON Schemas, compatibility analysis, invariant tests and
  schema tests together; real redacted fixtures; never guess an identity; never turn missing evidence
  into PASS.
- Gates before publishing: `ruff check .`, `ruff format --check .`, `mypy l9_ci`, `pytest -q`.
- Publish with `PR_REMEDIATE=0 OPEN_PR=1 make -C "$HOME/.cursor-governance" pr WS="$PWD"`. No `pr`
  target is added here. No Core caller workflow, no `L9_CORE_REF` or `L9_SDK_REF` pin (ADR 0016).
- A public-API change beyond the frozen symbols is a `CTO-QUESTION`.

## DONE-CRITERIA

- PR 1a, 1b, 1c each `ready-to-merge`: CI green on the current head, threads resolved, no conflict.
- Each of `L9-CI-SDK-001` to `005` has a named known-bad test that fails without the change and a
  known-good test that passes, cited in the pull request.
- ADR 0020 status reads Proposed and the index row exists.
- Every donor rule (8 + 8 + 4 + 39) has exactly one disposition row. No row is blank.

## ACTIVATION

Begin after role registration and `/coding-agent` mode reports ACTIVE. First status line carries the
mode JSON and the base SHA you fetched.
