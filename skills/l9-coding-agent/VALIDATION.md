# L9 Coding Agent Validation

**Release:** 1.4.0  
**Tier decision:** EXEMPLARY  
**Compiler authority:** `Quantum-L9/Cursor-Governance` `l9-skill-compiler` v3.8.0  
**Compiler source revision:** `a29657e8bafe07761a7cf6501864ffa77cdb9c56`

## Activated compiler directives

- skill doctrine
- compounding leverage
- build quality
- validation evidence
- anti-drift
- execution cost
- recursive improvement
- L9 platform adapter

The user-supplied Validate & Repair v1.0 kernel was applied as the bounded repair/hardening authority for this release. Repository wiring was not requested, so compiler Gate F is not applicable.

## Six validation classes

| Class | Result | Evidence |
|---|---|---|
| Structural | PASS | v3.8.0 `validate_skill_pack.py`; 30 files; package inventory closure |
| Contract | PASS | v3.8.0 `validate_exemplary_skill.py`; SMART spec validator; execution-contract positive/negative fixtures |
| Execution | PASS | runtime alignment, lazy bootstrap, Python compile, structured parse, contract smoke tests |
| Evidence | PASS | complete baseline inventory; finding-to-change-to-validation repair record; exact final checks |
| Operator | PASS | README, RUNBOOK, MANIFEST, failure paths, whole-target guard, handoff law |
| Regression | PASS | GAR/L9 sibling integration bytes preserved; 28/28 prior behavior cases retained; 12 new cases added |

## Runtime results

- Lazy bootstrap closure: **15 semantic owners reachable**.
- Package classification: **30/30 files classified**.
- Behavior conformance: **40 cases**.
- Execution-contract validator: valid fixture accepted; malformed/incomplete fixture rejected.
- Python scripts: compile successfully.
- YAML and JSON: all parse successfully.
- Whole-target readiness now requires complete authorized inventory or a bounded/Unknown result.
- Final delivery now requires validated-state identity to match delivered-state identity.

## v1.3 repair evidence

The repair intentionally changes execution semantics in the following bounded areas:

- separate inspection scope from modification scope;
- dependency-aware target graph and root-cause-first repair;
- evidence-backed finding matrix, fix map, and traceability;
- explicit validation result states including `Unknown`;
- whole-target inventory, regression, final hygiene, and handoff-fidelity gates;
- adaptive recursion only while a specific evidence-backed objective remains.

The GAR sibling contract and L9 runtime binding remain byte-identical to v1.2.0. The node identity, architecture boundary, lazy-bootstrap model, and implementation-detail sovereignty are preserved.

## Exemplary evidence

- Strong activation signals and explicit near-miss reject signals remain intact.
- Seven expert heuristics use condition -> judgment -> action.
- Three adapters remain conditional and change real decision rules.
- Five named failure modes retain prevention controls.
- Five leverage points score **23-24/25**; compiler threshold is 18/25.
- After-use capture is recompressed to four observation-only signals and cannot self-promote policy.
- Package intelligence remains package evidence, not runtime authority.

## v1.4 canonical invariant binding

Validated at Cursor-Governance `b8941d3`, `.github` `1f42b33`, and l9-semantic-compiler-engine `a1c4104`:

- lazy bootstrap closes 16 semantic owners and classifies 31 files;
- runtime alignment covers 52 behavior cases and the absent-projection negative control;
- `validate_skill_pack.py` and `validate_exemplary_skill.py` pass.

An evidence harness kept outside the repository ran 34 verifier cases against the real `.github` sources, all passing. The artifacts and receipts were **synthetic**. They prove consumer logic only.

### Live producer evidence (invariants source class)

Quantum-L9/l9-semantic-compiler-engine#8 (head `99dfde4`, not yet merged) implements `project` for one source class of a `.github` projection profile. Its output was checked at `.github@1f42b33` with this verifier unchanged:

- real output binds (`BOUND`), and the producer is byte-deterministic across runs;
- each adverse case changes one fact in real output or in a clone of the authority. All were caught:
  - tampered payload: `REJECTED`, including when its digests and receipt are recomputed;
  - non-canonical owner: `BLOCKED`;
  - removed selector: `BLOCKED`;
  - a material change to a bound invariant: `STALE`;
  - an unrelated upstream commit: stays `CURRENT`;
  - re-projection: binds again;
  - an unpinned production (receipt result `unknown`): `REJECTED`.

12/12 cases passed. Until #8 merges, the producer exists only on that PR branch. The other 8 source groups have no producer, so they stay `BLOCKED_UPSTREAM_PROJECTION_PRODUCER`.

## Known limitations

- Behavior conformance is deterministic declarative coverage, not production telemetry. No telemetry was invented.
- This release proof covers the pack as compiled. Its installation into `Quantum-L9/Cursor-Governance` is recorded in [CHANGELOG.md](CHANGELOG.md); that install adds exactly one frontmatter line (`disable-model-invocation: true`) and no runtime semantics.
- `agents/openai.yaml` is retained because ChatGPT remains an explicit supported target.
- Upstream gaps block a live canonical binding:
  - there is no producer for `l9.projection/cursor-governance-operating-plane@1`;
  - there is no `l9.projection.cursor-governance-operating-plane/v1` output schema;
  - no `semantic_digest` canonicalization algorithm is declared;
  - the profile has 9 source groups but the projection artifact is single-source, and no composition profile is declared;
  - the `conformance_profiles` source resolves outside `.github`.
- Receipts and projection digests are unkeyed. A forger who copies the source faithfully and claims the `l9-semantic-compiler` identity cannot be told apart from the real producer; authenticating the producer needs signed receipts upstream.
- Canonical-binding enforcement is instructional. Verifier invocation is required by the skill text, not enforced by a host hook.
- `SKILL.md` stays byte-identical to 1.3.0, so frontmatter `metadata.version` lags at 1.3.0. Generated skill registries outside the pack pin its `skill_sha256`, and regenerating them is outside this change's authorized path.
- `skill_intelligence_report.yaml` and `expertise_model.yaml` remain 1.3.0 package evidence and were not recompiled.

## Verdict

All applicable v3.8.0 compiler gates and v1.3.0 runtime gates pass. The pack remains **exemplary** and is ready for packaging.
