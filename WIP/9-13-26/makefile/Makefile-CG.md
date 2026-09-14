# Cursor-Governance repository command surface
#
# Architecture:
#   Makefile = stable repository API + capability graph
#   scripts  = implementation and complex control flow
#   targets  = reusable repository capabilities
#
# Rules:
#   - prerequisites express truths/capabilities a target requires;
#   - recipes express ordered state transitions;
#   - public targets are stable operator/agent interfaces;
#   - internal targets may be composed by public capabilities;
#   - complex behavior stays in scripts, not inline Make/shell;
#   - make pr is the sole canonical PR shipping entrypoint.

.DEFAULT_GOAL := help

# No suffix-based implicit build graph exists in this repository.
# Disable legacy suffix-rule discovery for a smaller, deterministic command graph.
.SUFFIXES:

# ---------------------------------------------------------------------------
# Repository context
# ---------------------------------------------------------------------------

GOV_ROOT := $(CURDIR)

# Workspace operated on by a target.
#
# When Make is entered with:
#   make -C "$$HOME/.cursor-governance" ...
#
# CURDIR is the governance root. Consumer repositories MUST therefore pass:
#   WS="$$(pwd)"
WS ?= $(CURDIR)

# ---------------------------------------------------------------------------
# PR policy
# ---------------------------------------------------------------------------

# Comparison ref used by changed-file resolution.
PR_BASE ?= origin/main

# Until tracked mypy debt is retired, default behavior matches CI.
PR_MYPY_STRICT ?= 0

# 0 = security findings are blocking.
# 1 = security scanners are advisory.
PR_SECURITY_ADVISORY ?= 0

# 1 = publish/open/reuse the PR after the local gate passes.
# 0 = run the exact same canonical gate but stop before publication.
OPEN_PR ?= 1

# 1 = emit the post-PR remediation handoff.
PR_REMEDIATE ?= 1

# Authorization propagated into the post-PR convergence plane.
# Supporting remediation/open-PR logic owns enforcement of:
#   exact-head green checks
#   mergeability
#   blocking reviews
#   conflict state
#   no force-push / no required-check bypass
PR_AUTOMERGE ?= 1

# ---------------------------------------------------------------------------
# Other policy/configuration
# ---------------------------------------------------------------------------

REF ?= openclaw-igorbot/github#token

CLEAN_MODE ?= apply
CLEAN_REMOTE ?= 1

PE_ROOT := environment/program-execution
AGENTS_TOOLS := environment/agents/tools

# ---------------------------------------------------------------------------
# Command-surface metadata
# ---------------------------------------------------------------------------
#
# PUBLIC_TARGETS are the supported human/agent command surface.
# INTERNAL_TARGETS are implementation capabilities: callable, but not API.
#
# Neither classification changes execution semantics; it makes ownership
# machine-visible and gives .PHONY one authoritative inventory.

PUBLIC_TARGETS := \
	help \
	start \
	venv \
	sync \
	wiring-check \
	symlinks-check \
	symlinks-install \
	claude-plugins \
	claude-skill-registry \
	sync-generated \
	claude-skills \
	claude-skills-check \
	claude-skills-test \
	claude-settings \
	claude-settings-check \
	claude-env \
	autonomy-contracts-validate \
	autonomy-validate \
	l4-status \
	l4-begin \
	l4-record-kernels \
	l4-authorize \
	agents-env \
	ide-profile \
	ide-profile-test \
	backup-gate-test \
	repo-write-lock-test \
	precommit-hook-contract \
	path-lint \
	precommit \
	precommit-repo \
	backup \
	push \
	graphiti-health \
	lint \
	lint-ruff \
	lint-mypy \
	test \
	uv-lock-check \
	pr \
	PR \
	Pr \
	pR \
	pr-security \
	pr-full \
	rules-validate \
	rules-stabilize \
	integrity-check \
	integrity-snapshot \
	secrets-sync \
	secrets-check \
	ui-operator-sync \
	program-execution-core-validate \
	program-execution-adapters \
	program-execution-conformance \
	program-execution-probe \
	peer-execution-conformance \
	rules-check \
	rules-contract-check \
	skills-check \
	hygiene \
	hygiene-fix \
	clean \
	workspace-clean

INTERNAL_TARGETS := \
	legacy-doctrine-residue \
	lint-ruff-full \
	scratch-hold-restore \
	scratch-hold-status \
	agents-runtime-bindings-validate \
	program-execution-campaign-schema \
	program-execution-campaign-compile \
	program-execution-controller-tests \
	peer-execution-validate \
	peer-execution-probe \
	agents-deployment-validate \
	agents-results-validate \
	agents-data-validate \
	agents-runtime-probe \
	claude-deepseek \
	claude-deepseek-verify \
	rules-contract-shadow

ALL_TARGETS := $(sort $(PUBLIC_TARGETS) $(INTERNAL_TARGETS))

.PHONY: $(ALL_TARGETS)

# These are ordered state-transition graphs. Their prerequisites must not be
# raced by a caller supplying -j.
.NOTPARALLEL: push pr-full

# ===========================================================================
##@ Command surface
# ===========================================================================

help: ## Show the supported repository command surface
	@awk 'BEGIN {FS = ":.*## "} \
		/^##@ / {printf "\n%s\n", substr($$0, 5); next} \
		/^[A-Za-z0-9_.-]+:.*## / {printf "  %-34s %s\n", $$1, $$2}' \
		$(MAKEFILE_LIST)
	@printf "\nConsumer repository:\n"
	@printf "  make -C \"\$$HOME/.cursor-governance\" pr WS=\"\$$(pwd)\"\n"

# ===========================================================================
##@ Bootstrap and environment
# ===========================================================================

start: ## Run the full session-start pipeline against WS
	@cd "$(WS)" && CURSOR_PROJECT_DIR="$(WS)" L9_BOOTSTRAP_SYNC=1 \
		bash "$(GOV_ROOT)/ops/hooks/session_start_bootstrap.sh" \
		| python3 "$(GOV_ROOT)/ops/scripts/render_bootstrap_context.py"

venv: ## Reconcile the pinned development environment from uv.lock
	uv sync --locked --extra dev

sync: ## Fast-forward synchronize the governance clone from origin/main
	bash ops/scripts/governance_sync.sh

wiring-check: ## Validate governance wiring for WS
	bash ops/scripts/check_governance_wiring.sh "$(WS)"

symlinks-check: ## Validate governance symlink health
	bash ops/scripts/validate_governance_symlinks.sh

symlinks-install: ## Install governance symlinks for a consumer workspace
	bash ops/scripts/setup_workspace_symlinks.sh

ide-profile: ## Reconcile the Cursor/VS Code IDE profile for WS
	bash ops/scripts/install_ide_profile.sh "$(WS)"

ui-operator-sync: ## Install optional UI-operator dependencies
	uv sync --extra ui-operator

# ===========================================================================
##@ Claude environment
# ===========================================================================

claude-plugins: ## Reconcile Claude Code plugins
	bash ops/scripts/setup_claude_code_plugins.sh \
		$(if $(WS),--workspace "$(WS)",)

claude-skill-registry: ## Build the deterministic Claude skill registry
	uv run python3 ops/scripts/build_claude_skill_registry.py \
		--root "$(GOV_ROOT)"

sync-generated: ## Reconcile generated governance projections
	python3 ops/scripts/sync_generated_artifacts.py \
		--root "$(GOV_ROOT)" --force --check

claude-skills: claude-skill-registry ## Reconcile L9 skills into Claude discovery paths
	python3 ops/scripts/reconcile_claude_l9_skills.py \
		--root "$(GOV_ROOT)" \
		--scope user \
		--scope project \
		--workspace "$(WS)"

claude-skills-check: ## Validate Claude skill activation and registry state
	python3 environment/agents/adapters/claude-code/validate_skill_activation.py

claude-skills-test: ## Run Claude/Cursor skill routing fixtures
	python3 environment/agents/adapters/claude-code/tests/test_skill_router.py
	python3 environment/agents/adapters/claude-code/tests/test_skill_reconciliation.py
	python3 environment/agents/adapters/claude-code/tests/test_cursor_skill_router.py

claude-settings: ## Reconcile Claude settings for governance/user/WS
	python3 ops/scripts/reconcile_claude_settings.py \
		--root "$(GOV_ROOT)" \
		$(if $(WS),--workspace "$(WS)",)

claude-settings-check: ## Read-only Claude settings drift check
	python3 ops/scripts/reconcile_claude_settings.py \
		--root "$(GOV_ROOT)" \
		--check \
		$(if $(WS),--workspace "$(WS)",)

claude-env: claude-settings ## Reconcile and validate the Claude environment
	python3 environment/agents/adapters/claude-code/validate_claude_env.py

# ===========================================================================
##@ Autonomy
# ===========================================================================

autonomy-contracts-validate: ## Validate first-class autonomy contracts
	python3 ops/scripts/validate_autonomy_contracts.py

autonomy-validate: autonomy-contracts-validate ## Validate bounded-concurrency autonomy runtime
	python3 environment/program-execution/peer_execution/autonomy/validate_autonomy.py

l4-status: ## Show L4 local-autonomy state
	python3 ops/autonomy/l4_local.py --workspace "$(WS)" status

l4-begin: ## Begin an L4 local-autonomy execution
	python3 ops/autonomy/l4_local.py \
		--workspace "$(WS)" begin \
		$(if $(CONTRACT_ID),--contract-id "$(CONTRACT_ID)",)

l4-record-kernels: ## Record L4 kernel state
	python3 ops/autonomy/l4_local.py \
		--workspace "$(WS)" record-kernels

l4-authorize: ## Authorize the L4 release transition
	python3 ops/autonomy/l4_local.py \
		--workspace "$(WS)" authorize-release

# ===========================================================================
##@ Agent environment
# ===========================================================================

agents-env: ## Validate multi-agent registry and adapter consistency
	python3 environment/agents/tools/validate_agents.py

agents-runtime-bindings-validate:
	python3 -B $(AGENTS_TOOLS)/validate_executable_peers.py --schema-only

# ===========================================================================
##@ Repository self-tests
# ===========================================================================

ide-profile-test: ## Run the IDE profile installer fixture
	bash ops/scripts/test_install_ide_profile.sh

backup-gate-test: ## Run the sessionEnd backup-gate fixture
	bash ops/scripts/test_backup_gate.sh

repo-write-lock-test: ## Run the repository-write-lock fixture
	bash ops/scripts/test_repo_write_lock.sh

precommit-hook-contract: ## Validate pre-commit read_only/writer declarations
	python3 ops/scripts/validate_precommit_hook_contract.py

path-lint: ## Reject hard-coded /Users and /home paths
	bash ops/scripts/validate_governance_no_hardcoded_paths.sh

legacy-doctrine-residue:
	python3 ops/scripts/validate_legacy_doctrine_residue.py

# ===========================================================================
##@ Quality
# ===========================================================================

precommit: ## Run the complete pre-commit YAML against the full tree
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "pre-commit not installed. Run: pip install pre-commit && pre-commit install"; \
		exit 1; \
	}
	pre-commit run --all-files

precommit-repo: ## Run pre-commit YAML against the PR changed-file set
	PR_BASE="$(PR_BASE)" \
		bash ops/scripts/run_pr_precommit.sh "$(WS)"

graphiti-health: venv ## Check Graphiti tool-plane health
	uv run python3 ops/graphiti/graphiti_memory_client.py health

lint-ruff: venv ## Run Ruff gates against changed Python files
	@tmp=$$(mktemp); py=$$(mktemp); \
	trap 'rm -f "$$tmp" "$$py"' EXIT; \
	if ! PR_BASE="$(PR_BASE)" WS="$(WS)" \
		bash ops/scripts/resolve_changed_files.sh >"$$tmp"; then \
		echo "FAIL: resolve_changed_files.sh"; \
		exit 1; \
	fi; \
	grep -E '\.(py|pyi)$$' "$$tmp" >"$$py" || true; \
	if [ ! -s "$$py" ]; then \
		echo "OK: no changed Python files for ruff"; \
		exit 0; \
	fi; \
	echo "ruff (changed): $$(grep -c . "$$py") file(s)"; \
	xargs uv run --no-build ruff check <"$$py" && \
	xargs uv run --no-build ruff format --check <"$$py"

lint-ruff-full: venv
	uv run --no-build ruff check .
	uv run --no-build ruff format --check .

lint-mypy: venv ## Run blocking full-tree mypy
	uv run mypy . \
		--show-error-codes \
		--pretty \
		--ignore-missing-imports

# lint targets are independent read-only capabilities after venv is ready.
# make -j lint may safely execute them concurrently while Make constructs
# venv only once in the invocation.
lint: lint-ruff-full lint-mypy ## Run full-tree Ruff and mypy

uv-lock-check: ## Fail when uv.lock disagrees with pyproject.toml
	@if [ -f uv.lock ]; then \
		uv lock --check; \
	else \
		echo "OK: no uv.lock present, skipping"; \
	fi

test: venv ## Run the repository pytest suites
	bash ops/scripts/run_pytest_suites.sh --tb=short -q

# ===========================================================================
##@ PR and release
# ===========================================================================

pr-security: ## Run changed-file PR security scanners
	PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_BASE="$(PR_BASE)" \
		bash ops/scripts/run_pr_security.sh "$(WS)"

scratch-hold-restore:
	python3 ops/scripts/scratch_hold.py \
		--workspace "$(or $(WS),$(GOV_ROOT))" \
		restore --all

scratch-hold-status:
	python3 ops/scripts/scratch_hold.py \
		--workspace "$(or $(WS),$(GOV_ROOT))" \
		status

# Canonical shipping command.
#
# IMPORTANT:
# There is intentionally NO pr-check target.
#
# make pr:
#   1. validates this repository state once;
#   2. fails immediately on gate failure;
#   3. publishes/reuses the PR only after PASS;
#   4. emits post-PR remediation authorization when enabled.
#
# After an agent repairs a failure it runs `make pr` again. That new state
# receives exactly one new canonical validation attempt.
#
# OPEN_PR=0 make pr is the sole gate-only form.
pr: ## Gate once, then publish/reuse and remediate the PR
	PR_BASE="$(PR_BASE)" \
	PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_MYPY_STRICT="$(PR_MYPY_STRICT)" \
	WS="$(WS)" \
		bash ops/scripts/run_pr_gate.sh
	@if [ "$(OPEN_PR)" = "1" ]; then \
		PR_BASE="$(PR_BASE)" \
		PR_REMEDIATE="$(PR_REMEDIATE)" \
		PR_AUTOMERGE="$(PR_AUTOMERGE)" \
		GOV_ROOT="$(GOV_ROOT)" \
			bash ops/scripts/open_pr_after_gate.sh "$(WS)"; \
	else \
		echo "OPEN_PR=0 — canonical PR gate PASS; publication skipped"; \
	fi

# Explicit compatibility aliases only.
# No parse-time shell/tr casing mechanism.
PR Pr pR: pr

# Intentional full-tree/nightly-adjacent local gate.
#
# These prerequisites are deliberately serialized via .NOTPARALLEL because
# pre-commit may reconcile files and later checks must inspect the resulting
# state. Shared `venv` is still deduplicated by the same Make invocation.
pr-full: venv precommit lint-ruff-full uv-lock-check test rules-validate ## Run the slow full-tree local gate
	@echo "NOTE: corpus security remains nightly CI"
	@echo "RESULT: PASS — full local gate"

backup: ## Commit/rebase/push the governance clone using the canonical implementation
	bash ops/scripts/backup_to_github.sh

# precommit MUST finish successfully before backup/push. Target-scoped
# .NOTPARALLEL prevents `make -j push` from racing the mutation against its gate.
push: precommit backup ## Run full pre-commit then backup/push

# ===========================================================================
##@ Rules, skills, and governance
# ===========================================================================

rules-validate: ## Read-only rules-manifest drift validation
	python3 ops/scripts/validate_rules_manifest.py \
		--root "$(GOV_ROOT)"

rules-stabilize: ## Run the full rules-subsystem stabilization harness
	bash ops/scripts/run_rules_stabilization_validation.sh

rules-check: ## Validate Cursor-native rules standards
	python3 ops/scripts/check_rules_standard.py

rules-contract-shadow:
	python3 ops/contracts/build_rules.py census

rules-contract-check: ## Validate the rules contract
	python3 ops/contracts/build_rules.py check

skills-check: ## Validate Cursor-native skill standards
	python3 ops/scripts/check_skills_standard.py

hygiene: ## Run repository housekeeping validation
	python3 tools/check_repo_hygiene.py

hygiene-fix: ## Show the repository housekeeping repair runbook
	@echo "See WIP/housekeeping-pack/RUNBOOK.md Section 4"

# ===========================================================================
##@ Integrity and secrets
# ===========================================================================

integrity-check: ## Read-only integrity-baseline drift report
	python3 integrity/hash-verifier.py --no-repair

integrity-snapshot: ## Intentionally refresh the integrity baseline
	python3 integrity/hash-verifier.py --snapshot

# venv is a true dependency, not an imperative sub-make.
# If both targets are requested in the same Make invocation, environment
# reconciliation occurs once.
secrets-sync: venv ## Synchronize the AWS secret-reference registry
	$(GOV_ROOT)/.venv/bin/python \
		ops/secrets/sync_secrets_registry.py

secrets-check: venv ## Verify a secret reference without printing its value
	$(GOV_ROOT)/.venv/bin/python \
		ops/secrets/resolve_secret.py \
		--ref "$(REF)" \
		--check

# ===========================================================================
##@ Program Execution
# ===========================================================================

program-execution-core-validate: ## Validate Program Execution core contracts
	PYTHONDONTWRITEBYTECODE=1 \
		python3 -B \
		$(PE_ROOT)/core/scripts/validate_pair.py \
		$(PE_ROOT)/core \
		--mode template
	$(MAKE) program-execution-campaign-schema
	$(MAKE) program-execution-campaign-compile

program-execution-campaign-schema:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		python3 -B -m unittest \
		$(PE_ROOT)/conformance/test_campaign_source_schema.py

program-execution-campaign-compile:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		python3 -B -m unittest \
		$(PE_ROOT)/scripts/tests/test_compile_campaign_source.py

program-execution-adapters: ## Validate execution adapters and thin providers
	PYTHONDONTWRITEBYTECODE=1 \
		python3 -B \
		$(PE_ROOT)/scripts/validate_execution_adapters.py
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		python3 -B \
		$(PE_ROOT)/scripts/validate_thin_providers.py

program-execution-conformance: autonomy-contracts-validate ## Run Program Execution conformance
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		python3 -B \
		$(PE_ROOT)/scripts/run_conformance.py
	PYTHONDONTWRITEBYTECODE=1 \
		python3 -B \
		$(PE_ROOT)/scripts/validate_manifest.py
	$(MAKE) program-execution-controller-tests

program-execution-controller-tests:
	PYTHONDONTWRITEBYTECODE=1 \
		python3 -B -m unittest discover \
		-s $(PE_ROOT)/core/program-execution-controller-template/scripts/tests \
		-p 'test_*.py'

program-execution-probe: ## Probe Program Execution adapter readiness
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		python3 -B \
		$(PE_ROOT)/scripts/probe_execution_adapters.py

# ===========================================================================
##@ Executable peers
# ===========================================================================

peer-execution-validate:
	python3 -B \
		$(AGENTS_TOOLS)/validate_executable_peers.py

peer-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 \
	PYTHONPATH=$(PE_ROOT) \
		python3 -B \
		$(PE_ROOT)/scripts/probe_executable_peers.py

# Deliberately ordered orchestration.
#
# These are not represented as unordered prerequisites because their sequence
# is part of the executable-peer contract and must remain deterministic even
# when the caller uses -j.
peer-execution-conformance: ## Run complete executable-peer conformance
	$(MAKE) agents-env
	$(MAKE) agents-runtime-bindings-validate
	$(MAKE) program-execution-adapters
	$(MAKE) program-execution-conformance
	$(MAKE) peer-execution-validate
	$(MAKE) peer-execution-probe
	$(MAKE) program-execution-core-validate

# ===========================================================================
##@ Agent runtime validation
# ===========================================================================

agents-deployment-validate:
	$(GOV_ROOT)/.venv/bin/python \
		-m pytest environment/agents/deployment/tests -q

agents-results-validate:
	$(GOV_ROOT)/.venv/bin/python \
		-m pytest \
		environment/agents/results/tests \
		environment/agents/lifecycle/tests \
		-q

agents-data-validate:
	$(GOV_ROOT)/.venv/bin/python \
		-m pytest \
		environment/agents/generated-data/ingress/tests \
		-q

agents-runtime-probe:
	$(GOV_ROOT)/.venv/bin/python \
		environment/agents/readiness/probe_runtime.py

# ===========================================================================
##@ Model routing
# ===========================================================================

claude-deepseek:
	./scripts/claude-deepseek.sh

claude-deepseek-verify:
	./scripts/verify-routing.sh

# ===========================================================================
##@ Workspace lifecycle
# ===========================================================================

clean: ## Ship leftover work to scoped PRs, prune merged locals, prime main
	CLEAN_MODE="$(CLEAN_MODE)" \
	CLEAN_REMOTE="$(CLEAN_REMOTE)" \
	PR_BASE="$(PR_BASE)" \
	WS="$(WS)" \
		bash "$(GOV_ROOT)/ops/scripts/run_workspace_clean.sh"

# One implementation, two public spellings.
workspace-clean: clean ## Alias for clean