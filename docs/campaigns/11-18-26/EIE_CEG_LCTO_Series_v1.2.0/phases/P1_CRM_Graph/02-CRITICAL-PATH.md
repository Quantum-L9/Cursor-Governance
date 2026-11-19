# Root cause and unlock order

The critical path is the smallest *actual dependency graph*, not a serial queue for all work. Only listed successors wait. Recheck changing facts at their declared hinge, not by restarting a census.

| Step | Owner | Real blocker | Required prior gates | Proof to unlock | Unblocks |
|---|---|---|---|---|---|
| CP10 | BASE | P0 spec and Gate compatibility are required for safe identity mapping. | none | Verify complete predecessor receipt and tenant pack; do not substitute snapshot. | G0 |
| CP11 | CRM | Existing scan accepts a supplied field list but lacks integrated customer record mapping and stable graph identities. | G0 | Two resource-specific source IDs map to typed ontology nodes without collision. | G1 |
| CP12 | GRAPH | Node graph must exist before association evidence can be linked. | G1, G2 | Publish green unit-tested source-shaped projection/edge PRs; actual signed graph readback deferred until final program rail. | G3, G4 |

**Proof distinctions:** Where relevant, source implementation, artifact publication, consumer availability, deployment, runtime operation and observed outcome are distinct. Apply only stages the objective needs; never invent a release ceremony.
