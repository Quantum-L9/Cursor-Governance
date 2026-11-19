# Root cause and unlock order

The critical path is the smallest *actual dependency graph*, not a serial queue for all work. Only listed successors wait. Recheck changing facts at their declared hinge, not by restarting a census.

| Step | Owner | Real blocker | Required prior gates | Proof to unlock | Unblocks |
|---|---|---|---|---|---|
| CP30 | BASE | P2 durable graph seam required before maximizing enrichment throughput. | none | Verify exact P2 receipt and current effective domain weights. | G0 |
| CP31 | INFER | Inference planning currently occurs after acquisition and undercounts source-defined downstream value. | G0 | Run cheap closure first, perform unique reachable unlock ranking, test zero-cost and multihop. | G1 |
| CP32 | PROJECTION | Unrequested prerequisites and evidence can be dropped at consumer-schema/typed-sync boundaries. | G0 | Prove graph-only declared fields survive EIE projection into typed CEG sync row fixtures, without CRM response widening; live CEG readback P4. | G3 |
| CP33 | QA | Provider and infer outputs are not enough without combined cost, evidence, graph proof. | G1, G2, G3 | Finish native cost/source/contract tests; record combined graph proof as a P4-only acceptance, not a P3 PR publication blocker. | G_DONE |

**Proof distinctions:** Where relevant, source implementation, artifact publication, consumer availability, deployment, runtime operation and observed outcome are distinct. Apply only stages the objective needs; never invent a release ceremony.
