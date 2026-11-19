# Root cause and unlock order

The critical path is the smallest *actual dependency graph*, not a serial queue for all work. Only listed successors wait. Recheck changing facts at their declared hinge, not by restarting a census.

| Step | Owner | Real blocker | Required prior gates | Proof to unlock | Unblocks |
|---|---|---|---|---|---|
| CP20 | BASE | Process-local state and live replay semantics must be bound to existing authoritative store. | none | Verify previous P1 published green PR receipts; no Docker or merged code required. | G0 |
| CP21 | OUT | EIE completed response can strand deferred CEG sync. | G0 | Persist and replay pinned payload through crash without extra provider calls. | G_OUT |
| CP22 | IN | CEG feedback accepted can be dropped before next convergence. | G_OUT | Existing durable store now supports accepted-then-restart-then-consumed semantics. | G_IN |
| CP23 | BASE | Healthy endpoints alone do not demonstrate cross-process state. | G_IN, G_FEED, G_SEAM | Close injected-store two-window restart simulator and readiness for P4 real signed Docker/Neo4j replay, without running Docker early. | G_DONE |
| CP_PERSISTENCE_SCHEMA | OUT | IN and OUT both need durable storage semantics, but schema/migration writes must have one owner and cannot wait for full outbound crash proof. | G0 | OUT publishes/locks a bounded storage interface and G_SCHEMA unit receipt immediately, unlocking IN in parallel with the rest of OUT and FEED. | G_SCHEMA, G_IN |

**Proof distinctions:** Where relevant, source implementation, artifact publication, consumer availability, deployment, runtime operation and observed outcome are distinct. Apply only stages the objective needs; never invent a release ceremony.
