L9_TARGETS += \
	graphiti-health \
	memory-binding \
	memory-readiness \
	memory-egress-check \
	memory-mcp-install \
	memory-mcp-check \
	memory-reconcile-legacy
# ---------------------------------------------------------------------------
# Memory control plane
# ---------------------------------------------------------------------------
# Compatibility alias. The retired provider client is absent from current
# main; readiness is the canonical R0..R9 memory health signal.
graphiti-health: memory-readiness
memory-binding:
	PYTHONPATH="$(CURDIR)" \
		$(PYTHON) -m ops.memory.diagnostics \
		--binding-only
memory-readiness:
	PYTHONPATH="$(CURDIR)" \
		$(PYTHON) -m ops.memory.diagnostics \
			--workspace "$(if $(WS),$(WS),$(CURDIR))" \
			$(if $(MEMORY_SKIP_VERIFY_MCP),--no-verify-mcp,)
memory-egress-check:
	$(PYTHON) ops/scripts/validate_memory_egress_boundary.py \
		$(if $(MEMORY_EGRESS_ENFORCE),--enforce,)
memory-mcp-install:
	PYTHONPATH="$(CURDIR)" \
		$(PYTHON) -m ops.memory.mcp_instantiation \
			$(if $(MCP_PATH),--path "$(MCP_PATH)",) \
			$(if $(MEMORY_VERIFY_MCP),--verify,)
memory-mcp-check:
	PYTHONPATH="$(CURDIR)" \
		$(PYTHON) -m ops.memory.mcp_instantiation \
			--check \
			--no-receipt \
			$(if $(MCP_PATH),--path "$(MCP_PATH)",)
memory-reconcile-legacy:
	PYTHONPATH="$(CURDIR)" \
		$(PYTHON) -m ops.memory.legacy_reconciliation \
			--export "$(EXPORT)" \
			--workspace "$(if $(WS),$(WS),$(CURDIR))" \
			$(if $(MEMORY_RECONCILE_APPLY),--apply,)
