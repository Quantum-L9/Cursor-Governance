"""
Harvest-Deploy Session DAG
==========================

Systematic workflow for harvesting code from documents and deploying.

Based on the 2026-01-25 session workflow:
1. Parse plan document
2. Extract code blocks
3. Deploy full files
4. Inject diffs
5. Validate
6. Report/Commit

Version: 1.0.0
"""

from workflows.session.interface import (
    GateType,
    NodeType,
    SessionDAG,
    SessionEdge,
    SessionNode,
)
from workflows.session.registry import register_session_dag

# =============================================================================
# HARVEST-DEPLOY DAG DEFINITION
# =============================================================================

HARVEST_DEPLOY_DAG = SessionDAG(
    id="harvest-deploy-v1",
    name="Harvest-Deploy Workflow",
    version="2.0.0",
    description="""
FULLY AUTOMATED workflow for harvesting code from markdown documents
and deploying to the L9 codebase. NO user prompts — runs to completion.

This DAG executes:
1. Parse plan/source documents
2. Extract code blocks (using sed, not manual copy)
3. Validate syntax automatically
4. Deploy full files (copy)
5. Inject diffs into existing files (sed)
6. Final validation
7. Auto-commit locally
8. Report completion

Use when: Deploying code from research documents, chat transcripts,
or planning documents that contain code blocks to harvest.

CRITICAL RULES:
- NO manual code writing - use sed/cp only
- Extract EXACTLY what's in the document
- Validate syntax before proceeding
- NO user confirmation gates - fully automated
- Auto-commit on success
""",
    tags=["harvest", "deploy", "sed", "systematic", "no-manual-write", "automated"],
    nodes=[
        # === ENTRY ===
        SessionNode(
            id="start",
            name="Start",
            node_type=NodeType.START,
            description="Entry point",
            action="Begin harvest-deploy workflow",
        ),
        # === PHASE: PARSE ===
        SessionNode(
            id="parse_plan",
            name="Parse Plan Document",
            node_type=NodeType.ANALYZE,
            description="Analyze the plan document for extraction instructions",
            action="""Read and analyze the plan document:

1. Identify CREATES (new files):
   - Source line ranges in markdown
   - Target file paths

2. Identify INJECTS (diffs):
   - Source line ranges in markdown
   - Target files and injection points
   - after_line or after_pattern

3. Identify REPLACES (replacements):
   - Source line ranges
   - Target file ranges to replace

Output: Extraction plan with line numbers""",
            outputs=["creates", "injects", "replaces", "source_document"],
        ),
        SessionNode(
            id="verify_sources",
            name="Verify Source Document",
            node_type=NodeType.VALIDATE,
            description="Verify source document exists and has expected line counts",
            action="""Verify source document:

wc -l {source_document}

Check that referenced line ranges exist:
sed -n '{start},{end}p' {source_document} | wc -l

Flag any discrepancies.""",
            validation="Source document exists, line counts verified",
        ),
        SessionNode(
            id="log_plan",
            name="Log Extraction Plan",
            node_type=NodeType.ANALYZE,
            description="Log extraction plan (no user confirmation needed)",
            action="""Log extraction plan to output (no wait):

### CREATES (New Files)
{creates_table}

### INJECTS (Diffs)
{injects_table}

### REPLACES
{replaces_table}

Proceeding automatically...""",
        ),
        # === PHASE: EXTRACT ===
        SessionNode(
            id="extract_files",
            name="Extract Code Blocks",
            node_type=NodeType.TRANSFORM,
            description="Extract code blocks using sed",
            action="""For each extraction pattern:

# Strip backticks (remove first and last line of code block)
sed -n '{start},{end}p' "{source}" | sed '1d' | sed '$d' > "{output}"

# Verify extraction
wc -l "{output}"

CRITICAL:
- Use sed ONLY
- Do NOT manually write or copy content
- Extract EXACTLY what's in the source""",
            validation="wc -l confirms expected line counts",
            outputs=["extracted_files"],
        ),
        SessionNode(
            id="validate_extraction",
            name="Validate Extraction",
            node_type=NodeType.VALIDATE,
            description="Validate extracted files",
            action="""For each extracted file:

1. Check it exists and has content:
   ls -la {extracted_files}

2. For Python files, validate syntax:
   python3 -m py_compile {file.py}

3. For SQL files, basic structure check:
   head -5 {file.sql}

Report any issues.""",
            validation="All extracted files valid",
        ),
        SessionNode(
            id="log_extraction",
            name="Log Extraction Results",
            node_type=NodeType.VALIDATE,
            description="Log extraction results (no user confirmation needed)",
            action="""Log extraction results (no wait):

**Files extracted:** {count}
**Validation:** {validation_results}

Proceeding to deploy automatically...""",
            validation="All extracted files valid, proceeding",
        ),
        # === PHASE: DEPLOY ===
        SessionNode(
            id="deploy_creates",
            name="Deploy Full Files",
            node_type=NodeType.TRANSFORM,
            description="Copy extracted files to target locations",
            action="""For each CREATE mapping:

# Ensure target directory exists
mkdir -p $(dirname "{target}")

# Copy file
cp "{source}" "{target}"

# Verify
ls -la "{target}"

CRITICAL:
- Use cp ONLY
- Create directories as needed
- Do NOT modify file contents during copy""",
            validation="All files copied to correct locations",
            outputs=["deployed_files"],
        ),
        SessionNode(
            id="deploy_injects",
            name="Inject Diffs",
            node_type=NodeType.TRANSFORM,
            description="Inject diff content into existing files",
            action="""For each INJECT mapping:

# Inject after specific line
sed -i '' '{line}r {source}' "{target}"

# Or inject after pattern
sed -i '' '/{pattern}/r {source}' "{target}"

CRITICAL:
- Use sed -i '' for macOS in-place edit
- Verify injection point exists before injecting
- Check line numbers haven't shifted from prior injections""",
            validation="Injections verified with grep",
            outputs=["modified_files"],
        ),
        SessionNode(
            id="deploy_replaces",
            name="Replace Sections",
            node_type=NodeType.TRANSFORM,
            description="Replace line ranges in existing files",
            action="""For each REPLACE mapping:

# Step 1: Delete the line range
sed -i '' '{start},{end}d' "{target}"

# Step 2: Insert new content at (start - 1)
sed -i '' '{start-1}r {source}' "{target}"

CRITICAL:
- Delete THEN insert (two-step process)
- Verify line numbers before each operation
- Check replacement was successful""",
            validation="Replacements verified",
        ),
        # === PHASE: VALIDATE ===
        SessionNode(
            id="validate_all",
            name="Full Validation",
            node_type=NodeType.VALIDATE,
            description="Validate all deployed and modified files",
            action="""Run full validation suite:

1. Python syntax:
   python3 -m py_compile {all_py_files}

2. Import check:
   python3 -c "from {module} import *"

3. Linting:
   ruff check {files} --select=E,F

4. Check for expected patterns:
   grep -l "{expected_pattern}" {target_files}

All must pass.""",
            validation="py_compile ✅, imports ✅, lint ✅",
        ),
        SessionNode(
            id="log_validation",
            name="Log Validation Results",
            node_type=NodeType.VALIDATE,
            description="Log validation results (no user confirmation needed)",
            action="""Log validation (no wait):

- Syntax: {syntax_results}
- Imports: {import_results}
- Lint: {lint_results}

Proceeding to commit automatically...""",
            validation="All validations passed, proceeding to commit",
        ),
        # === PHASE: REPORT ===
        SessionNode(
            id="generate_report",
            name="Generate Report",
            node_type=NodeType.TRANSFORM,
            description="Generate final deployment report",
            action="""Generate deployment report:

## HARVEST-DEPLOY REPORT

**Workflow ID:** {workflow_id}
**Started:** {started_at}
**Completed:** {completed_at}

### Files Created
| File | Lines |
|------|-------|
{created_files_table}

### Files Modified
| File | Change |
|------|--------|
{modified_files_table}

### Validation
- Syntax: ✅ PASSED
- Imports: ✅ PASSED
- Lint: ✅ PASSED

### Next Steps
- Review changes: git diff
- Commit if satisfied
- Run tests: pytest tests/""",
            outputs=["report"],
        ),
        SessionNode(
            id="auto_commit",
            name="Auto Commit",
            node_type=NodeType.COMMIT,
            description="Automatically commit changes (no user confirmation)",
            action="""Auto-commit (no wait):

**Changes staged:** {count} files

Committing automatically...""",
        ),
        SessionNode(
            id="commit",
            name="Commit Changes",
            node_type=NodeType.COMMIT,
            description="Git commit if user approves",
            action="""git add {files}

git commit -m "$(cat <<'EOF'
feat(harvest): deploy {module_name}

## Files Created
{created_list}

## Files Modified
{modified_list}

Deployed via harvest-deploy workflow.
EOF
)"

git log -1 --oneline""",
            outputs=["commit_hash"],
        ),
        # === EXIT ===
        SessionNode(
            id="end",
            name="End",
            node_type=NodeType.END,
            description="Workflow complete",
            action="Harvest-deploy workflow complete.",
        ),
    ],
    edges=[
        # Start -> Parse (linear flow, no gates)
        SessionEdge("start", "parse_plan"),
        SessionEdge("parse_plan", "verify_sources"),
        SessionEdge("verify_sources", "log_plan"),
        # Extract (no confirmation needed)
        SessionEdge("log_plan", "extract_files"),
        SessionEdge("extract_files", "validate_extraction"),
        SessionEdge("validate_extraction", "log_extraction"),
        # Deploy (no confirmation needed)
        SessionEdge("log_extraction", "deploy_creates"),
        SessionEdge("deploy_creates", "deploy_injects"),
        SessionEdge("deploy_injects", "deploy_replaces"),
        SessionEdge("deploy_replaces", "validate_all"),
        # Validate and commit (no confirmation needed)
        SessionEdge("validate_all", "log_validation"),
        SessionEdge("log_validation", "generate_report"),
        SessionEdge("generate_report", "auto_commit"),
        SessionEdge("auto_commit", "commit"),
        # End
        SessionEdge("commit", "end"),
    ],
    entry_node="start",
)


# Register on module import
register_session_dag(HARVEST_DEPLOY_DAG)


def get_harvest_deploy_dag() -> SessionDAG:
    """Get the harvest-deploy DAG."""
    return HARVEST_DEPLOY_DAG


# Generate Mermaid diagram for documentation
if __name__ == "__main__":
    print(HARVEST_DEPLOY_DAG.to_markdown())  # noqa: ADR-0019
