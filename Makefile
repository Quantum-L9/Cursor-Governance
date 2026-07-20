.PHONY: help sync wiring-check symlinks-check symlinks-install path-lint precommit backup push graphiti-health lint venv

help:
	@echo "Targets: sync wiring-check symlinks-check symlinks-install path-lint precommit backup push graphiti-health lint venv"

## Recreate the pinned .venv from uv.lock (interpreter + deps, incl. dev extras). Same as sessionStart hook.
venv:
	uv sync --locked --extra dev

## Fast-forward-only pull of this clone from origin/main (same as sessionStart hook)
sync:
	bash ops/scripts/governance_sync.sh

## Verify a consumer workspace's symlink wiring. Usage: make wiring-check WS=/path/to/repo
wiring-check:
	bash ops/scripts/check_governance_wiring.sh "$(WS)"

## Verify this clone's own symlink health
symlinks-check:
	bash ops/scripts/validate_governance_symlinks.sh

## Install .cursor-commands + ~/.cursor symlinks. Run from inside the CONSUMER repo, not here.
symlinks-install:
	bash ops/scripts/setup_workspace_symlinks.sh

## Fail if any script/rule/hook hardcodes a /Users or /home path instead of $$HOME
path-lint:
	bash ops/scripts/validate_governance_no_hardcoded_paths.sh

## Run the pre-commit pipeline (.pre-commit-config.yaml) across all files
precommit:
	@command -v pre-commit >/dev/null 2>&1 || { echo "pre-commit not installed. Run: pip install pre-commit && pre-commit install"; exit 1; }
	pre-commit run --all-files

## Commit + rebase + push this clone to origin/main (same as sessionEnd hook)
backup:
	bash ops/scripts/backup_to_github.sh

## Gate push behind the pre-commit pipeline: fails (no push) if precommit fails
push: precommit backup

## Check Graphiti tunnel + MCP tool-plane health (degraded MCP is expected pre-full-wiring)
graphiti-health: venv
	uv run python3 ops/graphiti/graphiti_memory_client.py health

## Ruff lint, via the locked venv (run `make venv` first, or let this pull it in)
lint: venv
	uv run ruff check .
