---
name: mac.automation Pipeline Run
overview: Create the mac.automation module block YAML and run the deterministic pipeline to generate 12 files in a single output folder for review.
todos:
  - id: create-block
    content: Create mac_automation.yaml module block
    status: pending
  - id: run-pipeline
    content: Run pipeline on mac_automation.yaml
    status: pending
    dependencies:
      - create-block
  - id: verify-output
    content: Verify 12 files generated in module.mac_automation/
    status: pending
    dependencies:
      - run-pipeline
---

# mac.automation Pipeline Execution

## Context

- `mac.automation` is a Tier 1 integration module for general Mac automation (AppleScript, keyboard/mouse, app control)
- Invoked via both internal HTTP endpoint and external webhook
- No module block YAML exists - must be created first

## Steps

### 1. Create Module Block YAML

Create [`examples/module_blocks/mac_automation.yaml`](examples/module_blocks/mac_automation.yaml) based on `email_adapter.yaml` template with:

- module_id: `mac.automation`
- tier: 1
- description: Mac automation gateway for AppleScript, keyboard/mouse, and app control
- surface: exposes_http_endpoint + exposes_webhook
- inbound: POST `/mac/automation/execute` with bearer auth
- outbound: internal calls to `aios.runtime:/chat` and `memory.service:/memory/ingest`
- idempotency: `event_id` pattern with substrate search
- threading: UUIDv5 from `[command_type, target_app, request_id]`
- acceptance_min: valid_command_executed, invalid_auth_rejected, idempotent_replay_cached, aios_response_forwarded, packet_written_on_success, error_handled

### 2. Run Pipeline

Execute:

```bash
./run_pipeline.sh examples/module_blocks/mac_automation.yaml module.mac_automation
```

### 3. Output

All 12 files will be generated in `module.mac_automation/`:

- Module-Spec-v2.6-mac_automation.yaml (authoritative spec)
- README.md, **init**.py, config.py, schemas.py
- adapters/mac_automation_adapter.py
- routes/mac_automation.py
- clients/mac_automation_client.py
- services/mac_automation_service.py
- tests/conftest.py, test_mac_automation.py, test_mac_automation_integration.py