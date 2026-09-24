# Cursor-Governance capability graph.
#
# Root ownership:
#   - shared variables and locked toolchain
#   - domain-fragment composition
#   - complete target registry
#   - single CONSUMER_SAFE classification authority
#   - help / introspection
#
# ops/make/*.mk owns domain composition.
# Scripts and Python modules own implementation.
.DEFAULT_GOAL := help
# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------
# Workspace a WS-aware capability acts on.
# Consumer:
#   make -C "$$HOME/.cursor-governance" <target> WS="$$(pwd)"
WS ?= $(CURDIR)
# ---------------------------------------------------------------------------
# Publication policy
# ---------------------------------------------------------------------------
PR_MYPY_STRICT ?= 0
PR_SECURITY_ADVISORY ?= 0
# Comparison ref for changed-file resolution.
PR_BASE ?= origin/main
# Publish against PR_BASE by default. Stacking is an explicit opt-in
# (`PR_STACK=auto make pr`) because ambiguous sibling chains block.
# Do not export globally; gate code controls propagation into tests.
PR_STACK ?=
# OPEN_PR=0 make pr = governed gate-only diagnosis.
OPEN_PR ?= 1
# After publication, emit the remediation handoff unless explicitly disabled.
PR_REMEDIATE ?= 1
# make improve IMPROVE_RECORD=1 records observed kernel results.
IMPROVE_RECORD ?= 0
# ---------------------------------------------------------------------------
# Locked governance toolchain
# ---------------------------------------------------------------------------
PYTHON := $(CURDIR)/.venv/bin/python
RUFF := $(CURDIR)/.venv/bin/ruff
MYPY := $(CURDIR)/.venv/bin/mypy
# One runtime root; accept the established alternate spelling.
L9_ROOT ?= $(or $(L9_RUNTIME_ROOT),$(HOME)/.l9)
export PYTHON
# ---------------------------------------------------------------------------
# Mechanical capability registry
#
# L9_TARGETS is inventory, not policy.
# Domain fragments append every capability they own.
# ---------------------------------------------------------------------------
L9_TARGETS := \
	help \
	targets \
	consumer-targets \
	l9-consumer-safe-list
MAKE_FRAGMENTS := \
	ops/make/core.mk \
	ops/make/quality.mk \
	ops/make/publish.mk \
	ops/make/adapters.mk \
	ops/make/program-execution.mk \
	ops/make/security.mk \
	ops/make/memory.mk \
	ops/make/maintenance.mk \
	ops/make/internal.mk
_MISSING_MAKE_FRAGMENTS := \
	$(filter-out $(wildcard $(MAKE_FRAGMENTS)),$(MAKE_FRAGMENTS))
ifneq ($(strip $(_MISSING_MAKE_FRAGMENTS)),)
$(error missing required Make fragments: $(_MISSING_MAKE_FRAGMENTS))
endif
include $(MAKE_FRAGMENTS)
# ---------------------------------------------------------------------------
# Dispatcher classification authority
#
# This remains the ONE CONSUMER_SAFE registry queried by the thin `l9`
# dispatcher. Domain fragments do not duplicate or extend this policy.
#
# There is deliberately no gate-only secondary target. Diagnose publication
# through:
#
#   OPEN_PR=0 make pr
#   OPEN_PR=0 l9 pr
# ---------------------------------------------------------------------------
L9_CONSUMER_SAFE_TARGETS := \
	start \
	pr \
	pr-security \
	improve \
	wiring-check \
	claude-projection \
	claude-projection-check \
	claude-skills \
	claude-settings \
	claude-settings-check \
	claude-install \
	claude-install-check \
	claude-plugins \
	claude-env \
	ide-profile \
	l4-status \
	l4-begin \
	l4-record-kernels \
	l4-authorize \
	clean \
	workspace-clean
# Every registered capability is command-like.
.PHONY: $(sort $(L9_TARGETS))
# ---------------------------------------------------------------------------
# Locked-interpreter prerequisite
#
# Every registered capability except help / venv / gov-python passes the
# governance interpreter probe.
#
# Deriving this from L9_TARGETS rather than MAKECMDGOALS matters: an unknown
# user goal must remain unknown and must not become an implicit Make rule merely
# because the interpreter probe was attached to it.
# ---------------------------------------------------------------------------
_GOV_PYTHON_FREE := help venv gov-python
_GOV_PYTHON_GATED_TARGETS := \
	$(filter-out $(_GOV_PYTHON_FREE),$(L9_TARGETS))
$(sort $(_GOV_PYTHON_GATED_TARGETS)): gov-python
# ---------------------------------------------------------------------------
# Introspection
# ---------------------------------------------------------------------------
help:
	@echo "Cursor-Governance capability graph"
	@echo
	@echo "Targets:"
	@printf '  %s\n' $(sort $(filter-out help targets consumer-targets l9-consumer-safe-list,$(L9_TARGETS)))
	@echo
	@echo "CONSUMER_SAFE:"
	@printf '  %s\n' $(L9_CONSUMER_SAFE_TARGETS)
	@echo
	@echo 'Consumer:  make -C "$$HOME/.cursor-governance" <target> WS="$$(pwd)"'
	@echo 'Dispatcher: l9 <consumer-safe-target> [VAR=value ...]'
	@echo 'Diagnose:   OPEN_PR=0 make pr'
targets:
	@printf '%s\n' $(sort $(L9_TARGETS))
consumer-targets:
	@printf '%s\n' $(L9_CONSUMER_SAFE_TARGETS)
# Machine-facing dispatcher contract. Keep whitespace-delimited on one line.
l9-consumer-safe-list:
	@echo $(L9_CONSUMER_SAFE_TARGETS)
