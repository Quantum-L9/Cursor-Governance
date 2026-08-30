🔬 **Microscope verdict:** the architecture is sound, but the order we were about to implement it was wrong.

The deepest finding is that **RiskPacket is not PEC's next problem**. PEC already has surprisingly strong runtime law—Program Lock, authorization intersection, exact rendered contracts, evidence semantics, real replan lifecycle, provider-neutral peer execution, receipt validation—but its **front half does not yet reliably preserve arbitrary human intent into that runtime**.

If we build RiskPacket first, we'd be giving a very disciplined execution engine instructions from a compiler we don't yet trust.

The optimal convergence is:

```text
FIRST:
human intent → faithful normalized IR → grounded live-repo model
             → reconciled requirements → correct Blueprint
             → reliable PEC execution

THEN:
exact effect → ImpactEngine → RiskPacket → Assurance
             → existing PEC execution → existing receipts
             → outcome comparison → existing replanner
```

I traced the architecture-bearing seams across current `Cursor-Governance`, `l9-assurance`, and Gate SDK. I would still require the executing Claude session to enumerate every companion schema/test/import locally before touching code, because GitHub's rendered surface is not a substitute for local symbol/call-graph inspection.

# 1. The biggest defect is exactly what you've been complaining about

PEC currently recognizes two input contracts, but the live behavior doesn't match your doctrine.

The compiler documents:

```text
program-execution.intent.v1
    = minimal human goal

l9.program-execution.architecture-intent.v1
    = dense architecture document
```

and the architecture path has a fairly sophisticated:

```text
source
→ segmentation
→ extraction
→ grounded IR
→ coverage/critic/repair
→ campaign-source.v2
→ Blueprint
→ PEC
```

pipeline. ([GitHub][1])

But the live campaign router currently **recognizes `PROGRAM_INTENT_V1` and deliberately excludes it from supported campaign input kinds**. The rejection tells the operator to synthesize/convert it before campaign execution. Meanwhile ordinary unmarked Markdown defaults toward the brief path unless the operator explicitly chooses architecture classification. ([GitHub][2])

That's backwards relative to the intended product:

```text
BAD

human
  ↓
"which internal PEC input contract
 am I supposed to write?"
  ↓
compiler


RIGHT

human
  ↓
anything intelligible
  ↓
compiler determines how to normalize it
```

**That is P0.**

The human should not choose `brief` versus `architecture` versus `program intent` to obtain correct semantics.

Those can remain internal compiler strategies.

---

# 2. Keep the strict schemas — move strictness downstream

`compiler/intent.py` is actually doing the right thing *for a canonical IR*. It strongly validates `program-execution.intent.v1` and intentionally rejects tasks, files, waves and prompts from that minimal intent representation. ([GitHub][3])

Don't loosen it.

Add something *before* it.

The converged compiler should look like:

```text
               ANY HUMAN INPUT
                       │
                       ▼
              IR0 SourceCapture
        exact original / hash / units
                       │
                       ▼
              IR1 SemanticIntent
        objective / requirements
        constraints / prohibitions
        acceptance / unknowns
                       │
                       ▼
            IR2 RepositoryGrounding
        live implementations / owners
        callers / schemas / tests
        canonical / legacy / duplicate
                       │
                       ▼
              IR3 Reconciliation
        ALREADY_SATISFIED
        MERGE_WITH_EXISTING
        HARDEN_WIRE
        CREATE
        DELETE_SUPERSEDED
        UNKNOWN
                       │
                       ▼
          IR4 Requirement + Authority
        SHALL / SHOULD / MAY
        evidence / ceilings / risk
        forbidden moves
                       │
                       ▼
             IR5 ExecutionGraph
        tasks / dependencies / gates
        rollback / resources
                       │
                       ▼
                   BLUEPRINT
                       │
                 validation
                       │
                       ▼
                 PROGRAM LOCK
```

That's the compiler PEC was supposed to be.

The strong strictness at Blueprint/Program Lock is an asset.

**Input strictness is the bug.**

---

# 3. I found a semantic-loss trap in architecture compilation

The architecture source-capture code deliberately looks for uppercase normative signals like:

```text
MUST
MUST NOT
NEVER
DO NOT
REQUIRED
ACCEPTANCE
```

and the implementation intentionally does **not** treat ordinary lowercase conversational equivalents as the same lexical signal. ([GitHub][4])

The coverage system is good in concept: every material source unit should acquire a disposition and traceability into semantic items/tasks. But its mechanical material-unit safety net heavily depends on that normative classification. ([GitHub][5])

So this perfectly reasonable input:

> don't replace assurance, just integrate with it

can be more vulnerable to silent semantic loss than:

> DO NOT REPLACE ASSURANCE

That violates your desired UX.

The correct fix is **not** removing the uppercase mechanism.

Keep it as a high-confidence deterministic anchor.

Add semantic materiality over *all* source units:

```text
LEXICAL NORMATIVE DETECTOR
       +
SEMANTIC MATERIALITY DETECTOR
       +
NEGATION / CONTRADICTION CHECK
       +
SOURCE-GROUNDED CRITIC
       ↓
unit disposition required
```

The existing IR is already designed around an excellent principle:

> extractor output is a claim, not authority.

It tracks source references, grounding and explicit semantic kinds such as requirement, constraint, prohibition, unknown, risk, acceptance, implementation seam and validation. ([GitHub][6])

Preserve that.

Make it harder for meaning to disappear.

---

# 4. The repo-grounding layer is nowhere near microscopic enough yet

`repo_truth.py` currently discovers useful high-level facts:

```text
repo root
remote
revision
owner
test command
package manager
runtime
constraints
ADR files
validation commands
rollback definitions
```

and explicitly prioritizes runtime/machine contracts above ADR/prose. That's good. ([GitHub][7])

But it isn't enough for architecture compilation.

It doesn't give PEC the equivalent of what we manually did in this conversation:

> “Wait, `REPLAN_CONTRACT.yaml` already exists.”

> “Wait, `replan.py` actually implements activation.”

> “Don't make another ActionReceipt; extend the existing receipt family.”

> “Assurance already owns this protocol boundary.”

That's why I would introduce a genuine **Repository Grounding IR** rather than overloading `RepoTruth`.

It needs to establish:

```text
artifact
symbol
definition
caller / callee
import / dependency
schema
test
runtime owner
authority owner
producer
consumer
generated?
deprecated?
superseded?
canonical?
duplicate?
active path?
```

Then connect semantic requirements to those facts.

That gives the compiler a disposition before task synthesis:

```text
"build replanner"
      │
      ▼
live grounding
      │
      ├── REPLAN_CONTRACT exists
      ├── replan.py exists
      ├── runtime activation exists
      └── several operations incomplete
              │
              ▼
       HARDEN_WIRE_EXISTING

not:

       CREATE REPLANNER
```

This is probably one of the most important components of PEC.

It's what turns an LLM planner into an **architecture-aware compiler**.

---

# 5. Task synthesis also has two dangerous shortcuts

The architecture lowering currently uses document section/headings as natural task boundaries. ([GitHub][8])

That's acceptable as a hint.

It is not a safe ownership rule.

An ADR section titled “Risk integration” may touch:

```text
PEC Controller
Assurance protocol
peer execution
receipt schemas
replan runtime
Gate lineage
```

Those are separate ownership seams.

Task boundaries should therefore be determined from:

```text
semantic obligation
        ×
canonical owner
        ×
implementation seam
        ×
dependency edge
```

with headings only as a weak clustering hint.

More concerning: when architecture lowering cannot identify a declared mutation path, current lowering can fall back to a documentation path such as a task document, while generated task risk can be initialized very conservatively/simplistically. ([GitHub][8])

That can turn:

> “we don't know where this implementation belongs”

into:

> “write a document and declare progress.”

Wrong.

Unknown implementation seam should become:

```text
DISCOVERY TASK
  read-only
     │
     ▼
produces grounded seam evidence
     │
     ▼
dependent mutation task
```

No fake write target.

No pretend T0 certainty.

---

# 6. Launchability is currently repairing compilation too late

Launchability has useful logic that can infer missing validation commands from repository context. But it can then write those synthesized validations back into Task Cards after initial Blueprint generation/validation. ([GitHub][9])

That's a smell.

Long-term:

```text
compiler
  ↓
complete all prescriptive semantics
  ↓
seal Blueprint
  ↓
validate
  ↓
launchability
       = ASSERT ONLY
```

Not:

```text
compile
→ validate
→ launchability discovers missing semantics
→ mutate compiled artifact
→ continue
```

Don't rewrite that yet.

First characterize it with tests.

Then move synthesis upstream.

---

# 7. Runtime PEC is considerably healthier

This is why I'm strongly recommending fixing the compiler before rewriting runtime.

The current authorization law is already excellent.

Effective permission is the intersection of:

```text
governance
∩ exact approval
∩ Blueprint authorization ceiling
∩ Controller policy
∩ Source Contract request
∩ Rendered Contract exact-state binding
```

and lower layers may narrow but never widen authority. Credentials themselves are explicitly not authorization. ([GitHub][10])

Existing evidence law already requires:

```text
retrievability
exact revision/digest
reproducibility/inspection
producer
time
freshness
scoped support
```

([GitHub][11])

Existing ownership law already says roughly:

```text
Blueprint  → design-time scope/ceilings
Controller → mutable runtime truth
worker     → attempt execution/claims
Controller → verification verdict/state
```

([GitHub][12])

**Don't replace any of that.**

Risk integrates with it.

---

# 8. I found the exact RiskPacket insertion seam

The Rendered Contract is already almost the `GoverningStateSnapshot` I proposed earlier.

At render time PEC currently binds things such as:

```text
Program Lock digest
Source Contract digest
base SHA
branch/worktree
lease
attempt
plan revision
active replan revision
```

and hashes the resulting exact rendered contract. ([GitHub][13])

So I retract the idea of making a second canonical `GoverningStateSnapshot`.

That would duplicate truth.

The correct pipeline is:

```text
Source Contract
      +
current Controller truth
      +
lease / plan / revision / target state
              │
              ▼
       Exact EffectSubject
              │
              ▼
          ImpactEngine
              │
              ▼
       ImpactAssessment
              │
              ▼
          RiskPacket
              │
              ▼
           Assurance
              │
              ▼
       AssuranceDecision
              │
              ▼
    FINAL Rendered Contract
 binds risk + decision digests
              │
              ▼
        start_task()
              │
        LAST-MOMENT CHECK
              │
              ▼
          EXECUTING
```

Currently `start_task()` performs its runtime preconditions and then transitions to `EXECUTING`; there is no consequence/risk admission guard at that exact transition. ([GitHub][14])

**That's the enforcement seam.**

Not another state machine.

Not another Controller.

Risk admission is an orthogonal predicate on transition to consequential execution.

---

# 9. Peer execution needs almost no conceptual redesign

This part is nice.

The peer-execution substrate already validates:

```text
Program Lock
Rendered Contract
provider capability
permission profile
context manifest
contract/runtime consistency
terminal result/receipt
```

and converts the current contract into a provider-neutral `CanonicalExecutionRequest`. ([GitHub][15])

Therefore we don't need:

```text
RiskExecutor
RiskDispatcher
RiskPeerProtocol
```

Absolutely not.

We extend the existing chain:

```text
RenderedContract
    risk_packet_ref
    risk_packet_digest
    assurance_decision_ref
    assurance_decision_digest
          │
          ▼
CanonicalExecutionRequest
          │
          ▼
existing provider execution
          │
          ▼
existing attempt receipt
```

The existing attempt receipt already carries contract/program binding, base and candidate SHAs, changed files, validations, evidence and residual unknowns. ([GitHub][16])

Add risk lineage to that family.

Don't create “ActionReceipt 2.”

---

# 10. The replanner really exists

This is no longer speculative.

Canonical replanning law already provides:

```text
Controller-only activation
proposer != verifier
staleness detection
previous plan preserved on failure
append-only historical receipts
```

and defines allowed versus forbidden deltas. ([GitHub][17])

Allowed includes things such as:

```text
reversible implementation strategy
dependency-valid reorder
split into children
diagnostic additions
scoped runtime unknown
unknown resolution from evidence
retry of compliant path
```

Forbidden includes:

```text
objective
architecture
public contract
ownership
target set
authorization ceiling
accepted risk
mandatory convergence gates
historical evidence
```

That is excellent mission-execution law.

### But runtime and law are not yet fully congruent.

The runtime machinery implements the core lifecycle, but some operations represented by the contract are only partially realized. One concrete example: runtime split children can surface as pending admission rather than becoming a completely admitted executable subtree. ([GitHub][14])

So the replan work is:

```text
NOT:
build replanner

YES:
make every canonical replan operation
have complete runtime semantics
or fail explicitly as unsupported
```

Then add autonomous trigger/candidate machinery around it.

---

# 11. Assurance is where the cross-L9 RiskPacket protocol belongs

This was another microscope correction.

`l9-assurance` explicitly claims ownership of:

```text
JSON Schema protocol contracts
exact-subject evidence admission
producer/check trust
freshness/integrity/replay
controls
policy
waivers/unknowns
deterministic verdict reduction
immutable decisions
```

and explicitly refuses ownership of execution, routing, orchestration and repository mutation. ([github.com][18])

That is precisely the abstraction boundary RiskPacket needs.

Today its exact subject is primarily oriented around an exact Git revision.

A consequential-effect subject is richer:

```text
exact action
+
exact arguments
+
exact target
+
exact state
+
exact authority context
+
exact impact assessment
```

So RiskPacket should become an **Assurance protocol subject/profile**, not a PEC-private authorization format.

PEC owns:

```text
EffectSubject construction
ImpactEngine
ImpactAssessment
RiskPacket production
runtime enforcement
```

Assurance owns:

```text
canonical RiskPacket protocol/schema
admission controls
policy evaluation
immutable AssuranceDecision
```

The repo already organizes schemas, profiles and registries in exactly that style. ([GitHub][19])

---

# 12. Gate stays almost completely untouched

Gate SDK is already where we want it:

> `TransportPacket` is the canonical wire format; semantic changes create child packets; node-originated work returns through Gate; Gate owns routing. ([GitHub][20])

Therefore:

```text
RiskPacket ≠ transport
```

When risk artifacts cross L9 node boundaries:

```text
TransportPacket
    payload/ref → RiskPacket
```

and semantic transitions retain child-packet lineage.

Inside a local PEC process, don't gratuitously route internal Controller calls through Gate just to satisfy “packet lineage.” Content-addressed references are enough until an actual transport boundary is crossed.

---

# 13. Final converged architecture

This is the architecture I would lock now:

```text
                         HUMAN
                           │
                    arbitrary intent
                           │
                           ▼
                ┌────────────────────┐
                │ HUMAN INTENT FRONT │
                │ permissive ingress │
                └─────────┬──────────┘
                          │
                          ▼
                  Source Capture IR
                          │
                          ▼
                   Semantic IR
                          │
                          ▼
               Repository Microscope
                          │
                          ▼
                  Reconciliation IR
                          │
                          ▼
              Requirements/Authority IR
                          │
                          ▼
                  Execution Graph
                          │
                          ▼
                      BLUEPRINT
                          │
                          ▼
                    PROGRAM LOCK
                          │
                          ▼
                 PROGRAM CONTROLLER
                          │
                   Source Contract
                          │
                          ▼
                  Exact EffectSubject
                          │
                          ▼
                 ┌────────────────┐
                 │  IMPACT ENGINE │
                 │ pure/read-only │
                 └───────┬────────┘
                         │
                 ImpactAssessment
                         │
                         ▼
                    RISKPACKET
                  exact/addressable
                         │
                         ▼
                     ASSURANCE
                         │
                         ▼
                AssuranceDecision
                         │
                         ▼
              final Rendered Contract
                         │
                   freshness guard
                         │
                         ▼
                    EXECUTING
                         │
                         ▼
                PEER EXECUTION
                         │
                         ▼
                 existing receipts
                         │
                         ▼
                outcome comparison
                         │
              ┌──────────┴─────────┐
              │                    │
            MATCH               DIVERGE
              │                    │
           continue                 ▼
                              ReplanTrigger
                                    │
                                    ▼
                            candidate generator
                             │      │      │
                             A      B      C
                             └──────┼──────┘
                                    ▼
                         REPLAN_CONTRACT containment
                                    │
                                    ▼
                              ImpactEngine
                                    │
                                    ▼
                         admissible candidate set
                                    │
                          deterministic dominance
                                    │
                                    ▼
                          independent verification
                                    │
                                    ▼
                      activation EffectSubject
                                    │
                              RiskPacket
                                    │
                              Assurance
                                    │
                                    ▼
                       Controller activates N+1
                                    │
                                    └─────────► LOOP
```

And later:

```text
World Model
     │
     └── becomes another ImpactSource
```

Nothing else changes.

That's how PEC can build the World Model before depending on it.

---

# 14. Implementation plan — execute these as contracts with Claude Code + DeepSeek

I would **not issue one monster contract**.

Use these sequential contracts. Each starts by reading every listed seam and its callers/tests/schemas before mutation, returns exact evidence, does not merge, and stops on architecture contradiction rather than improvising a second authority.

| Contract                                         | Objective                                                                                                    | Primary seams                                                                                                                                                   | Exit criterion                                                                                                                                         |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **C0 — PEC Baseline Microscope**                 | Reproduce current failures and establish characterization suite before changing semantics                    | `scripts/campaign_input.py`, `scripts/run_campaign.py`, compiler CLI, Blueprint validation, Controller bootstrap, peer-execution golden path, restart/reconcile | Exact failure matrix + tests reproducing every observed broken journey                                                                                 |
| **C1 — Unified Human Intent Ingress**            | Make raw human intent a supported public input without requiring operator knowledge of internal route/schema | `campaign_input.py`, minimal runner routing, new source-capture/normalization layer, existing `intent.py`, `resolver.py`                                        | one-liner, ADR, ordinary Markdown and explicit schema all normalize pre-side-effect; `program-execution.intent.v1` no longer dead-ends                 |
| **C2 — Semantic Fidelity Compiler**              | Prevent human meaning from falling out during normalization                                                  | `architecture_intent.py`, extractor, IR, coverage, critic/repair, tests                                                                                         | lowercase prohibitions/constraints, negation, conflicts and unknowns survive with source provenance                                                    |
| **C3 — Repository Microscope IR**                | Give compiler live implementation archaeology before task creation                                           | preserve `repo_truth.py`; add richer grounding/seam graph                                                                                                       | requirements classified as already satisfied / merge / harden / create / superseded / unknown with path+symbol evidence                                |
| **C4 — Grounded Lowering**                       | Synthesize tasks from semantic obligation × owner × implementation seam, not document formatting             | `architecture_to_campaign.py`, campaign-source lowering, synthesizer, validation inference                                                                      | no fake docs-path writes; unknown seam becomes discovery dependency; headings are hints only                                                           |
| **C5 — PEC Baseline Graduation**                 | Prove human intent → Blueprint → Program Lock → actual execution works before introducing risk               | entire golden path                                                                                                                                              | repeated end-to-end run with no manual artifact edits/private bypasses, restart-safe and provider-neutral                                              |
| **C6 — Replan Runtime Closure**                  | Bring runtime into exact agreement with existing `REPLAN_CONTRACT`                                           | `REPLAN_CONTRACT.yaml`, replan schema, `pec/replan.py`, Controller, projection/tests                                                                            | every allowed delta either has complete deterministic behavior or explicit fail-closed unsupported result                                              |
| **C7 — Assurance Consequential-Effect Protocol** | Introduce canonical RiskPacket/exact-effect subject in `l9-assurance`                                        | `schemas/v1`, registries, controls/claims/profiles, protocol bundle/tests                                                                                       | exact packet deterministically evaluated; changed subject/state/impact invalidates decision; no execution authority introduced                         |
| **C8 — PEC ImpactEngine + Shadow Risk**          | Compute actual runtime downstream impact without enforcement initially                                       | new Controller-owned risk package + current contract/runtime sources                                                                                            | deterministic content-addressed ImpactAssessments/RiskPackets for consequential effects; unknown ≠ zero                                                |
| **C9 — Risk Enforcement**                        | Bind RiskPacket/Assurance into exact execution                                                               | `contracts.py`, Controller `start_task`, rendered-contract schema, CanonicalExecutionRequest, existing receipt schemas                                          | no consequential effect reaches `EXECUTING` without fresh valid exact risk admission                                                                   |
| **C10 — Outcome Closure + Autonomous Replan**    | Turn observed divergence into bounded risk-aware replanning                                                  | verification/evidence, trigger detector, candidate generation, existing replanner, ImpactEngine                                                                 | failure/stale/provider loss/outcome divergence can produce bounded alternate plan; authority expansion never self-authorized                           |
| **C11 — PEC Dogfood Graduation**                 | Hand PEC the original messy human-level RiskPacket objective and make PEC compile/execute the job itself     | everything above                                                                                                                                                | PEC independently discovers existing machinery, avoids duplicates, builds only missing seams, executes and proves source→IR→task→diff→evidence lineage |

That is the order I would give Claude Code Desktop.

---

# 15. C0 is more important than it looks

Before DeepSeek fixes anything, make it prove current behavior.

I want a tiny **golden journey matrix**:

| Journey                                                        | Required |
| -------------------------------------------------------------- | -------: |
| freeform one-sentence intent                                   |      yes |
| long architecture document                                     |      yes |
| explicit minimal intent                                        |      yes |
| target inferred from current repository                        |      yes |
| explicit target                                                |      yes |
| compile only                                                   |      yes |
| Blueprint validation                                           |      yes |
| trivial read-only program                                      |      yes |
| bounded repository-local mutation                              |      yes |
| execution interrupted + resumed                                |      yes |
| same action retried idempotently                               |      yes |
| provider swapped without changing Program truth                |      yes |
| malformed/authority-expanding request fails before side effect |      yes |

Every failure records:

```text
source
IR/stage reached
canonical artifact produced
exact invariant violated
exception/refusal
whether side effects occurred
```

No “fix while investigating.”

First freeze reality.

---

# 16. The intent corpus should become permanent compiler conformance

This is essential.

Build fixtures containing deliberately human inputs:

```text
"fix PEC it's not taking my intent"

"add risk packet thing and don't replace assurance"

long ADR

chat transcript

lowercase prose with don't / never / should

conflicting requirements

feature request where implementation already exists

request for superseded architecture

vague business objective

detailed implementation spec

document with tables/code fences

intent with no target

intent with an explicit wrong target

authority-bearing ambiguity

harmless reversible ambiguity
```

Do **not** require identical generated prose.

Assert semantic properties:

```text
objective preserved
prohibition preserved
target resolution correct
authority ambiguity remains UNKNOWN
already-existing replanner = HARDEN_WIRE
duplicate Assurance = forbidden
acceptance conditions represented
source provenance retained
```

This is how you test an LLM compiler.

Not with golden strings.

---

# 17. Repository Microscope needs to become a first-class compiler stage

I would make this a serious subsystem.

Its output should support queries like:

```text
Who owns this behavior?

What is the canonical implementation?

Which runtime invokes this file?

Which schema validates its artifact?

Which tests prove it?

Is this artifact generated?

Is another version superseding it?

Does the requested concept already exist under another name?

What would call sites be affected if we changed it?

Where is authority actually enforced rather than documented?
```

This is the component that should eventually prevent the exact mistakes **I made** before doing the microscope read.

The compiler should be better at that than either of us manually.

---

# 18. RiskPacket after the compiler is green

The actual RiskPacket can now be much smaller than my original schema because PEC already owns most of the facts.

Conceptually:

```yaml
schema: l9.risk-packet.v1

subject:
  ref: ...
  digest: ...
  operation: ...
  capability: ...
  arguments_digest: ...
  target_set_digest: ...

execution_state:
  program_lock_digest: ...
  plan_revision: ...
  replan_revision_ref: ...
  exact_state_refs: [...]

declared_risk_envelope_ref: ...

impact:
  assessment_ref: ...
  assessment_digest: ...
  coverage: ...
  risk_vector: ...

authority_refs: [...]
policy_refs: [...]
evidence_refs: [...]

outcome_contract:
  expected_postconditions: [...]
  required_evidence: [...]

validity:
  created_at: ...
  expires_at: ...
  stale_on: [...]

lineage:
  source_contract_ref: ...

risk_packet_digest: ...
```

Notice what it **doesn't** duplicate:

```text
authorization policy
approval semantics
evidence definitions
Program state
transport
verdict
```

Assurance emits the verdict separately.

---

# 19. ImpactEngine v1 does not need World Model

PEC can compute useful bounded consequence now from:

```text
Program DAG
active replan adaptation
declared target/write set
repository revision
repository dependency data
resource claims
leases
concurrent claims
Task Card risk envelope
rollback semantics
capability/action class
```

Its artifact should carry:

```text
effect_subject_digest
engine version/digest
input source refs/digests

direct affected set
downstream affected set
critical affected set
max propagation depth

authority crossings
externalities
resource conflicts
concurrency conflicts

reversibility
rollback confidence

coverage:
  complete | bounded | partial | unknown

unknowns[]

risk_vector
```

And the hardest invariant is:

> **No graph edge found is not evidence that no graph edge exists.**

Unknown dependency coverage becomes `partial/unknown`.

Never `blast_radius = 0`.

---

# 20. Replanning after risk becomes genuinely interesting

Once these pieces are closed:

```text
current plan
    ↓
failure / drift / better route
    ↓
candidate generator
    ↓
A   B   C   D
```

Each candidate stays powerless.

Existing deterministic `REPLAN_CONTRACT` first rejects authority violations.

Then ImpactEngine evaluates survivors:

```text
A:
 downstream 200
 irreversible medium

B:
 downstream 12
 reversible
 no authority crossing

C:
 requires higher permission
 → rejected before selection
```

Use **dominance/Pareto filtering**, not “LLM says B feels safer.”

If B is no worse on all governed dimensions and strictly better on one, B dominates A.

Then independent verification.

Then activation itself gets:

```text
EffectSubject
→ ImpactAssessment
→ RiskPacket
→ Assurance
→ Controller activation
```

And that **still does not pre-authorize B's future machine actions**.

Each consequential action receives its own fresh risk binding when it becomes executable.

That's the closed loop.

---

# 21. Things DeepSeek must be explicitly forbidden from creating

This is the architectural negative space:

| Do not create                                  | Existing canonical owner               |
| ---------------------------------------------- | -------------------------------------- |
| second Program Controller                      | PEC Controller                         |
| second Program-state database                  | PEC Controller/runtime state           |
| second replanning protocol                     | `REPLAN_CONTRACT`                      |
| second transport                               | Gate `TransportPacket`                 |
| RiskPacket router                              | Gate                                   |
| parallel authorization model                   | existing authorization law + Assurance |
| parallel evidence model                        | `EVIDENCE_MODEL` + Assurance           |
| new generic receipt universe                   | existing PEC receipt families          |
| “approved” field inside RiskPacket             | AssuranceDecision                      |
| World Model dependency for Risk v1             | PEC-native impact sources              |
| automatic authority expansion                  | Blueprint/Program admission            |
| model-chosen risk permission                   | deterministic policy/Assurance         |
| fake docs task for unknown implementation seam | compiler discovery task                |
| post-seal “helpful” semantic mutation          | compiler must finish before seal       |

That table belongs in every relevant implementation contract.

---

# 22. PEC's graduation test

I would not call PEC working because `make campaign` turns green once.

I would call it **trusted enough to dogfood** when this holds:

```text
ordinary human intent
        ↓
no special schema knowledge
        ↓
meaning-preserving normalization
        ↓
live repository grounding
        ↓
already-existing work recognized
        ↓
missing work isolated
        ↓
authority preserved
        ↓
Blueprint correctly synthesized
        ↓
Program executes without manual repair
        ↓
restart/resume works
        ↓
evidence closes completion
        ↓
repository result matches original intent
```

Track at least:

| Metric                                               |                         Target |
| ---------------------------------------------------- | -----------------------------: |
| material-intent loss                                 |                          **0** |
| false CREATE where canonical implementation exists   |                          **0** |
| authority widening caused by normalization           |                          **0** |
| manual artifact edits required                       |                          **0** |
| private-stage bypasses required                      |                          **0** |
| restart/resume corruption                            |                          **0** |
| provider identity leaking into Program truth         |                          **0** |
| false completion                                     |                          **0** |
| semantic source→result traceability                  | **100% material requirements** |
| stale consequential execution after Risk enforcement |                          **0** |
| consequential execution without valid RiskPacket     |                          **0** |

For tiny deterministic fixtures, I'd want **10 consecutive clean runs**. For actual repository campaigns, at least several materially different successful campaigns before trusting it with the World Model.

---

## The implementation order I'd start tonight

**C0 → C1 → C2 → C3 → C4 → C5.**

Stop there and prove PEC's compiler/execution spine.

Only then:

**C6 → C7 → C8 → C9 → C10.**

Then **C11 is the moment PEC eats its own dog food**.

You give it a normal human request—not our giant machine-shaped ADR—and see whether it independently concludes:

```text
existing replanner → harden
existing auth      → preserve
existing evidence  → preserve
existing receipts  → extend
Gate                → preserve
ImpactEngine        → create
RiskPacket          → create/protocol
Assurance profile   → extend
runtime risk guard  → create
replan closure      → wire
```

If it does that, **we've finally built the compiler you've been aiming at all along**.

And *then* I would unleash that thing on the World Model.

[1]: https://github.com/Quantum-L9/Cursor-Governance/tree/main/environment/program-execution/compiler "https://github.com/Quantum-L9/Cursor-Governance/tree/main/environment/program-execution/compiler"
[2]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/scripts/campaign_input.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/scripts/campaign_input.py"
[3]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/intent.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/intent.py"
[4]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/architecture_intent.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/architecture_intent.py"
[5]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/architecture_coverage.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/architecture_coverage.py"
[6]: https://github.com/Quantum-L9/Cursor-Governance/blob/main/environment/program-execution/compiler/architecture_ir.py "https://github.com/Quantum-L9/Cursor-Governance/blob/main/environment/program-execution/compiler/architecture_ir.py"
[7]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/repo_truth.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/repo_truth.py"
[8]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/architecture_to_campaign.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/compiler/architecture_to_campaign.py"
[9]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/scripts/launchability.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/scripts/launchability.py"
[10]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/AUTHORIZATION_MODEL.yaml "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/AUTHORIZATION_MODEL.yaml"
[11]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/EVIDENCE_MODEL.yaml "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/EVIDENCE_MODEL.yaml"
[12]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/OWNERSHIP_MATRIX.yaml "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/OWNERSHIP_MATRIX.yaml"
[13]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py"
[14]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py"
[15]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/peer_execution/execution.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/peer_execution/execution.py"
[16]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/peer_execution/core_receipts.py "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/peer_execution/core_receipts.py"
[17]: https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/REPLAN_CONTRACT.yaml "https://raw.githubusercontent.com/Quantum-L9/Cursor-Governance/main/environment/program-execution/core/shared/REPLAN_CONTRACT.yaml"
[18]: https://github.com/Quantum-L9/l9-assurance "GitHub - Quantum-L9/l9-assurance: L9 Assurance Platform — governed CI/CD testing, validation, and evidence runtime with 52 workspace packages. · GitHub"
[19]: https://github.com/Quantum-L9/l9-assurance/tree/main/schemas "https://github.com/Quantum-L9/l9-assurance/tree/main/schemas"
[20]: https://raw.githubusercontent.com/Quantum-L9/Gate_SDK/main/README.md "https://raw.githubusercontent.com/Quantum-L9/Gate_SDK/main/README.md"
