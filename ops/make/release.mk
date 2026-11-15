L9_TARGETS += \
	release
# ---------------------------------------------------------------------------
# Release — thin front door to Core's release engine (docs/L9_RELEASE.md).
#
# The engine (tools.l9_release, schema l9.release/v1) and the release runner
# live in Quantum-L9/l9-ci-core, pinned in ops/config/release-core.json.
#
#   l9 release                 # engine `plan` (read-only)
#   l9 release DRY_RUN=1       # engine `plan` + `build`, locally; publishes nothing
#   l9 release DISPATCH=1      # dispatch the factory release schedule (calls Core's runner)
#   make -C "$$HOME/.cursor-governance" release WS="$$(pwd)" [DRY_RUN=1] [DISPATCH=1]
#
# Cursor-Governance never tags or publishes: publication is Core's runner.
# ---------------------------------------------------------------------------
DRY_RUN ?= 0
DISPATCH ?= 0
release:
	$(PYTHON) ops/scripts/l9_release.py \
		--workspace "$(WS)" \
		$(if $(filter 1,$(DRY_RUN)),--dry-run,) \
		$(if $(filter 1,$(DISPATCH)),--dispatch,)
