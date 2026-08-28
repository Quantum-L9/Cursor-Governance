Yes — the bridge should make **today’s manual Claude Code + DeepSeek execution look like a PEC execution from the outside**, without pretending PEC itself is ready.

The rule is:

> **Do not build a temporary orchestrator. Build a temporary execution adapter around the artifacts PEC is supposed to own.**

## Bridge architecture

```text
                         HUMAN
                           │
                    arbitrary intent
                           │
                           ▼
                ┌─────────────────────┐
                │  SOURCE INTENT      │
                │ immutable / hashed  │
                └──────────┬──────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │ BOOTSTRAP COMPILER  │
                │ currently human +   │
                │ Claude architecture │
                └──────────┬──────────┘
                           │
          ┌────────────────┼──────────────────┐
          ▼                ▼                  ▼
    Semantic Intent   Repo Grounding    Requirement Map
          │                │                  │
          └────────────────┼──────────────────┘
                           ▼
                ┌─────────────────────┐
                │ EXECUTION CONTRACT  │
                │ PEC-shaped, but     │
                │ manually compiled   │
                └──────────┬──────────┘
                           │
                           ▼
                  Claude Code Desktop
                    + DeepSeek worker
                           │
                           ▼
                ┌─────────────────────┐
                │ EVIDENCE BUNDLE     │
                │ diffs/tests/claims  │
                │ residual unknowns   │
                └──────────┬──────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      human acceptance              PEC SHADOW
                                    compile same
                                      intent
                                        │
                                        ▼
                              compare artifacts
```

The bridge has **two parallel lanes**:

### Production lane

```text
human intent
→ manually grounded contract
→ Claude/DeepSeek
→ evidence
→ repo
```

This gets work done.

### PEC shadow lane

```text
same exact human intent
→ PEC compiler
→ whatever IR/Blueprint it currently produces
→ NO EXECUTION
→ semantic diff against trusted manual contract
```

This fixes PEC using real workloads.

That is the key.

---

# 1. Make every manual job a `Bootstrap Contract Pack`

Don't just paste prompts into Claude Code.

Every piece of work gets a directory/artifact set conceptually like:

```text
bootstrap/
  <work-id>/
    00-source-intent.md
    01-intent-ir.yaml
    02-grounding.yaml
    03-requirements.yaml
    04-execution-contract.yaml
    05-evidence/
    06-completion.yaml
```

This is **not another runtime protocol**.

It's a temporary compilation record.

Eventually:

```text
00 → PEC IR0
01 → PEC semantic IR
02 → repository-grounding IR
03 → requirement/authority IR
04 → Blueprint/Task Contracts
05 → PEC receipts/evidence
06 → Program completion projection
```

So none of the intellectual work is wasted.

---

# 2. Raw intent remains sacred

`00-source-intent.md` is immutable.

Example:

```text
Make risk/authority first-class for consequential PEC effects.

Reuse the existing authorization, evidence, receipt, transport,
Controller, and replanning machinery.

Add downstream impact computation and RiskPacket.

Wire it through Assurance and execution.

Make existing replanning risk-aware.

Do not create duplicate authorities or protocols.
```

Hash it.

Never rewrite it into “better requirements” and throw away the original.

Everything downstream maintains provenance:

```text
requirement R17
  source:
    file: 00-source-intent.md
    span: ...
```

This becomes the foundation of the future PEC compiler's semantic-loss tests.

---

# 3. `IntentIR` should be permissive but explicit

The bridge compiler—currently us + Claude—normalizes human intent into something like:

```yaml
intent_id: RISK-PEC-001

objective:
  - integrate consequence-aware execution into PEC
  - make existing replanning risk-aware

preserve:
  - Program Controller authority
  - existing REPLAN_CONTRACT
  - existing authorization model
  - existing evidence model
  - existing receipt families
  - TransportPacket sovereignty

required_capabilities:
  - downstream impact computation
  - addressable risk artifact
  - Assurance admission
  - execution-time freshness enforcement
  - outcome-driven replan trigger

forbidden:
  - competing_controller
  - competing_transport
  - duplicate_replanner
  - duplicate_authorization_model
  - duplicate_evidence_model

unknowns: []
```

This is where messy English becomes semantic structure.

But it **still isn't an implementation plan**.

---

# 4. Then perform the Microscope pass

`02-grounding.yaml` is where we record reality.

For every concept:

```yaml
- concept: runtime_replanning
  disposition: HARDEN_WIRE_EXISTING
  canonical:
    - path: environment/program-execution/core/shared/REPLAN_CONTRACT.yaml
    - path: environment/program-execution/.../pec/replan.py
  evidence:
    - propose_exists
    - verify_exists
    - activate_exists
    - stale_detection_exists
  missing:
    - autonomous_trigger_loop
    - risk_aware_candidate_selection
```

Another:

```yaml
- concept: risk_packet
  disposition: CREATE
  canonical_owner: l9-assurance
  consumers:
    - PEC
  must_not_duplicate:
    - authorization_model
    - evidence_model
    - TransportPacket
```

This artifact is incredibly important because **this is exactly the intelligence PEC currently lacks**.

---

# 5. Requirements come after grounding

Then:

```text
intent
+
actual repo truth
=
requirements
```

Not:

```text
intent
=
tasks
```

Example:

```yaml
requirements:

  - id: RISK-001
    statement: >
      Every consequential effect SHALL possess a fresh
      exact-subject risk admission before EXECUTING.
    disposition: CREATE
    owner: PEC Controller
    depends_on:
      - RISK-004
      - RISK-007

  - id: REPLAN-001
    statement: >
      Existing canonical replanning lifecycle SHALL be preserved.
    disposition: KEEP

  - id: REPLAN-002
    statement: >
      Runtime replanning SHALL add autonomous trigger and
      candidate-selection machinery without introducing another
      plan authority.
    disposition: HARDEN_WIRE_EXISTING
```

Now Claude isn't being asked to infer architecture while coding.

---

# 6. The temporary Execution Contract is effectively a hand-compiled PEC Task Contract

This is the only thing DeepSeek receives as authority.

Something like:

```yaml
contract_id: PEC-RISK-C08

objective:
  implement PEC-native ImpactEngine and shadow RiskPacket production

base_revision: <exact SHA>

authority:
  allowed:
    - inspect entire repository
    - modify listed implementation seams
    - add tests
  forbidden:
    - merge
    - push unless separately authorized
    - modify Program authority semantics
    - create alternate transport
    - create alternate replanner
    - create alternate evidence model

read_before_write:
  - AUTHORIZATION_MODEL.yaml
  - EVIDENCE_MODEL.yaml
  - REPLAN_CONTRACT.yaml
  - contracts.py
  - controller.py
  - replan.py
  - peer_execution/
  - l9-assurance schemas/profiles

canonical_owners:
  program_state: PEC Controller
  authorization: existing PEC authorization + Assurance
  transport: Gate TransportPacket
  replanning: existing REPLAN_CONTRACT
  evidence: EVIDENCE_MODEL + Assurance

required_changes:
  - implement ImpactAssessment
  - implement deterministic PEC-native ImpactEngine
  - produce content-addressed shadow RiskPacket
  - do not enforce execution admission yet

acceptance:
  - deterministic identical input -> identical assessment digest
  - unknown dependency coverage != zero impact
  - no execution authority introduced
  - existing PEC tests remain green
  - new characterization tests green

required_evidence:
  - changed_files
  - test_commands
  - test_results
  - resulting revision
  - residual_unknowns

stop_conditions:
  - discovered canonical mechanism contradicts contract
  - authority widening required
  - proposed change duplicates existing canonical owner
```

This is much safer than:

> “Here is the ADR; go implement it.”

---

# 7. Claude/DeepSeek should be executor + local archaeologist

There is one nuance.

The contract should be authoritative, but **not stupidly brittle**.

Claude must still be allowed to discover:

> “This exact symbol moved.”

> “This functionality already landed.”

> “This planned file would duplicate something.”

When that happens:

```text
CONTRACT EXPECTATION
        ≠
LIVE REPOSITORY
```

the worker does **not blindly obey**.

It emits:

```text
CONTRACT_DRIFT
```

with evidence.

Then either:

```text
safe equivalent + same architecture
→ adapt within contract

material architecture difference
→ STOP
```

This mimics what PEC eventually needs.

---

# 8. Every execution returns an evidence bundle

No conversational:

> “Done!”

Instead:

```yaml
contract_id: PEC-RISK-C08
status: COMPLETE

base_revision: ...
result_revision: ...

changed:
  - path: ...
    reason: ...

validation:
  - command: ...
    exit_code: 0
    evidence_ref: ...

requirements:
  RISK-001: satisfied
  RISK-002: satisfied

architecture_boundaries:
  new_controller: false
  new_transport: false
  duplicate_replanner: false

unknowns:
  - ...

residual_work:
  - ...
```

This becomes future PEC fixture data.

---

# 9. Now the really powerful part: shadow-compile every contract through PEC

For each bootstrap job:

```text
              SAME SOURCE INTENT
                  /          \
                 /            \
                ▼              ▼
        trusted manual      current PEC
          compilation        compiler
                │              │
                ▼              ▼
        trusted contract     Blueprint
                │              │
                └──────┬───────┘
                       ▼
                SEMANTIC DIFF
```

Compare things such as:

```text
objective
requirements
prohibitions
unknowns
canonical ownership
already-existing machinery
planned creations
authority ceiling
acceptance conditions
execution dependencies
```

PEC doesn't need to produce identical wording.

It needs semantic equivalence.

---

# 10. This gives us a measurable PEC convergence score

For every real job:

```text
Intent Fidelity
Grounding Accuracy
Disposition Accuracy
Task Completeness
Authority Correctness
Evidence Completeness
Execution Correctness
```

Example:

```text
Intent fidelity:          100%
Prohibition retention:    100%
Existing-feature recall:   86%
False CREATE count:          2
Authority violations:        0
Task coverage:              94%
```

Then fix the compiler.

Run the same fixture again.

Eventually:

```text
False CREATE = 0
Material intent loss = 0
Authority widening = 0
Manual repair = 0
```

That's how PEC earns execution authority.

---

# 11. Gradual handoff instead of one giant flip

We don't go:

```text
manual
   ↓
PEC DOES EVERYTHING
```

Use staged transfer.

### Bridge Stage A — today

```text
Manual compile
Manual contracts
Claude/DeepSeek executes

PEC = shadow only
```

### Stage B

PEC owns:

```text
source capture
semantic normalization
```

Human verifies.

Manual grounding/contracts remain.

### Stage C

PEC owns:

```text
source capture
semantic normalization
repo grounding
reconciliation
```

Human verifies.

### Stage D

PEC owns compilation through Blueprint.

```text
PEC → Blueprint
human verifies
Claude/DeepSeek executes contracts
```

PEC still does **not** execute.

### Stage E

PEC owns:

```text
compile
Controller
execution
receipts
```

for low-consequence fixtures.

Claude Desktop becomes just another worker/provider.

### Stage F

RiskPacket lands.

PEC gains bounded consequential execution.

### Stage G

Replanning closes.

PEC gains mission-execution autonomy.

### Stage H

PEC constructs the World Model.

Then:

```text
World Model → ImpactEngine
ImpactEngine → better replanning
better replanning → larger PEC campaigns
larger campaigns → faster factory construction
```

There's your flywheel.

---

# 12. Important: Claude Desktop shouldn't disappear

Eventually DeepSeek/Claude Code becomes:

```text
PEC
 │
 ▼
CanonicalExecutionRequest
 │
 ▼
Provider adapter
 │
 ▼
Claude Code / DeepSeek
```

Meaning all the execution experience you're accumulating now should inform the future provider interface.

We're not using a disposable workaround.

We're effectively **prototyping one PEC executor manually**.

---

# 13. And RiskPacket fits naturally into the bridge

During bootstrap:

```text
execution contract
  contains declared mutation ceiling
  and explicit authority bounds
```

Later:

```text
execution contract
        │
        ▼
exact runtime EffectSubject
        │
        ▼
ImpactEngine
        │
        ▼
RiskPacket
        │
        ▼
Assurance
```

Don't try to manually recreate runtime RiskPacket semantics inside Bootstrap Contracts.

Bootstrap contracts declare the **maximum allowed authority**.

RiskPacket later determines whether **this actual state transition right now** fits inside it.

Different jobs.

---

# 14. The immediate next move

I would now create the first bridge contract:

```text
BOOTSTRAP-PEC-000
```

Objective:

> **Build the PEC compiler conformance harness and establish the manual-contract ↔ PEC-shadow comparison loop.**

Not fix everything.

Its deliverables should be:

```text
intent fixture corpus
      +
bootstrap artifact schema
      +
semantic assertion model
      +
PEC shadow compiler runner
      +
manual-vs-PEC semantic comparator
      +
baseline failure report
```

Then every contract we execute from that point onward becomes:

1. useful repository work,
2. a PEC compiler test,
3. a PEC training/debugging case,
4. evidence toward PEC graduation.

So instead of:

```text
we repair PEC
then someday dogfood PEC
```

we get:

```text
every piece of work
      ↓
repairs the system
      +
tests the compiler
      +
expands the fixture corpus
      +
moves PEC toward replacing the bridge
```

**That's how we bridge the gap without building throwaway infrastructure.**

And once that harness exists, I would feed the **PEC compiler repair itself** through this exact bridge before RiskPacket implementation starts.
