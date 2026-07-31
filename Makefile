.PHONY: help start sync wiring-check symlinks-check symlinks-install claude-plugins claude-env ide-profile ide-profile-test backup-gate-test path-lint precommit backup push graphiti-health lint venv rules-validate rules-stabilize integrity-check integrity-snapshot

# Workspace a target acts on. Defaults to the directory make was invoked from, so
# `make -C ~/.cursor-governance start` from inside a consumer repo targets that repo.
WS ?= $(CURDIR)

help:
	@echo "Targets: start sync wiring-check symlinks-check symlinks-install claude-plugins claude-env ide-profile ide-profile-test backup-gate-test path-lint precommit backup push graphiti-health lint venv rules-validate rules-stabilize integrity-check integrity-snapshot"

## Run the FULL session-start pipeline against WS, synchronously, with visible output.
## Same script Cursor runs on sessionStart — one implementation, no drift.
## Usage from a consumer repo: make -C "$$HOME/.cursor-governance" start WS="$$(pwd)"
start:
	@cd "$(WS)" && CURSOR_PROJECT_DIR="$(WS)" L9_BOOTSTRAP_SYNC=1 \
		bash "$(CURDIR)/ops/hooks/session_start_bootstrap.sh" \
		| python3 "$(CURDIR)/ops/scripts/render_bootstrap_context.py"

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

## Reconcile Claude Code plugins to the desired state declared in setup_claude_code_plugins.sh.
## Usage: make claude-plugins WS=/path/to/repo (defaults to cwd if WS omitted)
claude-plugins:
	bash ops/scripts/setup_claude_code_plugins.sh $(if $(WS),--workspace "$(WS)",)

## Validate the Claude Code environment adapter (CLI/Web/Mobile): files, JSON, no committed secrets
claude-env:
	python3 environment/claude-code/validate_claude_env.py

## Reconcile the Cursor IDE profile (extensions + .vscode settings). Usage: make ide-profile WS=/path/to/repo
ide-profile:
	bash ops/scripts/install_ide_profile.sh "$(WS)"

## Fixture selftest for the IDE profile installer (writes only under $$TMPDIR)
ide-profile-test:
	bash ops/scripts/test_install_ide_profile.sh

## Fixture selftest for the sessionEnd backup gate (writes only under $$TMPDIR)
backup-gate-test:
	bash ops/scripts/test_backup_gate.sh

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

## Ruff check + format check + mypy, via the locked venv (run `make venv` first, or let this pull it in).
## Matches the CI workflow's lint job (.github/workflows/l9-lint-test.yml) step for step.
lint: venv
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy . --show-error-codes --pretty --ignore-missing-imports

## Read-only drift check: does the committed rules/RULES-MANIFEST.* still match the
## live rules/*.mdc corpus? Writes nothing. Exit 1 (with a findings list) on drift.
rules-validate:
	python3 ops/scripts/validate_rules_manifest.py --root "$(CURDIR)"

## Full rules-subsystem validation harness: overlay/fingerprint/selective-sync test
## suites, manifest generate+validate, and corpus audit; report at
## reports/rules-stabilization-validation.md. NOTE: the generate/audit gates rewrite
## committed artifacts in place — run intentionally and review the diff. Not a
## pre-commit/CI gate. For a pure read-only check use `make rules-validate`.
rules-stabilize:
	bash ops/scripts/run_rules_stabilization_validation.sh

## Read-only integrity check: report drift/missing/extra governed files against the
## committed integrity/manifest-lock.json baseline. Never repairs, never writes to
## tracked files (report goes to the gitignored ops/logs/). If the baseline was never
## seeded it prints "manifest not seeded" and exits 0. Safe to run anytime.
integrity-check:
	python3 integrity/hash-verifier.py --no-repair

## Seed/refresh the integrity baseline: snapshot every governed file's sha256 + full
## base64 content into integrity/manifest-lock.json. Deliberate, high-footprint action
## (embeds file contents) — run intentionally and review the (large) diff. Not wired
## into any hook/CI. The self-heal auto-repair mode is intentionally NOT exposed as a
## target because it overwrites working-tree files from the baseline.
integrity-snapshot:
	python3 integrity/hash-verifier.py --snapshot
