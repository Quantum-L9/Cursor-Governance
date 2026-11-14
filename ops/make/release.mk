L9_TARGETS += \
	release \
	release-declaration-check
# ---------------------------------------------------------------------------
# Release — the sibling of `make pr` (docs/L9_RELEASE.md).
#
# Releases the workspace repository from a clean origin/<default> commit as
# declared by <repo>/.l9/release.json (schema l9.release/v1):
#
#   l9 release [VERSION=X.Y.Z] [DRY_RUN=1]
#   make -C "$$HOME/.cursor-governance" release WS="$$(pwd)" [VERSION=X.Y.Z] [DRY_RUN=1]
#
# DRY_RUN=1 runs declaration, preflight, the make-v1 gate and the reproducible
# double build, then stops before any tag or Release. Publication requires the
# operator's publish-path breakglass receipt naming the exact tag and commit;
# this target never force-pushes and never publishes to npm or PyPI. Receipt:
# <repo>/.l9/release/release-receipt.json.
# ---------------------------------------------------------------------------
VERSION ?=
DRY_RUN ?= 0
release:
	$(PYTHON) ops/scripts/l9_release.py \
		--workspace "$(WS)" \
		$(if $(VERSION),--version "$(VERSION)",) \
		$(if $(filter 1,$(DRY_RUN)),--dry-run,)
# Read-only: validate the workspace's .l9/release.json against l9.release/v1.
release-declaration-check:
	$(PYTHON) ops/scripts/release_declaration.py --workspace "$(WS)"
