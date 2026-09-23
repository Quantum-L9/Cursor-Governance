L9_TARGETS += \
	autonomy-contracts-validate \
	autonomy-validate \
	autonomy-policy-embed \
	autonomy-policy-check \
	backup-gate-test \
	repo-write-lock-test \
	precommit-hook-contract \
	path-lint \
	legacy-doctrine-residue \
	precommit \
	precommit-repo \
	lint-ruff \
	lint-ruff-full \
	lint-mypy \
	lint \
	uv-lock-check \
	test \
	test-ci-parity \
	corpus-reachability \
	rules-corpus-audit \
	rules-validate \
	rules-stabilize \
	rules-check \
	rules-contract-shadow \
	rules-contract-check \
	skills-check \
	hygiene \
	hygiene-fix
# ---------------------------------------------------------------------------
# Architecture / quality
# ---------------------------------------------------------------------------
autonomy-contracts-validate:
	$(PYTHON) ops/scripts/validate_autonomy_contracts.py
autonomy-validate: autonomy-contracts-validate
	$(PYTHON) \
		environment/program-execution/peer_execution/autonomy/validate_autonomy.py
autonomy-validate: autonomy-policy-check
autonomy-policy-embed:
	$(PYTHON) ops/scripts/regenerate_autonomy_policy_loader.py
autonomy-policy-check:
	$(PYTHON) ops/scripts/regenerate_autonomy_policy_loader.py --check
backup-gate-test:
	bash ops/scripts/test_backup_gate.sh
repo-write-lock-test:
	bash ops/scripts/test_repo_write_lock.sh
precommit-hook-contract:
	$(PYTHON) ops/scripts/validate_precommit_hook_contract.py
path-lint:
	bash ops/scripts/validate_governance_no_hardcoded_paths.sh
legacy-doctrine-residue:
	$(PYTHON) ops/scripts/validate_legacy_doctrine_residue.py
# Intentional full-tree hook catalog.
# This repository does not require `pre-commit install`.
precommit:
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "FAIL: pre-commit CLI missing. pipx install pre-commit — do not run pre-commit install"; \
		exit 1; \
	}
	pre-commit run --all-files
# Changed-file hook catalog used by the publication gate and remediation.
precommit-repo:
	PR_BASE="$(PR_BASE)" \
		bash ops/scripts/run_pr_precommit.sh "$(WS)"
# Hard Ruff gate on changed Python files only.
lint-ruff: venv
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
	xargs $(RUFF) check <"$$py"; \
	xargs $(RUFF) format --check <"$$py"
lint-ruff-full: venv
	$(RUFF) check .
	$(RUFF) format --check .
lint-mypy: venv
	$(MYPY) . \
		--show-error-codes \
		--pretty \
		--ignore-missing-imports
lint: lint-ruff-full lint-mypy
uv-lock-check:
	@if [ -f uv.lock ]; then \
		uv lock --check; \
	else \
		echo "OK: no uv.lock present, skipping"; \
	fi
test: venv
	bash ops/scripts/run_pytest_suites.sh --tb=short -q
# CI-parity Git-worktree validation with no developer Git identity inherited.
test-ci-parity:
	@parity_home="$$(mktemp -d)" || { \
		echo "test-ci-parity: mktemp failed" >&2; \
		exit 1; \
	}; \
	[ -n "$$parity_home" ] && [ -d "$$parity_home" ] || { \
		echo "test-ci-parity: refusing — scratch HOME unresolved" >&2; \
		exit 1; \
	}; \
	for key in user.name user.email; do \
		if val="$$(HOME="$$parity_home" git config --get "$$key" 2>/dev/null)"; then \
			echo "test-ci-parity: NOT at parity — git still resolves $$key=$$val" >&2; \
			echo "  a system-level gitconfig is leaking an identity CI would not have." >&2; \
			rm -rf -- "$$parity_home"; \
			exit 1; \
		fi; \
	done; \
	echo "--- CI parity: HOME=$$parity_home, no git identity resolvable ---"; \
	rc=0; \
	HOME="$$parity_home" \
		$(MAKE) \
			program-execution-campaign-brief \
			program-execution-controller-tests \
			|| rc=$$?; \
	rm -rf -- "$$parity_home"; \
	exit $$rc
corpus-reachability: venv
	$(PYTHON) ops/scripts/audit_corpus_reachability.py
rules-corpus-audit: venv
	$(PYTHON) ops/scripts/audit_rules_corpus.py
rules-validate:
	$(PYTHON) ops/scripts/validate_rules_manifest.py \
		--root "$(CURDIR)"
rules-stabilize:
	bash ops/scripts/run_rules_stabilization_validation.sh
rules-check:
	$(PYTHON) ops/scripts/check_rules_standard.py
rules-contract-shadow:
	$(PYTHON) ops/contracts/build_rules.py census
rules-contract-check:
	$(PYTHON) ops/contracts/build_rules.py check
skills-check:
	$(PYTHON) ops/scripts/check_skills_standard.py
hygiene:
	$(PYTHON) tools/check_repo_hygiene.py
hygiene-fix:
	@echo "See WIP/housekeeping-pack/RUNBOOK.md Section 4"
