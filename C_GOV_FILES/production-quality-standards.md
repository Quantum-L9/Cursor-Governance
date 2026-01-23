---
# === SUITE 6 CANONICAL HEADER ===
suite: "Cursor Governance Suite 6 (L9 + Suite 6)"
version: "1.0.0"
component_id: "INT-QS-001"
component_name: "Production Quality Standards"
layer: "intelligence"
domain: "quality_assurance"
type: "standards_document"
status: "active"
created: "2025-11-08T00:00:00Z"
updated: "2025-11-08T00:00:00Z"
author: "Igor Beylin"
maintainer: "Igor Beylin"

# === GOVERNANCE METADATA ===
governance_level: "critical"
compliance_required: true
audit_trail: true
security_classification: "internal"

# === TECHNICAL METADATA ===
dependencies: []
integrates_with: ["INT-WS-001", "CMD-002", "CMD-004", "FND-LG-003"]
api_endpoints: []
data_sources: ["user_preferences", "meta-learning-log", "quality_incidents"]
outputs: ["quality_enforcement", "verification_checklists", "standards_compliance"]

# === OPERATIONAL METADATA ===
execution_mode: "continuous"
monitoring_required: true
logging_level: "info"
performance_tier: "realtime"

# === BUSINESS METADATA ===
purpose: "Define and enforce production quality standards for all AI-generated code and deliverables"
summary: "Comprehensive quality directives ensuring production-ready output, zero-rework delivery, and top-1% execution standards across all projects"
business_value: "Eliminates rework, ensures production readiness, prevents .1 version fixes, maintains top-tier deployment quality"
success_metrics: ["zero_rework_rate >= 0.95", "production_readiness = 1.0", "quality_compliance >= 0.98"]

# === INTEGRATION METADATA ===
suite_2_origin: "Derived from user quality preferences and meta-learning patterns"
migration_notes: "Codifies user's quality-over-speed philosophy into enforceable standards"

# === TAGS & CLASSIFICATION ===
tags: ["quality-standards", "production-ready", "zero-rework", "verification", "excellence"]
keywords: ["quality", "production", "standards", "verification", "testing", "documentation"]
related_components: ["INT-WS-001", "CMD-002", "CMD-004", "INT-ML-001"]
startup_required: true
---

# Production Quality Standards

**Philosophy:** Ship slowly, ship once. Quality over speed. Production-ready from MVP forward.

---

## Core Principles

### 1. Zero-Rework Delivery

**Standard:** Deliverables must be complete, correct, and production-ready on first delivery.

**Requirements:**
- No .1 version updates for missed basics
- No debugging needed after delivery
- No "we'll fix it later" items
- Feature-complete before declaring done

### 2. Quality Over Speed

**Standard:** Taking longer to deliver quality is ALWAYS preferred over fast delivery requiring rework.

**Requirements:**
- Never rush to meet arbitrary deadlines
- Verify thoroughly even if it takes extra time
- Test comprehensively before delivery
- Document completely before declaring done

### 3. Production-Ready From Start

**Standard:** Even MVPs must be deployable to production without modifications.

**Requirements:**
- Complete error handling
- Comprehensive testing
- Full documentation
- Performance validated
- Security considered

---

## Verification & Validation Standards (9 Directives)

### Standard #1: Canonical Header Verification

```
DIRECTIVE:
✓ Verify canonical headers match existing governance files EXACTLY (not just close)
✓ Check all metadata sections present and correct
✓ Validate component IDs follow namespace conventions
✓ Confirm author/maintainer attribution correct
✓ Ensure all required sections included

NEVER:
✗ Assume "close enough" for headers
✗ Skip metadata validation
✗ Mix header formats within project
✗ Omit any required metadata sections
```

**Verification Method:**
- Read existing governance file headers
- Match format character-by-character
- Validate against schema
- Confirm all sections present

---

### Standard #2: Directory Structure Alignment

```
DIRECTIVE:
✓ Double-check directory structure aligns PERFECTLY with existing patterns
✓ Verify files placed in correct layer (foundation/intelligence/execution/operations/telemetry)
✓ Confirm naming conventions match existing files
✓ Validate symlinks point to correct locations
✓ Ensure no organizational inconsistencies

NEVER:
✗ Create ad-hoc directory structures
✗ Place files in convenient but wrong locations
✗ Mix organizational patterns
✗ Skip structure verification
```

**Verification Method:**
- List existing directory structure
- Map new components to appropriate layers
- Verify before deployment
- Test accessibility after deployment

---

### Standard #3: Component Testing Post-Deployment

```
DIRECTIVE:
✓ Test EACH component after deployment
✓ Verify functionality in deployed location
✓ Confirm imports work correctly
✓ Validate configuration loads properly
✓ Test with realistic inputs

NEVER:
✗ Deploy without testing
✗ Assume "it worked in development"
✗ Skip integration testing
✗ Test only happy paths
```

**Testing Levels:**
1. **Unit:** Individual function correctness
2. **Integration:** Component interactions
3. **Performance:** Speed and resource usage
4. **Edge Cases:** Boundary conditions
5. **Failure Modes:** Error handling

---

### Standard #4: Integration Point Validation

```
DIRECTIVE:
✓ Validate ALL integration points work bidirectionally
✓ Test dependencies are available and correct versions
✓ Verify API contracts match expectations
✓ Confirm data flows correctly between components
✓ Test failure modes and fallbacks

NEVER:
✗ Assume external systems work as documented
✗ Skip dependency version checks
✗ Test only success paths
✗ Ignore error conditions
```

**Integration Checklist:**
- [ ] Dependencies available
- [ ] Versions compatible
- [ ] APIs respond correctly
- [ ] Data formats match
- [ ] Error handling works
- [ ] Fallbacks tested

---

### Standard #5: Completeness Confirmation

```
DIRECTIVE:
✓ Confirm NOTHING was missed or rushed
✓ Verify all features implemented
✓ Check all edge cases handled
✓ Validate all documentation complete
✓ Ensure all TODOs resolved

NEVER:
✗ Leave TODO comments in delivered code
✗ Skip features "for later"
✗ Deliver partial implementations
✗ Rush final stages
```

**Completeness Checklist:**
- [ ] All specified features implemented
- [ ] No TODO/FIXME comments
- [ ] All edge cases covered
- [ ] All documentation written
- [ ] All tests passing
- [ ] All verification items checked

---

### Standard #6: Prefer Quality Over Speed

```
DIRECTIVE:
✓ ALWAYS prefer quality over speed
✓ Take time needed for thorough implementation
✓ Verify meticulously even if it takes longer
✓ Test comprehensively before delivery
✓ Document completely regardless of time

NEVER:
✗ Rush to finish quickly
✗ Skip verification to save time
✗ Cut testing short
✗ Deliver incomplete documentation
✗ Sacrifice quality for speed
```

---

### Standard #7: Production Quality Always

```
DIRECTIVE:
✓ ALL code ALL projects EVERY iteration MUST be production quality
✓ MVP must be ready to deploy
✓ No debugging needed on delivery
✓ No simple upgrades requiring .1 version updates
✓ Future-proof design from start

NEVER:
✗ Deliver "prototype quality" code
✗ Plan to "clean up later"
✗ Skip production considerations for MVPs
✗ Deliver code requiring immediate fixes
```

---

### Standard #8: MVP Must Be Deployable

```
DIRECTIVE:
✓ Even minimum viable products must be production-ready
✓ Include complete error handling from MVP
✓ Document from MVP onward
✓ Test MVP as thoroughly as final version
✓ Design MVP for extensibility

NEVER:
✗ Treat MVP as "throwaway" code
✗ Skip error handling "for now"
✗ Defer documentation "until later"
✗ Hard-code what should be configurable
```

---

### Standard #9: No Debugging On Delivery

```
DIRECTIVE:
✓ User should not need to debug delivered code
✓ All errors handled gracefully
✓ All edge cases covered
✓ All integrations tested
✓ All documentation accurate

NEVER:
✗ Deliver code with known bugs
✗ Skip error handling
✗ Leave edge cases unhandled
✗ Deliver untested integrations
```

---

## Code Quality Standards (5 Directives)

### Standard #10: Comprehensive Error Handling

```
DIRECTIVE:
✓ ALWAYS include try-except blocks with specific exception types
✓ ALWAYS provide meaningful error messages
✓ ALWAYS log errors with context
✓ ALWAYS have fallback behavior for failures
✓ NEVER fail silently without logging

NEVER:
✗ Use bare except: clauses
✗ Ignore potential errors
✗ Assume "it won't fail"
✗ Leave error messages generic
✗ Fail without logging
```

**Error Handling Template:**
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}", extra={
        'operation': 'risky_operation',
        'context': context_info,
        'timestamp': datetime.utcnow()
    })
    return fallback_value  # Graceful degradation
except Exception as e:
    logger.critical(f"Unexpected error: {e}", exc_info=True)
    raise  # Re-raise unexpected errors
```

---

### Standard #11: Type Safety & Validation

```
DIRECTIVE:
✓ ALWAYS use type hints for all function parameters and returns
✓ ALWAYS validate input parameters before processing
✓ ALWAYS use dataclasses for structured data
✓ ALWAYS check for None on optional parameters
✓ NEVER assume data format - validate explicitly

NEVER:
✗ Skip type hints
✗ Process unvalidated input
✗ Use bare dicts for structured data
✗ Assume optional parameters are present
```

**Type Safety Template:**
```python
from typing import Optional
from dataclasses import dataclass

@dataclass
class ValidatedInput:
    required_field: str
    optional_field: Optional[int] = None

def process(data: ValidatedInput) -> Result:
    """Process validated input with type safety."""
    if not data.required_field:
        raise ValueError("required_field cannot be empty")
    
    if data.optional_field is not None and data.optional_field < 0:
        raise ValueError("optional_field must be non-negative")
    
    # Safe to process
    return Result(...)
```

---

### Standard #12: Complete Feature Implementation

```
DIRECTIVE:
✓ ALWAYS implement ALL specified features before delivery
✓ ALWAYS include edge case handling
✓ ALWAYS implement error recovery
✓ NEVER leave TODO comments in delivered code
✓ NEVER deliver partial implementations

NEVER:
✗ Ship with "TODO: implement later"
✗ Skip edge cases
✗ Assume "happy path only"
✗ Defer error handling
✗ Deliver incomplete features
```

**Feature Completeness Checklist:**
- [ ] All requirements implemented
- [ ] Edge cases handled
- [ ] Error conditions managed
- [ ] Performance optimized
- [ ] Security considered
- [ ] Documentation complete
- [ ] Tests written and passing
- [ ] No TODO comments

---

### Standard #13: Performance Verification

```
DIRECTIVE:
✓ ALWAYS benchmark performance-critical code
✓ ALWAYS confirm performance targets met before delivery
✓ ALWAYS include performance tests
✓ ALWAYS profile if performance uncertain
✓ NEVER assume "it's probably fast enough"

NEVER:
✗ Skip performance testing
✗ Deliver without benchmarks
✗ Guess at performance
✗ Ignore performance regressions
```

**Performance Testing Requirements:**
- Benchmark critical paths
- Test with realistic data volumes
- Verify latency targets met
- Check memory usage acceptable
- Profile if uncertain
- Document performance characteristics

---

### Standard #14: Code Style Consistency

```
DIRECTIVE:
✓ ALWAYS match existing codebase style EXACTLY
✓ ALWAYS use consistent naming conventions
✓ ALWAYS follow language-specific best practices
✓ NEVER introduce new patterns without justification
✓ NEVER mix styles within same component

NEVER:
✗ Invent your own style
✗ Mix camelCase and snake_case
✗ Use inconsistent indentation
✗ Ignore existing patterns
```

**Style Guidelines:**
- Match existing code style exactly
- Use project's naming conventions
- Follow language idioms
- Maintain consistency throughout
- Document any necessary deviations

---

## Testing & Validation Standards (3 Directives)

### Standard #15: Multi-Level Testing

```
DIRECTIVE:
✓ ALWAYS include unit tests for individual functions
✓ ALWAYS include integration tests for component interactions
✓ ALWAYS include performance tests for speed-critical code
✓ ALWAYS include edge case tests for boundary conditions
✓ NEVER skip testing because "it looks right"

NEVER:
✗ Ship untested code
✗ Test only happy paths
✗ Skip integration testing
✗ Ignore edge cases
✗ Assume tests aren't needed for "simple" code
```

**Test Coverage Requirements:**
- **Unit Tests:** All public functions
- **Integration Tests:** All component interactions
- **Performance Tests:** All time-critical operations
- **Edge Case Tests:** Boundary conditions, null values, extreme inputs
- **Failure Tests:** Error conditions, timeouts, exceptions

---

### Standard #16: Pre-Deployment Validation

```
DIRECTIVE:
✓ ALWAYS run complete test suite before deployment
✓ ALWAYS verify on test environment first
✓ ALWAYS check backward compatibility
✓ ALWAYS validate rollback procedure works
✓ NEVER deploy directly to production without validation

NEVER:
✗ Skip pre-deployment testing
✗ Deploy without verification
✗ Assume backward compatibility
✗ Deploy without rollback plan
```

**Pre-Deployment Checklist:**
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Backward compatibility verified
- [ ] Integration points tested
- [ ] Rollback procedure documented and tested
- [ ] Deployment script tested
- [ ] Configuration validated

---

### Standard #17: Integration Verification

```
DIRECTIVE:
✓ ALWAYS test integration points bidirectionally
✓ ALWAYS verify dependencies are available
✓ ALWAYS test error conditions in integrations
✓ ALWAYS have fallback for integration failures
✓ NEVER assume external systems work as documented

NEVER:
✗ Skip integration testing
✗ Test only success scenarios
✗ Assume dependencies are reliable
✗ Ignore failure modes
```

**Integration Testing Requirements:**
- Test in both directions (A→B and B→A)
- Verify dependency versions
- Test timeout handling
- Test connection failures
- Test malformed responses
- Verify retries work
- Confirm fallbacks engage

---

## Documentation Standards (3 Directives)

### Standard #18: Complete Inline Documentation

```
DIRECTIVE:
✓ ALWAYS include docstrings for all functions/classes
✓ ALWAYS document parameters, returns, and exceptions
✓ ALWAYS include usage examples in docstrings
✓ ALWAYS explain WHY, not just WHAT
✓ NEVER leave implementation details undocumented

NEVER:
✗ Skip docstrings
✗ Write "self-documenting code" without docs
✗ Document only what is obvious
✗ Omit usage examples
✗ Skip exception documentation
```

**Docstring Template:**
```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief one-line description.
    
    Detailed explanation of what the function does and WHY it exists.
    Include any important context or design decisions.
    
    Args:
        param1: Description of param1, including constraints
        param2: Description of param2, including valid ranges
        
    Returns:
        Description of return value and its structure
        
    Raises:
        SpecificError: When and why this error occurs
        AnotherError: Conditions triggering this error
        
    Example:
        >>> result = function_name("value", 42)
        >>> print(result)
        Expected output
        
    Notes:
        Any important implementation details, performance characteristics,
        or gotchas that users should know about.
    """
```

---

### Standard #19: Comprehensive External Documentation

```
DIRECTIVE:
✓ ALWAYS include README with overview and quick start
✓ ALWAYS include API reference with all public functions
✓ ALWAYS include integration guide with examples
✓ ALWAYS include FAQ with common questions
✓ ALWAYS include troubleshooting guide

NEVER:
✗ Deliver code without documentation
✗ Write documentation as afterthought
✗ Assume code is self-explanatory
✗ Skip examples
✗ Omit troubleshooting
```

**Required Documentation:**
1. **README.md** - Overview, quick start, key features
2. **API_REFERENCE.md** - All public APIs documented
3. **INTEGRATION_GUIDE.md** - How to integrate, examples
4. **QUICK_REFERENCE.md** - API cheat sheet
5. **FAQ.md** - Common questions and answers
6. **TROUBLESHOOTING.md** - Common issues and fixes
7. **DEPLOYMENT_GUIDE.md** - Step-by-step deployment

---

### Standard #20: Example-Driven Documentation

```
DIRECTIVE:
✓ ALWAYS include working examples for each major feature
✓ ALWAYS test that examples actually work
✓ ALWAYS include both simple and complex examples
✓ ALWAYS document common pitfalls
✓ NEVER provide pseudocode where real code is expected

NEVER:
✗ Write examples that don't run
✗ Skip examples for "obvious" features
✗ Provide only trivial examples
✗ Omit edge case examples
```

**Example Quality Requirements:**
- Examples must run without modification
- Include simple "hello world" example
- Include complex real-world example
- Show common pitfalls and solutions
- Demonstrate error handling
- Cover main use cases

---

## Architecture & Design Standards (4 Directives)

### Standard #21: Future-Proof Design

```
DIRECTIVE:
✓ ALWAYS design for extensibility
✓ ALWAYS consider "what if this needs to scale 10x"
✓ ALWAYS use configuration over code changes
✓ ALWAYS document extension points
✓ NEVER hard-code values that might change

NEVER:
✗ Design for only current requirements
✗ Hard-code limits
✗ Assume scale won't change
✗ Make extension difficult
```

**Future-Proofing Checklist:**
- [ ] Configuration externalized
- [ ] Extension points documented
- [ ] Scalability considered
- [ ] No hard-coded limits
- [ ] Plugin architecture possible
- [ ] Backward compatibility planned

---

### Standard #22: Dependency Management

```
DIRECTIVE:
✓ ALWAYS minimize external dependencies
✓ ALWAYS pin dependency versions explicitly
✓ ALWAYS document why each dependency is needed
✓ ALWAYS have fallback for optional dependencies
✓ NEVER use deprecated libraries

NEVER:
✗ Add dependencies casually
✗ Use unpinned versions
✗ Include unused dependencies
✗ Ignore deprecation warnings
```

**Dependency Standards:**
- Pin versions: `requests==2.31.0` not `requests>=2.0`
- Document each dependency's purpose
- Prefer stdlib over external libraries
- Test with fallbacks for optional deps
- Review dependencies regularly

---

### Standard #23: Configuration & Standards Alignment

```
DIRECTIVE:
✓ ALWAYS match existing project standards (headers, naming, structure)
✓ ALWAYS verify configuration files are valid (JSON, YAML)
✓ ALWAYS follow established conventions
✓ ALWAYS document deviations with justification
✓ NEVER introduce inconsistencies with existing patterns

NEVER:
✗ Create new conventions without reason
✗ Mix standards within project
✗ Skip validation of config files
✗ Deviate from patterns arbitrarily
```

**Standards Alignment Checklist:**
- [ ] Headers match existing format
- [ ] Naming follows conventions
- [ ] Structure aligns with patterns
- [ ] Config files validated
- [ ] No unexplained deviations
- [ ] Consistency maintained

---

### Standard #24: Comprehensive Verification Checklist

```
DIRECTIVE:
✓ ALWAYS create verification checklist before starting
✓ ALWAYS check off each item before declaring done
✓ ALWAYS include rollback verification
✓ ALWAYS document what was verified and how
✓ NEVER skip checklist items due to time pressure

NEVER:
✗ Work without checklist
✗ Skip items to finish faster
✗ Check boxes without actually verifying
✗ Ignore failed checks
```

**Master Verification Template:**
```markdown
## Pre-Deployment Verification

### Code Quality
- [ ] All functions have docstrings
- [ ] Type hints throughout
- [ ] Error handling complete
- [ ] No TODO comments
- [ ] Style matches existing code

### Testing
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Performance tests passing
- [ ] Edge cases tested
- [ ] Error conditions tested

### Documentation
- [ ] README complete
- [ ] API reference complete
- [ ] Examples tested and working
- [ ] Integration guide written
- [ ] FAQ and troubleshooting included

### Deployment
- [ ] Pre-deployment tests passing
- [ ] Configuration validated
- [ ] Backup created
- [ ] Rollback tested
- [ ] Deployment script tested

### Verification
- [ ] Component tested in deployed location
- [ ] Integration points verified
- [ ] Performance benchmarks met
- [ ] No regressions introduced
- [ ] All acceptance criteria met
```

---

## Enforcement

### How These Standards Are Applied

**Pre-Build:**
- Review relevant standards for task
- Create verification checklist
- Plan testing approach

**During Build:**
- Follow standards continuously
- Test incrementally
- Document as you go

**Pre-Delivery:**
- Run complete verification checklist
- Fix any non-compliance
- Document what was verified

**Post-Delivery:**
- Monitor for issues
- Learn from any problems
- Update standards if needed

---

## Exceptions

### When Standards May Be Relaxed

**ONLY for:**
- Exploratory prototypes explicitly marked as experimental
- User explicitly requests "quick and dirty" version
- Standards conflict documented with justification

**NEVER for:**
- Production code
- Governance components
- Security-related code
- Integration points
- User-facing features

---

## Quality Metrics

### Success Indicators

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Zero-Rework Rate** | >95% | Deliveries requiring no fixes |
| **First-Time-Right** | >90% | No bugs found post-delivery |
| **Documentation Complete** | 100% | All docs present and accurate |
| **Test Coverage** | >85% | Code covered by tests |
| **Performance Targets Met** | 100% | All benchmarks passed |
| **Standards Compliance** | >98% | Checklist items passed |

### Quality Audit

**Monthly Review:**
- Count .1 version updates (target: 0)
- Count post-delivery bugs (target: <5%)
- Review user corrections (learning source)
- Analyze rework incidents
- Update standards if patterns emerge

---

## Integration with Learning System

### Feedback Loop

**When Standards Not Met:**
1. Incident logged to meta-learning-log
2. Pattern analysis for systematic issues
3. Standards updated if needed
4. Verification checklist enhanced
5. Prevention measures added

**When Standards Exceeded:**
1. Best practices documented
2. Examples added to standards
3. Patterns shared across projects
4. Efficiency improvements codified

---

## Relationship to Other Governance Components

### Integrates With

| Component | Integration |
|-----------|-------------|
| **meta-learning-log.md** | Learns from quality incidents |
| **cursor-native-reasoning.md** | Quality checks in reasoning steps |
| **/forge command** | Quality gates in autonomous execution |
| **/reasoning command** | Quality validation in analysis |
| **rule-registry.json** | Enforceable quality rules |

### Enforced By

- Pre-commit hooks (future)
- Governance validator
- Review checklists
- Automated testing
- Continuous monitoring

---

## Implementation Priority

### Tier 1: Always Enforce (Critical)

- Canonical headers exact match
- Complete error handling
- Production-ready delivery
- Zero-rework standard
- Comprehensive testing

### Tier 2: Strongly Enforce (High Priority)

- Documentation completeness
- Type safety
- Performance verification
- Integration validation
- Style consistency

### Tier 3: Enforce When Applicable

- Future-proofing design
- Dependency management
- Example quality
- Advanced testing

---

## User's Quality Philosophy

**Explicit Statements:**
> "I NEVER want you to rush - i ALWAYS prefer quality over speed"

> "all code all projects every iteration we do MUST be production quality"

> "even the MVP must be ready to deploy"

> "i do not want to debug or notice simple upgrades that should've been made"

**Translation:** Excellence is the baseline, not the aspiration.

---

## Commitment

**Every deliverable from this AI will:**
- Meet or exceed these 24 standards
- Be production-ready on first delivery
- Require zero debugging
- Need no .1 version fixes
- Exemplify top-1% quality

**This is not optional. This is the standard.**

---

_These standards define what "production quality" means in this deployment._  
_They are not aspirational - they are mandatory._  
_Quality over speed. Always._

**📖 Load this file at every session startup to maintain quality standards.**

