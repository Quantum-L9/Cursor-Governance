# Evidence-based definition of done

| Gate | Owner | Dependency | Claim | Required proof | Status | Receipt |
|---|---|---|---|---|---|---|
| G0 | BASE | none | P0 code and docs PRs are published and green at pinned stacked heads, with compatible test-domain contracts; no Docker or merge required. | Verify P0 PR URLs, parent refs, unit/contract CI on exact heads and current spec source; parent stack basis in P1 ledger. | NOT_RUN | NOT_RUN |
| G1 | CRM | G0 | CRM metadata and records map to declared ontology fields with stable provider/resource/record identities. | Source-shaped CRM fixture with company/facility distinction and separate association, rejected ambiguity, original source provenance. | NOT_RUN | NOT_RUN |
| G2 | GRAPH | G0 | CEG graph node/child projection generates correct typed idempotent operations in isolated handler/unit tests; live Neo4j readback deferred to P4. | Run existing CEG tests with fake/mock graph driver and expected Cypher/typed node/edge operations, including idempotency and tenant negatives. | NOT_RUN | NOT_RUN |
| G3 | ASSOC | G1, G2 | CRM association maps to a spec-declared evidence edge with correct identity, source and endpoint preconditions in non-Docker tests. | Unit/contract fixture with known endpoints and missing endpoint negative, CEG row type/ref checks and exact evidence identifiers. | NOT_RUN | NOT_RUN |
| G4 | QA | G1, G2, G3 | P1 CRM bootstrap graph hydration code is published on green stacked PRs; source-shaped projection/relationship assertions are proven without claiming live graph state. | Current-head green P1 PRs + fixture path from CRM record/field metadata through EIE mapping to CEG typed sync and relationship contracts; final Neo4j readback in P4. | NOT_RUN | NOT_RUN |

## Negative controls

- **G0**: Do not require previous phase full five-service execution.
- **G1**: Different CRM resources sharing name/id cannot collide.
- **G2**: In-memory or fake graph result must never be reported as an actual database write.
- **G3**: No inferred commercial relevance from observed association membership.
- **G4**: No premature Docker/Neo4j runtime claim or CRM auto-write.

No gate passes from a job's green banner when mandatory steps were skipped. A source file, PR, release artifact, deployed image and real runtime are distinct evidence stages. A PASS is eligible only when the actual required proof executed and the final exact head/result is bound. A BLOCKED gate needs one actual wake condition, not a fabricated retry. NOT_APPLICABLE requires the rationale recorded in CAMPAIGN.json.

All in-scope findings must be FIXED, ALREADY_SATISFIED, INVALID, or explicitly BLOCKED with owner and wake action. An unresolved BLOCKED cannot be called DONE.
