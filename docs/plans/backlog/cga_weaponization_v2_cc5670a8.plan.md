---
name: CGA Weaponization v2
overview: Synthesize AI-OS Strategy, QPF Factory Strategy, 81 CGA YAML specs, and meta-yaml-pack into a unified, contract-driven code generation pipeline with compliance enforcement, gap detection, and LLM-powered enrichment. Uses Module-Spec-v2.4 as the canonical schema, sympy for symbolic computation, and a closed-loop compliance scanner.
todos:
  - id: T1.1-metacontract-model
    content: Create MetaContract Pydantic model mapping all 22 Module-Spec-v2.4 sections in ir_engine/meta_ir.py
    status: pending
  - id: T1.2-schema-validator
    content: Create schema_validator.py enforcing Module-Spec-v2.4 constraints (no inference, required fields)
    status: pending
    dependencies:
      - T1.1-metacontract-model
  - id: T1.3-sample-schema-tests
    content: Create test_sample_schemas.py validating all 4 sample schemas parse correctly
    status: pending
    dependencies:
      - T1.1-metacontract-model
  - id: T2.1-meta-loader
    content: Create meta_loader.py with validation against MetaContract schema
    status: pending
    dependencies:
      - T1.2-schema-validator
  - id: T2.2-ir-compiler
    content: Create compile_meta_to_ir.py transforming MetaContract to code generation targets
    status: pending
    dependencies:
      - T2.1-meta-loader
  - id: T2.3-ir-to-python
    content: Create ir_to_python.py with sympy CodeGenerator integration for symbolic expressions
    status: pending
    dependencies:
      - T2.2-ir-compiler
  - id: T3.1-file-emitter
    content: Create file_emitter.py with Module-Prompt-CURSOR wiring patterns
    status: pending
    dependencies:
      - T2.3-ir-to-python
  - id: T3.2-readme-renderer
    content: Create readme_renderer.py using README.meta.yaml templates
    status: pending
    dependencies:
      - T3.1-file-emitter
  - id: T3.3-test-generator
    content: Create test_generator.py scaffolding tests from MetaContract.acceptance
    status: pending
    dependencies:
      - T3.1-file-emitter
  - id: T4.1-compliance-scanner
    content: Create meta_compliance_scanner.py adapted from ci_meta_check_and_tests.py
    status: pending
    dependencies:
      - T3.1-file-emitter
  - id: T4.2-gap-reporter
    content: Create gap_reporter.py outputting machine-readable meta-gaps.yaml
    status: pending
    dependencies:
      - T4.1-compliance-scanner
  - id: T4.3-superprompt-integration
    content: Create SuperPrompt_Emitter.py consuming meta-gaps.yaml for LLM enrichment
    status: pending
    dependencies:
      - T4.2-gap-reporter
  - id: T5.1-cga-orchestrator
    content: Create codegen_agent.py orchestrating full pipeline (load → compile → emit → validate → fill)
    status: pending
    dependencies:
      - T2.1-meta-loader
      - T3.1-file-emitter
      - T4.1-compliance-scanner
  - id: T5.2-pipeline-validator
    content: Create pipeline_validator.py with Module-Prompt-CURSOR verification gates
    status: pending
    dependencies:
      - T5.1-cga-orchestrator
  - id: T5.3-rollback-hook
    content: Create rollback_hook.py for snapshot/revert capability
    status: pending
    dependencies:
      - T5.1-cga-orchestrator
---

# CGA Weaponization Plan v2.0

## Strategic Integration

Four source packs combine into a closed-loop codegen system:

| Pack | Role | Key Asset |
|------|------|-----------|
| AI-OS Strategy | VISION | god_research_agent_aios concepts |
| QPF Factory | METHOD | Tensor schemas, SuperPrompt patterns |
| CGA Spec Library | FRAGMENTS | 81 YAML module specs |
| **meta-yaml-pack** | **CONTRACTS** | Module-Spec-v2.4, compliance scanner |

## Architecture

```
Contract (Module-Spec-v2.4)
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ SCHEMA LAYER                                               │
│   MetaContract Pydantic model validates 22 sections        │
│   Sample schemas provide test fixtures                     │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ IR ENGINE                                                  │
│   meta_loader.py → compile_meta_to_ir.py → ir_to_python.py │
│   Uses sympy CodeGenerator for symbolic expressions        │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ CODE GENERATION                                            │
│   file_emitter.py writes Python + tests + READMEs          │
│   Auto-wires to AgentRegistry, ToolGraph, API routes       │
└────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│ COMPLIANCE LOOP (NEW)                                      │
│   ci_meta_check.py → meta-gaps.yaml → SuperPrompt → Patch  │
│   Iterative refinement until all contracts satisfied       │
└────────────────────────────────────────────────────────────┘
```

## Phase 1: Schema Layer Foundation

### T1.1: Create MetaContract Pydantic Model

**File:** [`ir_engine/meta_ir.py`](ir_engine/meta_ir.py)

Map all 22 sections from [`codegen/meta-yaml-pack/Module-Spec-v2.4.yaml`](codegen/meta-yaml-pack/Module-Spec-v2.4.yaml) to Pydantic models:

```python
class MetaContract(BaseModel):
    schema_version: str = "2.4"
    metadata: ModuleMetadata          # Section 1
    ownership: OwnershipSpec          # Section 2
    runtime_wiring: RuntimeWiringSpec # Section 3 (KEYSTONE)
    external_surface: ExternalSurface # Section 4
    dependencies: DependencySpec      # Section 5
    packet_contract: PacketContract   # Section 6
    # ... sections 7-22
```

### T1.2: Create Schema Validator

**File:** `ir_engine/schema_validator.py` (NEW)

Enforce Module-Spec-v2.4 constraints:
- No "if applicable" allowed
- runtime_wiring is REQUIRED
- packet_contract.emits must be non-empty
- global_invariants_ack all true

### T1.3: Sample Schema Test Suite

**File:** `tests/codegen/test_sample_schemas.py` (NEW)

Load each file from [`codegen/meta-yaml-pack/sample_schemas/`](codegen/meta-yaml-pack/sample_schemas/):
- `domain_adapter.yaml` - Complex adapter with tensor integration
- `glue_layer.yaml` - Simple bridging layer
- `orchestrator.yaml` - Multi-agent coordination
- `simple_agent.yaml` - Minimal agent

Assert all parse to valid MetaContract.

## Phase 2: IR Engine

### T2.1: Meta Loader with Validation

**File:** [`agents/codegen_agent/meta_loader.py`](agents/codegen_agent/meta_loader.py)

```python
def load_meta(path: str) -> MetaContract:
    """Load and validate meta.yaml against Module-Spec-v2.4 schema."""
    raw = yaml.safe_load(open(path))
    return MetaContract(**raw)  # Pydantic validates
```

### T2.2: IR Compiler

**File:** [`ir_engine/compile_meta_to_ir.py`](ir_engine/compile_meta_to_ir.py)

Transform validated MetaContract into intermediate representation:
- Extract code generation targets from `repo.allowed_new_files`
- Build dependency graph from `dependencies.outbound_calls`
- Map `packet_contract.emits` to required imports

### T2.3: IR-to-Python Compiler with sympy

**File:** `ir_engine/ir_to_python.py` (NEW)

Key integration with [`codegen/sympy/symbolic_computation_core.py`](codegen/sympy/symbolic_computation_core.py):

```python
from codegen.sympy.symbolic_computation_core import CodeGenerator

class IRToPythonCompiler:
    def __init__(self):
        self.sympy_codegen = CodeGenerator()
        self.jinja_env = jinja2.Environment(...)

    def compile(self, ir: MetaContract) -> Dict[str, str]:
        files = {}
        for target in ir.repo.allowed_new_files:
            template = self.get_template(target)
            files[target] = template.render(ir=ir)
        return files
```

## Phase 3: Code Generation with Templates

### T3.1: File Emitter with Wiring

**File:** [`agents/codegen_agent/file_emitter.py`](agents/codegen_agent/file_emitter.py)

Use patterns from [`codegen/meta-yaml-pack/Module-Prompt-CURSOR-v2.0.yaml`](codegen/meta-yaml-pack/Module-Prompt-CURSOR-v2.0.yaml):
- Phase 3: Write code files
- Phase 6: Wire server.py
- Phase 7: Verification gates

### T3.2: README Template Renderer

**File:** `agents/codegen_agent/readme_renderer.py` (NEW)

Use templates from [`codegen/meta-yaml-pack/README.meta.yaml.md`](codegen/meta-yaml-pack/README.meta.yaml.md):
- `root_readme` → Generate root README.md
- `subsystem_readme` → Generate per-folder READMEs
- `component_readme` → Generate detailed component docs

### T3.3: Test Scaffold Generator

**File:** `agents/codegen_agent/test_generator.py` (NEW)

Generate from MetaContract.acceptance:
- Positive tests from `acceptance.positive[]`
- Negative tests from `acceptance.negative[]`
- Integration tests if `test_scope.integration == true`
- Docker smoke tests if `test_scope.docker_smoke == true`

## Phase 4: Compliance Loop

### T4.1: Meta Compliance Scanner

**File:** `ci/meta_compliance_scanner.py` (NEW)

Adapt from [`codegen/meta-yaml-pack/ci_meta_check_and_tests.py.md`](codegen/meta-yaml-pack/ci_meta_check_and_tests.py.md):

```python
def scan_for_gaps(repo_root: Path) -> List[Gap]:
    gaps = []
    for meta_path in repo_root.rglob("*.meta.yaml"):
        meta = load_yaml(meta_path)
        # Check required docs exist
        # Check required tests exist
        # Check wiring complete
    return gaps
```

### T4.2: Gap Report Generator

**File:** `ci/gap_reporter.py` (NEW)

Output machine-readable `meta-gaps.yaml`:

```yaml
gaps:
  - kind: "missing_doc"
    meta: "agents/codegen_agent/README.meta.yaml"
    target: "agents/codegen_agent/README.md"
  - kind: "missing_test"
    meta: "agents/codegen_agent/tests.meta.yaml"
    target: "tests/test_codegen_agent.py"
    required_behaviors:
      - "CodeGenAgent basic happy path"
```

### T4.3: SuperPrompt Emitter Integration

**File:** [`runtime/perplexity/SuperPrompt_Emitter.py`](runtime/perplexity/SuperPrompt_Emitter.py)

Consume `meta-gaps.yaml` and emit prompts for Perplexity to fill:

```python
def build_superprompt_from_gaps(gaps: List[Gap]) -> dict:
    return {
        "intent": "Fill missing artifacts",
        "gaps": [gap.dict() for gap in gaps],
        "output_format": "YAML patches or complete files"
    }
```

## Phase 5: CodeGenAgent Orchestrator

### T5.1: Main Orchestrator

**File:** [`agents/codegen_agent/codegen_agent.py`](agents/codegen_agent/codegen_agent.py)

```python
class CodeGenAgent:
    async def generate_from_contract(self, contract_path: str) -> GenerationResult:
        # 1. Load and validate (T1, T2.1)
        meta = self.meta_loader.load(contract_path)

        # 2. Compile to IR (T2.2)
        ir = self.ir_compiler.compile(meta)

        # 3. Generate Python (T2.3)
        files = self.python_compiler.compile(ir)

        # 4. Emit files (T3.1)
        written = self.file_emitter.emit(files)

        # 5. Generate docs (T3.2)
        self.readme_renderer.render(meta)

        # 6. Generate tests (T3.3)
        self.test_generator.generate(meta)

        # 7. Validate compliance (T4.1)
        gaps = self.compliance_scanner.scan()

        if gaps:
            # 8. Fill gaps via SuperPrompt (T4.3)
            await self.superprompt_emitter.fill(gaps)

        return GenerationResult(files=written, gaps=gaps)
```

### T5.2: Pipeline Validator

**File:** [`agents/codegen_agent/pipeline_validator.py`](agents/codegen_agent/pipeline_validator.py)

Verification gates from Module-Prompt-CURSOR:
- Gate 1: All imports resolve
- Gate 2: No syntax errors
- Gate 3: Unit tests pass
- Gate 4: Routes reachable

### T5.3: Rollback Hook

**File:** `agents/codegen_agent/rollback_hook.py` (NEW)

Track all generated files for potential revert:

```python
class RollbackHook:
    def setup(self, files: List[str]):
        self.snapshot = {f: read_file(f) for f in files if exists(f)}

    def rollback(self):
        for path, content in self.snapshot.items():
            write_file(path, content)
```

## File Organization

```
agents/codegen_agent/
├── __init__.py
├── codegen_agent.py        # T5.1: Main orchestrator
├── meta_loader.py          # T2.1: YAML loading
├── file_emitter.py         # T3.1: File writing + wiring
├── readme_renderer.py      # T3.2: Doc generation
├── test_generator.py       # T3.3: Test scaffolds
├── pipeline_validator.py   # T5.2: Verification gates
└── rollback_hook.py        # T5.3: Revert capability

ir_engine/
├── __init__.py
├── meta_ir.py              # T1.1: MetaContract model
├── schema_validator.py     # T1.2: Spec enforcement
├── compile_meta_to_ir.py   # T2.2: YAML → IR
└── ir_to_python.py         # T2.3: IR → Python + sympy

ci/
├── meta_compliance_scanner.py  # T4.1: Gap detection
└── gap_reporter.py             # T4.2: meta-gaps.yaml

runtime/perplexity/
├── SuperPrompt_Emitter.py      # T4.3: Gap filling
└── Construct_Enhancer.py       # Response processing

tests/codegen/
└── test_sample_schemas.py      # T1.3: Sample validation
```

## Success Criteria

- [ ] All 4 sample schemas parse to valid MetaContract
- [ ] IR engine generates syntactically valid Python
- [ ] Generated code passes ruff + mypy
- [ ] Compliance scanner detects all missing artifacts
- [ ] SuperPrompt fills gaps with valid patches
- [ ] Self-hosting: CGA can regenerate itself from spec

## Dependencies

- **sympy integration:** [`codegen/sympy/symbolic_computation_core.py`](codegen/sympy/symbolic_computation_core.py) provides CodeGenerator
- **Sample schemas:** [`codegen/meta-yaml-pack/sample_schemas/`](codegen/meta-yaml-pack/sample_schemas/) provide test fixtures
- **Contract template:** [`codegen/meta-yaml-pack/Module-Spec-v2.4.yaml`](codegen/meta-yaml-pack/Module-Spec-v2.4.yaml) defines schema
