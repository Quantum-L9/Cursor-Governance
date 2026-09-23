L9_TARGETS += \
	claude-plugins \
	claude-projection \
	claude-projection-check \
	claude-skill-registry \
	claude-skills \
	claude-skills-check \
	claude-skills-test \
	claude-settings \
	claude-settings-check \
	claude-install \
	claude-install-check \
	claude-env \
	claude-diagnose \
	claude-readiness \
	claude-deepseek \
	claude-deepseek-verify \
	agents-env \
	ide-profile \
	ide-profile-test \
	ui-operator-sync \
	l9-dispatcher-install \
	l9-dispatcher-check \
	cursor-install \
	cursor-install-check \
	manus-adapter-check \
	manus-install \
	manus-install-check \
	cursor-projection-check \
	skill-plane-test \
	claude-preservation-check \
	claude-preservation-baseline \
	claude-desktop-install \
	claude-desktop-check \
	manus-mcp-serve \
	manus-mcp-test
# ---------------------------------------------------------------------------
# Claude Code
# ---------------------------------------------------------------------------
claude-plugins:
	bash ops/scripts/setup_claude_code_plugins.sh \
		$(if $(WS),--workspace "$(WS)",)
claude-skill-registry:
	$(PYTHON) ops/scripts/build_claude_skill_registry.py \
		--root "$(CURDIR)"
claude-projection: claude-skill-registry
	$(PYTHON) ops/scripts/claude_projection.py \
		--root "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" \
		--summary
claude-projection-check:
	$(PYTHON) ops/scripts/claude_projection.py \
		--root "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" \
		--check \
		--summary
claude-skills: claude-skill-registry
	$(PYTHON) ops/scripts/claude_projection.py \
		--root "$(CURDIR)" \
		--workspace "$(WS)" \
		--domains skills \
		--summary \
		--no-receipt
claude-skills-check:
	$(PYTHON) \
		environment/agents/adapters/claude-code/validate_skill_activation.py
claude-skills-test:
	$(PYTHON) \
		environment/agents/adapters/claude-code/tests/test_skill_router.py
	$(PYTHON) \
		environment/agents/adapters/claude-code/tests/test_skill_reconciliation.py
	$(PYTHON) \
		environment/agents/adapters/claude-code/tests/test_cursor_skill_router.py
claude-install:
	bash environment/agents/adapters/claude-code/install.sh \
		--governance "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))"
claude-install-check:
	bash environment/agents/adapters/claude-code/install.sh \
		--check \
		--governance "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))"
claude-settings:
	$(PYTHON) ops/scripts/reconcile_claude_settings.py \
		--root "$(CURDIR)" \
		$(if $(WS),--workspace "$(WS)",)
claude-settings-check:
	$(PYTHON) ops/scripts/reconcile_claude_settings.py \
		--root "$(CURDIR)" \
		--check \
		$(if $(WS),--workspace "$(WS)",)
claude-env:
	@structural=0; runtime=0; \
	$(MAKE) claude-install-check || structural=$$?; \
	$(PYTHON) environment/agents/adapters/claude-code/validate_claude_env.py \
		|| structural=$$?; \
	$(PYTHON) ops/secrets/validate_capability_hosts.py \
		|| structural=$$?; \
	$(PYTHON) environment/agents/adapters/claude-code/verify_account_env.py \
		|| true; \
	$(PYTHON) environment/agents/adapters/claude-code/validate_claude_env.py \
		--runtime || runtime=$$?; \
	if [ $$structural -ne 0 ]; then \
		exit $$structural; \
	fi; \
	exit $$runtime
claude-diagnose:
	@echo "capability broker experiment retired (never shipped); not probed"
	$(PYTHON) ops/scripts/probe_network_posture.py
claude-readiness:
	$(PYTHON) ops/scripts/emit_claude_readiness.py \
		--root "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" \
		--read
claude-deepseek:
	./scripts/claude-deepseek.sh
claude-deepseek-verify:
	./scripts/verify-routing.sh
# ---------------------------------------------------------------------------
# Shared agent / IDE surfaces
# ---------------------------------------------------------------------------
agents-env:
	$(PYTHON) environment/agents/tools/validate_agents.py
ide-profile:
	bash ops/scripts/install_ide_profile.sh "$(WS)"
ide-profile-test:
	bash ops/scripts/test_install_ide_profile.sh
ui-operator-sync:
	uv sync --extra ui-operator
# ---------------------------------------------------------------------------
# Thin l9 dispatcher
# ---------------------------------------------------------------------------
l9-dispatcher-install:
	bash "$(CURDIR)/ops/scripts/install_l9_dispatcher.sh"
l9-dispatcher-check:
	bash "$(CURDIR)/ops/scripts/install_l9_dispatcher.sh" --check
# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------
cursor-install:
	bash "$(CURDIR)/environment/agents/adapters/cursor/install.sh" \
		--governance "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))"
cursor-install-check:
	bash "$(CURDIR)/environment/agents/adapters/cursor/install.sh" \
		--governance "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" \
		--check
	L9_GOV_ROOT="$(CURDIR)" \
		$(PYTHON) ops/scripts/claude_bootstrap_receipt.py \
			--surface cursor \
			--path "$$HOME/.l9/cursor/bootstrap-check.json" \
			--json
# ---------------------------------------------------------------------------
# Manus
# ---------------------------------------------------------------------------
manus-adapter-check:
	$(PYTHON) \
		environment/agents/adapters/manus/validate_manus_adapter.py \
		--repo-root "$(CURDIR)"
manus-install:
	bash "$(CURDIR)/environment/agents/adapters/manus/install.sh" \
		--governance "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))"
manus-install-check:
	bash "$(CURDIR)/environment/agents/adapters/manus/install.sh" \
		--governance "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" \
		--check
# ---------------------------------------------------------------------------
# Virtual skill plane
# ---------------------------------------------------------------------------
cursor-projection-check:
	$(PYTHON) \
		environment/agents/adapters/cursor/validate_skill_projection.py \
		--root "$(CURDIR)"
skill-plane-test:
	$(PYTHON) -m pytest \
		ops/skill_routing/tests \
		environment/agents/adapters/cursor/tests \
		-q
# ---------------------------------------------------------------------------
# Claude preservation
# ---------------------------------------------------------------------------
claude-preservation-check:
	$(PYTHON) ops/scripts/claude_projection_snapshot.py \
		--root "$(CURDIR)" \
		--check
	$(PYTHON) -m pytest -q \
		environment/agents/adapters/claude-code/tests/test_claude_preservation_contract.py
claude-preservation-baseline:
	$(PYTHON) ops/scripts/claude_projection_snapshot.py \
		--root "$(CURDIR)" \
		--write-baseline
# ---------------------------------------------------------------------------
# Claude Desktop
# ---------------------------------------------------------------------------
claude-desktop-install:
	$(PYTHON) \
		environment/agents/adapters/claude-desktop/render_claude_desktop_config.py \
		$(if $(MEMORY_VERIFY_MCP),--verify,)
claude-desktop-check:
	$(PYTHON) \
		environment/agents/adapters/claude-desktop/render_claude_desktop_config.py \
		--check

# ---------------------------------------------------------------------------
# Manus governance MCP
# ---------------------------------------------------------------------------
# Streamable-HTTP server and focused contract tests. The server is read-only
# by default; bootstrap apply and memory lifecycle require a managed bearer token.
manus-mcp-serve:
	bash "$(CURDIR)/environment/agents/adapters/manus/serve_mcp.sh" \
		--governance "$(CURDIR)"
manus-mcp-test:
	$(PYTHON) -m unittest \
		environment.agents.adapters.manus.tests.test_mcp_server \
		environment.agents.adapters.manus.tests.test_memory_lifecycle \
		environment.agents.adapters.manus.tests.test_memory_authority
