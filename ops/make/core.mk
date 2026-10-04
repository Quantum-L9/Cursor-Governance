L9_TARGETS += \
	gov-python \
	venv \
	start \
	sync-generated \
	sync-generated-pe
# ---------------------------------------------------------------------------
# Runtime / bootstrap
# ---------------------------------------------------------------------------
gov-python:
	@bash "$(CURDIR)/ops/scripts/ensure_gov_python.sh" "$(CURDIR)"
# One local sync owner. A raw `uv sync` here was a second door with different
# rules: no --no-build, no environment lock, no in-progress marker, no
# host-architecture guard and no import verification. `venv` is also the one
# goal exempt from the gov-python auto-prereq, so that weaker door was the one
# a broken environment reached for. The script seals the memory artifact itself.
venv:
	bash "$(CURDIR)/ops/scripts/ensure_uv_environment.sh" "$(CURDIR)"
start:
	@cd "$(WS)" && \
		CURSOR_PROJECT_DIR="$(WS)" \
		L9_BOOTSTRAP_SYNC=1 \
		bash "$(CURDIR)/ops/hooks/session_start_bootstrap.sh" \
		| $(PYTHON) "$(CURDIR)/ops/scripts/render_bootstrap_context.py"
sync-generated:
	$(PYTHON) ops/scripts/sync_generated_artifacts.py \
		--root "$(CURDIR)" \
		--force \
		--check

# Also reconcile the Program Execution manifest. This stays separate from
# sync-generated because it hashes the entire mutable PE tree.
sync-generated-pe:
	$(PYTHON) ops/scripts/sync_generated_artifacts.py \
		--root "$(CURDIR)" \
		--force \
		--check \
		--pe-manifest
