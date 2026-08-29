Execute the next implementation phase for https://github.com/cryptoxdog/IB-Odoo_19 by resuming from the repository’s actual current state, not rebuilding existing work. Treat Staging as the working/default integration branch unless repository inspection proves otherwise. First inspect the current code, git history, tests, documentation, migration artifacts, CieTrade exports, VanillaSoft integration code, Odoo models/fields, Makefile/command conventions, and existing contract/schema work. Preserve correct existing implementation and explicitly classify anything unverified as UNKNOWN.

The primary objective is to complete and prove two deterministic, repeatable data-ingestion workflows: CieTrade → Odoo and VanillaSoft → Odoo. Both must be safe to rerun, reconcile source records to resulting Odoo state, expose a single canonical repository-supported command, fail closed on material errors, and produce machine-readable execution summaries. Do not perform production imports, production database mutations, pushes, or merges without explicit authorization.

For CieTrade, recover and reuse the existing plasticos_partner_import implementation, but correct the source boundary so the tracked raw CieTrade export can be imported directly without undocumented preprocessing. Inspect the actual source files and use source-native identifiers as reconciliation identities, particularly CpID, AddressID, CT_ID, and any other verified source identifiers. Do not use partner names or derived names as authoritative identity where a stable source identifier exists. Introduce or reuse the smallest coherent external-reference mechanism needed to persist (source, entity type, external id) → Odoo record identity and make reruns deterministic.

Validate every CieTrade source field against the actual Odoo model schema before finalizing mappings. For every source field record: source field, source type, target model, target field, transformation, required/optional status, null behavior, identity/match role, and mapping status. Allowed statuses are VERIFIED, NEEDS_CORRECTION, UNMAPPED_INTENTIONALLY, and UNKNOWN. Any intentionally excluded field must have an explicit reason. Never silently discard source data. Never infer undocumented CieTrade business semantics, including role/status codes. If a mapping cannot be established from repository evidence or actual Odoo schema, leave it UNKNOWN.

The CieTrade pipeline must implement the complete sequence: source load, source/schema validation, normalization, mapping, entity resolution, import/upsert, reconciliation, validation, and report generation. Validate before database mutation. Support dry-run where practical. Surface partial failures explicitly. Preserve source identifiers. Define duplicate detection and rerun behavior. On the same validated input, a second execution must not create unexpected duplicates.

The CieTrade end-to-end validation must run against a verified nonproduction Odoo database and reconcile: source rows, accepted rows, rejected rows, created records, updated records, unchanged records, duplicate records, failed records, and resulting Odoo records. Sample and verify identifiers, names, addresses, contacts, statuses, relations, dates, numeric/monetary values where present, and custom fields. Verify parent/child relationships and company/contact relationships. Zero unexplained record loss, zero unexplained duplicates, and zero silent field truncation are required for acceptance.

Expose one canonical repository command using the existing command surface, preferably the Makefile, rather than creating a parallel CLI framework. The intended operator experience is conceptually:

make import-cietrade

with optional explicit source override where appropriate. The command itself must perform environment preflight, source validation, import, reconciliation, result validation, summary emission, and proper nonzero exit on failure. It must not hide undocumented manual preparation.

For VanillaSoft, recover the existing automated work in plasticos_crm_sync and the old manual CSV import flow before changing anything. Reuse working transport, pagination, retry, authentication, watermark, mapping, and external-reference logic where correct. Do not fabricate API behavior or credentials.

Establish one minimal CRM-neutral adapter boundary and implement VanillaSoft only. The shared pipeline must remain source-neutral. Remove or decommission HubSpot, Salesforce, Zoho, or any other CRM adapter implementations/stubs/placeholders if they exist solely as future placeholders. Do not create future CRM adapter directories, classes, fake connectors, or placeholder mappings. Future CRM support belongs in roadmap documentation only.

The VanillaSoft adapter is responsible for source authentication/access, retrieval, pagination, retries/rate-limit handling, source-specific field interpretation, translation into canonical CRM records, source identity, incremental sync markers where supported, inactive/deleted semantics where supported, malformed-record handling, and source error reporting. VanillaSoft-specific status/source semantics must be normalized inside the VanillaSoft adapter rather than leaking into the shared Odoo ingestion pipeline.

The shared CRM pipeline is responsible only for canonical validation, normalization, Odoo mapping, entity resolution, deduplication, upsert/import, reconciliation, observability, and reporting. No VanillaSoft-specific strings, field names, or logic should remain in the shared orchestrator except at the explicit adapter interface.

Use the existing plasticos.crm.external.ref model, or an equivalent already-authoritative repository mechanism, as the runtime identity authority for CRM records. If legacy vanillasoft_id fields exist, treat them as migration/backfill inputs rather than an ongoing second identity authority. Perform an idempotent backfill if needed, then make external references the canonical runtime match path. Avoid maintaining two independent deduplication systems.

Refactor VanillaSoft writes so each source record is deterministically classified as created, updated, unchanged, duplicate/rejected, or failed. Do not blindly write matched records when their normalized values are unchanged. Source failures and malformed records must never become silent record loss.

Fully deprecate the old manual VanillaSoft import path. Identify its entrypoints and callers first. Migrate any required behavior to the automated path. After that, remove it if safe; otherwise leave only a compatibility entrypoint that fails immediately with a clear deprecation message directing operators to the automated command. Do not leave the manual CSV importer active as a competing authoritative path, and do not maintain duplicate mapping authority.

Expose one canonical VanillaSoft command using the repository’s existing command conventions, conceptually:

make import-vanillasoft

The command must perform preflight, VanillaSoft adapter access, retrieval, canonical translation, validation, Odoo upsert, reconciliation, summary emission, and nonzero exit on material failure. It must support safe repeated execution.

Both import workflows must report at minimum:

* source
* start_time
* completion_time
* records_seen
* records_valid
* records_rejected
* records_created
* records_updated
* records_unchanged
* duplicates
* errors
* final_status

Sensitive values and credentials must never be logged.

Add automated tests covering mappings, transformations, identity resolution, deduplication, adapter contract behavior, CieTrade-to-Odoo integration, VanillaSoft-adapter-to-shared-pipeline integration, shared-pipeline-to-Odoo integration, invalid source, missing required fields, invalid mapping, unavailable CRM source, malformed records, duplicate source data, partial batch failure, invalid Odoo targets, and source/API failures.

For each workflow, execute a representative first import and then run the exact same workflow again. Prove that the second run produces the expected unchanged/update behavior rather than duplicate creation. Also test a changed source record and verify deterministic update behavior.

After implementation, perform a clean replay from a clean verified repository checkout and nonproduction Odoo state using only the two documented canonical commands. No runtime code edits, undocumented preprocessing, manual field remapping, or normal-rerun database cleanup may be required.

The repository also contains an existing draft contract/schema architecture, and there are ten recovered candidate v2 schemas outside the current authoritative tree:

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

These recovered schemas are not part of the import critical path. Preserve them and assess them against the current repository contracts, but do not make CieTrade or VanillaSoft runtime execution depend on them during this phase. Treat them as a later contract-convergence effort after Odoo data integrity is proven.

Their intended architecture is that Odoo remains authoritative while canonical snapshots, evidence, temporal memory, semantic memory, structural/graph projections, opportunities, match execution, transaction candidates, and improvement proposals are replaceable downstream contracts/projections. Do not introduce a second canonical business authority.

During schema assessment, specifically inspect and correct known likely issues before any adoption: nonstandard JSON Schema constructs such as $data; root additionalProperties: false conflicts with conditionally introduced properties; conditional minItems rules that fail to actually require the corresponding arrays; packet lineage fields that are constrained but not required for derived generations; edge deletion identity inconsistencies; and any malformed trailing YAML/prose. Reconcile these files with the existing contracts/schemas tree rather than creating a parallel schema universe.

Do not allow this schema work to expand or block completion of the import/data-foundation milestone. The import milestone comes first.

Document a future CRM adapter roadmap only after the VanillaSoft implementation is complete. The roadmap must describe the adapter extension contract, onboarding requirements, canonical record contract, validation expectations, and testing requirements. Do not select future CRM vendors and do not create future adapter stubs.

Required architecture after convergence:

CieTrade source → CieTrade normalization/import boundary → shared deterministic Odoo upsert/reconciliation → Odoo authoritative state

VanillaSoft source → VanillaSoft adapter → canonical CRM records → shared CRM-neutral Odoo upsert/reconciliation → Odoo authoritative state

and only after authoritative data is proven:

Odoo → canonical snapshots/evidence → semantic/temporal/structural projections → opportunities → matching → transaction candidates → outcomes → governed improvement proposals

Implementation authority:

* repository inspection: allowed
* local repository changes: allowed
* local tests: allowed
* verified-safe nonproduction database imports: allowed
* temporary nonproduction test data: allowed
* production import/database mutation: forbidden without explicit authorization
* push: forbidden without explicit authorization
* merge: forbidden without explicit authorization

Stop rather than fabricate if required source data, credentials, business semantics, Odoo schema, or runtime environment cannot be verified. Record those facts as UNKNOWN.

Do not rebuild correct existing work from scratch. Do not silently discard source fields. Do not create future CRM adapters. Do not leave placeholder adapters. Do not preserve two authoritative VanillaSoft paths. Do not claim mapping correctness without inspecting the actual Odoo schema. Do not claim import correctness without database reconciliation. Do not claim idempotency without a repeated-run test. Do not claim one-command operation while undocumented manual preparation remains.

Run recursive inspect → implement → test → reconcile → replay passes until the result is stable, with at least three convergence passes. Completion requires all of the following:

* existing CieTrade work located and reused where valid
* CieTrade raw mapping verified against actual Odoo schema
* CieTrade import completed in nonproduction
* CieTrade reconciliation passed
* CieTrade repeated-run behavior passed
* canonical one-command CieTrade workflow passed
* old VanillaSoft manual flow completely accounted for
* VanillaSoft automated adapter/pipeline operational
* CRM-neutral adapter boundary enforced
* only VanillaSoft implemented
* VanillaSoft mapping verified
* VanillaSoft first and repeat imports reconciled
* changed-record update behavior verified
* manual VanillaSoft authority removed/deprecated
* canonical one-command VanillaSoft workflow passed
* future CRM integrations represented only as roadmap guidance
* clean replay of both workflows passed
* recovered v2 schema set classified and preserved without becoming an import dependency
* all remaining unresolved facts explicitly listed as UNKNOWN

At completion, return the actual changed-file summary, commands executed, tests run, reconciliation results, repeat-run results, schema disposition summary, unresolved UNKNOWNs, and any remaining blockers. Do not report completion if database reconciliation, repeat execution, or clean replay has not actually been performed.