.PHONY: help start sync wiring-check symlinks-check symlinks-install claude-plugins claude-env claude-skill-registry claude-skills claude-skills-check claude-skills-test autonomy-validate agents-env ide-profile ide-profile-test backup-gate-test path-lint precommit precommit-repo backup push graphiti-health lint lint-ruff lint-mypy test uv-lock-check pr pr-check pr-security pr-full venv rules-validate rules-stabilize integrity-check integrity-snapshot

# Workspace a target acts on. Defaults to the directory make was invoked from, so
# `make -C ~/.cursor-governance start` from inside a consumer repo targets that repo.
WS ?= $(CURDIR)

# When 1, `make pr` fails on mypy errors. Default 0 matches CI (mypy is
# continue-on-error while the tracked debt in TODO.md remains).
PR_MYPY_STRICT ?= 0

# When 1, security scanners report findings but do not fail `make pr`.
PR_SECURITY_ADVISORY ?= 0

# Comparison ref for changed-file resolution (merge-base with HEAD ∪ working tree).
# Full-tree scans are nightly CI / `make precommit` / `make pr-full` — not make pr.
PR_BASE ?= origin/main

help:
	@echo "Targets: start sync wiring-check symlinks-check symlinks-install claude-plugins claude-env claude-skill-registry claude-skills claude-skills-check claude-skills-test autonomy-validate agents-env ide-profile ide-profile-test backup-gate-test path-lint precommit precommit-repo backup push graphiti-health lint lint-ruff lint-mypy test uv-lock-check pr pr-check pr-security pr-full venv rules-validate rules-stabilize integrity-check integrity-snapshot"
	@echo "  make pr           — CHANGED-FILES local PR gate (pre-commit + ruff + security); not full-tree"
	@echo "  make pr-security  — gitleaks/bandit/semgrep/pip-audit on changed files only (WS-aware)"
	@echo "  make pr-full      — intentional full-tree local gate (nightly-equivalent; slow)"
	@echo "  Consumer repos: make -C \"\$$HOME/.cursor-governance\" pr WS=\"\$$(pwd)\""
	@echo "  Prefer l9-ci-core thin Makefile (identical across repos) when adopting the common workflow."

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

## Build the deterministic Claude runtime registry from the canonical skill manifest.
claude-skill-registry:
	uv run python3 ops/scripts/build_claude_skill_registry.py --root "$(CURDIR)"

## Reconcile L9 skills into Claude native user + project discovery paths.
claude-skills: claude-skill-registry
	python3 ops/scripts/reconcile_claude_l9_skills.py --root "$(CURDIR)" \
		--scope user --scope project --workspace "$(WS)"

## Read-only registry/frontmatter/hook/routing drift validation.
claude-skills-check:
	python3 environment/claude-code/validate_skill_activation.py

## Behavioral router + reconciliation fixture tests.
claude-skills-test:
	python3 environment/claude-code/tests/test_skill_router.py
	python3 environment/claude-code/tests/test_skill_reconciliation.py

## Validate the Claude Code environment adapter and proactive skill activation.
claude-env:
	python3 environment/claude-code/validate_claude_env.py

## Validate the Claude Code bounded-concurrency autonomy runtime (contracts + unit tests).
autonomy-validate:
	python3 environment/claude-code/autonomy/validate_autonomy.py

## Validate the multi-agent environment pack: registry naming law, identity uniqueness,
## role catalog, adapter consistency, no committed secrets
agents-env:
	python3 environment/agents/tools/validate_agents.py

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

## Full-tree pre-commit (nightly / intentional). Not used by `make pr`.
precommit:
	@command -v pre-commit >/dev/null 2>&1 || { echo "pre-commit not installed. Run: pip install pre-commit && pre-commit install"; exit 1; }
	pre-commit run --all-files

## Changed-files pre-commit for PR velocity (skips machine-local symlinks-check).
precommit-repo:
	PR_BASE="$(PR_BASE)" bash ops/scripts/run_pr_precommit.sh "$(WS)"

## Commit + rebase + push this clone to origin/main (same as sessionEnd hook)
backup:
	bash ops/scripts/backup_to_github.sh

## Gate push behind the full pre-commit pipeline: fails (no push) if precommit fails
push: precommit backup

## Check Graphiti tunnel + MCP tool-plane health (degraded MCP is expected pre-full-wiring)
graphiti-health: venv
	uv run python3 ops/graphiti/graphiti_memory_client.py health

## Hard ruff gates on CHANGED files only (make pr). Full-tree: lint-ruff-full / make pr-full.
## Resolver errors fail closed (do not treat as "no Python files").
lint-ruff: venv
	@tmp=$$(mktemp); py=$$(mktemp); \
	trap 'rm -f "$$tmp" "$$py"' EXIT; \
	if ! PR_BASE="$(PR_BASE)" WS="$(WS)" bash ops/scripts/resolve_changed_files.sh >"$$tmp"; then \
		echo "FAIL: resolve_changed_files.sh"; exit 1; \
	fi; \
	grep -E '\.(py|pyi)$$' "$$tmp" >"$$py" || true; \
	if [ ! -s "$$py" ]; then echo "OK: no changed Python files for ruff"; exit 0; fi; \
	echo "ruff (changed): $$(grep -c . "$$py") file(s)"; \
	xargs uv run --no-build ruff check <"$$py"; \
	xargs uv run --no-build ruff format --check <"$$py"

lint-ruff-full: venv
	uv run --no-build ruff check .
	uv run --no-build ruff format --check .

## mypy via the locked venv. Advisory in CI today (TODO.md mypy debt); still
## useful as a local signal. `make lint` keeps it blocking for intentional debt work.
lint-mypy: venv
	uv run mypy . --show-error-codes --pretty --ignore-missing-imports

## Full-tree ruff + mypy (not the PR gate).
lint: lint-ruff-full lint-mypy

## Fail if uv.lock is out of sync with pyproject.toml (same as CI lockfile drift guard).
## Skipped by make pr unless a dependency manifest is in the change set.
uv-lock-check:
	@if [ -f uv.lock ]; then uv lock --check; else echo "OK: no uv.lock present, skipping"; fi

## Pytest suite. make pr runs this only when Python files changed.
## Splits root autonomy/ from environment/claude-code/autonomy/ (same package name).
test: venv
	bash ops/scripts/run_pytest_suites.sh --tb=short -q

## Local PR security scanners on CHANGED files only.
## Pins: l9-ci-core security.yml (gitleaks 8.24.3, bandit==1.8.6, pip-audit==2.9.0).
## Semgrep: SDK supported range >=1.100.0,<2.0.0. Full-tree = nightly CI.
pr-security:
	PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" PR_BASE="$(PR_BASE)" \
		bash ops/scripts/run_pr_security.sh "$(WS)"

## Local PR gate — CHANGED FILES ONLY (invariant). Does not scan the whole tree.
## Nightly GHA owns full-corpus scans. Alias: pr-check.
pr pr-check:
	PR_BASE="$(PR_BASE)" PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_MYPY_STRICT="$(PR_MYPY_STRICT)" WS="$(WS)" \
		bash ops/scripts/run_pr_gate.sh

## Intentional full-tree local gate (nightly-adjacent). Slow; not the default.
pr-full: venv precommit lint-ruff-full uv-lock-check test rules-validate
	@echo "NOTE: corpus security remains nightly CI; pr-full runs local full lint/test/precommit"
	@echo "RESULT: PASS — full local gate (lint/test/precommit)"

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
