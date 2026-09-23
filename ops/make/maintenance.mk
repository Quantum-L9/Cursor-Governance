CLEAN_PYC_MODE ?= apply
CLEAN_MODE ?= apply
CLEAN_REMOTE ?= 1
L9_TARGETS += \
	sync \
	wiring-check \
	symlinks-check \
	symlinks-install \
	backup \
	push \
	clean \
	workspace-clean \
	clean-pyc \
	wip-hygiene \
	wip-inventory \
	ff \
	ff-clone \
	ff-ssot
# ---------------------------------------------------------------------------
# Repository / workspace maintenance
# ---------------------------------------------------------------------------
sync:
	bash ops/scripts/governance_sync.sh
wiring-check:
	bash ops/scripts/check_governance_wiring.sh "$(WS)"
symlinks-check:
	bash ops/scripts/validate_governance_symlinks.sh
symlinks-install:
	bash ops/scripts/setup_workspace_symlinks.sh
backup:
	bash ops/scripts/backup_to_github.sh
push: precommit-repo backup
clean workspace-clean:
	CLEAN_MODE="$(CLEAN_MODE)" \
	CLEAN_REMOTE="$(CLEAN_REMOTE)" \
	PR_BASE="$(PR_BASE)" \
	WS="$(WS)" \
		bash "$(CURDIR)/ops/scripts/run_workspace_clean.sh"
clean-pyc:
	CLEAN_PYC_MODE="$(CLEAN_PYC_MODE)" \
		bash "$(CURDIR)/ops/scripts/clean_pyc.sh" "$(WS)"
wip-hygiene:
	$(PYTHON) ops/scripts/wip_corpus.py \
		hygiene \
		--root "$(CURDIR)"
wip-inventory:
	$(PYTHON) ops/scripts/wip_corpus.py \
		inventory \
		--root "$(CURDIR)"
ff:
	CURSOR_GOVERNANCE_DIR="$(CURDIR)" \
		bash skills/l9-repo-sync/scripts/ff.sh
ff-clone:
	bash skills/l9-repo-sync/scripts/ff.sh --clone
ff-ssot:
	bash skills/l9-repo-sync/scripts/ff.sh --ssot
