# Swarm scheduling and exclusive ownership

| Lane | Assignment | Kind | Exclusive files / patterns | Lane predecessor | Gate barrier |
|---|---|---|---|---|---|
| BASE | P0 receipt and identity assurance | assurance | READ-ONLY | none | none |
| CRM | EIE CRM field and entity projection | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/crm/base.py, app/services/crm/hubspot_client.py, app/services/crm/odoo_client.py, app/services/crm/salesforce_client.py, app/services/crm_field_scanner.py, app/services/domain_spec_workflow.py, app/api/v1/converge.py, tests/test_crm_field_scanner.py, tests/contracts/test_crm_provider_parity.py | none | G0 |
| GRAPH | CEG tenant node, child and relationship materialization | writer | https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/intake/crm_field_scanner.py, engine/intake/intake_compiler.py, engine/intake/impact_reporter.py, engine/sync/generator.py, engine/sync/row_contract.py, engine/handlers.py, tests/unit/test_domain_neutrality_acceptance.py | none | G0 |
| ASSOC | EIE observed CRM associations producer | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/services/crm/observed_relationship_producer.py, tests/unit/test_observed_relationship_producer.py, tests/integration/test_observed_relationship_producer.py | none | G0 |
| QA | Cross-engine bootstrap integration | assurance | READ-ONLY | none | G0 |

- Size the pool to useful concurrent lanes and current mode capacity. An assurance lane can operate while a writer waits. Reuse idle slots rather than spawning replacements as scaling.
- Every writer is the exclusive owner of its declared paths, lockfiles, generated outputs and branch. The compiler refuses possible write-scope collisions; any necessary shared file goes to one owner and is sequenced, never edited concurrently.
- Each child brief begins with exact `repository_access`. This is descriptive scope, not a technical access-control grant. Host permissions must enforce it.
- Agents own their PR remediation to ready-to-merge; the LCTO owns cross-lane review and integration and never edits a lane's branch to fix a bug.
- Keep source and integration branches bound to the current live base/stack. Never force-stack unrelated PRs or block independent lanes on an unrelated merge.
- On Claude Code cloud, the active LCTO launch adapter owns repository attachment, role registration and derived child prompts. On Cursor, use the native Task continuation semantics. Do not improvise child system prompts or session transport.
