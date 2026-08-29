Execute the next bounded architecture and implementation phase for https://github.com/cryptoxdog/IB-Odoo_19 under the assumption that the CieTrade and VanillaSoft ingestion milestone has been completed and validated, while still verifying the repository state before relying on that assumption.

The purpose of this program is to establish the canonical contract and projection foundation that sits between authoritative Odoo business state and all future semantic memory, temporal memory, graph, analytical, opportunity, matching, and agent systems.

Do not implement the matching engine, transaction-candidate execution, future CRM integrations, or vendor-specific memory infrastructure in this program. The goal is to make those later systems possible without creating a second source of business truth.

Architectural intent

Odoo MUST remain the authoritative operational and canonical business system.

Everything downstream of Odoo—including semantic documents, temporal episodes, structural graphs, analytical signals, vector stores, graph databases, agents, workers, opportunity engines, and matching services—must be treated as a rebuildable projection, derived contract, evidence layer, or consumer.

The target flow is:

External sources → validated import/adapters → Odoo authoritative state → canonical snapshots/evidence/episodes → rebuildable projections → future opportunity/matching systems

Do not allow memory providers, graph providers, event transports, external workers, agents, or analytical services to become an independent canonical authority.

Phase 1 — Verify current repository state

Begin from the actual repository state.

Inspect:

* current default/integration branch
* recent relevant git history
* INVARIANTS.md
* existing contracts/
* existing JSON/YAML schemas
* Odoo canonical identity fields
* existing UUID/revision/provenance patterns
* projection or synchronization models
* outbox/event models
* workers/jobs/cron mechanisms
* graph integrations
* semantic/vector integrations
* memory-related modules
* evidence/history/audit models
* tests
* documentation
* Makefile and existing command surface

Do not rebuild mechanisms that already exist and are correct.

Classify findings as:

* VERIFIED
* NEEDS_CORRECTION
* SUPERSEDED
* DEFERRED
* UNKNOWN

Any assumption that cannot be established from repository evidence or runtime inspection remains UNKNOWN.

Phase 2 — Recover and converge the v2 contract candidate set

Locate or introduce, as recovered candidate material, the following schemas:

* canonical-snapshot.schema.yaml
* evidence-record.schema.yaml
* temporal-episode.schema.yaml
* semantic-document.schema.yaml
* structural-projection.schema.yaml
* opportunity-protocol.schema.yaml
* transaction-candidate.schema.yaml
* packet.schema.yaml
* match-execution-packet.schema.yaml
* improvement-packet.schema.yaml

Treat these as candidate v2 contracts, not automatically authoritative contracts.

Compare them against the existing repository contract tree and determine for each one whether it:

* extends an existing contract
* replaces an existing contract
* partially overlaps an existing contract
* conflicts with an existing contract
* represents a genuinely new bounded contract

Do not maintain two competing authoritative contract definitions for the same concept.

Establish one coherent contract hierarchy and document supersession where required.

Preserve useful existing repository contracts rather than replacing them simply because the recovered schemas are newer or more detailed.

Phase 3 — Repair schema correctness before adoption

Validate all candidate contracts using standards-compliant JSON Schema Draft 2020-12 tooling.

Correct structural/schema defects before declaring any schema authoritative.

Specifically inspect for:

* non-standard $data validation usage
* additionalProperties: false combined with properties introduced only inside conditionals
* conditional minItems constraints that fail to make arrays required
* lineage fields that are constrained but not actually required
* invalid or ambiguous recursive references
* impossible conditional branches
* inconsistent UUID field naming
* deletion targets whose identifiers differ from creation identifiers
* fields with incompatible nullability between base and specialized schemas
* invalid YAML
* trailing prose accidentally included in YAML files
* schema references whose relative paths do not resolve
* duplicate concepts represented differently across contracts
* inconsistent enum casing or naming
* ambiguous revision semantics
* ambiguous fingerprint semantics
* inconsistent tenant/company scoping
* inconsistent timestamp semantics
* security fields that cannot be enforced consistently

Use standard JSON Schema wherever possible.

Cross-field business invariants that cannot be represented portably in Draft 2020-12 should be moved into an explicit semantic/domain validator rather than relying on validator-specific extensions.

Phase 4 — Establish canonical identity semantics

Define and implement one repository-wide contract for canonical identity.

Every Odoo subject eligible for downstream projection must have:

* stable canonical UUID
* tenant UUID
* company UUID where applicable
* Odoo source model
* Odoo source record ID
* explicit revision
* lifecycle state where relevant
* deterministic fingerprint
* generated/updated timestamp
* provenance
* security classification where appropriate

The Odoo integer primary key may be included as a local implementation reference, but downstream systems MUST use canonical UUIDs as durable identities.

Determine the smallest compatible implementation needed to introduce canonical UUID/revision semantics into existing models.

Avoid invasive rewrites if an existing UUID or identity mechanism can be reused.

Define precisely:

* UUID generation rules
* UUID immutability
* revision increment conditions
* fingerprint calculation
* semantic versus non-semantic changes
* deletion/archive behavior
* company/tenant boundaries
* canonical identity lookup
* migration/backfill behavior for existing records

Backfills must be deterministic and idempotent.

Phase 5 — Implement the Canonical Snapshot compiler

Make canonical-snapshot the principal boundary between Odoo business state and downstream projection systems.

Implement a deterministic compiler that accepts an authoritative Odoo record and produces a canonical snapshot containing:

* canonical subject identity
* revision
* lifecycle state
* normalized business fields
* relationships
* textual representations where appropriate
* evidence references
* provenance
* security metadata
* deterministic fingerprints
* intended projection targets
* generated timestamp

Model-specific knowledge belongs in explicit canonical projectors/compilers.

Do not allow downstream consumers to construct canonical truth by arbitrarily querying Odoo tables.

The same unchanged Odoo record and projector version must produce the same semantic snapshot/fingerprint.

A meaningful authoritative change must result in a new revision or an explicitly documented new snapshot version according to the chosen contract.

Phase 6 — Implement Evidence Records

Adopt and harden evidence-record as the system contract for observations and assertions that support, contradict, qualify, or contextualize canonical business state.

Evidence should cover appropriate concepts such as:

* price quotes
* price observations
* freight quotes
* freight observations
* processing quotes
* material observations
* capacity observations
* capability assertions
* relationship assertions
* negotiation assertions
* transaction outcomes
* market references
* model inference
* document assertions
* human assertions

Evidence MUST preserve:

* evidence UUID
* subject references
* source
* source timestamp
* temporal validity
* evidence state
* value
* units/currency where relevant
* confidence
* method
* supersession
* contradiction/support relationships
* security
* fingerprint

Evidence MUST NOT silently mutate canonical Odoo business truth.

Promotion of evidence into canonical state must occur only through explicit, governed business rules or authorized workflows.

Phase 7 — Implement Temporal Episodes

Adopt and harden temporal-episode as the provider-neutral history contract.

Support episodes such as:

* calls
* emails
* messages
* meetings
* notes
* supplier intakes
* buyer intakes
* proposals
* negotiations
* quotes
* claims
* transaction exceptions
* payments
* deliveries
* system observations
* agent observations
* document ingestion

Each episode must preserve:

* stable episode UUID
* participants
* canonical subject references
* occurred/effective times
* content
* attachments/references where applicable
* evidence references
* provenance
* security
* source identity
* idempotency key
* content hash

Repeated ingestion of the same source event must not create duplicate episodes.

Do not bind this contract to VanillaSoft or any particular communications provider.

Phase 8 — Implement reliable projection/outbox semantics

Do not directly update external vector databases, graph databases, or remote intelligence services inside Odoo business transactions.

Implement or reuse a durable Odoo-owned projection/outbox boundary.

A projection event should contain enough information to identify:

* canonical subject
* subject revision
* projection type
* source snapshot
* causation ID
* correlation ID
* projector/compiler version
* idempotency identity
* processing state
* retry state
* created/processed timestamps
* failure information

Required states should support at least the equivalent of:

* pending
* processing
* completed
* failed
* superseded

External projection failure MUST NOT roll back already-valid canonical Odoo business state.

Workers must safely retry.

The system must be able to determine whether a given subject revision has already been projected.

Projection order must be deterministic where ordering matters.

Phase 9 — Semantic document projection

Adopt/harden semantic-document only after canonical snapshots are stable.

Implement deterministic:

CanonicalSnapshot / Evidence / Episode → SemanticDocument

compilation.

The contract must remain embedding-provider neutral.

Do not choose or tightly couple the architecture to a specific vector database or embedding provider unless the repository already has an approved provider abstraction.

Semantic documents must include:

* canonical subject references
* source revision
* textual content
* structured metadata
* deterministic content hash
* chunking policy/version
* security/retrieval scope
* embedding state

If vectors are stored in the contract, validate supplied vector length against declared dimensions at the semantic validation layer.

Semantic projections must be fully rebuildable from authoritative source contracts.

Phase 10 — Structural graph projection

Adopt/harden structural-projection as a provider-neutral graph mutation contract.

Structural projections must be generated only from:

* canonical snapshots
* approved evidence relationships
* explicitly approved graph mappings

Graph nodes and edges must preserve canonical UUID identity.

Correct any inconsistent edge-deletion identity contract before adoption.

Support deterministic:

* upsert
* delete
* reconcile
* rebuild

A graph provider must never become the canonical holder of an organization, facility, material, opportunity, or commercial relationship.

A complete graph reconstruction from authoritative Odoo snapshots and evidence must be possible.

Do not make Neo4j, Neptune, Memgraph, or any other graph technology a permanent domain dependency unless such a provider is already an approved infrastructure choice.

Phase 11 — Packet contract

Review and harden packet.schema.yaml as the provider-neutral envelope for communication between bounded contexts, services, workers, and agents.

Preserve:

* correlation
* causation
* ancestry
* authority
* subject references
* evidence references
* policy/model versions
* fingerprints
* validation
* lifecycle
* trace metadata

Ensure that generated/derived packets are required to include the lineage necessary to reconstruct causality.

Packets MUST carry authority constraints.

Packets do not grant authority simply because an agent or service emitted them.

Phase 12 — Explicitly defer opportunity and matching implementation

Review and repair these contracts for later adoption:

* opportunity-protocol.schema.yaml
* match-execution-packet.schema.yaml
* transaction-candidate.schema.yaml
* improvement-packet.schema.yaml

They may be corrected, tested, versioned, and documented in this program, but their runtime engines MUST NOT be implemented unless required only to prove schema/compiler boundaries.

Specifically:

Opportunity protocol

Prepare one common normalized protocol for future supply and demand opportunities without implementing the matching engine.

Match execution

Preserve the machine-first execution contract for future matching runs.

Transaction candidate

Preserve candidate economics, routes, processing legs, evidence gaps, gates, margin, and next actions.

Improvement packet

Preserve governed reverse-flow learning.

direct_mutation_permitted must remain false or equivalent.

Analytical or agent-generated improvement suggestions may propose changes but MUST NOT directly mutate canonical policy, taxonomy, capability, workflow, or business records.

Phase 13 — Security and authority

Projection architecture must propagate security classification from canonical source into downstream contracts.

At minimum account for:

* public
* internal
* confidential
* restricted
* highly restricted

Do not project sensitive source fields blindly.

Explicitly define:

* allowed projection layers
* redacted fields
* permitted consumers
* prohibited consumers/topics where supported
* credentials exclusion
* PII handling
* financial information handling

Credentials MUST never enter semantic documents, vector embeddings, temporal episodes, graph projections, packets, logs, or analytical datasets.

Phase 14 — Determinism and replay

Every projection path must be deterministic and idempotent.

Test at minimum:

1. compile canonical snapshot
2. compile it again unchanged
3. verify equivalent content/fingerprint
4. modify an authoritative field
5. verify expected revision/fingerprint change
6. project semantic document
7. repeat projection
8. verify no duplicate semantic artifact
9. project temporal episode
10. repeat identical source event
11. verify no duplicate episode
12. project graph mutation
13. replay it
14. verify equivalent graph state
15. force projection failure
16. retry
17. verify eventual success without canonical Odoo mutation
18. rebuild projections from authoritative source
19. compare resulting semantic/structural state with expected deterministic state

Clean rebuild must not require manual repair.

Phase 15 — Testing

Implement unit tests for:

* schema validation
* schema reference resolution
* canonical UUID behavior
* revision behavior
* fingerprints
* snapshot compilation
* evidence validation
* evidence supersession
* temporal idempotency
* security propagation
* semantic compilation
* structural compilation
* projection idempotency
* outbox retry
* packet lineage
* authority enforcement

Implement integration tests for:

* Odoo record → canonical snapshot
* canonical snapshot → projection event
* projection event → semantic document
* projection event → structural projection
* source interaction → temporal episode
* evidence creation → snapshot/evidence relationship
* retry after projector failure
* complete projection rebuild

Add negative tests for:

* malformed contracts
* missing canonical identity
* stale revision
* duplicate idempotency key
* invalid schema version
* invalid subject relationship
* unauthorized projection
* sensitive data leakage
* invalid packet authority
* broken causation lineage
* impossible graph deletion
* provider failure

Phase 16 — Command surface and observability

Use existing repository command conventions.

Expose the smallest coherent commands for validation/rebuild rather than introducing an independent operational framework.

Conceptually support commands equivalent to:

make contracts-validate

make projections-test

make projections-rebuild db=odoo_test

Exact names should follow repository conventions discovered during inspection.

Every projection run should report enough information to reconcile:

* run UUID
* projection type
* records/snapshots seen
* created
* updated
* unchanged
* superseded
* rejected
* failed
* retried
* final status
* start time
* completion time
* projector version

Do not log sensitive projected content unnecessarily.

Program invariants

The implementation MUST converge on all of these:

1. Odoo is authoritative.
2. Canonical UUIDs are stable.
3. Odoo integer IDs do not become external global identities.
4. Canonical contracts are provider-neutral.
5. Projections are disposable and rebuildable.
6. External projection failure does not corrupt Odoo transactions.
7. Evidence is not silently promoted to canonical truth.
8. Agents cannot directly mutate authority through improvement packets.
9. Memory infrastructure is replaceable.
10. Graph infrastructure is replaceable.
11. Transport infrastructure is replaceable.
12. No second canonical contract tree exists.
13. No provider-specific identifiers leak into canonical contracts unnecessarily.
14. All projection execution is idempotent.
15. Security restrictions propagate downstream.
16. Matching remains deferred until this foundation is proven.

Do not prematurely introduce infrastructure

Do not introduce Kafka, NATS, SQS, Redis Streams, or another event bus merely for architectural completeness.

First implement or reuse the reliable Odoo-local outbox/projection boundary.

Do not choose a vector database merely to complete this program.

Do not choose a graph database merely to complete this program.

Provider integrations can be implemented later behind stable contracts after deterministic projections are proven.

Convergence process

Run iterative:

inspect → classify → design → implement → validate → replay → simplify

passes until stable.

Minimum convergence passes: 3.

On each pass check specifically for:

* duplicate contract authority
* accidental provider coupling
* hidden Odoo model coupling in downstream services
* non-deterministic fingerprints
* unstable UUID generation
* incorrect revision behavior
* projection duplicates
* security leakage
* synchronous external side effects inside canonical transactions
* non-rebuildable external state
* dead or obsolete schemas
* undocumented semantic validators
* premature matching implementation

Prefer deleting redundant abstractions over preserving parallel authorities.

Authority

Allowed:

* repository inspection
* git history inspection
* local code changes
* schema changes
* local migrations
* local tests
* safe nonproduction Odoo database changes
* temporary nonproduction projection data
* deterministic projection rebuilds against verified test environments
* documentation updates

Forbidden without explicit authorization:

* production database mutation
* production projection rebuild
* production external-system mutation
* push
* merge
* destructive production operation

Stop conditions

Do not:

* fabricate missing business semantics
* invent canonical mappings without repository/runtime evidence
* create a second source of truth
* make an external memory or graph provider canonical
* hide provider-specific fields in supposedly canonical contracts
* implement opportunity matching before this foundation passes
* build future CRM adapters
* silently weaken security controls
* claim deterministic replay without executing replay
* claim rebuildability without performing a clean rebuild
* claim contract validity without actual schema validation
* claim runtime correctness without nonproduction integration evidence

Mark unresolved facts UNKNOWN.

Completion criteria

This program is complete only when:

* existing and recovered contracts have been reconciled into one authoritative contract architecture
* adopted schemas validate correctly
* semantic/domain validation is separated cleanly from portable JSON Schema where necessary
* canonical identity rules are implemented and tested
* canonical revision behavior is implemented and tested
* canonical fingerprints are deterministic
* canonical snapshot compilation works against verified Odoo models
* evidence-record creation and validation work
* temporal-episode ingestion is idempotent
* reliable projection/outbox behavior exists
* projection retry is verified
* semantic-document compilation is deterministic
* structural-projection compilation is deterministic
* semantic and structural projections are rebuildable
* provider failures do not corrupt Odoo authoritative state
* packet lineage and authority rules are validated
* security/redaction constraints propagate into projections
* opportunity/matching contracts have been classified/repaired but runtime matching remains deferred
* no duplicate canonical schema authority remains
* tests pass
* at least one full clean projection rebuild against nonproduction state passes
* repeated projection execution produces no unexplained duplicates
* documentation describes the canonical/projection architecture and extension rules
* all remaining unresolved facts are explicitly listed as UNKNOWN

At completion return:

* verified starting state
* changed files
* contracts adopted
* contracts superseded
* contracts deferred
* migrations performed
* canonical identity rules
* revision/fingerprint rules
* projection architecture
* commands executed
* test results
* replay/rebuild results
* idempotency evidence
* security validation results
* remaining UNKNOWNs
* blockers
* exact reasons any completion criterion was not met

Do not report this program complete unless deterministic replay and a clean nonproduction projection rebuild have actually passed.