# Swarm scheduling and exclusive ownership

| Lane | Assignment | Kind | Exclusive files / patterns | Lane predecessor | Gate barrier |
|---|---|---|---|---|---|
| BASE | P3/current integration proof census | assurance | READ-ONLY | none | none |
| SWEEP | EIE CEG-readiness-driven enrichment orchestration | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: app/engines/enrichment_sweep.py, app/engines/sweep_handlers.py, app/services/sweep_store.py, tests/unit/test_enrichment_sweep.py | none | G0 |
| DECISION | CEG graph-backed matching, readiness and evidence | writer | https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/health/api.py, engine/health/gap_prioritizer.py, engine/handlers.py, engine/scoring/graph_evidence.py, tests/unit/test_handle_score.py | none | G0 |
| E2E | Real signed integration test and crash replay | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: tests/e2e/*, tests/integration/test_eie_ceg_mesh.py, scripts/eie_ceg_mesh_verify.sh | none | G0 |
| DOC | EIE final as-built README, agent, invariant and ADR alignment | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: README.md, AGENTS.md, docs/INVARIANTS.md, docs/ARCHITECTURE.md, docs/EXECUTION_FLOWS.md, docs/REPO_MAP.md, docs/contracts/README.md, docs/adr/*.md, docs/FILE_INDEX_FOR_AGENTS.md | none | G0 |

- Size the pool to useful concurrent lanes and current mode capacity. An assurance lane can operate while a writer waits. Reuse idle slots rather than spawning replacements as scaling.
- Every writer is the exclusive owner of its declared paths, lockfiles, generated outputs and branch. The compiler refuses possible write-scope collisions; any necessary shared file goes to one owner and is sequenced, never edited concurrently.
- Each child brief begins with exact `repository_access`. This is descriptive scope, not a technical access-control grant. Host permissions must enforce it.
- Agents own their PR remediation to ready-to-merge; the LCTO owns cross-lane review and integration and never edits a lane's branch to fix a bug.
- Keep source and integration branches bound to the current live base/stack. Never force-stack unrelated PRs or block independent lanes on an unrelated merge.
- On Claude Code cloud, the active LCTO launch adapter owns repository attachment, role registration and derived child prompts. On Cursor, use the native Task continuation semantics. Do not improvise child system prompts or session transport.
