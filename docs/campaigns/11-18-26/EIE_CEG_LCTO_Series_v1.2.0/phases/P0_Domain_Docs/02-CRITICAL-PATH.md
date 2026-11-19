# Root cause and unlock order

The critical path is the smallest *actual dependency graph*, not a serial queue for all work. Only listed successors wait. Recheck changing facts at their declared hinge, not by restarting a census.

| Step | Owner | Real blocker | Required prior gates | Proof to unlock | Unblocks |
|---|---|---|---|---|---|
| CP00 | BASE | No pinned, admitted deployment tenant spec or signed live seam receipt is available. | none | Bind current native test-pack/source and current LCTO authority for code; active production admission is an explicit P4-only Unknown. | G0 |
| CP01 | ESPEC | EIE typed sync from an old CEG spec snapshot is insufficient for a cross-engine live compatibility claim. | G0 | Run native EIE/CEG typed compatibility checks without Docker; final live pack tested only in P4. | G_SPEC |
| CP02 | DOC | Docs/guides do not accurately describe the as-built code, product objective and review authority. | none | Current README + concise AGENTS + sharp local invariant tests + ADR index/successor + CI docs check. | G_DOC |
| CP03 | BASE | Independent passing checks do not prove the common signed sync seam. | G_DOC, G_SPEC, G_ROUTE | Unit/contract action parity, policy and negative actor tests; defer real signed service integration to P4. | G_DONE |

**Proof distinctions:** Where relevant, source implementation, artifact publication, consumer availability, deployment, runtime operation and observed outcome are distinct. Apply only stages the objective needs; never invent a release ceremony.
