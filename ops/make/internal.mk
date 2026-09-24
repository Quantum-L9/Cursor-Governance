L9_TARGETS += \
	campaign-materialize \
	campaign-drive \
	campaign-reset
# ---------------------------------------------------------------------------
# Internal / temporary replay helpers
#
# Not the live Program Execution path.
#
# RETIRED WRITERS: `campaign-materialize` and `campaign-reset` no longer copy
# paths, retire runtime state, or rewind branches. replay_campaign.py refuses
# both with ReplayError because they bypassed Controller lease, task-state and
# recovery authority; `campaign-drive` refuses the same way when REF= is given.
# Execution recovery is Controller-owned: `pec recover` / `pec recover-execution`
# in environment/program-execution/core/program-execution-controller-template.
# The targets stay registered so the refusal is reachable and explicit.
# ---------------------------------------------------------------------------
campaign-materialize:
	@test -n "$(CAMPAIGN_ID)" || ( \
		echo "CAMPAIGN_ID= is required" >&2; \
		exit 2 \
	)
	@test -n "$(TASK)" || ( \
		echo "TASK= is required" >&2; \
		exit 2 \
	)
	@test -n "$(REF)" || ( \
		echo "REF= is required" >&2; \
		exit 2 \
	)
	$(PYTHON) \
		environment/program-execution/scripts/replay_campaign.py \
		materialize \
		--workspace "$(or $(L9_ROOT),$(HOME)/.l9)/programs/$(CAMPAIGN_ID)" \
		--task "$(TASK)" \
		--target "$(or $(TARGET),$(or $(L9_ROOT),$(HOME)/.l9)/program-worktrees/$(CAMPAIGN_ID))" \
		--ref "$(REF)" \
		$(if $(HOLD_BACK),--hold-back "$(HOLD_BACK)")
campaign-drive:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to activate seed is required" >&2; \
		exit 2 \
	)
	@test -n "$(CAMPAIGN_ID)" || ( \
		echo "CAMPAIGN_ID= is required" >&2; \
		exit 2 \
	)
	$(PYTHON) \
		environment/program-execution/scripts/replay_campaign.py \
		drive \
		--intent "$(INTENT)" \
		--isolate "$(CURDIR)" \
		--workspace "$(or $(L9_ROOT),$(HOME)/.l9)/programs/$(CAMPAIGN_ID)" \
		--target "$(or $(TARGET),$(or $(L9_ROOT),$(HOME)/.l9)/program-worktrees/$(CAMPAIGN_ID))" \
		$(if $(REF),--ref "$(REF)") \
		$(if $(HOLD_BACK),--hold-back "$(HOLD_BACK)")
campaign-reset:
	@test -n "$(INTENT)" || ( \
		echo "INTENT= path to activate seed is required" >&2; \
		exit 2 \
	)
	@test -n "$(CAMPAIGN_ID)" || ( \
		echo "CAMPAIGN_ID= is required" >&2; \
		exit 2 \
	)
	@test -n "$(BASE)" || ( \
		echo "BASE= commit SHA is required" >&2; \
		exit 2 \
	)
	$(PYTHON) \
		environment/program-execution/scripts/replay_campaign.py \
		reset \
		--campaign-id "$(CAMPAIGN_ID)" \
		--isolate "$(CURDIR)" \
		--target "$(or $(TARGET),$(or $(L9_ROOT),$(HOME)/.l9)/program-worktrees/$(CAMPAIGN_ID))" \
		--base "$(BASE)" \
		--intent "$(INTENT)" \
		--l9-root "$(or $(L9_ROOT),$(HOME)/.l9)"
