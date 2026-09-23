REF ?= openclaw-igorbot/github#token
REQUIRE ?=
L9_TARGETS += \
	secrets-sync \
	secrets-check \
	capability-contract-validate \
	capability-check \
	capability-broker-preflight \
	broker-serve
# ---------------------------------------------------------------------------
# Secrets / capability security
# ---------------------------------------------------------------------------
secrets-sync:
	@$(MAKE) venv
	$(PYTHON) ops/secrets/sync_secrets_registry.py
secrets-check:
	@$(MAKE) venv
	$(PYTHON) ops/secrets/resolve_secret.py \
		--ref "$(REF)" \
		--check
capability-contract-validate:
	$(PYTHON) ops/secrets/validate_capability_contract.py
capability-check:
	@bash ops/secrets/bootstrap_agent_env.sh \
		--check \
		--surface "$${L9_GOVERNANCE_SURFACE:-unknown}" \
		$(if $(REQUIRE),--require-capabilities "$(REQUIRE)",)
capability-broker-preflight:
	@echo "capability broker experiment retired (never shipped)" >&2
	@exit 2
broker-serve:
	@echo "capability broker experiment retired (never shipped)" >&2
	@exit 2
