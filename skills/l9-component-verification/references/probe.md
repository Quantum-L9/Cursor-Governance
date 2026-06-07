<!-- L9_META
l9_schema: 1
origin: skill-hardening GMP-SKILL-HARDEN-001
tags: [probe, import, runtime]
status: active
/L9_META -->

# Probe (/probe)

Safe runtime import verification — zero mutation.

## Usage

```
/probe memory.substrate_repository
/probe core.tools.tool_embeddings
```

## Execution

Import target module in runtime environment; report success, registry activity, dependency failures, circular imports.

## When to use

After refactors, dependency changes, before enabling traffic, when "should work" is insufficient.
