.PHONY: help start sync wiring-check symlinks-check symlinks-install claude-plugins claude-env claude-skill-registry sync-generated claude-skills claude-skills-check claude-skills-test autonomy-validate autonomy-contracts-validate agents-env ide-profile ide-profile-test backup-gate-test path-lint precommit precommit-repo backup push graphiti-health lint lint-ruff lint-mypy test uv-lock-check pr PR Pr pR pr-check pr-security pr-full venv rules-validate rules-stabilize integrity-check integrity-snapshot secrets-sync secrets-check ui-operator-sync
.PHONY: l4-status l4-begin l4-record-kernels l4-authorize
.PHONY: repo-write-lock-test precommit-hook-contract

# Case-insensitive `pr` goal: Make PR / Pr / pR / make pr all run the same target.
# (GNU Make matches goals case-sensitively; remap any non-canonical casing to `pr`.)
_pr_case_aliases := $(foreach g,$(MAKECMDGOALS),$(if $(filter pr,$(shell printf '%s' '$(g)' | tr '[:upper:]' '[:lower:]')),$(if $(filter-out pr,$(g)),$(g))))
ifneq ($(_pr_case_aliases),)
.PHONY: $(_pr_case_aliases)
$(_pr_case_aliases): pr
endif

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

# When 1, `make pr` (any capitalization) push+open GitHub PR after gate PASS.
# Gate-only: `make pr-check` or `OPEN_PR=0 make pr`.
OPEN_PR ?= 1

# When 1 (default), after open: GitHub-subscribe + emit L9_AGENT_REQUIRED so the
# agent spawns background l9-pr-remediation (poll_worker). PR_REMEDIATE=0 to skip.
PR_REMEDIATE ?= 1

help:
	@echo "Targets: start sync wiring-check symlinks-check symlinks-install claude-plugins claude-env claude-skill-registry sync-generated claude-skills claude-skills-check claude-skills-test autonomy-validate autonomy-contracts-validate agents-env ide-profile ide-profile-test backup-gate-test path-lint precommit precommit-repo backup push graphiti-health lint lint-ruff lint-mypy test uv-lock-check pr PR Pr pR pr-check pr-security pr-full venv rules-validate rules-stabilize integrity-check integrity-snapshot secrets-sync secrets-check ui-operator-sync"
	@echo "  make repo-write-lock-test / precommit-hook-contract — repo-write lock selftest; pre-commit hook read_only/writer contract"
	@echo "  make l4-status / l4-begin / l4-record-kernels / l4-authorize — L4 local autonomy (no mid-exec push)"
	@echo "  make pr (any case) — gate → open PR → subscribe → agent spawns l9-pr-remediation (OPEN_PR=0 / PR_REMEDIATE=0 / pr-check to skip)"
	@echo "  make sync-generated — heal RULES/COMMANDS/PE manifests, skill-registry, skillOverrides (idempotent)"
	@echo "  make pr-security  — gitleaks/bandit/semgrep/pip-audit on changed files only (WS-aware)"
	@echo "  make pr-full      — intentional full-tree local gate (nightly-equivalent; slow)"
	@echo "  make secrets-sync — sync openclaw-igorbot registry from AWS Secrets Manager (refs only)"
	@echo "  make secrets-check REF='openclaw-igorbot/github#token' — resolve --check (no value printed)"
	@echo "  make ui-operator-sync — uv sync --extra ui-operator (then: playwright install)"
	@echo "  Consumer repos: make -C \"\$$HOME/.cursor-governance\" pr WS=\"\$$(pwd)\""
	@echo "  Prefer l9-ci-core thin Makefile (identical across repos) when adopting the common workflow."
	@echo "  make clean / workspace-clean — ship leftover work to scoped PRs by repo, prune merged locals, prime main (CLEAN_MODE=plan to preview; CLEAN_REMOTE=0 to stay local)"
	@echo "  Consumer repos: make -C \"\$$HOME/.cursor-governance\" clean WS=\"\$$(pwd)\""

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

## Heal derived manifests/registries/overrides (rules, skills, commands, PE).
## Idempotent; used by pre-commit and make pr. Never a reason to block make pr alone.
sync-generated:
	python3 ops/scripts/sync_generated_artifacts.py --root "$(CURDIR)" --force --check

## Reconcile L9 skills into Claude native user + project discovery paths.
claude-skills: claude-skill-registry
	python3 ops/scripts/reconcile_claude_l9_skills.py --root "$(CURDIR)" \
		--scope user --scope project --workspace "$(WS)"

## Read-only registry/frontmatter/hook/routing drift validation.
claude-skills-check:
	python3 environment/agents/adapters/claude-code/validate_skill_activation.py

## Behavioral router + reconciliation fixture tests.
claude-skills-test:
	python3 environment/agents/adapters/claude-code/tests/test_skill_router.py
	python3 environment/agents/adapters/claude-code/tests/test_skill_reconciliation.py
	python3 environment/agents/adapters/claude-code/tests/test_cursor_skill_router.py

.PHONY: claude-settings claude-settings-check claude-install claude-install-check

## Install the Claude Code adapter on THIS machine (CLI / Desktop).
## Runs the exact same installer Web and Mobile reach through
## web/setup.bootstrap.sh -> web/setup.sh, so there is one adapter to maintain:
## locked toolchain from uv.lock, settings triad, skills, MCP front door,
## git excludes, preflight.
## Usage: make claude-install WS=/path/to/repo   (WS defaults to this clone)
claude-install:
	bash environment/agents/adapters/claude-code/install.sh \
		--governance "$(CURDIR)" --workspace "$(if $(WS),$(WS),$(CURDIR))"

## Read-only: report adapter drift without writing anything.
claude-install-check:
	bash environment/agents/adapters/claude-code/install.sh --check \
		--governance "$(CURDIR)" --workspace "$(if $(WS),$(WS),$(CURDIR))"

## Reconcile Claude settings triad (template → gov .claude → ~/.claude → optional WS).
## Component step of claude-install; use claude-install for a full adapter wire-up.
## Usage: make claude-settings WS=/path/to/repo
## Check: make claude-settings-check WS=/path/to/repo
claude-settings:
	python3 ops/scripts/reconcile_claude_settings.py --root "$(CURDIR)" \
		$(if $(WS),--workspace "$(WS)",)

claude-settings-check:
	python3 ops/scripts/reconcile_claude_settings.py --root "$(CURDIR)" --check \
		$(if $(WS),--workspace "$(WS)",)

## Validate the Claude Code environment adapter and proactive skill activation.
## Heals the settings triad first (idempotent), then runs structural validation.
claude-env:
	$(MAKE) claude-settings
	python3 environment/agents/adapters/claude-code/validate_claude_env.py

## Fail-closed first-class autonomy family registry (environment/contracts/autonomy).
autonomy-contracts-validate:
	python3 ops/scripts/validate_autonomy_contracts.py

## Validate the Claude Code bounded-concurrency autonomy runtime (contracts + unit tests).
autonomy-validate: autonomy-contracts-validate
	python3 environment/program-execution/peer_execution/autonomy/validate_autonomy.py


## L4 local autonomy (stacked local commits → kernels → authorize → push/PR).
l4-status:
	python3 ops/autonomy/l4_local.py --workspace "$(WS)" status

l4-begin:
	python3 ops/autonomy/l4_local.py --workspace "$(WS)" begin $(if $(CONTRACT_ID),--contract-id "$(CONTRACT_ID)",)

l4-record-kernels:
	python3 ops/autonomy/l4_local.py --workspace "$(WS)" record-kernels

l4-authorize:
	python3 ops/autonomy/l4_local.py --workspace "$(WS)" authorize-release


## Validate the multi-agent environment pack: registry naming law, identity uniqueness,
## role catalog, adapter consistency, no committed secrets
agents-env:
	python3 environment/agents/tools/validate_agents.py

## Validate PEER_RUNTIME_BINDINGS.yaml against peer-runtime-bindings.schema.json
## (topology SSOT schema gate; full cross-plane rules are peer-execution-validate).
agents-runtime-bindings-validate:
	python3 -B environment/agents/tools/validate_executable_peers.py --schema-only

## Reconcile the Cursor IDE profile (extensions + .vscode settings). Usage: make ide-profile WS=/path/to/repo
ide-profile:
	bash ops/scripts/install_ide_profile.sh "$(WS)"

## Fixture selftest for the IDE profile installer (writes only under $$TMPDIR)
ide-profile-test:
	bash ops/scripts/test_install_ide_profile.sh

## Fixture selftest for the sessionEnd backup gate (writes only under $$TMPDIR)
backup-gate-test:
	bash ops/scripts/test_backup_gate.sh

## Fixture selftest for the repo-write lock (writes only under $$TMPDIR)
repo-write-lock-test:
	bash ops/scripts/test_repo_write_lock.sh

## Fail if a pre-commit hook is not declared read_only or writer
precommit-hook-contract:
	python3 ops/scripts/validate_precommit_hook_contract.py

## Fail if any script/rule/hook hardcodes a /Users or /home path instead of $$HOME
path-lint:
	bash ops/scripts/validate_governance_no_hardcoded_paths.sh

## Fail if active surfaces teach retired Dropbox SSOT or L9_MEMORY_HTTP side doors
legacy-doctrine-residue:
	python3 ops/scripts/validate_legacy_doctrine_residue.py

## Full-tree pre-commit (nightly / intentional). Not used by `make pr`.
precommit:
	@command -v pre-commit >/dev/null 2>&1 || { echo "pre-commit not installed. Run: pip install pre-commit && pre-commit install"; exit 1; }
	pre-commit run --all-files

## Changed-files pre-commit for PR velocity.
## Skips machine-local symlinks-check unless WS is a local governance SSOT clone
## (skills/AUTONOMY_MANIFEST.yaml + rules/RULES-MANIFEST.yaml present).
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
## Splits root autonomy/ from environment/program-execution/peer_execution/autonomy/ (same package name).
test: venv
	bash ops/scripts/run_pytest_suites.sh --tb=short -q

## Local PR security scanners on CHANGED files only.
## Pins: l9-ci-core security.yml (gitleaks 8.24.3, bandit==1.8.6, pip-audit==2.9.0).
## Semgrep: SDK supported range >=1.100.0,<2.0.0. Full-tree = nightly CI.
pr-security:
	PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" PR_BASE="$(PR_BASE)" \
		bash ops/scripts/run_pr_security.sh "$(WS)"

## Local PR gate — CHANGED FILES ONLY (invariant). Does not scan the whole tree.
## Nightly GHA owns full-corpus scans. Gate only (no GitHub PR).

# Never-lose scratch hold (non-WIP vault under .l9/scratch-hold/)
scratch-hold-restore:
	python3 ops/scripts/scratch_hold.py --workspace "$(or $(WS),$(CURDIR))" restore --all

scratch-hold-status:
	python3 ops/scripts/scratch_hold.py --workspace "$(or $(WS),$(CURDIR))" status

pr-check:
	PR_BASE="$(PR_BASE)" PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_MYPY_STRICT="$(PR_MYPY_STRICT)" WS="$(WS)" \
		bash ops/scripts/run_pr_gate.sh

## Gate → open/reuse GitHub PR → subscribe → emit l9-pr-remediation agent handoff.
## `make pr` / `make PR` / `make Pr` / `make pR` are equivalent (case-insensitive).
## Requires a feature branch with commits ahead of PR_BASE.
## OPEN_PR=0 → gate only. PR_REMEDIATE=0 → open+subscribe without agent spawn marker.
pr: pr-check
	@if [ "$(OPEN_PR)" = "1" ]; then \
		PR_BASE="$(PR_BASE)" PR_REMEDIATE="$(PR_REMEDIATE)" GOV_ROOT="$(CURDIR)" \
			bash ops/scripts/open_pr_after_gate.sh "$(WS)"; \
	else \
		echo "OPEN_PR=0 — skipped GitHub PR open (gate already PASS)"; \
	fi

# Explicit aliases (also covered by _pr_case_aliases remap above).
PR Pr pR: pr

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
## committed artifacts in place — run intentionally and review the diff.
## Day-to-day: `generate-rules-manifest` in .pre-commit-config.yaml and
## `make pr` (run_pr_gate.sh) auto-regenerate RULES-MANIFEST.* before validate.
## For a pure read-only check use `make rules-validate`.
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

## Sync ops/secrets/openclaw-igorbot.registry.yaml from AWS Secrets Manager (refs/key names only).
secrets-sync:
	@$(MAKE) venv
	$(CURDIR)/.venv/bin/python ops/secrets/sync_secrets_registry.py

## Resolve a secret ref with --check (never prints the value). Example:
##   make secrets-check REF='openclaw-igorbot/github#token'
REF ?= openclaw-igorbot/github#token
secrets-check:
	@$(MAKE) venv
	$(CURDIR)/.venv/bin/python ops/secrets/resolve_secret.py --ref "$(REF)" --check

## Install optional UI-operator deps (playwright + boto3). Not required for make pr.
## After this: playwright install
ui-operator-sync:
	uv sync --extra ui-operator

# PROGRAM_EXECUTION_ADAPTER_LAYER_V1
PE_ROOT := environment/program-execution
.PHONY: program-execution-core-validate program-execution-adapters 	program-execution-conformance program-execution-probe

program-execution-core-validate:
	PYTHONDONTWRITEBYTECODE=1 python3 -B $(PE_ROOT)/core/scripts/validate_pair.py 		$(PE_ROOT)/core --mode template
	$(MAKE) program-execution-campaign-schema
	$(MAKE) program-execution-campaign-compile

program-execution-adapters:
	PYTHONDONTWRITEBYTECODE=1 python3 -B 		$(PE_ROOT)/scripts/validate_execution_adapters.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B $(PE_ROOT)/scripts/validate_thin_providers.py

program-execution-conformance: autonomy-contracts-validate
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B 		$(PE_ROOT)/scripts/run_conformance.py
	PYTHONDONTWRITEBYTECODE=1 python3 -B $(PE_ROOT)/scripts/validate_manifest.py
	$(MAKE) program-execution-controller-tests

program-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B 		$(PE_ROOT)/scripts/probe_execution_adapters.py

AGENTS_TOOLS := environment/agents/tools
.PHONY: peer-execution-validate peer-execution-probe peer-execution-conformance
.PHONY: agents-runtime-bindings-validate

# Executable Peer Contract v1 — structural cross-registry gate (E1-E15):
# agent_registry.yaml execution bindings <-> program-execution adapters +
# registry <-> canonical autonomy provider. validate_executable_peers.py.
# v2 also gates PEER_RUNTIME_BINDINGS.yaml topology SSOT (see agents-runtime-bindings-validate).
peer-execution-validate:
	python3 -B $(AGENTS_TOOLS)/validate_executable_peers.py

# Binding-level readiness probe. Emits per-(agent,surface,adapter) receipts
# under $$HOME/.l9/programs/_peer-readiness/ and fails if any enabled agent
# has no READY binding. Runtime/session-scoped availability gate.
# Receipts also land under $$L9_RUNTIME_ROOT/agents/readiness/ (default ~/.l9/agents/readiness/).
peer-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B \
		$(PE_ROOT)/scripts/probe_executable_peers.py
# Honest BLOCKED (Cursor file-drop / missing Claude host) is inventory, not FAIL.

# Full executable-peer conformance: compose the identity, adapter, program,
# and readiness gates (Executable Peer Contract v1, section 14).
# Also runs agents-runtime-bindings-validate (Executable Peer Contract v2 schema gate).
peer-execution-conformance:
	$(MAKE) agents-env
	$(MAKE) agents-runtime-bindings-validate
	$(MAKE) program-execution-adapters
	$(MAKE) program-execution-conformance
	$(MAKE) peer-execution-validate
	$(MAKE) peer-execution-probe
	$(MAKE) program-execution-core-validate

.PHONY: agents-deployment-validate agents-results-validate agents-data-validate agents-runtime-probe
agents-deployment-validate:
	$(CURDIR)/.venv/bin/python -m pytest environment/agents/deployment/tests -q
agents-results-validate:
	$(CURDIR)/.venv/bin/python -m pytest environment/agents/results/tests environment/agents/lifecycle/tests -q
agents-data-validate:
	$(CURDIR)/.venv/bin/python -m pytest environment/agents/generated-data/ingress/tests -q
agents-runtime-probe:
	$(CURDIR)/.venv/bin/python environment/agents/readiness/probe_runtime.py

# DeepSeek V4 Pro launcher for Claude Code (env-routed; no keys in git)
.PHONY: claude-deepseek claude-deepseek-verify
claude-deepseek:
	./scripts/claude-deepseek.sh

claude-deepseek-verify:
	./scripts/verify-routing.sh

.PHONY: program-execution-campaign-schema program-execution-campaign-compile
.PHONY: program-execution-controller-tests
program-execution-campaign-schema:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B -m unittest \
		$(PE_ROOT)/conformance/test_campaign_source_schema.py

program-execution-campaign-compile:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) python3 -B -m unittest \
		$(PE_ROOT)/scripts/tests/test_compile_campaign_source.py

program-execution-controller-tests:
	PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
		-s $(PE_ROOT)/core/program-execution-controller-template/scripts/tests \
		-p 'test_*.py'

.PHONY: rules-check
## Cursor-native rules frontmatter + always-apply ratchet (docs/rules-standard.md).
rules-check:
	python3 ops/scripts/check_rules_standard.py

.PHONY: rules-contract-shadow rules-contract-check
## Foundation shadow: stdout only. Does not write rules or census files.
rules-contract-shadow:
	python3 ops/contracts/build_rules.py census
rules-contract-check:
	python3 ops/contracts/build_rules.py check

.PHONY: skills-check
## Cursor-native skill frontmatter + discovery-footprint ratchet (docs/skills-standard.md).
skills-check:
	python3 ops/scripts/check_skills_standard.py

.PHONY: hygiene hygiene-fix
## RB-HK-001 repository housekeeping gate.
hygiene:
	python3 tools/check_repo_hygiene.py

hygiene-fix:
	@echo "See WIP/housekeeping-pack/RUNBOOK.md Section 4"

# Workspace ship+reset. Default apply opens scoped PRs (never main).
# Preview: CLEAN_MODE=plan. Local only: CLEAN_REMOTE=0.
# Consumer: make -C "$(HOME)/.cursor-governance" clean WS="$(pwd)"
CLEAN_MODE ?= apply
CLEAN_REMOTE ?= 1
.PHONY: clean workspace-clean
clean workspace-clean:
	CLEAN_MODE="$(CLEAN_MODE)" CLEAN_REMOTE="$(CLEAN_REMOTE)" PR_BASE="$(PR_BASE)" \
	WS="$(WS)" bash "$(CURDIR)/ops/scripts/run_workspace_clean.sh"
