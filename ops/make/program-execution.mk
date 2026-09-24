PE_ROOT := environment/program-execution
AGENTS_TOOLS := environment/agents/tools
L9_TARGETS += \
	campaign \
	campaign-architecture \
	campaign-architecture-check \
	campaign-check-input \
	campaign-stack-base \
	program-execution-core-validate \
	program-execution-adapters \
	program-execution-conformance \
	program-execution-probe \
	pe-smoke \
	agents-runtime-bindings-validate \
	peer-execution-validate \
	peer-execution-probe \
	peer-execution-conformance \
	agents-deployment-validate \
	agents-results-validate \
	agents-data-validate \
	agents-runtime-probe \
	program-execution-campaign-promotion \
	program-execution-campaign-schema \
	program-execution-campaign-compile \
	program-execution-campaign-brief \
	program-execution-controller-tests
# ---------------------------------------------------------------------------
# Campaign entrypoints
# ---------------------------------------------------------------------------
campaign:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to activate seed is required" >&2; \
		exit 2 \
	)
	TARGET="$(TARGET)" \
		$(PYTHON) environment/program-execution/scripts/run_campaign.py \
			--intent "$(INTENT)" \
			--until "$(or $(CAMPAIGN_UNTIL),execute)" \
			$(if $(TARGET),--target "$(TARGET)") \
			$(if $(TARGET_CHECKOUT),--target-checkout "$(TARGET_CHECKOUT)") \
			$(CAMPAIGN_ARGS)
campaign-architecture:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to the architecture document is required" >&2; \
		exit 2 \
	)
	TARGET="$(TARGET)" \
		$(PYTHON) environment/program-execution/scripts/run_campaign.py \
			--intent "$(INTENT)" \
			--until "$(or $(CAMPAIGN_UNTIL),execute)" \
			$(if $(TARGET),--target "$(TARGET)") \
			$(if $(TARGET_CHECKOUT),--target-checkout "$(TARGET_CHECKOUT)") \
			$(CAMPAIGN_ARGS)
campaign-architecture-check:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to the architecture document is required" >&2; \
		exit 2 \
	)
	$(PYTHON) \
		environment/program-execution/scripts/compile_architecture_intent.py \
			--intent "$(INTENT)" \
			--repo-root "$(CURDIR)" \
			$(if $(TARGET),--target "$(TARGET)") \
			$(if $(TARGET_CHECKOUT),--target-checkout "$(TARGET_CHECKOUT)") \
			$(ARCHITECTURE_ARGS)
campaign-check-input:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to classify is required" >&2; \
		exit 2 \
	)
	$(PYTHON) \
		environment/program-execution/scripts/run_campaign.py \
		--check-input "$(INTENT)"
campaign-stack-base:
	@test -n "$(CAMPAIGN_ID)" || ( \
		echo "CAMPAIGN_ID= is required" >&2; \
		exit 2 \
	)
	$(PYTHON) ops/scripts/stack_pr.py \
		base \
		--stack \
		"$(or $(L9_ROOT),$(HOME)/.l9)/programs/$(CAMPAIGN_ID)/runtime/STACK.json"
# ---------------------------------------------------------------------------
# Program Execution validation
# ---------------------------------------------------------------------------
program-execution-core-validate:
	PYTHONDONTWRITEBYTECODE=1 \
		$(PYTHON) -B \
			$(PE_ROOT)/core/scripts/validate_pair.py \
			$(PE_ROOT)/core \
			--mode template
	$(MAKE) program-execution-campaign-schema
	$(MAKE) program-execution-campaign-compile
	$(MAKE) program-execution-campaign-promotion
program-execution-adapters:
	PYTHONDONTWRITEBYTECODE=1 \
		$(PYTHON) -B \
			$(PE_ROOT)/scripts/validate_execution_adapters.py
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B \
			$(PE_ROOT)/scripts/validate_thin_providers.py
# Integrity deliberately runs after behavioral controller validation.
program-execution-conformance: autonomy-contracts-validate
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B \
			$(PE_ROOT)/scripts/run_conformance.py
	$(MAKE) program-execution-controller-tests
	PYTHONDONTWRITEBYTECODE=1 \
		$(PYTHON) -B \
			$(PE_ROOT)/scripts/validate_manifest.py
program-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B \
			$(PE_ROOT)/scripts/probe_execution_adapters.py
pe-smoke:
	PYTHONDONTWRITEBYTECODE=1 \
		$(PYTHON) -B -m pytest -q \
			$(PE_ROOT)/scripts/tests/test_pe_smoke_campaign.py \
			$(PE_ROOT)/scripts/tests/test_launchability.py \
			$(PE_ROOT)/core/program-execution-controller-template/scripts/tests/test_verify_lifecycle.py \
			$(PE_ROOT)/core/program-execution-controller-template/scripts/tests/test_execution_recovery.py
# ---------------------------------------------------------------------------
# Executable peers / agents
# ---------------------------------------------------------------------------
agents-runtime-bindings-validate:
	$(PYTHON) -B \
		$(AGENTS_TOOLS)/validate_executable_peers.py \
		--schema-only
peer-execution-validate:
	$(PYTHON) -B \
		$(AGENTS_TOOLS)/validate_executable_peers.py
peer-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B \
			$(PE_ROOT)/scripts/probe_executable_peers.py
peer-execution-conformance:
	$(MAKE) agents-env
	$(MAKE) agents-runtime-bindings-validate
	$(MAKE) program-execution-adapters
	$(MAKE) program-execution-conformance
	$(MAKE) peer-execution-validate
	$(MAKE) peer-execution-probe
	$(MAKE) program-execution-core-validate
agents-deployment-validate:
	$(PYTHON) -m pytest \
		environment/agents/deployment/tests \
		-q
agents-results-validate:
	$(PYTHON) -m pytest \
		environment/agents/results/tests \
		environment/agents/lifecycle/tests \
		-q
agents-data-validate:
	$(PYTHON) -m pytest \
		environment/agents/generated-data/ingress/tests \
		-q
agents-runtime-probe:
	$(PYTHON) environment/agents/readiness/probe_runtime.py
# ---------------------------------------------------------------------------
# Campaign compiler / promotion
# ---------------------------------------------------------------------------
program-execution-campaign-promotion:
	PYTHONDONTWRITEBYTECODE=1 \
		$(PYTHON) -B \
			$(PE_ROOT)/scripts/validate_campaign_promotion.py
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B -m unittest \
			$(PE_ROOT)/scripts/tests/test_validate_campaign_promotion.py
program-execution-campaign-schema:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B -m unittest \
			$(PE_ROOT)/conformance/test_campaign_source_schema.py
program-execution-campaign-compile:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B -m unittest \
			$(PE_ROOT)/scripts/tests/test_compile_campaign_source.py
program-execution-campaign-brief:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		$(PYTHON) -B -m unittest \
			$(PE_ROOT)/scripts/tests/test_run_campaign.py \
			$(PE_ROOT)/scripts/tests/test_replay_campaign.py \
			$(CURDIR)/skills/l9-pe-campaign-activate/scripts/test_compile_brief.py
program-execution-controller-tests:
	cd $(PE_ROOT)/core/program-execution-controller-template && \
	find scripts/tests -maxdepth 1 -name 'test_*.py' -print0 \
		| sort -z \
		| PYTHONDONTWRITEBYTECODE=1 \
			xargs -0 \
				-P "$${PES_CONTROLLER_JOBS:-$$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}" \
				-I{} \
				$(PYTHON) -B {}
