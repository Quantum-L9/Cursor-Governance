# Cursor Subagent Delegation
Status: active contract  
Scope: Cursor-native subagents only  
Runtime owner: active main Cursor agent  
Safety owner: root `autonomy/`  
Durable document owner: `environment/agents/generated-data/`
## Purpose
This module lets the active main Cursor agent fan out bounded work to native
Cursor subagents while continuing critical-path work.
It does not launch Cursor, select an LLM, poll CI, discover GitHub work, create a
second scheduler, or write memory.
The module defines:
1. the supported Cursor subagent roles;
2. the delegation and concurrency contract;
3. the required result-document schema;
4. the bridge from accepted result documents into the existing generated-data
   packet format.
## Supported roles
| Role | Cursor type | Mutation | Result document |
|---|---|---:|---|
| `recon` | `explore` | no | `ReconReport` |
| `pr_remediation` | `generalPurpose` | bounded | `PRRemediationReport` |
| `test` | `generalPurpose` | bounded | `TestReport` |
| `documentation` | `generalPurpose` | bounded | `DocumentationReport` |
| `verifier_reviewer` | `generalPurpose` | no | `VerificationReviewReport` |
## Authority boundaries
### Active main Cursor agent
The main agent:
- retains architecture, synthesis, integration, and user-facing decisions;
- identifies independently delegable work;
- launches native Cursor subagents;
- continues critical-path work while background subagents execute;
- accepts, rejects, or requests correction of returned result documents.
### Root autonomy
Root `autonomy/` remains authoritative for:
- campaign and action readiness;
- leases;
- base revision binding;
- capability acknowledgement;
- resource and writable-path claims;
- conflict prevention;
- typed artifact acceptance;
- executor and reviewer separation.
This module does not inspect or mutate autonomy runtime storage directly.
### Campaign execution
When a formal campaign is active, `environment/program-execution/` may supply
ready campaign tasks and their authority boundaries.
The Cursor subagent layer does not advance campaign state or evaluate gates.
### Generated-data pipeline
Only accepted result documents are projected into the existing
`environment/agents/generated-data/` packet format.
The generated-data subsystem remains authoritative for validation, harvesting,
classification, routing, promotion, delivery, retrieval, and invalidation.
Raw subagent chat must not be written directly to memory.
### Admission token
Mint one token per native Task with
`python -m autonomy.adapters.cursor.mint_admission` (calls only
`CursorHostBridge.create_admission`). Embed `L9_ADMISSION_TOKEN=…`.
A Task without a READY Autonomy action stays denied. Do not add a second
token store.
## Execution lifecycle
```text
ready campaign action or bounded main-agent task
    ↓
autonomy lease and resource claims
    ↓
mint admission (`autonomy/adapters/cursor/mint_admission.py` → `create_admission`)
    ↓
existing Cursor task renderer embeds `L9_ADMISSION_TOKEN=…`
    ↓
main Cursor agent launches native subagent
    ↓
subagent returns one structured result document
    ↓
main agent accepts or rejects the document
    ↓
result_bridge validates and projects the document
    ↓
existing generated-data processor
    ↓
governed promotion and eventual memory delivery

Concurrency law

The main agent should launch the largest currently safe concurrent wave.

A task may run concurrently when:

* its dependencies are satisfied;
* its autonomy lease is active;
* its resource claims do not conflict;
* its writable paths do not overlap another active mutator;
* it does not require unresolved main-agent synthesis;
* it does not violate executor/reviewer separation.

Read-only work may run concurrently.

Mutating work may run concurrently only when autonomy has granted non-conflicting
claims.

The main agent must not wait idly for background subagents when independent
critical-path work remains available.

Result documents

Every subagent must return exactly one document conforming to:

schemas/cursor-subagent-result.schema.json

Natural-language claims such as “done” or “tests pass” are not completion
artifacts.

Every result document binds:

* campaign;
* graph;
* action;
* agent;
* lease;
* exact base SHA;
* role and objective;
* files inspected and changed;
* commands and validations;
* reusable findings;
* unresolved items;
* provenance.

A verifier_reviewer must name the subject agent and must not review its own
work.

Recon and verifier/reviewer documents must not claim changed files.

Python bridge

from result_bridge import (
    to_generated_data_packet,
    validate_result_document,
    with_artifact_digest,
)
document = with_artifact_digest(document)
validate_result_document(document)
packet = to_generated_data_packet(
    document,
    repository="Quantum-L9/Cursor-Governance",
)

to_generated_data_packet() does not process, promote, or deliver the packet.
It only projects the accepted document into the existing canonical packet
format.

Validation

python3 -m unittest discover \
  -s environment/agents/cursor-subagents/tests \
  -p 'test_*.py' \
  -v
python3 environment/agents/tools/validate_agents.py

Non-goals

This module does not provide:

* CI signal ingestion;
* GitHub polling;
* PR discovery;
* Cursor SDK integration;
* external agent launch services;
* model routing;
* multi-platform dispatch;
* another scheduler;
* another lease system;
* another generated-data processor;
* direct Graphiti or memory writes;
* autonomous merge or remote mutation.
