L9_TARGETS += \
	l4-status \
	l4-begin \
	l4-record-kernels \
	l4-authorize \
	kernel-precommit \
	improve \
	pr-preflight \
	pr-security \
	pr-security-full \
	scratch-hold-restore \
	scratch-hold-status \
	pr \
	PR \
	Pr \
	pR \
	pr-full \
	pr-full-corpus
# ---------------------------------------------------------------------------
# L4 / kernel lifecycle
# ---------------------------------------------------------------------------
l4-status:
	$(PYTHON) ops/autonomy/l4_local.py \
		--workspace "$(WS)" \
		status
l4-begin:
	$(PYTHON) ops/autonomy/l4_local.py \
		--workspace "$(WS)" \
		begin \
		$(if $(CONTRACT_ID),--contract-id "$(CONTRACT_ID)",)
l4-record-kernels:
	@test -n "$(RA)" -a -n "$(VR)" || { \
		echo "ERROR: RA and VR are required — e.g. make l4-record-kernels RA=passed VR=passed"; \
		echo "  Record what you observed after applying both kernels. Do not use this to APPLY them."; \
		exit 2; \
	}
	$(PYTHON) ops/autonomy/l4_local.py \
		--workspace "$(WS)" \
		record-kernels \
		--recursive-alignment "$(RA)" \
		--validate-repair "$(VR)"
l4-authorize:
	$(PYTHON) ops/autonomy/l4_local.py \
		--workspace "$(WS)" \
		authorize-release
kernel-precommit:
	$(PYTHON) ops/autonomy/kernel_gate.py \
		precommit \
		--workspace "$(WS)"
improve:
	IMPROVE_RECORD="$(IMPROVE_RECORD)" \
	CONTRACT_ID="$(CONTRACT_ID)" \
	PR_BASE="$(PR_BASE)" \
	WS="$(WS)" \
		bash ops/scripts/run_improve.sh
# ---------------------------------------------------------------------------
# Publication
# ---------------------------------------------------------------------------
# Internal read-only publish predicates.
pr-preflight:
	PR_BASE="$(PR_BASE)" \
	WS="$(WS)" \
	PR_STACK="$(PR_STACK)" \
		bash ops/scripts/pr_preflight.sh "$(WS)"
pr-security:
	PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_BASE="$(PR_BASE)" \
		bash ops/scripts/run_pr_security.sh "$(WS)"
pr-security-full:
	PR_SECURITY_PROFILE=full \
	PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_BASE="$(PR_BASE)" \
		bash ops/scripts/run_pr_security.sh "$(WS)"
scratch-hold-restore:
	$(PYTHON) ops/scripts/scratch_hold.py \
		--workspace "$(or $(WS),$(CURDIR))" \
		restore \
		--all
scratch-hold-status:
	$(PYTHON) ops/scripts/scratch_hold.py \
		--workspace "$(or $(WS),$(CURDIR))" \
		status
# `make pr` is the one publication ceremony.
#
# Phase 1: preflight.
# Phase 2: changed-file gate.
# Phase 3: publish when OPEN_PR=1.
#
# OPEN_PR=0 executes phases 1+2 and stops before GitHub publication.
pr: pr-preflight
	PR_BASE="$(PR_BASE)" \
	PR_SECURITY_ADVISORY="$(PR_SECURITY_ADVISORY)" \
	PR_MYPY_STRICT="$(PR_MYPY_STRICT)" \
	WS="$(WS)" \
	PR_STACK="$(PR_STACK)" \
		bash ops/scripts/run_pr_gate.sh
	@if [ "$(OPEN_PR)" = "1" ]; then \
		PR_OVERLAP="$(PR_OVERLAP)" \
		PR_STACK="$(PR_STACK)" \
		PR_BASE="$(PR_BASE)" \
		PR_REMEDIATE="$(PR_REMEDIATE)" \
		GOV_ROOT="$(CURDIR)" \
			bash ops/scripts/open_pr_after_gate.sh "$(WS)"; \
	else \
		echo "OPEN_PR=0 — skipped GitHub PR open (gate already PASS)"; \
	fi
# Complete two-letter case surface; no dynamic shell remapping required.
PR Pr pR: pr
# GNU Make 3.81 requires exported target-specific variables for recipe shells.
pr: export PR_EARLY_OVERLAP = 1
# Snapshot rather than recursively self-reference on GNU Make 3.81.
precommit-repo: export PR_STACK := $(PR_STACK)
# ---------------------------------------------------------------------------
# Full local gate
# ---------------------------------------------------------------------------
pr-full: \
	venv \
	precommit \
	lint-ruff-full \
	uv-lock-check \
	test \
	rules-validate
	@echo "NOTE: corpus security remains nightly CI; pr-full runs local full lint/test/precommit"
	@echo "RESULT: PASS — full local gate (lint/test/precommit)"
pr-full: capability-contract-validate
pr-full: pr-full-corpus
pr-full: pr-security-full
pr-full-corpus: venv
	$(PYTHON) ops/scripts/validate_legacy_doctrine_residue.py
	$(PYTHON) ops/scripts/validate_workflow_action_pins.py
	$(PYTHON) ops/scripts/validate_governance_contract_surface.py
	$(PYTHON) ops/scripts/validate_git_denial_residue.py
	$(PYTHON) ops/scripts/audit_corpus_reachability.py
	$(PYTHON) ops/scripts/audit_rules_corpus.py
