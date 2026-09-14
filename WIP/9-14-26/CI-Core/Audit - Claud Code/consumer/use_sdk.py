"""External consumer of the l9-ci SDK wheel — public API only."""
from pathlib import Path
from l9_ci import __version__
from l9_ci.providers import build_default_registry
from l9_ci.repository import enumerate_repository_files
from l9_ci.artifacts.validator import validate_bundle
from l9_ci.capabilities import detect_repository_capabilities

print("SDK version via wheel:", __version__)
reg = build_default_registry()
print("provider ids:", sorted(reg.provider_ids()))
files = enumerate_repository_files(Path("."), include_untracked=False)
print("enumerated consumer files:", len(files))
caps = detect_repository_capabilities(root=Path("."))
print("detected capabilities:", sorted(caps.languages))
