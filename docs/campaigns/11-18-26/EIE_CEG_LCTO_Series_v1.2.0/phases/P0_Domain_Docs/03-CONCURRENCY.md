# Swarm scheduling and exclusive ownership

| Lane | Assignment | Kind | Exclusive files / patterns | Lane predecessor | Gate barrier |
|---|---|---|---|---|---|
| BASE | Authority, baseline and seam assurance | assurance | READ-ONLY | none | none |
| DOC | EIE documentation and invariants single writer | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: README.md, AGENTS.md, docs/INVARIANTS.md, docs/ARCHITECTURE.md, docs/EXECUTION_FLOWS.md, docs/REPO_MAP.md, docs/FILE_INDEX_FOR_AGENTS.md, docs/contracts/README.md, docs/CLAUDE.md, CLAUDE.md, docs/adr/*.md, .github/workflows/docs-consistency.yml, local_pr_pipeline/docs_consistency_local.sh, local_pr_pipeline/docs_link_check_local.py | none | none |
| ESPEC | EIE native spec and typed compatibility | writer | https://github.com/Quantum-L9/Enrichment.Inference.Engine: domains/plasticos/spec.yaml, app/engines/domain_spec_compatibility.py, app/engines/domain_yaml_reader.py, tests/fixtures/ceg/plasticos.spec.yaml, tests/contracts/test_native_domain_spec.py, tests/unit/test_effective_domain_reader.py | none | G0 |
| CEGSPEC | CEG native admission correction when actually needed | writer | https://github.com/Quantum-L9/Cognitive.Engine.Graphs: engine/config/loader.py, engine/config/tenant_mapping.py, engine/sync/row_contract.py, tests/unit/test_domain_pack_loader.py, tests/unit/test_native_domain_integrity.py | none | G0 |
| SEAM | Gate route and security assurance | assurance | READ-ONLY | none | G0 |

- Size the pool to useful concurrent lanes and current mode capacity. An assurance lane can operate while a writer waits. Reuse idle slots rather than spawning replacements as scaling.
- Every writer is the exclusive owner of its declared paths, lockfiles, generated outputs and branch. The compiler refuses possible write-scope collisions; any necessary shared file goes to one owner and is sequenced, never edited concurrently.
- Each child brief begins with exact `repository_access`. This is descriptive scope, not a technical access-control grant. Host permissions must enforce it.
- Agents own their PR remediation to ready-to-merge; the LCTO owns cross-lane review and integration and never edits a lane's branch to fix a bug.
- Keep source and integration branches bound to the current live base/stack. Never force-stack unrelated PRs or block independent lanes on an unrelated merge.
- On Claude Code cloud, the active LCTO launch adapter owns repository attachment, role registration and derived child prompts. On Cursor, use the native Task continuation semantics. Do not improvise child system prompts or session transport.
