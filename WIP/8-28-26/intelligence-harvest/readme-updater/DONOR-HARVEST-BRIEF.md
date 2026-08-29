# Donor Harvest Brief — /tmp/l9-ih-readme-updater-donor → skills/l9-update-agent-docs [readme updater]

## Executive Picture
Status: PARTIAL. Highest-leverage nugget: c-required-section-validation.

## Source Identity
```json
{'file_count': 7, 'git_sha': 'b785c41599f0b6336c30c55d4a4d746be7dc6bb0', 'inventory_status': 'PASS', 'kind': 'directory', 'path': '/private/tmp/l9-ih-readme-updater-donor', 'ref': 'main', 'remote': 'Quantum-L9/L9_Original_Repo'}
```

## Inventory
- config/subsystems/readme_config.yaml | canonical
- .github/scripts/validate-readme-sections.py | canonical
- scripts/generate_subsystem_readmes.py | canonical
- core/agents/codegenagent/readme_generator.py | canonical
- agents/codegenagent/readme_generator.py | duplicate
- tests/core/agents/codegenagent/test_readme_generator.py | active
- workflows/dags/readme_pipeline_dag.py | active

## System Reconstruction
```json
{'control_flow': [{'from': 'config/subsystems/readme_config.yaml', 'relation': 'SSOT input', 'to': 'scripts/generate_subsystem_readmes.py'}, {'from': 'config/subsystems/readme_config.yaml', 'relation': 'required-section contract', 'to': '.github/scripts/validate-readme-sections.py'}, {'from': 'scripts/generate_subsystem_readmes.py', 'relation': 'overwrite after optional .bak', 'to': 'subsystem README.md'}, {'from': 'core/agents/codegenagent/readme_generator.py', 'relation': 'in-memory template render; not the pipeline SSOT', 'to': 'GeneratedReadme'}], 'dependencies': [{'name': 'PyYAML', 'used_by': 'generator and validator'}, {'name': 'worldtimeapi.org / timeapi.io', 'note': 'donor infrastructure; not harvested', 'used_by': 'verify_system_time in generator'}], 'identity': 'Donor readme-updater cluster on Quantum-L9/L9_Original_Repo@b785c415: a config-SSOT pipeline that generates and validates subsystem README.md files, plus a separate CodeGenAgent template generator.', 'must_not_own': ['CodeGenAgent runtime', 'DORA metadata blocks', 'donor worldtime verification', 'wholesale README generation inside l9-update-agent-docs', 'readme-pipeline-v1 DAG ownership (already under workflows/)'], 'ownership_boundaries': [{'owner': 'readme_config.yaml', 'owns': 'required sections, tiers, forbidden/allowed scopes, invariants'}, {'owner': 'generate_subsystem_readmes.py', 'owns': 'live generate/list/validate CLI for subsystem READMEs'}, {'owner': 'ReadmeGenerator', 'owns': 'CodeGenAgent module/subsystem/metadata templates'}, {'owner': 'skills/l9-update-agent-docs', 'owns': 'root pointer-stack writes; not subsystem README generation'}], 'workflows': [{'evidence_ids': ['e-dag-keys'], 'id': 'readme-pipeline-v1', 'steps': ['gap analysis of config vs directories', 'config enrichment', 'template update', 'generate via scripts/generate_subsystem_readmes.py', 'validate required sections', 'report']}]}
```

## Surface / Target Graph
- scripts/generate_subsystem_readmes.py | /tmp/l9-ih-readme-updater-donor/scripts/generate_subsystem_readmes.py | cli
- .github/scripts/validate-readme-sections.py | /tmp/l9-ih-readme-updater-donor/.github/scripts/validate-readme-sections.py | cli
- workflows/dags/readme_pipeline_dag.py | /tmp/l9-ih-readme-updater-donor/workflows/dags/readme_pipeline_dag.py | session-dag
- core/agents/codegenagent/readme_generator.py | /tmp/l9-ih-readme-updater-donor/core/agents/codegenagent/readme_generator.py | library

## Duplicate and Drift Register
- Two ReadmeGenerator modules exist with different sha256 (8304bb11 vs 4656b575). | core/agents/codegenagent/readme_generator.py | Tests import the core path; agents/ copy is duplicate.
- Beneficiary already has readme-pipeline-v1 DAG text that names generate_subsystem_readmes.py and readme_config.yaml, but those files are absent locally. | donor scripts/generate_subsystem_readmes.py plus config SSOT | DAG projection without generator is stale wiring, not an l9-update-agent-docs ownership claim.

## Nugget Register
- c-required-section-validation | Declarative required-section validation | PORT_WITH_HARDENING | leverage=5 | destination=skills/l9-update-agent-docs Step 3 README write plus Validation
- c-bind-before-write | Inventory live README targets before write | MERGE_WITH_EXISTING | leverage=3 | destination=skills/l9-update-agent-docs Step 1 Bind live targets

## Beneficiary Fit
- c-required-section-validation | PORT_WITH_HARDENING | skills/l9-update-agent-docs Step 3 README write plus Validation
- c-bind-before-write | MERGE_WITH_EXISTING | skills/l9-update-agent-docs Step 1 Bind live targets

## Safety and Portability Audit
- CONFIRMED | Donor code was inventoried and read, not executed.
- CONFIRMED | No files under skills/l9-update-agent-docs were created or edited.
- CONFIRMED | CodeGenAgent templates, DORA footers, and worldtime verification were not treated as transferable machinery.

## Concept Acceptance Tests
- c-required-section-validation | Given a live README whose declared required index headings are missing | When the beneficiary README step runs | Then the run reports the missing headings and does not treat the index as honest | Must not overwrite the README from a template or invent missing root files
- c-bind-before-write | Given a declared README path that does not exist | When the skill binds targets | Then the path is recorded Unknown and is not created | Must not create a root README to satisfy a template
- c-readme-as-binding-contract | Given a proposal to make root README.md a binding AI-scope contract | When beneficiary fit is applied | Then the concept is rejected and pointer-only README ownership remains | Must not move operating rules from AGENTS.md into README.md
- c-config-driven-overwrite | Given this harvest | When transfer is considered | Then the generator and backup overwrite stay donor-local | Must not copy generate_subsystem_readmes.py into the skill pack
- c-pipeline-dag-ownership | Given readme-pipeline-v1 already registered under workflows/ | When beneficiary destination is l9-update-agent-docs | Then DAG ownership is rejected for this skill | Must not move or re-own readme-pipeline-v1 inside the skill pack

## Rejected and Local Concepts
- c-readme-as-binding-contract | REJECT | README as binding contract with AI scopes
- c-config-driven-overwrite | KEEP_LOCAL | Config-driven README overwrite with backup
- c-pipeline-dag-ownership | REJECT | readme-pipeline-v1 DAG as skill capability

## Highest-Leverage Next Action
c-required-section-validation

## UNKNOWNs
- Whether .github/scripts/validate-readme-sections.py is invoked by donor CI; workflows were outside the sparse inventory.
- The exact semantic delta between the two readme_generator.py copies beyond unequal sha256.
- Which headings a hardened pointer-stack required-section map should name; beneficiary README live headings were not re-audited as a count in this harvest.
