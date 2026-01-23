============================================================================
GMP VARIABLE SPEC — L9 GMP v1.1 (ALIGNMENT GUIDE FOR LLMS)
============================================================================

PURPOSE OF THIS FILE

This file defines every variable used by the L9 GMP v1.1 prompt and gives
precise instructions for how an LLM must interpret and use each variable.

This file does NOT change behavior itself. It is a contract:
- Between the GMP prompt
- And any spec or supplemental files that provide values

If there is ever a conflict between:
- The GMP core text, and
- A value or instruction implied by these variables,

THE GMP CORE TEXT WINS.

============================================================================
GLOBAL RULES FOR VARIABLE USE
============================================================================

1. DO NOT INVENT VALUES
   - If a required variable is missing, STOP and request clarification.
   - Do NOT guess, infer, or synthesize values for required variables.

2. READ-ONLY CONTRACT
   - Treat spec/supplemental files as authoritative for variable values.
   - Do not re-interpret or rewrite spec content when inserting variables.
   - Preserve identifiers and paths exactly as written.

3. SCOPE OF VARIABLES
   - Variables only affect:
     • Titles
     • Paths
     • Short natural-language context
   - Variables DO NOT:
     • Loosen modification locks
     • Weaken invariants
     • Bypass fail/STOP rules

4. PRIORITY ORDER
   When deciding what to do, follow this priority:
   1) GMP core rules and invariants
   2) Explicit TODO plan
   3) Variable values from spec
   4) Other conversation context

5. NO HIDDEN BEHAVIOR
   - Do not use variables to secretly expand scope.
   - Do not interpret descriptive text (e.g., EXECUTION_SCOPE) as a license
     to ignore GMP constraints.

============================================================================
VARIABLE INDEX (REQUIRED)
============================================================================

These variables MUST be present to begin Phase 0. If any are missing or empty,
STOP and ask for them.

--------------------------------------------------------------------
1. TASK_NAME
--------------------------------------------------------------------
TYPE:
- Short string (no spaces or minimal, e.g. "add_memory_search_tool")

MEANING:
- A stable, deterministic identifier for this execution run.

USE:
- Insert exactly where `{{TASK_NAME}}` appears in GMP_L9_V1_1:
  • Report title: `# EXECUTION REPORT — {{TASK_NAME}}`
  • Report path: `{{REPORT_ROOT}}/GMP_Report_{{TASK_NAME}}.md`
  • Role binding: "supplied spec for `{{TASK_NAME}}`"

RULES:
- Do NOT change TASK_NAME mid-execution.
- Do NOT derive new names from TASK_NAME; use it exactly as given.
- If the user/task description conflicts with TASK_NAME, do not rename;
  instead, STOP and surface the conflict.

--------------------------------------------------------------------
2. EXECUTION_SCOPE
--------------------------------------------------------------------
TYPE:
- 1–3 sentences of natural language, human-readable description.

MEANING:
- A concise, high-level statement of what this change must achieve.

USE:
- Insert where `{{EXECUTION_SCOPE}}` appears under "EXECUTION SCOPE (FROM SPEC)".
- Use EXECUTION_SCOPE as a *filter* for what belongs in the TODO plan,
  NOT as a license to extend or change GMP rules.

RULES:
- If EXECUTION_SCOPE is broad, STILL respect all architectural invariants.
- If EXECUTION_SCOPE conflicts with invariants or modification lock,
  do NOT follow it; instead, STOP and report the conflict.
- Do not silently shrink or expand EXECUTION_SCOPE; reflect it faithfully.

--------------------------------------------------------------------
3. SPEC_PATH
--------------------------------------------------------------------
TYPE:
- String path (relative or absolute) to primary spec/supplement file.

MEANING:
- Traceability link showing where spec instructions came from.

USE:
- Insert where `{{SPEC_PATH}}` appears in "EXECUTION SCOPE (FROM SPEC)".

RULES:
- Do NOT assume SPEC_PATH is writable; treat it as read-only.
- If SPEC_PATH is missing, it is acceptable to proceed, but display an
  explicit placeholder such as `SPEC PATH (optional): <none>`.

--------------------------------------------------------------------
4. REPORT_ROOT
--------------------------------------------------------------------
TYPE:
- Directory path string (e.g. `/l9/reports`).

MEANING:
- Base directory where the GMP report must be stored.

USE:
- Insert where `{{REPORT_ROOT}}` appears:
  • Path declaration block.
  • Phase 0 and Phase 6 report path references.
  • Final declaration.

DEFAULT:
- If not explicitly provided, assume `/l9/reports`.

RULES:
- Do NOT choose a different default.
- Never write reports outside REPORT_ROOT.
- If REPORT_ROOT appears invalid (e.g. obviously outside repo), STOP and ask.

============================================================================
VARIABLE INDEX (RISK & VALIDATION – OPTIONAL BUT RECOMMENDED)
============================================================================

These variables refine behavior but do not override core GMP rules.

--------------------------------------------------------------------
5. RISK_LEVEL
--------------------------------------------------------------------
TYPE:
- Enum-like string: "Low", "Medium", or "High".

MEANING:
- The operational and/or safety risk of the requested change.

USE:
- Insert where `{{RISK_LEVEL}}` appears in "EXECUTION SCOPE (FROM SPEC)".
- Influence **degree** of testing, not the existence of GMP phases.

RECOMMENDED BEHAVIOR:
- Low: Narrow, targeted tests acceptable if clearly relevant.
- Medium: Targeted tests strongly recommended; avoid skipping validation.
- High: Prefer broader or full relevant test suites; be conservative.

RULES:
- Never use Low or Medium as justification to skip Phases 3–5.
- If RISK_LEVEL appears inconsistent with EXECUTION_SCOPE (e.g. "High-risk
  kernel refactor" but RISK_LEVEL = Low), flag the inconsistency.

--------------------------------------------------------------------
6. IMPACT_METRICS
--------------------------------------------------------------------
TYPE:
- Short text or bullet list naming metrics, e.g.:
  "latency, error rate, memory usage"

MEANING:
- Signals that this change might affect or must not degrade.

USE:
- Insert under "IMPACT METRICS: {{IMPACT_METRICS}}`.
- In Phase 4, reference these metrics when reasoning about validations
  (e.g., which tests or checks matter most).

RULES:
- Do NOT invent metrics; only echo what is specified.
- If no metrics are given, do not fabricate them; simply note that they
  were not specified.

--------------------------------------------------------------------
7. VALIDATION_NOTES
--------------------------------------------------------------------
TYPE:
- Short paragraph or bullet list with validation hints, e.g.:
  "Run pytest -k 'memory_search' and smoke test /health endpoint."

MEANING:
- Human guidance about which validations are most important for this task.

USE:
- Insert under "VALIDATION NOTES (OPTIONAL, FROM SPEC)".
- In Phase 4, treat VALIDATION_NOTES as strong recommendations but still
  subordinate to GMP rules (no bypassing fail conditions).

RULES:
- If VALIDATION_NOTES suggests skipping tests or checks that GMP implies
  are required, obey GMP, not the notes, and explain the conflict.
- Do not expand VALIDATION_NOTES into a larger test matrix than necessary.

============================================================================
HOW LLMS SHOULD INTERPRET THESE VARIABLES
============================================================================

1. LOAD VARIABLES FIRST
   - Before planning Phase 0, read all variable values from:
     • The main spec file at SPEC_PATH (if given)
     • Any explicitly referenced supplemental files
   - Do not overwrite or mutate these values.

2. USE VARIABLES ONLY IN THEIR DESIGNATED SLOTS
   - Only substitute variables at their `{{...}}` positions in the GMP text.
   - Do not sprinkle variable values into unrelated sections.

3. USE VARIABLES AS CONSTRAINTS, NOT EXPANSION LEVERS
   - EXECUTION_SCOPE constrains *what* you should be doing, not *how far*
     you may deviate from GMP and invariants.
   - RISK_LEVEL, IMPACT_METRICS, and VALIDATION_NOTES tune validation
     effort inside Phase 4; they do NOT disable other phases.

4. ON CONFLICTS, ESCALATE, DO NOT GUESS
   - If any variable contradicts:
     • L9 invariants,
     • Modification lock,
     • Security & Safety rules,
     • Or TODO validity rules,
     you MUST:
       a) STOP execution, and
       b) Clearly report the conflict, citing the offending variable.

5. MINIMIZE VARIABLE SURFACE IN OTHER LOGIC
   - When generating TODOs:
     • Use EXECUTION_SCOPE and TASK_NAME to decide which files/paths
       are in-scope, but still honor invariants.
   - When writing the report:
     • Use TASK_NAME and REPORT_ROOT strictly for names and paths.

============================================================================
SPEC AUTHORING GUIDELINES (FOR HUMANS)
============================================================================

When humans create or edit spec files that supply these variables:

- Keep TASK_NAME:
  • Short
  • Stable
  • Machine-friendly (no spaces or minimal spaces)

- Keep EXECUTION_SCOPE:
  • Concrete (what exactly should be changed)
  • Bounded (avoid vague goals like “make it better”)

- Use RISK_LEVEL conservatively:
  • If unsure, default to Medium or High.
  • High-risk work includes anything touching:
    - Kernels
    - Memory substrates
    - Security, auth, or safety-critical paths

- Use VALIDATION_NOTES sparingly:
  • Highlight the 1–3 most important tests or checks.
  • Do not restate full test strategy; GMP covers the general behavior.

============================================================================
LLM ALIGNMENT CHECKLIST
============================================================================

Before starting Phase 0, the LLM MUST verify:

- [ ] TASK_NAME is present and non-empty.
- [ ] EXECUTION_SCOPE is present and non-empty.
- [ ] REPORT_ROOT is present or defaulted to `/l9/reports`.
- [ ] SPEC_PATH is recorded (or explicitly noted as absent).
- [ ] Any optional variables present are well-formed (e.g. RISK_LEVEL ∈ {Low, Medium, High}).

If any check fails, STOP and request correction instead of proceeding
with execution.

============================================================================
END OF GMP_L9_VARIABLE_SPEC
============================================================================
"""
