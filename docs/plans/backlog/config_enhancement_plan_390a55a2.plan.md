---
name: Config Enhancement Plan
overview: Enhance 4 config files (mcp_servers.yaml, research-agent-v1.yaml, kernel_discovery.yaml, high_risk_tools.yaml) with error_recovery sections, implementation paths, and schema references following the cursor_workflow_kernel.yaml pattern.
todos:
  - id: mcp-servers
    content: Add health_check, error_recovery, retry_policy to mcp_servers.yaml
    status: pending
  - id: research-agent
    content: Add error_recovery, implementations paths to research-agent-v1.yaml
    status: pending
  - id: kernel-discovery
    content: Add error_recovery section with failure behaviors to kernel_discovery.yaml
    status: pending
  - id: high-risk-tools
    content: Add implementation paths and audit config to high_risk_tools.yaml
    status: pending
---

# Config Enhancement Plan (Items 2-5)

Apply the cursor_workflow_kernel.yaml enhancement pattern to 4 config files.

## Pattern Reference

From [cursor_workflow_kernel.yaml](agents/cursor/cursor_workflow_kernel.yaml):
- T1: MCP Tool Mapping (concrete tool references)
- T2: Error Recovery (graceful degradation)
- T3: Implementation Paths (YAML to Python)
- T4: Required Context Loading (with fallbacks)
- T5: Schema Validation (CI checkable)

---

## File 2: mcp_servers.yaml (HIGH priority)

**File:** [config/mcp_servers.yaml](config/mcp_servers.yaml)

**Current State:** 48 lines, minimal server definitions with no resilience

**Missing:**
- Health check configuration
- Retry/timeout logic
- Fallback servers
- Error recovery behavior

**Changes:**

Add after line 17 (before `servers:`):

```yaml
# Health & Resilience
health_check:
  enabled: true
  interval_seconds: 30
  timeout_ms: 5000
  unhealthy_threshold: 3
  healthy_threshold: 2

error_recovery:
  server_unavailable:
    behavior: skip_and_warn
    retry_count: 2
    retry_delay_ms: 1000

  connection_timeout:
    timeout_ms: 10000
    behavior: failover_to_next

  spawn_failure:
    behavior: log_and_disable
    re_enable_after_seconds: 300

retry_policy:
  max_attempts: 3
  backoff_ms: [500, 1000, 2000]
  circuit_breaker_threshold: 5

schema: config/schemas/mcp_servers.schema.yaml

implementation:
  loader: runtime.mcp_server_registry.load_mcp_servers_from_yaml
  health_checker: runtime.mcp_server_registry.check_server_health
```

Add to each server entry:

```yaml
health_endpoint: null  # or /health if supported
startup_timeout_ms: 30000
```

---

## File 3: research-agent-v1.yaml (MEDIUM priority)

**File:** [config/agents/research-agent-v1.yaml](config/agents/research-agent-v1.yaml)

**Current State:** 137 lines, well-structured with Python bindings

**Missing:**
- Error recovery for Perplexity API failures
- Explicit implementation paths per capability
- Schema reference

**Changes:**

Add after line 90 (after `environment:` section):

```yaml
# Error Recovery (Perplexity API resilience)
error_recovery:
  api_timeout:
    timeout_ms: 120000  # 2 minutes for deep research
    retry_count: 2
    retry_delay_ms: 5000
    on_exhaust: return_partial_results

  rate_limit_exceeded:
    behavior: exponential_backoff
    max_wait_seconds: 300
    fallback: queue_for_later

  invalid_response:
    behavior: log_and_retry
    max_retries: 1
    validation: agents.research_agent.validate_response

  api_key_missing:
    behavior: fail_fast
    error_code: CONFIG_ERROR
    message: "PERPLEXITY_API_KEY required"

# Implementation Paths (YAML to Python binding)
implementations:
  synthesize:
    module: agents.research_agent
    method: ResearchAgent.synthesize
    async: true
  discover:
    module: agents.research_agent
    method: ResearchAgent.discover
    async: true
  generate_spec:
    module: agents.research_agent
    method: ResearchAgent.generate_spec
    async: true
  research_to_code:
    module: agents.research_agent
    method: ResearchAgent.research_to_code
    async: true

schema: config/schemas/research_agent.schema.yaml
```

---

## File 4: kernel_discovery.yaml (MEDIUM priority)

**File:** [config/kernel_discovery.yaml](config/kernel_discovery.yaml)

**Current State:** 221 lines, comprehensive validation flags but no explicit error behavior

**Missing:**
- Error recovery section (what happens on failure)
- Recovery actions (not just validation flags)
- Schema reference

**Changes:**

Add after line 63 (after `validation:` section):

```yaml
# Error Recovery (failure behavior, not just validation)
error_recovery:
  kernel_file_missing:
    behavior: fail_loudly_if_required
    required_check: required_kernels
    optional_behavior: skip_and_warn
    log_level: error

  kernel_parse_error:
    behavior: fail_loudly
    include_file_path: true
    include_line_number: true
    emit_metric: l9.kernel.parse_error

  integrity_check_failed:
    behavior: fail_if_production
    env_override:
      dev: warn_only
      test: skip
      staging: fail_loudly
      production: fail_loudly

  minimum_count_violated:
    behavior: fail_loudly
    emit_metric: l9.kernel.minimum_count_violation
    escalate_to: igor

  loader_exception:
    behavior: use_fallback
    fallback_config: FALLBACK_CONFIG
    log_level: error
    emit_metric: l9.kernel.loader_exception

implementation:
  loader: runtime.kernel_config_loader.load_kernel_config
  validator: runtime.kernel_config_loader.validate_config
  fallback_provider: runtime.kernel_config_loader.FALLBACK_CONFIG

schema: config/schemas/kernel_discovery.schema.yaml
```

---

## File 5: high_risk_tools.yaml (LOW priority)

**File:** [config/policies/high_risk_tools.yaml](config/policies/high_risk_tools.yaml)

**Current State:** 146 lines, static policy with no enforcement links

**Missing:**
- Implementation paths linking policy to Python enforcement
- Runtime validation reference
- Audit hooks

**Changes:**

Add after line 138 (after `side_effect:` section):

```yaml
# Implementation Paths (Policy to Enforcement)
implementation:
  policy_loader: core.governance.tool_risk_policy._load_tool_risk_policy

  enforcement_modules:
    - module: orchestrators.action_tool.validator
      function: validate_tool_call
      gate_type: pre_execution

    - module: core.governance.approval_manager
      function: check_approval_required
      gate_type: approval_gate

    - module: core.compliance.audit_reporter
      function: log_high_risk_execution
      gate_type: post_execution

  check_functions:
    is_high_risk: core.governance.tool_risk_policy.is_high_risk
    requires_igor: core.governance.tool_risk_policy.requires_igor_approval
    is_safe: core.governance.tool_risk_policy.is_safe

# Runtime Validation
runtime:
  cache_policy: true
  cache_invalidation: on_file_change
  hot_reload: true

  validation_hook:
    on_load: validate_tool_ids_exist
    validator: ci.check_tool_wiring.validate_tools_exist

# Audit Configuration
audit:
  log_all_high_risk: true
  require_justification: true
  retention_days: 365
  audit_trail_module: core.compliance.audit_reporter

schema: config/schemas/high_risk_tools.schema.yaml
```

---

## Schema Files (Optional Enhancement)

Create minimal schema files for CI validation:

**config/schemas/mcp_servers.schema.yaml** - Validate server entries
**config/schemas/research_agent.schema.yaml** - Validate agent config
**config/schemas/kernel_discovery.schema.yaml** - Validate kernel config
**config/schemas/high_risk_tools.schema.yaml** - Validate policy structure

---

## Summary

| File | Priority | Lines Added | Key Enhancement |
|------|----------|-------------|-----------------|
| mcp_servers.yaml | HIGH | ~35 | Health check + retry + failover |
| research-agent-v1.yaml | MEDIUM | ~40 | API error recovery + impl paths |
| kernel_discovery.yaml | MEDIUM | ~35 | Failure behaviors + recovery |
| high_risk_tools.yaml | LOW | ~40 | Enforcement paths + audit |

Total: ~150 lines of YAML additions across 4 files
