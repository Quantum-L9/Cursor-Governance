L9_TARGETS += \
	campaign \
	campaign-check-input
# ---------------------------------------------------------------------------
# Program Execution, registered stage (CANONICAL_LAW
# PROGRAM_EXECUTION_REGISTERED_STAGE_V1). The only two Program Execution
# targets in the root graph; the rest of ops/make/program-execution.mk stays
# uncomposed. A rendered plan runs while that operator's session has
# /coding-agent on in WS; the runner refuses otherwise. It finishes with the
# governance SSOT make pr (PROGRAM_EXECUTION_MAKE_PR_FINISH_V1).
#
#   make campaign <plan.md>
#
# The plan path is the operator invocation. Make reads it from MAKECMDGOALS
# and gives that extra goal an empty recipe so an existing file is not a
# second target. INTENT= remains for a campaign input that is not a rendered
# .plan.md. CAMPAIGN_UNTIL=execute stops at verified local commits; nothing
# runs past pr.
# ---------------------------------------------------------------------------
CAMPAIGN_PLAN_PATH :=
ifneq ($(filter campaign,$(MAKECMDGOALS)),)
CAMPAIGN_PLAN_PATH := $(filter-out campaign,$(MAKECMDGOALS))
endif
ifeq ($(words $(CAMPAIGN_PLAN_PATH)),0)
CAMPAIGN_INTENT := $(if $(INTENT),$(abspath $(if $(filter /%,$(INTENT)),$(INTENT),$(WS)/$(INTENT))),)
else ifeq ($(words $(CAMPAIGN_PLAN_PATH)),1)
CAMPAIGN_INTENT := $(abspath $(CAMPAIGN_PLAN_PATH))
else
$(error make campaign accepts one plan path)
endif
ifeq ($(words $(CAMPAIGN_PLAN_PATH)),1)
.PHONY: $(CAMPAIGN_PLAN_PATH)
$(CAMPAIGN_PLAN_PATH):
	@:
endif
campaign:
	@if [ -z "$(CAMPAIGN_INTENT)" ]; then \
		echo "usage: make campaign <plan.md>" >&2; \
		exit 2; \
	fi; \
	if [ -n "$(CAMPAIGN_PLAN_PATH)" ] && [ -z "$$L9_PE_OPERATOR_INVOCATION" ]; then \
		L9_PE_OPERATOR_INVOCATION="make campaign $(CAMPAIGN_PLAN_PATH)"; \
		export L9_PE_OPERATOR_INVOCATION; \
	fi; \
	L9_PE_MODE_WORKSPACE="$(WS)" \
	TARGET="$(TARGET)" \
		$(PYTHON) environment/program-execution/scripts/run_campaign.py \
			--intent "$(CAMPAIGN_INTENT)" \
			--until "$(or $(CAMPAIGN_UNTIL),pr)" \
			$(if $(TARGET),--target "$(TARGET)") \
			$(if $(TARGET_CHECKOUT),--target-checkout "$(TARGET_CHECKOUT)") \
			$(CAMPAIGN_ARGS)
campaign-check-input:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to classify is required" >&2; \
		exit 2 \
	)
	$(PYTHON) environment/program-execution/scripts/run_campaign.py \
		--check-input "$(CAMPAIGN_INTENT)"
