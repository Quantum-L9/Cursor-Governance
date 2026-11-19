# Swarm scheduling and exclusive ownership

| Lane | Assignment | Kind | Exclusive files / patterns | Lane predecessor | Gate barrier |
|---|---|---|---|---|---|
| BASE | P2 receipts and domain/value authority | assurance | READ-ONLY | none | none |
| INFER | Inference graph, first-pass closure and value-directed planner | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/convergence_controller.py, app/engines/meta_prompt_planner.py, app/engines/inference/rule_loader.py, app/engines/inference_bridge_v2.py, app/engines/inference_bridge_adapter.py, app/engines/convergence/field_evidence.py, tests/unit/test_inference_bridge_v2.py | none | G0 |
| RESEARCH | DeepSeek + Perplexity bounded research | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/enrichment_orchestrator.py, app/engines/search_optimizer.py, app/services/perplexity_client.py, app/services/prompt_builder.py, app/services/deepseek_client.py, app/core/config.py, tests/unit/test_enrichment_orchestrator.py | none | G0 |
| PROJECTION | Eligible graph intelligence projection separate from CRM wire response | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/handlers.py, app/engines/packet_router.py, domains/plasticos/spec.yaml, tests/contracts/test_graph_sync_contract.py, tests/unit/test_typed_spec_contract.py | none | G0 |
| QA | Independent research+graph evidence audit | assurance | READ-ONLY | none | G0 |

- Size the pool to useful concurrent lanes and current mode capacity. An assurance lane can operate while a writer waits. Reuse idle slots rather than spawning replacements as scaling.
- Every writer is the exclusive owner of its declared paths, lockfiles, generated outputs and branch. The compiler refuses possible write-scope collisions; any necessary shared file goes to one owner and is sequenced, never edited concurrently.
- Each child brief begins with exact `repository_access`. This is descriptive scope, not a technical access-control grant. Host permissions must enforce it.
- Agents own their PR remediation to ready-to-merge; the LCTO owns cross-lane review and integration and never edits a lane's branch to fix a bug.
- Keep source and integration branches bound to the current live base/stack. Never force-stack unrelated PRs or block independent lanes on an unrelated merge.
- On Claude Code cloud, the active LCTO launch adapter owns repository attachment, role registration and derived child prompts. On Cursor, use the native Task continuation semantics. Do not improvise child system prompts or session transport.
