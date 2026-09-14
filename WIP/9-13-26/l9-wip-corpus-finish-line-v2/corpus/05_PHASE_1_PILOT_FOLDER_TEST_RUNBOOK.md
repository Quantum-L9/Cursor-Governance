# Phase 1 - Pilot Folder Test Playbook

## Objective
Prove the complete corpus path on one deliberately messy representative folder before scaling.

## Pilot corpus
Use 25-75 artifacts and include, where realistic:
- current spec
- older spec
- exact duplicate
- near-duplicate draft
- roadmap
- TODOs
- explicit dependency
- explicit blocker
- superseded artifact
- references / see-also links
- mixed formats such as PDF/DOCX
- nested ZIP/archive

## Pass 1 - Acquisition
Run l9-meta-injector local-source in read-only mode.

Verify:
- every expected artifact is accounted for or explicitly reported as a coverage gap
- exact duplicate detection
- Depends on / Requires
- Blocked by
- References / See also
- Supersedes / Superseded by
- open tasks and declared statuses
- unsupported/scanned/encrypted files are gaps, not silently empty documents

Gate: if observation is wrong, stop.

## Pass 2 - Topology compilation
Feed Repository Model Packet(s) and corpus analysis input into l9-constellation-topology.

Check:
- expected DEPENDS_ON edges
- expected SUPERSEDES edges
- DUPLICATE_OF semantics
- REFERENCES remains weaker than DEPENDS_ON
- blockers represented
- unresolved targets remain unresolved
- candidate relations never become canonical accidentally

Gate: Topology validation must be passed.

## Pass 3 - Publication preflight
Generate publication plan and inspect:
- eligible
- held
- rejected
- skipped

Run l9-graphiti-memory ingestion in preflight mode only.

Gate: held/rejected/skipped candidates produce zero writes.

## Pass 4 - Apply, query, replay
Apply only after preflight matches expectations.

Verify at:
- canonical Memory store
- projection outbox
- Graphiti projection

Query acceptance questions:
- What files depend on X?
- What is blocked by Y?
- Which artifact supersedes Z?
- What files are connected to project A?
- Which exact duplicates exist?
- What upstream artifacts led to this spec?
- What is impacted if foundational contract X changes?

Replay the same ingestion unchanged.
Expected: no duplicate logical memory.

## Mutation test
Change the pilot corpus intentionally:
- edit one dependency
- add a draft
- remove a file
- rename without changing bytes
- change supersession
- add conflicting status
- add duplicate elsewhere

Expected:
source delta -> corpus delta -> topology delta -> memory lifecycle change -> Graphiti projection change

## Exit criteria
Do not scale until:
- expected corpus coverage is explicit
- identities are stable
- evidence survives to Topology
- candidate/canonical separation holds
- Topology validates
- publication fails closed
- preflight matches plan
- apply admits expected records
- relationships are queryable
- replay is idempotent
- changed-source rerun updates instead of multiplying stale truth
- projection rebuild works
