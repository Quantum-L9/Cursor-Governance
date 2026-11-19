# Swarm scheduling and exclusive ownership

| Lane | Assignment | Kind | Exclusive files / patterns | Lane predecessor | Gate barrier |
|---|---|---|---|---|---|
| BASE | Previous phase and durable state source census | assurance | READ-ONLY | none | none |
| OUT | EIE persisted result to CEG durable outbox | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/side_effect_coordinator.py, app/services/pg_models.py, migrations/versions/*, app/engines/handlers.py, app/engines/packet_router.py, tests/unit/test_side_effect_coordinator.py, tests/unit/test_converge_graph_sync.py, tests/unit/test_score_invalidation.py | none | G0 |
| IN | EIE durable CEG inference feedback intake | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/graph_return_channel.py, app/services/chassis_handlers.py, tests/services/test_graph_return_channel.py, tests/services/test_chassis_handlers.py | none | G_SCHEMA |
| FEED | CEG feedback sender and owned rule trigger | writer | https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/gate_egress.py, engine/handlers.py, engine/inference_rule_registry.py, tests/unit/test_graph_inference_egress.py, tests/unit/test_admin_tenant_binding.py | none | G0 |
| SEAM | Gate and scoring cache seam audit | assurance | READ-ONLY | none | G0 |

- Size the pool to useful concurrent lanes and current mode capacity. An assurance lane can operate while a writer waits. Reuse idle slots rather than spawning replacements as scaling.
- Every writer is the exclusive owner of its declared paths, lockfiles, generated outputs and branch. The compiler refuses possible write-scope collisions; any necessary shared file goes to one owner and is sequenced, never edited concurrently.
- Each child brief begins with exact `repository_access`. This is descriptive scope, not a technical access-control grant. Host permissions must enforce it.
- Agents own their PR remediation to ready-to-merge; the LCTO owns cross-lane review and integration and never edits a lane's branch to fix a bug.
- Keep source and integration branches bound to the current live base/stack. Never force-stack unrelated PRs or block independent lanes on an unrelated merge.
- On Claude Code cloud, the active LCTO launch adapter owns repository attachment, role registration and derived child prompts. On Cursor, use the native Task continuation semantics. Do not improvise child system prompts or session transport.
