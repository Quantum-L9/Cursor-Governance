You are operating in BUILD → VALIDATION → DEFINITION OF DONE mode on:

```text
https://github.com/Quantum-L9/l9-graphiti-memory
```

## Objective

Activate and prove the following immediate topology:

```text
Multiple coding agents
        │
        │ MCP / CLI
        ▼
Shared L9 memory service
        │
        ├── MemoryService
        ├── RecordStore
        ├── Retrieval planner
        ├── Projection outbox
        └── Projection adapters
                ├── Graphiti
                └── Zep
```

TransportPacket integration, Gate integration, constellation orchestration, cross-region operation, and multi-node consensus are explicitly deferred.

The goal is to prove that multiple local coding agents can use one shared canonical L9 memory and that Graphiti and Zep lifecycle behavior works against real credentialed providers.

## Safety and authority

You may:

* inspect the repository;
* create an isolated virtual environment;
* install dependencies;
* create temporary test data;
* create an external non-secret configuration file;
* create an external credential environment file with restrictive permissions if credentials are supplied through a secure local mechanism;
* run local servers and workers;
* run live Graphiti and Zep lifecycle tests;
* create backup copies;
* execute migration and rollback rehearsals in isolated temporary directories;
* update repository tests, scripts, or operational documentation when a verified gap prevents repeatable validation;
* generate validation evidence.

You may not:

* commit;
* push;
* publish;
* tag;
* merge;
* deploy to production;
* change GitHub repository settings;
* write secrets into the repository;
* write secrets into `~/.cursor/mcp.json`;
* echo secret values to logs;
* modify unrelated user configuration;
* claim any check passed unless it was executed successfully.

## Credential contract

Expect these variables to be available in the execution environment:

```bash
GRAPHITI_MCP_URL
GRAPHITI_MCP_TOKEN
ZEP_API_KEY
```

Optionally:

```bash
ZEP_API_URL
```

Before doing anything else:

1. Confirm each required variable exists without printing its value.
2. Record only:

   * variable name;
   * present or absent;
   * optionally the value length;
   * never the secret.
3. Stop the affected provider branch if its credentials are absent.
4. Continue all other safely executable branches.
5. Ensure shell tracing is disabled:

```bash
set +x
```

6. Ensure generated logs redact:

   * authorization headers;
   * bearer tokens;
   * API keys;
   * query-string credentials;
   * environment dumps.

## Phase A — Bind and inspect

1. Clone or open the repository.
2. Record:

```bash
git rev-parse HEAD
git branch --show-current
git status --porcelain=v1
python --version
```

3. Read at minimum:

```text
AGENTS.md
README.md
QUICKSTART.md
RUNBOOK.md
MIGRATION.md
VALIDATION.md
SECURITY.md
docs/CURSOR_INSTANTIATION.md
config/memory.yaml.example
pyproject.toml
scripts/validate_release.sh
```

4. Discover the real package version, migration mechanism, provider adapters, worker entrypoint, database schema versioning, lifecycle tests, and validation commands.
5. Do not assume filenames or commands beyond what the repository proves.
6. Preserve unrelated working-tree changes.

## Phase B — Create an isolated runtime

Create an isolated working area outside the repository:

```bash
export L9_TEST_ROOT="${TMPDIR:-/tmp}/l9-memory-activation-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$L9_TEST_ROOT"/{data,state,logs,backups,evidence}
chmod 700 "$L9_TEST_ROOT"
```

Create and activate a virtual environment:

```bash
python -m venv "$L9_TEST_ROOT/venv"
. "$L9_TEST_ROOT/venv/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e '.[server,zep]'
```

If editable installation is unsuitable for the repository, build and install the wheel using the repository-supported mechanism instead.

Create a non-secret configuration file outside the repository:

```yaml
data_dir: <L9_TEST_ROOT>/data
state_dir: <L9_TEST_ROOT>/state
workspace_namespace: l9-graphiti-memory
memory_enabled: true
write_gates_enabled: false
gate_ttl_minutes: 30
projection_backend: none
projection_required: false
http_auth_required: true
local_principal_id: local-operator
local_tenant_id: local
local_organization_id: local
local_workspace_id: l9
local_agent_id: cursor-activation-agent
local_read_namespaces:
  - l9-graphiti-memory
local_write_namespaces:
  - l9-graphiti-memory
local_promote_namespaces: []
local_is_admin: true
outbox_batch_size: 50
outbox_max_attempts: 8
outbox_base_delay_seconds: 5
default_search_limit: 20
default_token_budget: 1200
log_level: INFO
json_logs: true
```

Export:

```bash
export L9_MEMORY_CONFIG="$L9_TEST_ROOT/memory.yaml"
export L9_MEMORY_LOCAL_READ_NAMESPACES=l9-graphiti-memory
export L9_MEMORY_LOCAL_WRITE_NAMESPACES=l9-graphiti-memory
export L9_MEMORY_LOCAL_PROMOTE_NAMESPACES=
export L9_MEMORY_LOCAL_IS_ADMIN=true
```

Do not enable write gates yet.

## Phase C — Prove the canonical shared-memory path

Run the repository’s supported resolution and health commands:

```bash
l9-memory resolve
l9-memory health
```

Write unique test records from at least three distinct logical agent identities. Use the real supported mechanism for setting agent identity. If identity is config-bound, create three separate external config files sharing the same `data_dir` and namespace but using different `local_agent_id` values.

Use unique content such as:

```text
agent-alpha shared-memory probe <RUN_ID>
agent-beta shared-memory probe <RUN_ID>
agent-gamma shared-memory probe <RUN_ID>
```

For each logical agent:

1. Write one observation or decision.
2. Record the returned receipt.
3. Capture the stable record ID.
4. Search for records written by the other agents.
5. Hydrate a context that should include all three records.
6. Verify all agents observe the same canonical state.
7. Verify namespace isolation by querying a disallowed namespace and confirming fail-closed behavior.
8. Verify duplicate/idempotent write behavior using the repository’s supported idempotency mechanism.
9. Run a bounded concurrency test with multiple client processes writing and reading the same canonical store.
10. Confirm:

    * no database-lock corruption;
    * no lost writes;
    * no duplicate canonical records beyond documented idempotency semantics;
    * stable record IDs;
    * successful cross-agent visibility;
    * valid receipts.

Do not allow separate agents to bypass `MemoryService` or directly modify the SQLite database.

## Phase D — Install and prove Cursor MCP configuration

Use only the canonical CLI lifecycle:

```bash
l9-memory client cursor inspect
l9-memory client cursor install --dry-run
l9-memory client cursor install
l9-memory client cursor verify --timeout 60
l9-memory client cursor status
```

Requirements:

1. Preserve unrelated Cursor MCP servers.
2. Confirm the managed entry contains no `env` block.
3. Confirm file permissions are `0600` when supported.
4. Confirm a digest-bound backup was created.
5. Confirm `verify` completes:

   * initialize;
   * initialized notification;
   * tools/list;
   * `memory.health`.
6. Capture the JSON receipts.
7. Confirm the canonical MCP tool inventory is present.
8. Do not manually edit `~/.cursor/mcp.json`.

If Cursor uses a non-default config path, discover and pass it with `--path`.

Do not claim that the Cursor desktop application has loaded the server until the user completes the desktop-only confirmation described in the user checklist.

## Phase E — Credentialed Graphiti lifecycle

Create a provider-specific external config using:

```yaml
projection_backend: http
projection_required: false
graphiti_mcp_url: <from GRAPHITI_MCP_URL>
```

Keep the token in `GRAPHITI_MCP_TOKEN`; never persist it in YAML.

Run the real Graphiti lifecycle using a unique namespace and run ID.

Required lifecycle:

```text
canonical write
→ outbox event
→ Graphiti projection
→ provider search/read verification
→ canonical supersession or update
→ updated projection verification
→ canonical deletion request
→ provider deletion processing
→ provider absence verification
→ replay/idempotency verification
```

Execute:

1. Provider connectivity/tool-discovery check.
2. Canonical write that creates a projection event.
3. `l9-memory-worker --once` or the repository-supported worker command.
4. Verify the provider locator is durably stored.
5. Search Graphiti using the supported adapter/tool dialect.
6. Confirm:

   * content;
   * namespace/group;
   * record identity correlation;
   * metadata;
   * provider locator.
7. Supersede or update the canonical record using the supported contract.
8. Run the worker again.
9. Verify the newest state is searchable and stale state is handled according to repository semantics.
10. Delete the canonical record using the governed delete command and a test verification reference.
11. Run the outbox worker.
12. Verify provider deletion.
13. Replay or rerun the same outbox operation.
14. Confirm idempotent behavior.
15. Exercise provider failure classification where safely possible:

    * invalid token using an intentionally fake token in a subprocess;
    * timeout using a deliberately unreachable local URL;
    * unavailable endpoint;
    * retryable response if a safe test endpoint exists.
16. Confirm provider failure does not corrupt the canonical record.
17. Confirm a failed provider deletion never creates a false completed deletion receipt.

Do not intentionally attack or load-test the external provider.

## Phase F — Credentialed Zep lifecycle

Create a provider-specific external config using:

```yaml
projection_backend: zep
projection_required: false
zep_api_url: <ZEP_API_URL when supplied>
```

Keep `ZEP_API_KEY` only in the runtime environment.

Execute the same lifecycle:

```text
canonical write
→ outbox event
→ Zep projection
→ provider search/read verification
→ canonical supersession or update
→ updated projection verification
→ canonical deletion request
→ provider deletion processing
→ provider absence verification
→ replay/idempotency verification
```

Verify:

* real operation changes health from unverified to successful/healthy according to the implementation;
* namespace/group isolation;
* metadata preservation;
* locator persistence;
* search visibility;
* supersession behavior;
* deletion behavior;
* retry behavior;
* idempotent replay;
* canonical persistence remains correct during provider failures.

Exercise an invalid-key branch in a subprocess without exposing either the valid or invalid key in logs.

## Phase G — Production-like migration rehearsal

Use isolated copies only.

1. Determine the actual current schema and migration mechanism.
2. Build or obtain the oldest supported database state using authoritative repository fixtures or a pinned compatible release.
3. Populate representative data:

   * canonical records;
   * multiple namespaces;
   * temporal records;
   * quarantined records if supported;
   * idempotency records;
   * outbox events in multiple states;
   * projection links;
   * deletion-pending records;
   * recovery items;
   * phase-lock or guard state where applicable.
4. Record:

   * row counts per table;
   * schema version;
   * content digests over stable normalized exports;
   * foreign-key validation;
   * database integrity result.
5. Make an immutable backup.
6. Run the supported upgrade.
7. Verify:

   * SQLite integrity;
   * foreign keys;
   * expected schema version;
   * row-count reconciliation;
   * stable IDs;
   * canonical searches;
   * temporal queries;
   * pending outbox preservation;
   * projection locator preservation;
   * deletion state preservation.
8. Simulate interruption only through a safe supported mechanism:

   * terminate between documented migration units;
   * never corrupt a real user database.
9. Restart and verify resume or deterministic failure behavior.
10. Preserve all logs and database copies under `$L9_TEST_ROOT/evidence`.

## Phase H — Rollback rehearsal

Rollback is a data and runtime recovery exercise, not merely `git revert`.

1. Stop all test writers and workers.
2. Preserve the upgraded database for diagnosis.
3. Restore the immutable pre-upgrade backup into a separate path.
4. Start the pinned earlier compatible runtime against the restored database only.
5. Verify read-only health and representative searches.
6. Never point old and new runtimes at the same writable database.
7. Restart the current runtime against a fresh copy of the upgraded database.
8. Confirm:

   * startup;
   * health;
   * canonical read/write;
   * outbox replay;
   * no loss of stable identifiers;
   * no corruption.
9. Document whether rollback is:

   * directly supported;
   * restore-only;
   * incompatible after a specific schema boundary.

Do not invent downgrade support if the repository only supports backup restoration.

## Phase I — Backup and restore proof

1. Stop writers.
2. Back up:

   * SQLite database;
   * non-secret config;
   * external registry if used;
   * external principal mapping if used.
3. Restore into a separate isolated test root.
4. Start with:

```bash
export L9_MEMORY_PROJECTION_BACKEND=none
```

5. Run:

   * health;
   * stats;
   * representative historical searches;
   * hydration;
   * stable-ID checks.
6. Re-enable one provider.
7. Replay pending outbox events.
8. Confirm restored canonical state remains authoritative.

## Phase J — Secret loading and rotation proof

Perform rotation separately for Graphiti and Zep.

For each provider:

1. Confirm credential A works.
2. Introduce credential B through the environment or configured secret manager.
3. Restart only the affected server/worker process.
4. Confirm credential B works.
5. Revoke credential A using the provider administration interface only if API support and authorization are available.
6. Confirm credential A fails.
7. Confirm credential B continues to work.
8. Scan:

   * repository;
   * Cursor MCP JSON;
   * generated config;
   * validation logs;
   * shell-history artifacts within the test environment;
   * process command lines where applicable.
9. Confirm no plaintext credential was persisted.

If provider-side key creation or revocation cannot be performed through an authenticated API available to this environment, classify that substep as UserRequired. Do not fabricate it.

## Phase K — Full repository validation

Run the repository-defined checks, including at minimum:

```bash
pytest -q
python tools/assurance/validate_harvest_coverage.py
python tools/assurance/validate_adrs.py
bash scripts/preflight.sh
bash scripts/validate_release.sh
```

Also run any newly discovered mandatory formatting, lint, type, package, migration, provider, or integration checks.

Validation must target the exact final working tree.

Do not weaken tests or gates to obtain a pass.

## Phase L — Evidence package

Create an evidence directory outside the repository containing:

```text
activation-evidence/
├── target.yaml
├── environment.yaml
├── canonical-shared-memory/
├── cursor/
├── graphiti/
├── zep/
├── migration/
├── rollback/
├── backup-restore/
├── secret-rotation/
├── repository-validation/
├── findings.yaml
├── validation-summary.yaml
└── SHA256SUMS
```

Redact all secrets.

`target.yaml` must include:

* repository URL;
* exact commit SHA;
* dirty/clean state;
* Python version;
* package version;
* operating system;
* execution timestamp;
* explicitly deferred TransportPacket/Gate scope.

`validation-summary.yaml` must classify each item as:

```text
Passed
Failed
Skipped
NotApplicable
Unknown
UserRequired
```

Required gates:

```yaml
shared_canonical_memory: Passed
multi_agent_cross_visibility: Passed
concurrent_access: Passed
namespace_isolation: Passed
cursor_cli_installation: Passed
cursor_mcp_probe: Passed
graphiti_live_lifecycle: Passed
zep_live_lifecycle: Passed
migration_rehearsal: Passed
rollback_or_restore_rehearsal: Passed
backup_restore: Passed
secret_loading_no_plaintext: Passed
repository_validation: Passed
```

These may remain `UserRequired`:

```yaml
cursor_desktop_visual_confirmation: UserRequired
github_hosted_controls: UserRequired
provider_key_issue_or_revoke_when_no_api_is_available: UserRequired
final_production_approval: UserRequired
```

## Completion rules

Do not declare completion when a required automated gate is Failed or Unknown.

A valid final state for this execution is:

```yaml
execution_status: Succeeded
deployment_readiness: AwaitingUserOnlyControls
```

only when every Cursor-executable gate passes and the remaining items truly require user or hosted-administrator action.

Return:

1. exact commit tested;
2. exact commands executed;
3. artifacts changed;
4. canonical-memory test result;
5. Cursor configuration/probe result;
6. Graphiti lifecycle result;
7. Zep lifecycle result;
8. migration result;
9. rollback/restore result;
10. secret-rotation result;
11. full repository-validation result;
12. residual findings;
13. evidence directory path;
14. exactly one next action for the user.
