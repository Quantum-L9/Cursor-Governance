#!/usr/bin/env python3
"""Compatibility wrapper for the skill-owned AST module README generator.

Implementation lives in skills/l9-update-agent-docs/scripts/generate_module_readmes.py.
This module re-exports that API so DAG, tests, and existing CLI paths keep working.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SKILL_SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "l9-update-agent-docs" / "scripts"
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))

from generate_module_readmes import (  # noqa: E402
    CONFIG_PATH,
    GENERATED_MARKER,
    LEGACY_HANDWRITTEN_RE,
    README_TEMPLATE,
    ROOT_README,
    ClassInfo,
    FunctionInfo,
    ModuleFacts,
    classify_readme,
    discover_module_paths,
    extract_subsystem_facts,
    generate_readme,
    is_generated,
    is_handwritten,
    is_legacy_generated,
    is_root_readme,
    list_subsystems,
    load_config,
    main,
    report_gaps,
    resolve_repo_root,
    resolve_under_root,
    select_targets,
    spec_for_path,
    validate_sections,
    validate_subsystem_config,
    write_missing_module_readmes,
    write_readme,
)

__all__ = [
    "CONFIG_PATH",
    "GENERATED_MARKER",
    "LEGACY_HANDWRITTEN_RE",
    "README_TEMPLATE",
    "ROOT_README",
    "ClassInfo",
    "FunctionInfo",
    "ModuleFacts",
    "classify_readme",
    "discover_module_paths",
    "extract_subsystem_facts",
    "generate_readme",
    "is_generated",
    "is_handwritten",
    "is_legacy_generated",
    "is_root_readme",
    "list_subsystems",
    "load_config",
    "main",
    "report_gaps",
    "resolve_repo_root",
    "resolve_under_root",
    "select_targets",
    "spec_for_path",
    "validate_sections",
    "validate_subsystem_config",
    "write_missing_module_readmes",
    "write_readme",
]

if __name__ == "__main__":
    raise SystemExit(main())
