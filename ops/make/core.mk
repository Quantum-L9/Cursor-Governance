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
venv:
	uv sync --locked --extra dev
	PYTHONPATH="$(CURDIR)" $(PYTHON) \
		-m ops.memory.seal_artifact_provenance \
		--root "$(CURDIR)"
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
