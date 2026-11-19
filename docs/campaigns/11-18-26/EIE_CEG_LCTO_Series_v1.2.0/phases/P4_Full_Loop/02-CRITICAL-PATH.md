# Root cause and unlock order

The critical path is the smallest *actual dependency graph*, not a serial queue for all work. Only listed successors wait. Recheck changing facts at their declared hinge, not by restarting a census.

| Step | Owner | Real blocker | Required prior gates | Proof to unlock | Unblocks |
|---|---|---|---|---|---|
| CP40 | BASE | Previous completed EIE provider/graph durability receipts and signed keys are needed for true acceptance. | none | Bind green prior P3 PR code, not Docker/runtime secrets; defer test credentials to G_PUBLISH. | G0 |
| CP41 | DECISION | A rich graph is only commercially useful if it changes a CEG decision on actual graph evidence. | G0 | Build deterministic CEG score/match evidence fixtures and targeted unit tests before PUBLISH; real before/after Neo4j causal proof under P4 G_RAIL. | G_SCORE |
| CP42 | E2E | Separate tests do not prove integrated graph and retry. | G_PUBLISH | After all PRs are published green, execute one complete signed Docker rail on pinned EIE/CEG/Gate branch heads; rerun if necessary after owner fixes. | G_RAIL |
| CP43 | DOC | P4 DOC PR must be published green before Docker without claiming future runtime results; afterwards docs must reflect actual observed integration. | G0 | Author/publish DOC changes before Docker (G_DOC_PREP); after G_RAIL correct observed behavior within the same PR and complete G_DOC. | G_DOC_PREP, G_DOC, G_DONE |
| CP_PUBLISH | BASE | Final Docker would be wasted on incomplete or wrongly based PR trains. | G_SWEEP, G_SCORE, G_E2E_CODE, G_DOC_PREP | Check E2E test-code and DOC prepublication gates, then all P0-P4 PR URLs and exact stack base/head/CI, and bounded signing secrets before Docker. | G_PUBLISH, G_RAIL |

**Proof distinctions:** Where relevant, source implementation, artifact publication, consumer availability, deployment, runtime operation and observed outcome are distinct. Apply only stages the objective needs; never invent a release ceremony.
