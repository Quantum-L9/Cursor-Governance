L9_TARGETS += \
	campaign \
	campaign-check-input
# ---------------------------------------------------------------------------
# Program Execution, registered stage (CANONICAL_LAW
# PROGRAM_EXECUTION_REGISTERED_STAGE_V1). The only two Program Execution
# targets in the root graph; the rest of ops/make/program-execution.mk stays
# uncomposed. A campaign still runs only on the operator's own words
# (L9_PE_OPERATOR_INVOCATION) and only while that operator's session has
# /coding-agent on in WS; the runner refuses otherwise. It finishes with the
# governance SSOT make pr (PROGRAM_EXECUTION_MAKE_PR_FINISH_V1).
#
#   L9_PE_OPERATOR_INVOCATION="<your words>" \
#     make -C "$HOME/.cursor-governance" campaign INTENT=<path> WS="$PWD"
#
# INTENT is resolved against WS when relative. CAMPAIGN_UNTIL=execute stops at
# verified local commits; nothing runs past pr.
# ---------------------------------------------------------------------------
CAMPAIGN_INTENT = $(abspath $(if $(filter /%,$(INTENT)),$(INTENT),$(WS)/$(INTENT)))
campaign:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to a campaign input (make campaign-check-input) is required" >&2; \
		exit 2 \
	)
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
