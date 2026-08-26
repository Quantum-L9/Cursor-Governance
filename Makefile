.PHONY: help start sync wiring-check symlinks-check symlinks-install claude-plugins claude-projection claude-projection-check claude-env claude-skill-registry sync-generated claude-skills claude-skills-check claude-skills-test autonomy-validate autonomy-contracts-validate agents-env ide-profile ide-profile-test backup-gate-test path-lint precommit precommit-repo backup push graphiti-health lint lint-ruff lint-mypy test uv-lock-check pr PR Pr pR pr-check pr-security pr-full venv rules-validate rules-stabilize integrity-check integrity-snapshot secrets-sync secrets-check ui-operator-sync
.PHONY: l4-status l4-begin l4-record-kernels l4-authorize
.PHONY: improve pr-preflight
.PHONY: repo-write-lock-test precommit-hook-contract
.PHONY: capability-contract-validate capability-check capability-broker-preflight
.PHONY: broker-serve

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

# Stack on an overlapping open PR head by default. Do not export this variable:
# `make pr-check` pytest would inherit it and false-pass overlap tests.
# Opt out (publish against main): PR_STACK= make pr
PR_STACK ?= auto

# When 1, `make pr` (any capitalization) push+open GitHub PR after gate PASS.
# Gate-only: `make pr-check` or `OPEN_PR=0 make pr`.
OPEN_PR ?= 1

# When 1 (default), after open: GitHub-subscribe + emit L9_AGENT_REQUIRED so the
# agent spawns background l9-pr-remediation (poll_worker). PR_REMEDIATE=0 to skip.
PR_REMEDIATE ?= 1

# make improve IMPROVE_RECORD=1 records kernels + authorize-release after the
# agent applied Recursive Alignment and Validate & Repair.
IMPROVE_RECORD ?= 0

# Locked interpreter: pyproject.toml + uv.lock (`make venv`).
# macOS /usr/bin/make is GNU Make 3.81 — it does not export `export VAR :=`
# into recipe shells. Recipes MUST call $(PYTHON)/$(RUFF)/$(MYPY), never PATH python3.
PYTHON := $(CURDIR)/.venv/bin/python
RUFF := $(CURDIR)/.venv/bin/ruff
MYPY := $(CURDIR)/.venv/bin/mypy
export PYTHON

.PHONY: gov-python
gov-python:
	@bash "$(CURDIR)/ops/scripts/ensure_gov_python.sh" "$(CURDIR)"

# Every requested goal except help/venv must pass the locked-interpreter probe.
_GOV_PYTHON_FREE := help venv gov-python
_GOV_PYTHON_REQ := $(filter-out $(_GOV_PYTHON_FREE),$(MAKECMDGOALS))
ifneq ($(_GOV_PYTHON_REQ),)
$(_GOV_PYTHON_REQ): gov-python
endif

help:
	@echo "Targets: start sync wiring-check symlinks-check symlinks-install claude-plugins claude-projection claude-projection-check claude-env claude-skill-registry sync-generated claude-skills claude-skills-check claude-skills-test autonomy-validate autonomy-contracts-validate agents-env ide-profile ide-profile-test backup-gate-test path-lint precommit precommit-repo backup push graphiti-health lint lint-ruff lint-mypy test uv-lock-check pr PR Pr pR pr-check pr-security pr-full venv rules-validate rules-stabilize integrity-check integrity-snapshot secrets-sync secrets-check ui-operator-sync"
	@echo "  make capability-contract-validate / capability-check / capability-broker-preflight — zero-static-secret capability plane"
	@echo "  make repo-write-lock-test / precommit-hook-contract — repo-write lock selftest; pre-commit hook read_only/writer contract"
	@echo "  make l4-status / l4-begin / l4-record-kernels / l4-authorize — L4 local autonomy (no mid-exec push)"
	@echo "  make campaign INTENT=path — PE activate seed → worktree emit → blueprint → pec → host PR → merge-if-green"
	@echo "  make campaign-architecture INTENT=arch.md TARGET=owner/repo — long-form architecture → campaign_source → blueprint → PEC"
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
	@echo "  make gov-python — fail-closed .venv interpreter + runtime import probe"

## Run the FULL session-start pipeline against WS, synchronously, with visible output.
## Same script Cursor runs on sessionStart — one implementation, no drift.
## Usage from a consumer repo: make -C "$$HOME/.cursor-governance" start WS="$$(pwd)"
start:
	@cd "$(WS)" && CURSOR_PROJECT_DIR="$(WS)" L9_BOOTSTRAP_SYNC=1 \
		bash "$(CURDIR)/ops/hooks/session_start_bootstrap.sh" \
		| $(PYTHON) "$(CURDIR)/ops/scripts/render_bootstrap_context.py"

.PHONY: campaign
## Activate a PE campaign from a memo .md or an activate YAML.
## INTENT= required (brief.md or seed.yaml). No campaign_id required for memos.
## CAMPAIGN_UNTIL=activate|blueprint|bootstrap|execute (default execute).
## Local-commit-only: prepare, execute, validate, verify, commit, STOP. The pr and
## merge stages are a separate governed release transition, not a campaign stage.
## Does not implement target-repo tasks or close the ledger after a host-only merge.
campaign:
	@test -n "$(INTENT)" || (echo "INTENT= path to activate seed is required" >&2; exit 2)
	$(PYTHON) environment/program-execution/scripts/run_campaign.py \
	  --intent "$(INTENT)" \
	  --until "$(or $(CAMPAIGN_UNTIL),execute)" \
	  $(CAMPAIGN_ARGS)

.PHONY: campaign-architecture
## Compile a long-form architecture design, microscope audit, or technical review
## straight into an executable campaign. INTENT= required (raw .md needs no edits),
## TARGET=owner/repo required unless the document declares its own `target:`.
## Route: architecture -> campaign_source -> blueprint -> PEC.
## CAMPAIGN_UNTIL=activate|blueprint|bootstrap|execute (default execute), same as make campaign.
## TARGET_CHECKOUT=path to an existing local clone (optional, read-only) so generated
## validations resolve to that repository's own test/lint commands.
campaign-architecture:
	@test -n "$(INTENT)" || (echo "INTENT= path to the architecture document is required" >&2; exit 2)
	TARGET="$(TARGET)" $(PYTHON) environment/program-execution/scripts/run_campaign.py \
	  --architecture \
	  --intent "$(INTENT)" \
	  --until "$(or $(CAMPAIGN_UNTIL),execute)" \
	  $(if $(TARGET),--target "$(TARGET)") \
	  $(if $(TARGET_CHECKOUT),--target-checkout "$(TARGET_CHECKOUT)") \
	  $(CAMPAIGN_ARGS)

.PHONY: campaign-architecture-check
## Compile architecture intent to a campaign source and stop. Writes only the
## compiler cache under $L9_ROOT/primed/; creates no worktree and no PEC state.
campaign-architecture-check:
	@test -n "$(INTENT)" || (echo "INTENT= path to the architecture document is required" >&2; exit 2)
	$(PYTHON) environment/program-execution/scripts/compile_architecture_intent.py \
	  --intent "$(INTENT)" \
	  --repo-root "$(CURDIR)" \
	  $(if $(TARGET),--target "$(TARGET)") \
	  $(if $(TARGET_CHECKOUT),--target-checkout "$(TARGET_CHECKOUT)") \
	  $(ARCHITECTURE_ARGS)

.PHONY: campaign-check-input
## Classify a PE campaign input and print its route. Runs no campaign stage. INTENT= required.
## ARCHITECTURE=1 forces the architecture reading, the way campaign-architecture does.
campaign-check-input:
	@test -n "$(INTENT)" || (echo "INTENT= path to classify is required" >&2; exit 2)
	$(PYTHON) environment/program-execution/scripts/run_campaign.py --check-input "$(INTENT)" \
	  $(if $(ARCHITECTURE),--architecture)

.PHONY: campaign-stack-base
## Print the next campaign PR base from $L9_ROOT/programs/$CAMPAIGN_ID/runtime/STACK.json.
## Never falls back to main. CAMPAIGN_ID= required.
campaign-stack-base:
	@test -n "$(CAMPAIGN_ID)" || (echo "CAMPAIGN_ID= is required" >&2; exit 2)
	$(PYTHON) ops/scripts/stack_pr.py base --stack \
	  "$(or $(L9_ROOT),$(HOME)/.l9)/programs/$(CAMPAIGN_ID)/runtime/STACK.json"

.PHONY: campaign-materialize campaign-drive campaign-reset
## Temporary replay helpers. Not the live campaign path.
## Copy a task's declared writable paths from REF into its pec worktree.
campaign-materialize:
	@test -n "$(CAMPAIGN_ID)" || (echo "CAMPAIGN_ID= is required" >&2; exit 2)
	@test -n "$(TASK)" || (echo "TASK= is required" >&2; exit 2)
	@test -n "$(REF)" || (echo "REF= is required" >&2; exit 2)
	python3 environment/program-execution/scripts/replay_campaign.py materialize \
	  --workspace "$(or $(L9_ROOT),$(HOME)/.l9)/programs/$(CAMPAIGN_ID)" \
	  --task "$(TASK)" \
	  --target "$(or $(TARGET),$(or $(L9_ROOT),$(HOME)/.l9)/program-worktrees/$(CAMPAIGN_ID))" \
	  --ref "$(REF)" \
	  $(if $(HOLD_BACK),--hold-back "$(HOLD_BACK)")

## Drive execute by materializing each incomplete task from REF, then re-running.
campaign-drive:
	@test -n "$(INTENT)" || (echo "INTENT= path to activate seed is required" >&2; exit 2)
	@test -n "$(CAMPAIGN_ID)" || (echo "CAMPAIGN_ID= is required" >&2; exit 2)
	python3 environment/program-execution/scripts/replay_campaign.py drive \
	  --intent "$(INTENT)" \
	  --isolate "$(CURDIR)" \
	  --workspace "$(or $(L9_ROOT),$(HOME)/.l9)/programs/$(CAMPAIGN_ID)" \
	  --target "$(or $(TARGET),$(or $(L9_ROOT),$(HOME)/.l9)/program-worktrees/$(CAMPAIGN_ID))" \
	  $(if $(REF),--ref "$(REF)") \
	  $(if $(HOLD_BACK),--hold-back "$(HOLD_BACK)")

## Retire the live pec runtime, rewind the target to BASE, and re-arm.
campaign-reset:
	@test -n "$(INTENT)" || (echo "INTENT= path to activate seed is required" >&2; exit 2)
	@test -n "$(CAMPAIGN_ID)" || (echo "CAMPAIGN_ID= is required" >&2; exit 2)
	@test -n "$(BASE)" || (echo "BASE= commit SHA is required" >&2; exit 2)
	python3 environment/program-execution/scripts/replay_campaign.py reset \
	  --campaign-id "$(CAMPAIGN_ID)" \
	  --isolate "$(CURDIR)" \
	  --target "$(or $(TARGET),$(or $(L9_ROOT),$(HOME)/.l9)/program-worktrees/$(CAMPAIGN_ID))" \
	  --base "$(BASE)" \
	  --intent "$(INTENT)" \
	  --l9-root "$(or $(L9_ROOT),$(HOME)/.l9)"

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

## Reconcile Claude Code plugins to the desired state declared in
## environment/agents/adapters/claude-code/plugins.desired.json (imperative
## fallback path — the claude-projection engine is the standing route).
## Usage: make claude-plugins WS=/path/to/repo (defaults to cwd if WS omitted)
claude-plugins:
	bash ops/scripts/setup_claude_code_plugins.sh $(if $(WS),--workspace "$(WS)",)

## One Claude projection engine: skills, commands, rules mount, settings triad,
## hooks, declarative plugins. Writes ~/.l9/claude/projection-receipt.json.
## Usage: make claude-projection WS=/path/to/repo (WS defaults to this clone)
## Check: make claude-projection-check WS=/path/to/repo
claude-projection: claude-skill-registry
	$(PYTHON) ops/scripts/claude_projection.py --root "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" --summary

claude-projection-check:
	$(PYTHON) ops/scripts/claude_projection.py --root "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" --check --summary

## Build the deterministic Claude runtime registry from the canonical skill manifest.
claude-skill-registry:
	$(PYTHON) ops/scripts/build_claude_skill_registry.py --root "$(CURDIR)"

## Heal derived manifests/registries/overrides (rules, skills, commands, PE).
## Idempotent; used by pre-commit and make pr. Never a reason to block make pr alone.
sync-generated:
	$(PYTHON) ops/scripts/sync_generated_artifacts.py --root "$(CURDIR)" --force --check

## Reconcile L9 skills into Claude native user + project discovery paths.
## (Skills-only view of the claude-projection engine.)
claude-skills: claude-skill-registry
	$(PYTHON) ops/scripts/claude_projection.py --root "$(CURDIR)" \
		--workspace "$(WS)" --domains skills --summary --no-receipt

## Read-only registry/frontmatter/hook/routing drift validation.
claude-skills-check:
	$(PYTHON) environment/agents/adapters/claude-code/validate_skill_activation.py

## Behavioral router + reconciliation fixture tests.
claude-skills-test:
	$(PYTHON) environment/agents/adapters/claude-code/tests/test_skill_router.py
	$(PYTHON) environment/agents/adapters/claude-code/tests/test_skill_reconciliation.py
	$(PYTHON) environment/agents/adapters/claude-code/tests/test_cursor_skill_router.py

.PHONY: claude-settings claude-settings-check
.PHONY: claude-install claude-install-check

## Install the Claude Code adapter on THIS machine (CLI / Desktop).
## Runs the exact same installer Web and Mobile reach through
## web/setup.bootstrap.sh -> web/setup.sh, so there is one adapter to maintain:
## locked toolchain from uv.lock, settings triad, skills, MCP front door,
## git excludes, preflight. `claude-settings` below is a component step of this
## target; use claude-install for a full adapter wire-up.
## Usage: make claude-install WS=/path/to/repo   (WS defaults to this clone)
claude-install:
	bash environment/agents/adapters/claude-code/install.sh \
		--governance "$(CURDIR)" --workspace "$(if $(WS),$(WS),$(CURDIR))"

## Read-only: report adapter drift without writing anything.
claude-install-check:
	bash environment/agents/adapters/claude-code/install.sh --check \
		--governance "$(CURDIR)" --workspace "$(if $(WS),$(WS),$(CURDIR))"

## Reconcile Claude settings triad (template → gov .claude → ~/.claude → optional WS).
## Usage: make claude-settings WS=/path/to/repo
## Check: make claude-settings-check WS=/path/to/repo
claude-settings:
	$(PYTHON) ops/scripts/reconcile_claude_settings.py --root "$(CURDIR)" \
		$(if $(WS),--workspace "$(WS)",)

claude-settings-check:
	$(PYTHON) ops/scripts/reconcile_claude_settings.py --root "$(CURDIR)" --check \
		$(if $(WS),--workspace "$(WS)",)

## Canonical Claude environment doctor: full adapter install check (reports drift
## per the health accumulator; --check writes bootstrap-check.json, never the
## session's own receipt) + the structural/contract validator + runtime readiness.
##
## Every step runs. As a plain recipe, make aborted on the first non-zero step,
## so a structural failure took the RUNTIME verdict down with it — and runtime is
## the half that answers "was any of this actually loaded into this session?".
## Exit 5 (documented in CLAUDE.md as "not wired") was therefore unreachable
## whenever anything structural was red, which is exactly when it is worth
## reading. Structural failure still dominates the exit code; it no longer
## suppresses the report.
claude-env:
	@structural=0; runtime=0; \
	$(MAKE) claude-install-check || structural=$$?; \
	$(PYTHON) environment/agents/adapters/claude-code/validate_claude_env.py || structural=$$?; \
	$(PYTHON) ops/secrets/validate_capability_hosts.py || structural=$$?; \
	$(PYTHON) environment/agents/adapters/claude-code/verify_account_env.py || true; \
	$(PYTHON) environment/agents/adapters/claude-code/validate_claude_env.py --runtime || runtime=$$?; \
	if [ $$structural -ne 0 ]; then exit $$structural; fi; \
	exit $$runtime

## Diagnose why the capability plane is unavailable, and whether egress matches
## the posture recorded in docs/NETWORK_POSTURE.md. Both report rather than fail:
## on a hosted surface the primary blocker is platform-issued identity, which no
## change in this repository can resolve (docs/DEGRADED_MODE_CONTRACT.md).
.PHONY: claude-diagnose
claude-diagnose:
	$(PYTHON) ops/secrets/probe_broker.py || true
	$(PYTHON) ops/scripts/probe_network_posture.py

## Fail-closed first-class autonomy family registry (environment/contracts/autonomy).
autonomy-contracts-validate:
	$(PYTHON) ops/scripts/validate_autonomy_contracts.py

## Validate the Claude Code bounded-concurrency autonomy runtime (contracts + unit tests).
autonomy-validate: autonomy-contracts-validate
	$(PYTHON) environment/program-execution/peer_execution/autonomy/validate_autonomy.py

autonomy-validate: autonomy-policy-check

.PHONY: autonomy-policy-embed autonomy-policy-check

## Re-embed autonomy/policies + examples + golden specs into autonomy/policy_loader.py.
## The JSON files are the source of truth; the module is generated (no runtime file I/O).
autonomy-policy-embed:
	$(PYTHON) ops/scripts/regenerate_autonomy_policy_loader.py

## Fail when the embedded policy module drifts from its JSON sources.
autonomy-policy-check:
	$(PYTHON) ops/scripts/regenerate_autonomy_policy_loader.py --check


## L4 local autonomy (stacked local commits → kernels → authorize → push/PR).
l4-status:
	$(PYTHON) ops/autonomy/l4_local.py --workspace "$(WS)" status

l4-begin:
	$(PYTHON) ops/autonomy/l4_local.py --workspace "$(WS)" begin $(if $(CONTRACT_ID),--contract-id "$(CONTRACT_ID)",)

l4-record-kernels:
	$(PYTHON) ops/autonomy/l4_local.py --workspace "$(WS)" record-kernels

l4-authorize:
	$(PYTHON) ops/autonomy/l4_local.py --workspace "$(WS)" authorize-release

# PUBLIC: kernel revision phase. Composes l4-begin / l4-record-kernels / l4-authorize.
# INTERNAL leaves stay callable; agents use make improve.
improve:
	IMPROVE_RECORD="$(IMPROVE_RECORD)" CONTRACT_ID="$(CONTRACT_ID)" \
	PR_BASE="$(PR_BASE)" WS="$(WS)" \
		bash ops/scripts/run_improve.sh

# INTERNAL: read-only publish predicates (branch, commits-ahead, L4 receipt).
pr-preflight:
	PR_BASE="$(PR_BASE)" WS="$(WS)" \
		bash ops/scripts/pr_preflight.sh "$(WS)"


## Validate the multi-agent environment pack: registry naming law, identity uniqueness,
## role catalog, adapter consistency, no committed secrets
agents-env:
	$(PYTHON) environment/agents/tools/validate_agents.py

## Validate PEER_RUNTIME_BINDINGS.yaml against peer-runtime-bindings.schema.json
## (topology SSOT schema gate; full cross-plane rules are peer-execution-validate).
agents-runtime-bindings-validate:
	$(PYTHON) -B environment/agents/tools/validate_executable_peers.py --schema-only

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
	$(PYTHON) ops/scripts/validate_precommit_hook_contract.py

## Fail if any script/rule/hook hardcodes a /Users or /home path instead of $$HOME
path-lint:
	bash ops/scripts/validate_governance_no_hardcoded_paths.sh

## Fail if active surfaces teach retired Dropbox SSOT or L9_MEMORY_HTTP side doors
legacy-doctrine-residue:
	$(PYTHON) ops/scripts/validate_legacy_doctrine_residue.py

## INTERNAL: full-tree of the same hook catalog `make pr-check` already runs
## on changed files. Not a public gate. Git `pre-commit install` is not required.
## Full-tree pre-commit (nightly / intentional). Not used by `make pr`.
precommit:
	@command -v pre-commit >/dev/null 2>&1 || { echo "FAIL: pre-commit CLI missing (INTERNAL leaf of make pr-check). pipx install pre-commit — do not run pre-commit install"; exit 1; }
	pre-commit run --all-files

## INTERNAL leaf of `make pr-check` (changed-files hook catalog).
## Changed-files pre-commit for PR velocity.
## Skips machine-local symlinks-check unless WS is a local governance SSOT clone
## (skills/AUTONOMY_MANIFEST.yaml + rules/RULES-MANIFEST.yaml present).
precommit-repo:
	PR_BASE="$(PR_BASE)" bash ops/scripts/run_pr_precommit.sh "$(WS)"

## Commit + rebase + push this clone to origin/main (same as sessionEnd hook)
backup:
	bash ops/scripts/backup_to_github.sh

## Gate push behind changed-file precommit-repo (not --all-files). Corpus = make precommit / pr-full.
push: precommit-repo backup

## Check Graphiti tunnel + MCP tool-plane health (degraded MCP is expected pre-full-wiring)
graphiti-health: venv
	$(PYTHON) ops/graphiti/graphiti_memory_client.py health

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
	xargs $(RUFF) check <"$$py"; \
	xargs $(RUFF) format --check <"$$py"

lint-ruff-full: venv
	$(RUFF) check .
	$(RUFF) format --check .

## mypy via the locked venv. Advisory in CI today (TODO.md mypy debt); still
## useful as a local signal. `make lint` keeps it blocking for intentional debt work.
lint-mypy: venv
	$(MYPY) . --show-error-codes --pretty --ignore-missing-imports

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
	$(PYTHON) ops/scripts/scratch_hold.py --workspace "$(or $(WS),$(CURDIR))" restore --all

scratch-hold-status:
	$(PYTHON) ops/scripts/scratch_hold.py --workspace "$(or $(WS),$(CURDIR))" status

pr-check:
	PR_BASE="$(PR_BASE)" PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_MYPY_STRICT="$(PR_MYPY_STRICT)" WS="$(WS)" \
		bash ops/scripts/run_pr_gate.sh

# Velocity path: run_pr_gate.sh owns precommit (run_pr_precommit.sh) once.
# Do not re-add a Make prereq that double-runs precommit-repo on pr-check or pr.
# capability-contract is domain-gated inside the gate; corpus lives on pr-full.

## Gate → open/reuse GitHub PR → subscribe → emit l9-pr-remediation agent handoff.
## `make pr` / `make PR` / `make Pr` / `make pR` are equivalent (case-insensitive).
## Requires a feature branch with commits ahead of PR_BASE.
## OPEN_PR=0 → gate only. PR_REMEDIATE=0 → open+subscribe without agent spawn marker.
pr: pr-preflight pr-check
	@if [ "$(OPEN_PR)" = "1" ]; then \
		PR_OVERLAP="$(PR_OVERLAP)" PR_STACK="$(PR_STACK)" \
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

# Additive: validators skipped on the velocity path (make pr / pr-check).
.PHONY: pr-full-corpus
pr-full: capability-contract-validate
pr-full: pr-full-corpus
pr-full-corpus: venv
	$(PYTHON) ops/scripts/validate_legacy_doctrine_residue.py
	$(PYTHON) ops/scripts/validate_workflow_action_pins.py
	$(PYTHON) ops/scripts/validate_governance_contract_surface.py
	$(PYTHON) ops/scripts/validate_git_denial_residue.py

## Read-only drift check: does the committed rules/RULES-MANIFEST.* still match the
## live rules/*.mdc corpus? Writes nothing. Exit 1 (with a findings list) on drift.
rules-validate:
	$(PYTHON) ops/scripts/validate_rules_manifest.py --root "$(CURDIR)"

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
	$(PYTHON) integrity/hash-verifier.py --no-repair

## Seed/refresh the integrity baseline: snapshot every governed file's sha256 + full
## base64 content into integrity/manifest-lock.json. Deliberate, high-footprint action
## (embeds file contents) — run intentionally and review the (large) diff. Not wired
## into any hook/CI. The self-heal auto-repair mode is intentionally NOT exposed as a
## target because it overwrites working-tree files from the baseline.
integrity-snapshot:
	$(PYTHON) integrity/hash-verifier.py --snapshot

## Sync ops/secrets/openclaw-igorbot.registry.yaml from AWS Secrets Manager (refs/key names only).
secrets-sync:
	@$(MAKE) venv
	$(PYTHON) ops/secrets/sync_secrets_registry.py

## Resolve a secret ref with --check (never prints the value). Example:
##   make secrets-check REF='openclaw-igorbot/github#token'
REF ?= openclaw-igorbot/github#token
secrets-check:
	@$(MAKE) venv
	$(PYTHON) ops/secrets/resolve_secret.py --ref "$(REF)" --check

## Validate the zero-static-secret capability contract: no credential may be
## assigned in an agent surface environment, and no LLM-facing code may reach for
## raw secret material unless explicitly marked trusted-operator-only.
capability-contract-validate:
	$(PYTHON) ops/secrets/validate_capability_contract.py

## Report which named capabilities this surface can use. Never resolves a secret.
##   make capability-check REQUIRE=sonar.read_issues,graphiti.query
REQUIRE ?=
capability-check:
	@bash ops/secrets/bootstrap_agent_env.sh --check \
		--surface "$${L9_GOVERNANCE_SURFACE:-unknown}" \
		$(if $(REQUIRE),--require-capabilities "$(REQUIRE)",)

## Broker posture (trusted side): boundary isolation + workload identity.
capability-broker-preflight:
	$(PYTHON) ops/secrets/capability_broker.py preflight

## Run capability broker locally for CLI surfaces.
## Binds to localhost:8787, authenticates to Infisical via AWS bootstrap.
## Set L9_CAPABILITY_BROKER_URL=http://localhost:8787 in your shell.
## For cloud surfaces: deploy to K8s with ops/secrets/k8s/broker-deployment.yaml
broker-serve:
	@echo "Starting L9 capability broker on http://localhost:8787"
	@echo "Set: export L9_CAPABILITY_BROKER_URL=http://localhost:8787"
	$(PYTHON) ops/secrets/capability_broker.py serve --audience cli_local --port 8787 --bind 127.0.0.1

## Install optional UI-operator deps (playwright + boto3). Not required for make pr.
## After this: playwright install
ui-operator-sync:
	uv sync --extra ui-operator

# PROGRAM_EXECUTION_ADAPTER_LAYER_V1
PE_ROOT := environment/program-execution
.PHONY: program-execution-core-validate program-execution-adapters 	program-execution-conformance program-execution-probe

program-execution-core-validate:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B $(PE_ROOT)/core/scripts/validate_pair.py 		$(PE_ROOT)/core --mode template
	$(MAKE) program-execution-campaign-schema
	$(MAKE) program-execution-campaign-compile
	$(MAKE) program-execution-campaign-promotion

program-execution-adapters:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B 		$(PE_ROOT)/scripts/validate_execution_adapters.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B $(PE_ROOT)/scripts/validate_thin_providers.py

program-execution-conformance: autonomy-contracts-validate
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B 		$(PE_ROOT)/scripts/run_conformance.py
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B $(PE_ROOT)/scripts/validate_manifest.py
	$(MAKE) program-execution-controller-tests

program-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B 		$(PE_ROOT)/scripts/probe_execution_adapters.py

# PE execution certification: the two-task smoke campaign runs a real worker
# end to end, then again after a simulated interruption. This is the health
# check to run when PE "prepares forever but never writes code".
.PHONY: pe-smoke
pe-smoke:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m pytest -q 		$(PE_ROOT)/scripts/tests/test_pe_smoke_campaign.py 		$(PE_ROOT)/scripts/tests/test_launchability.py 		$(PE_ROOT)/core/program-execution-controller-template/scripts/tests/test_verify_lifecycle.py 		$(PE_ROOT)/core/program-execution-controller-template/scripts/tests/test_execution_recovery.py

AGENTS_TOOLS := environment/agents/tools
.PHONY: peer-execution-validate peer-execution-probe peer-execution-conformance
.PHONY: agents-runtime-bindings-validate

# Executable Peer Contract v1 — structural cross-registry gate (E1-E15):
# agent_registry.yaml execution bindings <-> program-execution adapters +
# registry <-> canonical autonomy provider. validate_executable_peers.py.
# v2 also gates PEER_RUNTIME_BINDINGS.yaml topology SSOT (see agents-runtime-bindings-validate).
peer-execution-validate:
	$(PYTHON) -B $(AGENTS_TOOLS)/validate_executable_peers.py

# Binding-level readiness probe. Emits per-(agent,surface,adapter) receipts
# under $$HOME/.l9/programs/_peer-readiness/ and fails if any enabled agent
# has no READY binding. Runtime/session-scoped availability gate.
# Receipts also land under $$L9_RUNTIME_ROOT/agents/readiness/ (default ~/.l9/agents/readiness/).
peer-execution-probe:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B \
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
	$(PYTHON) -m pytest environment/agents/deployment/tests -q
agents-results-validate:
	$(PYTHON) -m pytest environment/agents/results/tests environment/agents/lifecycle/tests -q
agents-data-validate:
	$(PYTHON) -m pytest environment/agents/generated-data/ingress/tests -q
agents-runtime-probe:
	$(PYTHON) environment/agents/readiness/probe_runtime.py

# DeepSeek V4 Pro launcher for Claude Code (env-routed; no keys in git)
.PHONY: claude-deepseek claude-deepseek-verify
claude-deepseek:
	./scripts/claude-deepseek.sh

claude-deepseek-verify:
	./scripts/verify-routing.sh

.PHONY: program-execution-campaign-schema program-execution-campaign-compile
.PHONY: program-execution-campaign-promotion
.PHONY: program-execution-controller-tests
## Campaign promotion must be mechanically valid and portable before it lands.
program-execution-campaign-promotion:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B $(PE_ROOT)/scripts/validate_campaign_promotion.py
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B -m unittest \
		$(PE_ROOT)/scripts/tests/test_validate_campaign_promotion.py

program-execution-campaign-schema:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B -m unittest \
		$(PE_ROOT)/conformance/test_campaign_source_schema.py

program-execution-campaign-compile:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B -m unittest \
		$(PE_ROOT)/scripts/tests/test_compile_campaign_source.py

.PHONY: program-execution-campaign-brief
program-execution-campaign-brief:
	PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(PE_ROOT) $(PYTHON) -B -m unittest \
		$(PE_ROOT)/scripts/tests/test_run_campaign.py \
		$(PE_ROOT)/scripts/tests/test_replay_campaign.py \
		$(CURDIR)/skills/l9-pe-campaign-activate/scripts/test_compile_brief.py

program-execution-controller-tests:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -B -m unittest discover \
		-s $(PE_ROOT)/core/program-execution-controller-template/scripts/tests \
		-p 'test_*.py'

.PHONY: rules-check
## Cursor-native rules frontmatter + always-apply ratchet (docs/rules-standard.md).
rules-check:
	$(PYTHON) ops/scripts/check_rules_standard.py

.PHONY: rules-contract-shadow rules-contract-check
## Foundation shadow: stdout only. Does not write rules or census files.
rules-contract-shadow:
	$(PYTHON) ops/contracts/build_rules.py census
rules-contract-check:
	$(PYTHON) ops/contracts/build_rules.py check

.PHONY: skills-check
## Cursor-native skill frontmatter + discovery-footprint ratchet (docs/skills-standard.md).
skills-check:
	$(PYTHON) ops/scripts/check_skills_standard.py

.PHONY: hygiene hygiene-fix
## RB-HK-001 repository housekeeping gate.
hygiene:
	$(PYTHON) tools/check_repo_hygiene.py

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

.PHONY: wip-hygiene wip-inventory
## Dated WIP corpus on main: file loose drops, inventory, high-evidence prune.
wip-hygiene:
	$(PYTHON) ops/scripts/wip_corpus.py hygiene --root "$(CURDIR)"

wip-inventory:
	$(PYTHON) ops/scripts/wip_corpus.py inventory --root "$(CURDIR)"

# PUSH_ONLY=1 make pr: gate + L4 + push; skip gh pr create (open_pr_after_gate.sh).
# OPEN_PR=0 make pr remains gate-only (script is not invoked). Do not rewrite the
# existing pr recipe — GNU Make 3.81 exports PUSH_ONLY from the invoking env.
PUSH_ONLY ?= 0

.PHONY: ff
## In-place /ff catch-up (l9-repo-sync). Parks unique work. Never activate_fresh. Never stash -u.
ff:
	CURSOR_GOVERNANCE_DIR="$(CURDIR)" bash skills/l9-repo-sync/scripts/ff.sh

# L9_DISPATCHER_FACADE_V1
# Single classification authority for the thin `l9` cross-repo facade
# (environment/agents/adapters/claude-code/bin/l9). A CONSUMER_SAFE target is
# WS-aware: it acts on the consumer workspace ($(WS)) and never mutates
# Governance by path confusion (Governance work uses $(CURDIR) via `make -C`).
# The dispatcher exposes exactly these; every other target is GOVERNANCE_ONLY
# and must be run directly with `make -C "$$HOME/.cursor-governance" <target>`.
# See docs/L9_DISPATCHER.md. Keep in sync with any new WS-aware target.
L9_CONSUMER_SAFE_TARGETS := start pr pr-check pr-security improve wiring-check \
  claude-projection claude-projection-check claude-skills claude-settings \
  claude-settings-check claude-install claude-install-check claude-plugins \
  claude-env ide-profile l4-status l4-begin l4-record-kernels l4-authorize \
  clean workspace-clean

.PHONY: l9-consumer-safe-list l9-dispatcher-install l9-dispatcher-check
## Print the CONSUMER_SAFE target allowlist (the dispatcher's classification source).
l9-consumer-safe-list:
	@echo $(L9_CONSUMER_SAFE_TARGETS)

## Install/reconcile the thin l9 dispatcher to $$HOME/.local/bin/l9.
l9-dispatcher-install:
	bash "$(CURDIR)/ops/scripts/install_l9_dispatcher.sh"

## Report l9 dispatcher drift without writing anything.
l9-dispatcher-check:
	bash "$(CURDIR)/ops/scripts/install_l9_dispatcher.sh" --check

.PHONY: claude-readiness
## Emit + print the machine-readable Claude readiness receipt (schema
## l9.claude-readiness.v1 → ~/.l9/claude/readiness-receipt.json). Truthful:
## a missing/skipped required check, an unloaded MCP, a TCP-only Graphiti, or a
## stale governance SHA cannot report READY. Usage: make claude-readiness WS=/path
claude-readiness:
	$(PYTHON) ops/scripts/emit_claude_readiness.py --root "$(CURDIR)" \
		--workspace "$(if $(WS),$(WS),$(CURDIR))" --read
