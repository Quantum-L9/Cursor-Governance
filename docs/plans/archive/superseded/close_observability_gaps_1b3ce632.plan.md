---
name: Close Observability Gaps
overview: Add OpenTelemetry integration to the chassis and engine layers, create the missing engine/spec.yaml template, and fix the broken set_memory_records import in chassis/app.py.
todos:
  - id: otel-deps
    content: Add OpenTelemetry dependencies to pyproject.toml
    status: pending
  - id: telemetry-module
    content: Create chassis/telemetry.py with OTel configuration
    status: pending
  - id: chassis-app-integrate
    content: Integrate telemetry into chassis/chassis_app.py lifespan
    status: pending
  - id: fix-broken-import
    content: Fix set_memory_records broken import in chassis/app.py
    status: pending
  - id: add-memory-records
    content: Add set_memory_records function to app/observability.py
    status: pending
  - id: bridge-tracing
    content: Update engine/observability/tracing.py to bridge to OTel
    status: pending
  - id: spec-template
    content: Create engine/spec.yaml.template
    status: pending
  - id: spec-yaml
    content: Create engine/spec.yaml for Gate node
    status: pending
  - id: validate
    content: Run validation checklist (imports, tests, startup)
    status: pending
isProject: false
---

  
---  
name: Close Observability Gaps  
overview: "Fix broken set_memory_records import, add OpenTelemetry integration, and create engine/spec.yaml. Split into 3 PRs per agent rules: fix, feat, chore."  
todos:  
  - id: check-pr12-conflicts  
    content: Run git diff to check for conflicts with feat/transport-packet-migration-clean on engine/__init__.py and engine/[handlers.py](http://handlers.py)  
    status: pending  
  - id: pr-a-fix-memory-records  
    content: "PR A: Add set_memory_records Gauge and function to app/[observability.py](http://observability.py)"  
    status: pending  
  - id: pr-b-otel-deps  
    content: "PR B: Add OTel dependencies to pyproject.toml"  
    status: pending  
  - id: pr-b-telemetry-file  
    content: "PR B: Create chassis/[telemetry.py](http://telemetry.py) with corrected configure_telemetry (honor enabled param, wire MeterProvider exporter, env-var for insecure)"  
    status: pending  
  - id: pr-b-engine-observability  
    content: "PR B: Create engine/observability/__init__.py and engine/observability/[tracing.py](http://tracing.py)"  
    status: pending  
  - id: pr-b-wire-chassis  
    content: "PR B: Wire telemetry into chassis/chassis_[app.py](http://app.py)"  
    status: pending  
  - id: pr-c-spec-yaml  
    content: "PR C: Create engine/spec.yaml and engine/spec.yaml.template with P0-reserved comment"  
    status: pending  
isProject: false  
---  
  
# Close Observability Gaps Plan  
  
## Pre-Execution Checks  
  
### PR #12 Conflict Check (REQUIRED)  
  
Before branching, verify no conflict with `feat/transport-packet-migration-clean`:  
  
```bash  
git fetch origin  
git diff origin/feat/transport-packet-migration-clean...HEAD -- engine/__init__.py engine/[handlers.py](http://handlers.py)  
```  
  
If conflicts exist, coordinate merge order.  
  
---  
  
## PR A: fix/broken-set-memory-records  
  
**Branch**: `fix/broken-set-memory-records`  
**Commit**: `fix: add set_memory_records gauge to app/observability`  
  
### Problem  
  
[chassis/[app.py](http://app.py)](chassis/[app.py](http://app.py)) line 9 imports `set_memory_records` from `app.observability`, but the function does not exist. Line 42 calls it:  
  
```python  
set_memory_records(count=int(payload["memory_records"]))  
```  
  
### Solution  
  
Add to [app/[observability.py](http://observability.py)](app/[observability.py](http://observability.py)):  
  
```python  
MEMORY_RECORDS_GAUGE = Gauge("l9_memory_records", "Memory records count", ["service"], registry=REGISTRY)  
  
def set_memory_records(count: int) -> None:  
    MEMORY_RECORDS_GAUGE.labels(service=get_config().service_name).set(count)  
```  
  
### Files  
  
- `app/observability.py` â€” add Gauge and function  
  
---  
  
## PR B: feat/opentelemetry-integration  
  
**Branch**: `feat/opentelemetry-integration`  
**Commit**: `feat: add OTel tracing and metrics to chassis and engine`  
  
### Dependencies (pyproject.toml)  
  
```toml  
"opentelemetry-api>=1.27,<2.0",  
"opentelemetry-sdk>=1.27,<2.0",  
"opentelemetry-exporter-otlp>=1.27,<2.0",  
"opentelemetry-instrumentation-fastapi>=0.48b0,<1.0",  
"opentelemetry-instrumentation-httpx>=0.48b0,<1.0",  
```  
  
### New File: chassis/[telemetry.py](http://telemetry.py)  
  
**Issues to fix from review:**  
  
1. **Dead parameter bug**: `configure_telemetry(enabled: bool)` is immediately overwritten by `os.getenv()`. Fix: honor the parameter OR remove it.  
2. **MeterProvider has no exporter**: `OTLPMetricExporter` is imported but not wired. Fix: add `PeriodicExportingMetricReader` or document as stub.  
3. **Hardcoded `insecure=True`**: Should be env-var driven `OTEL_INSECURE`).  
  
### Corrected [telemetry.py](http://telemetry.py) structure:  
  
```python  
def configure_telemetry(*, enabled: bool | None = None) -> None:  
    # Honor parameter, fallback to env var  
    resolved_enabled = enabled if enabled is not None else os.getenv("OTEL_ENABLED", "false").lower() == "true"  
    if not resolved_enabled:  
        return  
      
    # Tracer setup with env-var for insecure  
    insecure = os.getenv("OTEL_INSECURE", "true").lower() == "true"  
    span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)  
      
    # Meter setup WITH exporter (not stub)  
    metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=insecure)  
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60000)  
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])  
```  
  
### New Directory: engine/observability/  
  
- Create `engine/observability/__init__.py`  
- Create `engine/observability/tracing.py` (engine-side trace bridge)  
  
### Files  
  
- `pyproject.toml` â€” add OTel deps  
- `chassis/telemetry.py` â€” new file (corrected)  
- `chassis/chassis_app.py` â€” wire telemetry  
- `engine/observability/__init__.py` â€” new file  
- `engine/observability/tracing.py` â€” new file  
  
---  
  
## PR C: chore/engine-spec-yaml  
  
**Branch**: `chore/engine-spec-yaml`  
**Commit**: `chore: add engine/spec.yaml and spec.yaml.template`  
  
### Issue from review  
  
Template shows `priority_class: P1` as default, but Gate uses `P0`. Add comment that P0 is Gate-infrastructure-reserved.  
  
### Files  
  
**engine/spec.yaml** (Gate-specific):  
  
```yaml  
node_name: gate  
node_type: router  
priority_class: P0  # P0 reserved for Gate infrastructure  
health_endpoint: /v1/health  
internal_url: [http://gate:8000](http://gate:8000)  
actions:  
  - match  
  - sync  
  - admin  
```  
  
**engine/spec.yaml.template**:  
  
```yaml  
# L9 Constellation Node Specification Template  
# P0 is RESERVED for Gate infrastructure - use P1/P2/P3 for other nodes  
node_name: ${NODE_NAME}  
node_type: ${NODE_TYPE}  # router | worker | aggregator  
priority_class: P1  # P0=Gate-reserved, P1=high, P2=normal, P3=low  
health_endpoint: /v1/health  
internal_url: [http://${NODE_NAME}:8000](http://${NODE_NAME}:8000)  
actions: []  
```  
  
### Files  
  
- `engine/spec.yaml` â€” new file  
- `engine/spec.yaml.template` â€” new file  
  
---  
  
## Execution Order  
  
1. **Check PR #12 conflicts** before any branching  
2. **PR A (fix)** â€” smallest, unblocks chassis/[app.py](http://app.py)  
3. **PR B (feat)** â€” largest, depends on PR A being merged  
4. **PR C (chore)** â€” independent, can parallel with PR B  
  
---  
  
## Validation Checklist  
  
- `mypy --strict` passes (no dead parameters)  
- `ruff check` passes (no unused imports)  
- `pytest tests/` passes  
- `engine/observability/__init__.py` exists before [tracing.py](http://tracing.py)  
- MeterProvider has PeriodicExportingMetricReader attached  
- `OTEL_INSECURE` env var controls TLS mode  
- spec.yaml.template has P0-reserved comment  
