REF ?= openclaw-igorbot/github#token
REQUIRE ?=
L9_TARGETS += \
	secrets-sync \
	secrets-check \
	secrets-aws-sync \
	secrets-aws-check \
	capability-contract-validate \
	capability-check \
	capability-broker-preflight \
	broker-serve
# ---------------------------------------------------------------------------
# Secrets / capability security
# ---------------------------------------------------------------------------
# Infisical is the secret store (ADR-0053): secrets-check binds-and-checks the
# Infisical name (NAME=GITHUB_TOKEN) or a legacy ref (REF=openclaw-igorbot/...).
secrets-check:
	@$(MAKE) venv
	$(PYTHON) ops/secrets/capability_bind.py --check "$(or $(NAME),$(REF))"
# Legacy AWS tools — Cursor / operator login seed only, never an agent path.
secrets-aws-sync:
	@$(MAKE) venv
	$(PYTHON) ops/secrets/sync_secrets_registry.py
secrets-aws-check:
	@$(MAKE) venv
	$(PYTHON) ops/secrets/resolve_secret.py \
		--ref "$(REF)" \
		--check
secrets-sync:
	@echo "secrets-sync is deprecated: AWS is legacy (ADR-0053); running secrets-aws-sync"
	@$(MAKE) secrets-aws-sync
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
