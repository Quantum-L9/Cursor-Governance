"""
README Pipeline Session DAG
===========================

Systematic workflow for generating and validating subsystem READMEs.

Based on the 2026-01-25 session workflow:
1. Gap analysis - identify missing subsystems
2. Config enrichment - add missing entries to readme_config.yaml
3. Template update - enhance README_TEMPLATE if needed
4. Generate - run generator script
5. Validate - verify output
6. Report - summarize results

Version: 1.0.0
"""

# ============================================================================
__dora_meta__ = {
    "component_name": "Readme Pipeline Dag",
    "module_version": "1.0.0",
    "created_by": "Igor Beylin",
    "created_at": "2026-01-26T11:14:45Z",
    "updated_at": "2026-01-31T22:21:54Z",
    "layer": "operations",
    "domain": "workflows",
    "module_name": "readme_pipeline_dag",
    "type": "utility",
    "status": "active",
    "integrates_with": {
        "api_endpoints": [],
        "datasources": [],
        "memory_layers": [],
        "imported_by": ["workflows.dags.__init__"],
    },
}
# ============================================================================

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)
from workflows.session.registry import register_session_dag

# =============================================================================
# README PIPELINE DAG DEFINITION
# =============================================================================

README_PIPELINE_DAG = SessionDAG(
    id="readme-pipeline-v1",
    name="README Generation Pipeline",
    version="1.0.0",
    description="""
Systematic workflow for generating and validating subsystem READMEs.

This DAG guides through:
1. Gap analysis - compare config vs actual directories
2. Config enrichment - add missing subsystems to readme_config.yaml
3. Template update - enhance README_TEMPLATE if needed
4. Generate - run scripts/generate_subsystem_readmes.py
5. Validate - verify all READMEs generated correctly
6. Report - summarize what was generated

Use when: Adding new subsystems, regenerating READMEs after template changes,
or auditing README coverage across the codebase.

KEY FILES:
- Config: config/subsystems/readme_config.yaml
- Generator: scripts/generate_subsystem_readmes.py
- Skill: skills/l9-update-agent-docs (invokes this DAG; never writes root README.md)
- Output: <module>/README.md for live (non-skip) config keys only
""",
    tags=["readme", "documentation", "generation", "subsystems"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin README pipeline workflow",
        ),
        # === PHASE 1: GAP ANALYSIS ===
        SessionNode(
            id="gap_analysis",
            name="Gap Analysis",
            node_type=NodeType.ANALYZE,
            description="Identify missing subsystems in config",
            action="""Analyze gaps between config and codebase:

1. List configured modules:
   ```bash
   python scripts/generate_subsystem_readmes.py --list
   ```

2. Report stale or unguarded handwritten paths (do not `find` the tree):
   ```bash
   python scripts/generate_subsystem_readmes.py --gaps
   ```

3. Document results in state from that CLI only:
   - stale / invalid config paths
   - handwritten READMEs that are not skip: true

Do not invent modules. Do not treat repo-root README.md as a gap to generate.

Pre-reading: config/subsystems/readme_config.yaml
   skills/l9-update-agent-docs/SKILL.md Step 3b
""",
            outputs=["gaps", "stale_entries"],
        ),
        # === GATE: GAPS FOUND? ===
        SessionNode(
            id="gate_gaps",
            name="Gaps Found?",
            node_type=NodeType.GATE,
            description="Check if there are gaps to address",
            action="If gaps exist, proceed to enrichment. Otherwise skip to generate.",
            gate_type=GateType.CONDITIONAL,
            validation="len(state.get('gaps', [])) > 0",
        ),
        # === PHASE 2: CONFIG ENRICHMENT ===
        SessionNode(
            id="enrich_config",
            name="Enrich Config",
            node_type=NodeType.TRANSFORM,
            description="Add missing subsystems to readme_config.yaml",
            action="""Add only paths `--gaps` reported as missing after a human or locked-plan confirm.

Required fields: path, title, tier, description.
Allowed tiers here: operations | control_plane | documentation.
path must be a directory under the repo root, never `.` or `..`.

Mark handwritten indexes `skip: true` (see commands/, workflows/).
Do not copy donor L9-OS fields (forbidden_scopes, airules, DORA).

Pre-reading: config/subsystems/readme_config.yaml
""",
            outputs=["config_updated"],
        ),
        # === PHASE 3: TEMPLATE UPDATE (OPTIONAL) ===
        SessionNode(
            id="gate_template",
            name="Template Update Needed?",
            node_type=NodeType.GATE,
            description="Check if template needs enhancement",
            action="If template changes requested, proceed to update. Otherwise skip to generate.",
            gate_type=GateType.USER_CONFIRM,
        ),
        SessionNode(
            id="update_template",
            name="Update Template",
            node_type=NodeType.TRANSFORM,
            description="Enhance README_TEMPLATE in generator script",
            action="""Change README_TEMPLATE only when the user asked for a new *module* section.

Keep Purpose + Components. Do not add DORA frontmatter, ASCII banners, or
AI allow/restrict/forbid scopes. After edit:

```bash
python -c "from scripts.generate_subsystem_readmes import README_TEMPLATE; print('OK')"
```

Pre-reading: scripts/generate_subsystem_readmes.py
""",
            outputs=["template_updated"],
        ),
        # === PHASE 4: GENERATE ===
        SessionNode(
            id="generate",
            name="Generate READMEs",
            node_type=NodeType.TRANSFORM,
            description="Run the generator script",
            action="""Execute README generation:

```bash
# Full generation (all subsystems)
python scripts/generate_subsystem_readmes.py --skip-time-verify

# Or specific subsystem
python scripts/generate_subsystem_readmes.py --subsystem ops_autonomy --skip-time-verify

# Or specific tier
python scripts/generate_subsystem_readmes.py --tier operations --skip-time-verify
```

Expected output: generated=N skipped=M. Root README.md must stay unwritten.
skip: true modules are skipped unless --force.

Pre-reading: config/subsystems/readme_config.yaml
   skills/l9-update-agent-docs/SKILL.md Step 3b
""",
            outputs=["generated_count", "skipped_count"],
        ),
        # === PHASE 5: VALIDATE ===
        SessionNode(
            id="validate",
            name="Validate Output",
            node_type=NodeType.VALIDATE,
            description="Verify READMEs were generated correctly",
            action="""Validate generated module READMEs (never the repo-root README.md):

```bash
python scripts/generate_subsystem_readmes.py --validate
python scripts/generate_subsystem_readmes.py --validate-sections
python skills/l9-update-agent-docs/scripts/validate_pointer_headings.py --root .
```

Required module headings come from config defaults (Purpose, Components).
Handwritten files (auto_generated: false) and skip: true keys are not Failed.
Root pointer-stack headings stay on the skill map, not this generator.
""",
            outputs=["validation_passed", "validation_errors"],
        ),
        # === GATE: VALIDATION PASSED? ===
        SessionNode(
            id="gate_validation",
            name="Validation Passed?",
            node_type=NodeType.GATE,
            description="Check if validation succeeded",
            action="If validation passed, proceed to report. Otherwise loop back to fix.",
            gate_type=GateType.CONDITIONAL,
            validation="state.get('validation_passed', False)",
        ),
        # === PHASE 6: REPORT ===
        SessionNode(
            id="report",
            name="Generate Report",
            node_type=NodeType.ANALYZE,
            description="Summarize pipeline results",
            action="""Generate summary report:

## README Pipeline Report

| Metric | Value |
|--------|-------|
| Subsystems in config | {config_count} |
| READMEs generated | {generated_count} |
| Gaps identified | {len(gaps)} |
| Validation | {passed/failed} |

### Files Modified
- config/subsystems/readme_config.yaml
- scripts/generate_subsystem_readmes.py (if template updated)
- */README.md (generated)

### Next Steps
- [ ] Review generated READMEs
- [ ] Commit changes
- [ ] Update CI if needed
""",
            outputs=["report"],
        ),
        # === END ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="Workflow complete",
            action="README pipeline complete",
        ),
    ],
    edges=[
        # Main flow
        SessionEdge(from_node="start", to_node="gap_analysis"),
        SessionEdge(from_node="gap_analysis", to_node="gate_gaps"),
        # Conditional: gaps found
        SessionEdge(
            from_node="gate_gaps",
            to_node="enrich_config",
            condition="gaps_exist",
            label="Gaps found",
        ),
        SessionEdge(
            from_node="gate_gaps",
            to_node="gate_template",
            condition="no_gaps",
            label="No gaps",
        ),
        SessionEdge(from_node="enrich_config", to_node="gate_template"),
        # Conditional: template update
        SessionEdge(
            from_node="gate_template",
            to_node="update_template",
            condition="template_update_requested",
            label="Update needed",
        ),
        SessionEdge(
            from_node="gate_template",
            to_node="generate",
            condition="no_template_update",
            label="Skip template",
        ),
        SessionEdge(from_node="update_template", to_node="generate"),
        # Generate → Validate → Report
        SessionEdge(from_node="generate", to_node="validate"),
        SessionEdge(from_node="validate", to_node="gate_validation"),
        # Conditional: validation
        SessionEdge(
            from_node="gate_validation",
            to_node="report",
            condition="validation_passed",
            label="Passed",
        ),
        SessionEdge(
            from_node="gate_validation",
            to_node="enrich_config",
            condition="validation_failed",
            label="Fix issues",
        ),
        SessionEdge(from_node="report", to_node="end"),
    ],
)


# =============================================================================
# REGISTRATION
# =============================================================================


def register():
    """Register the README pipeline DAG."""
    register_session_dag(README_PIPELINE_DAG)


# Auto-register on import
register()
# ============================================================================
# DORA FOOTER META - AUTO-GENERATED - DO NOT EDIT MANUALLY
# ============================================================================
__dora_footer__ = {
    "component_id": "WOR-OPER-030",
    "governance_level": "medium",
    "compliance_required": True,
    "audit_trail": True,
    "dependencies": [],
    "tags": ["api", "caching", "metrics", "operations", "utility", "workflows"],
    "keywords": [
        "analysis",
        "dag",
        "missing",
        "pipeline",
        "readme",
        "register",
        "session",
        "workflow",
    ],
    "business_value": (
        "1. Gap analysis - identify missing subsystems 2. Config enrichment - add "
        "missing entries to readme_config.yaml 3. Template update - enhance "
        "README_TEMPLATE if needed 4. Generate - run generator script"
    ),
    "last_modified": "2026-01-31T22:21:54Z",
    "modified_by": "L9_Codegen_Engine",
    "change_summary": "Initial generation with DORA compliance",
}
# ============================================================================
# L9 DORA BLOCK - AUTO-UPDATED - DO NOT EDIT
# Runtime execution trace - updated automatically on every execution
# ============================================================================
__l9_trace__ = {
    "trace_id": "",
    "task": "",
    "timestamp": "",
    "patterns_used": [],
    "graph": {"nodes": [], "edges": []},
    "inputs": {},
    "outputs": {},
    "metrics": {"confidence": "", "errors_detected": [], "stability_score": ""},
}
# ============================================================================
# END L9 DORA BLOCK
# ============================================================================
