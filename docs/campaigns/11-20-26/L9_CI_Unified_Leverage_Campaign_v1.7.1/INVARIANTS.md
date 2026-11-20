# CI invariant ownership and non-duplication

**Status:** Candidate wording, not admitted source authority. The exact proposed statements are frozen in `INVARIANTS.yaml` and in `candidates/*.patch`. The patches are reviewable starting points tied to the pinned source revisions, not permission to bypass existing schema or edit the target blindly.

## Existing canonical L9 law (reuse; no `.github/semantics/invariants.yaml` additions)

Canonical snapshot: `Quantum-L9/.github@c788b991f2ed5f670a2d5660a7faa4e1d52f64e3`, path `semantics/invariants.yaml`. Its registered canonical authority is distinct from `.github/policies/ORG_INVARIANTS.yaml`, which still identifies its current 4.1.0 as a candidate pending signed owner admission. Do not amend or mirror that candidate as if admitted.

| Existing ID | Campaign interpretation |
|---|---|
| `L9-OWNER-001` | One canonical owner for each semantic scope; consumer copy and SDK execution do not transfer ownership. |
| `L9-MONOTONIC-001` | Subordinate product rules may strengthen constraints, not weaken central requirements. |
| `L9-ASSURANCE-001` | A green job is not proof of executed scan, effective enforcement or complete coverage. |
| `L9-UNKNOWN-001` | Skipped, missing, ambiguous, unavailable and unproved states remain explicit. |
| `L9-EVIDENCE-001` | SDK observations and receipts cannot grant governance or execution authority. |
| `L9-CAPABILITY-001` | Tool existence, entitlement, availability, authorization, and successful invocation are distinct. |
| `L9-COORD-001` | Tool, ruleset, configuration and CI results bind to exact governing revisions. |
| `L9-INTEGRATION-001` | Cross-owner merged state requires integrated acceptance, not component green checks alone. |
| `L9-HARD-001` | CI cost optimization cannot compensate for violation of required hard controls. |

## New invariants with scoped source owners

### Core: `.l9/governance-contract.yaml`
Core governs versions, runtime config, requiredness, scheduling, permissions, promotion, and required-check enforcement. These statements supplement its current ownership and failure rules; they do not transfer provider semantics to Core.

**Applicability:** Core 001/002 govern the Core/SDK-managed required execution
path. Their no-stamp/no-consumer-pin requirement does not supersede the accepted
separate native CodeQL plane: Cursor-Governance owns reusable workflows and suite
config, and its thin consumer callers retain SHA pins/adoption updates until an
explicitly admitted compatible successor. Existing native configuration generators
and project identities also retain their owners. Core 005/006 still require native
provenance, privilege isolation and actual enforcement proof. A retained native
caller pin never authorizes overriding Core/SDK pins. The eleven exact statements
and proposal patch representations are unchanged by this clarification.

| ID | Exact concern | Positive test | Negative test |
|---|---|---|---|
| `L9-CI-CORE-001` | Central control is non-delegable | Consumer with no local scanner configuration inherits the Core-resolved tool and policy; a product-only declaration is accepted. | A consumer-local file attempts to set a weaker scanner mode, replace the provider pin or suppress an organization rule; required CI refuses or ignores the override with evidence. |
| `L9-CI-CORE-002` | Central configuration is inherited without stamp churn | A new Python or TypeScript repo without copied tool configs runs applicable centrally configured checks; its native test/project config still works. | Removing a formerly stamped config causes an accidental drift failure, or an unpinned downloaded rule changes results between identical evaluated revisions. |
| `L9-CI-CORE-003` | All required applicable checks must conclude truthfully | A Python+TypeScript fixture produces separate valid completed executions and an aggregated required result. | One language is skipped or a required provider times out while the required organization check is green. |
| `L9-CI-CORE-004` | Central promotion precedes consumer retirement | Central scanner reproduces a consumer rule finding and its negative fixture in live canary CI before that consumer workflow is retired. | A local Semgrep/CodeQL/Sonar check is deleted on static config similarity or a green SDK unit test without integrated execution proof. |
| `L9-CI-CORE-005` | Native privileged scanners retain proper trust boundaries | A read-only PR scan and separate authorized CodeQL analysis both report real, revision-bound results without exposing write tokens to PR code. | Central PR job acquires security-events write, cloud scanner token or unrelated paid account permission merely to combine reports. |
| `L9-CI-CORE-006` | Coverage is proved at the actual enforcement boundary | An eligible org repository and a separately governed cryptoxdog repository each have independent verified enforcement and run evidence. | A green workflow in one repo or a rule in the Quantum-L9 org is reported as proof that Odoo under cryptoxdog is protected. |

### SDK: `.l9/integration-contract.yaml`
SDK owns complete capability facts, scanner/runtime rule composition, provider reports, coverage records and canonical observations. Existing `INVARIANTS.md` `INV-001..INV-014` and `.l9/architecture.yaml` boundaries remain binding; do not invent a second SDK policy owner.

| ID | Exact concern | Positive test | Negative test |
|---|---|---|---|
| `L9-CI-SDK-001` | Repository capability selection is exhaustive and deterministic | A mixed Python+TypeScript repository selects both required scan targets, and Odoo detection recognizes relevant Python and XML capabilities. | A primary-language heuristic hides a supported second language, or malformed manifest evidence is silently accepted as absence. |
| `L9-CI-SDK-002` | Not applicable and coverage are evidence states | A no-supported-code fixture has a reasoned not-applicable outcome, while a repo with a missing provider executable reports incomplete/failure. | Scanner reports zero findings after scanning zero relevant files, or the wrapper maps process skip to successful completion. |
| `L9-CI-SDK-003` | Rulepack composition is immutable and monotonic | SDK baseline plus tested Odoo and product-specific rules resolves the same rule IDs and content digest on repeated runs. | A consumer-local exclusion disables a baseline rule, or a remote registry update changes results without a pinned content coordinate. |
| `L9-CI-SDK-004` | Specialized rule behavior is preserved by falsifiable fixtures | EIE/CEG portable Semgrep rules and Odoo indirect SQL rules preserve positive and negative detection tests after consolidation. | A product rule is removed because its name resembles a central rule, without testing SQL taint or scope exclusions. |
| `L9-CI-SDK-005` | Native facts and unique findings survive normalization | The same vulnerability reported by Semgrep and CodeQL remains traceable to both native reports while presented as correlated evidence. | A distinct native finding disappears during dedup, a skipped CodeQL scan is described as SDK-executed, or a technical gate is labeled final Assurance. |

## Invariant admission and realization order

1. Preflight source revision and canonical registry; resolve any existing conflicting admitted owner or target-schema restriction. Do not claim a verified GAR projection or authority receipt without producer proof.
2. First PRs: add the **exact** candidate statements to their scoped Core and SDK contracts (or the same existing owner-specified semantic surface if typed schema rejects the proposed field); include targeted tests. A field-placement correction is allowed only with explicit same-meaning mapping and evidence.
3. Test each invariant with the corresponding positive and negative witness. A pure YAML assertion without a running enforcement path does not count as implemented.
4. Integrate the source-owner PRs under existing SDK compatibility and pinned Core promotion path. Validate the exact combined heads. The full fleet is not admitted by component PR publication.
5. Only after canary, vendor and native-provider parity may consumers remove duplicate checks. Preserve Odoo account isolation, native CodeQL privileges and real product test commands.

## Failure dispositions

- **Existing global law:** reused as external authority by ID and immutable SHA, not copied into another canonical ledger.
- **New source owner invariant:** proposed with exact owner, patch and falsifiable acceptance tests; not yet admitted.
- **New global invariant:** none justified. The canonical constitutional invariant catalog already covers ownership, monotonicity, evidence, uncertainty and integration.
- **Paid tool tuning:** a campaign acceptance and vendor-specific configuration obligation, not a new constitutional semantic invariant. A paid tier or entitlement remains unverified until native account evidence.
- **Target contract schema compatibility:** unknown until the target owner verifies the patches using its actual validators at kickoff. If incompatible, revise only the target-owned representation, preserving exact meaning and the owner review boundary.

## ADR-to-invariant binding

**Consumer integration application (no new global invariant):**
`L9-CI-CORE-004` is satisfied only by the promoted live
Cursor-Governance acceptance in `CURSOR_CANARY.md`, not by Core unit tests.
`L9-CI-SDK-003/004` requires candidate rulepack scope, exact donor provenance,
and positive/negative fixture evidence from `HARVEST.md`. These are
implementation proof requirements of the existing 11 campaign candidates,
not 11 new organization-wide laws.

The campaign does not use ADR prose as a substitute for executable invariant enforcement. ADRs are the recorded architecture decisions; `INVARIANTS.yaml` is the scoped exact rule proposal and tests are the proof.

- **Core ADR 0001:** `L9-CI-CORE-001`, `002`, `003`, `006`; global constitutional references, immutable Core/SDK authority split, total required execution and inherited runtime config.
- **Core ADR 0002:** `L9-CI-CORE-004`, `005`, `006`; promotion/canary/parity, native permissions, fleet proof and measured paid-tool leverage.
- **SDK ADR 0020:** `L9-CI-SDK-001` through `005`; complete deterministic detection, execution evidence, immutable composition, specialized positive/negative fixtures and lossless source findings.

An agent may not treat an ADR as implementing its invariants. It must prove each mandatory runtime path independently and cite the ADR + invariant + code change + live witness at closure.
