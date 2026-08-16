

----
The World Model is the part that turns Quantum from a pipeline of generators into a **persistent fictional reality**.

Without it, every agent is effectively improvising from context. With it, every agent works inside the same authoritative universe.

The simplest definition is:

> **The World Model is the canonical, machine-readable representation of everything that is true, believed, known, possible, located, owned, damaged, changed, or established in the fictional universe at any point in story time.**

It answers one question:

> **What is true right now, and how did it become true?**

That sounds simple. It is probably the most consequential subsystem in the studio.

# 1. The problem it solves

Generative models are naturally stateless in exactly the wrong way for long-form filmmaking.

Suppose Shot 12 establishes:

```text
Aria damages her left shoulder.
```

Shot 38 establishes:

```text
Aria gives Marcus's key to Eva.
```

Shot 74 reveals:

```text
Eva learns that Marcus created Aria.
```

Shot 141 establishes:

```text
The station's east reactor is offline.
```

By Shot 217, the Director needs to know all of this:

```text
Aria:
  left shoulder damaged
  no longer owns key
  knows X
  does not know Y
  emotionally distrusts Eva

Eva:
  owns Marcus's key
  knows Marcus created Aria
  has not told Aria

Station:
  east reactor offline

Audience:
  knows Marcus created Aria

Aria:
  does NOT know Marcus created Aria
```

A normal generative pipeline tends to solve this with increasingly gigantic prompts.

Something like:

```text
Here is everything that happened in the previous 216 shots...
```

That breaks down.

You get:

* forgotten details
* contradictory details
* wrong props
* impossible geography
* character knowledge leaks
* identity drift
* inconsistent injuries
* relationships changing without cause
* characters acting against established motivations
* objects magically reappearing
* clues appearing after they're needed
* location layouts changing
* story rules being violated
* downstream agents inventing alternate canon

At 10 shots, you can survive some of that.

At 300 shots, it becomes catastrophic.

At:

```text
3 seasons
24 episodes
5,000 shots
```

prompt memory is not remotely sufficient.

The World Model replaces:

> “Please remember everything.”

with:

> **“Query reality.”**

---

# 2. It is not just memory

This distinction matters enormously.

A memory system answers:

> What information has been recorded about Aria?

The World Model answers:

> What is Aria's authoritative state at story frame 81,442?

Those are different problems.

Memory might contain:

```text
Aria injured her shoulder in Episode 1.
Aria repaired her shoulder in Episode 4.
Aria injured it again in Episode 7.
```

The World Model determines:

```text
At Episode 6 Scene 3 Shot 18:
aria.left_shoulder.condition = repaired
```

So I think of it as:

```text
LONG-TERM MEMORY
"What happened historically?"
        │
        ▼
WORLD MODEL
"What does that imply is true now?"
```

The World Model is **operational state**.

---

# 3. Think of the fictional universe like a running simulation

This is the mental model I'd use.

A videogame engine doesn't rediscover where every object is each frame.

It has world state:

```python
player.position
door.is_open
enemy.health
inventory["key"]
quest.completed
```

Quantum needs the cinematic equivalent.

For example:

```python
world.character("aria").location
world.character("aria").injuries
world.character("aria").knowledge
world.character("aria").emotion

world.prop("receiver").owner
world.location("comms_room").power_state

world.relationship("aria", "eva").trust

world.audience.knowledge

world.cinematic.screen_direction
```

The film is then a sequence of state transitions:

```text
State 216
   │
   ▼
Shot 217
   │
   ▼
State 217
```

A shot doesn't merely show something.

It **changes reality**.

---

# 4. The fundamental abstraction is a transaction

I would treat every scene—and eventually every shot—almost like a database transaction.

Before Shot 217:

```yaml
aria:
  location: communications_room

  right_hand:
    holding: receiver

  emotion:
    hope: 0.41
    fear: 0.32

receiver:
  powered: true
```

Shot 217 intends to do:

```text
receiver flickers
receiver dies
Aria realizes signal is gone
```

Postconditions:

```yaml
aria:
  emotion:
    hope: 0.07
    fear: 0.61

receiver:
  powered: false
```

So:

```text
PRECONDITIONS
     ↓
   SHOT
     ↓
POSTCONDITIONS
```

Quantum validates the preconditions before directing it.

Then after the shot passes QC:

```text
COMMIT
```

Only then does the post-state become authoritative.

That is a really powerful idea.

Generated footage itself isn't truth.

The semantic event is truth.

---

# 5. Why this matters for autonomy

A human director currently carries a huge amount of implicit state.

They remember things like:

> She lost that necklace three scenes ago.

> He doesn't know she's his daughter yet.

> Her left arm is injured.

> We've established the doorway is behind camera-right.

> The audience knows this, but the detective doesn't.

> That character would never casually reveal that information.

A fully human-free studio cannot rely on that invisible human brain.

The World Model becomes that shared production brain.

Without it, every autonomous agent has to independently reason about reality.

That means:

```text
Writer guesses.
Director guesses.
Renderer guesses.
Editor guesses.
Critic guesses.
```

Eventually the guesses diverge.

With a World Model:

```text
                 WORLD MODEL
                     │
     ┌───────────────┼────────────────┐
     │               │                │
     ▼               ▼                ▼
   Writer          Director        Renderer
     │               │                │
     ▼               ▼                ▼
 "what is true?"  "what is true?"  "what must appear?"
```

They aren't coordinating with one another by conversation.

They are coordinating through **shared truth**.

That is a much more scalable architecture.

---

# 6. There isn't just one kind of truth

This is where the concept becomes interesting.

Consider this:

```text
Marcus is alive.
```

Maybe objectively:

```yaml
objective_truth:
  marcus.alive: true
```

But Aria believes:

```yaml
character_belief:
  aria:
    marcus.alive: false
```

Eva knows:

```yaml
character_knowledge:
  eva:
    marcus.alive: true
```

And the audience currently believes:

```yaml
audience_model:
  marcus.alive: unknown
```

Those states can coexist without contradiction.

That gives us at least four epistemic layers:

```text
OBJECTIVE TRUTH

What is actually true?


CHARACTER KNOWLEDGE

What has this character actually learned?


CHARACTER BELIEF

What does this character believe,
including false beliefs?


AUDIENCE KNOWLEDGE

What has the movie revealed to viewers?
```

This alone solves a massive class of writing errors.

---

# 7. It prevents information leakage

Imagine Scene 8 reveals to the audience:

```text
Marcus sabotaged the station.
```

Aria wasn't present.

Later the Writer writes:

```text
ARIA
Why did Marcus sabotage the station?
```

A normal LLM might do that because it knows the whole screenplay.

The World Model rejects it:

```text
EPISTEMIC VIOLATION

Fact:
marcus_sabotaged_station

Known by:
- audience
- eva

Not known by:
- aria
```

The Writer has to produce something consistent with Aria's perspective.

This is extremely important for:

* mystery
* suspense
* dramatic irony
* deception
* twists
* political intrigue
* crime
* romance
* basically any sophisticated narrative

---

# 8. Physical continuity becomes machine-enforceable

The obvious case:

```text
Shot 77:
Aria picks up key.

Shot 80:
Aria puts key in pocket.

Shot 114:
Aria gives key to Eva.
```

World Model:

```yaml
qprop_key_01:
  owner: eva
  location: eva.jacket.left_pocket
```

Shot 151 attempts:

```text
Aria removes the key from her pocket.
```

Reject:

```text
WORLD.PROP_OWNERSHIP_VIOLATION
```

No amount of visual quality can save that shot.

This catches:

* held objects
* clothing
* damage
* wounds
* blood
* dirt
* hair changes
* weather
* doors
* lights
* vehicles
* weapons
* location occupancy
* battery levels
* broken equipment
* basically any persistent physical fact

---

# 9. Character continuity becomes deeper than appearance

Suppose Aria begins:

```text
trust(Eva) = 0.21
```

Then several events occur:

```text
Eva saves Aria      +0.16
Eva lies             -0.24
Eva reveals truth    +0.11
```

Now:

```text
trust(Eva) ≈ 0.24
```

I'm not saying every emotion should literally be a scalar.

But the model should maintain **structured psychological state**.

For example:

```yaml
aria:
  current_goal:
    find_signal_origin

  emotional_state:
    hope: moderate
    fear: increasing
    anger_at_eva: suppressed

  relationship_state:
    eva:
      trust: low
      dependence: medium
      affection: emerging
      unresolved:
        - betrayal
```

Then the Performance Director and Writer get different guidance than if:

```yaml
trust: high
```

That's how you make characters feel like they persist through time.

---

# 10. It gives characters memory without giving agents giant prompts

Suppose Aria has appeared in 40 episodes.

You don't send the Director 800 pages of history.

You ask:

```python
ctx = world.context_for_shot("qshot_4829")
```

and receive:

```yaml
character:
  aria:

    relevant_canon:
      - synthetic maintenance engineer
      - memory discontinuity

    current_state:
      location: hangar_3
      physical_condition: exhausted
      left_shoulder: repaired

    current_goal:
      reach_shuttle

    emotional_context:
      trusts_eva: reluctantly
      fears_abandonment: active

    relevant_history:
      - eva lied about Marcus in episode 04
      - aria chose to save eva in episode 07

    knowledge:
      knows:
        - Marcus survived
      does_not_know:
        - Eva caused reactor failure
```

That's the context needed **for this shot**.

Not the whole universe.

This is one of the biggest scaling levers.

---

# 11. Context becomes a compiled view

This is an important implementation concept.

The World Model can contain millions of facts eventually.

Agents shouldn't query raw facts manually.

Instead:

```text
World Model
    │
    ▼
Context Compiler
    │
    ▼
Role-specific context
```

For the Writer:

```text
character psychology
current knowledge
narrative promises
relationship state
```

For the Renderer:

```text
visual variants
physical condition
held props
location state
lighting
```

For the Director:

```text
all of those
+
cinematic geography
```

For the Sound Designer:

```text
location material
environment
distance
physical events
```

Same reality.

Different projections.

---

# 12. This can drastically reduce hallucination

Today, a generative system often has to answer:

> What should Aria be wearing?

with generative inference.

Bad.

The answer should usually already exist:

```yaml
aria.current_variant:
  chassis: aria_base_v4
  damage: damage_state_07
  accessories:
    - maintenance_harness
```

The renderer isn't being creative about identity.

It's **resolving state**.

You reserve creativity for things where creativity is wanted.

This is one of the deeper principles:

> **Every decision moved from model inference into explicit state increases consistency.**

That directly improves autonomous reliability.

---

# 13. Scaling leverage: one character becomes infinitely reusable

This is especially relevant to your series idea.

Without a World Model:

```text
Episode 1 Aria
     ≈
Episode 2 Aria
     ≈
Episode 3 Aria
```

They're basically reinterpretations.

With a World Model:

```text
                       qchar_000001
                            ARIA
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
        identity          history            state
           │                  │                  │
           ▼                  ▼                  ▼
    permanent canon     accumulated events   current truth
```

Now Episode 50 is operating on the same entity that Episode 1 created.

That means:

```text
character = persistent data object
```

rather than:

```text
character = recurring prompt
```

That is a massive IP-level difference.

---

# 14. The same applies to worlds

Suppose Quantum eventually has:

```text
Universe A
  7 series
  83 episodes
  19 recurring characters
  44 locations
  300 named props/artifacts
  1,200 historical events
```

A world model lets another story happen inside the existing universe without redefining it.

The compiler can query:

```text
What inhabited locations exist near Mars in year 2381?
```

or:

```text
Which characters plausibly know about Project Helios?
```

or:

```text
Which existing unresolved events could naturally create this story?
```

Now the world becomes **story-generative infrastructure**.

That's another huge scaling leverage point.

---

# 15. The World Model can generate stories

This is where it goes beyond continuity.

Once you have persistent state, unresolved tensions themselves become story seeds.

For example:

```yaml
aria:
  unresolved:
    - origin_of_memory_wipe

eva:
  secret:
    - knows_origin_of_memory_wipe

relationship:
  aria_eva:
    trust: fragile

world:
  event:
    memory_archive_reactivation: possible
```

A future Story Architect can query:

> Find latent conflicts involving Aria with high emotional stakes and unresolved causal links.

And the graph effectively says:

```text
Eva knows truth
       │
       ▼
Aria doesn't
       │
       ▼
Aria trusts Eva reluctantly
       │
       ▼
memory archive can reveal truth
```

There's your episode.

The World Model becomes a **story engine**, not merely a continuity database.

---

# 16. It improves story originality through consequence

One common weakness in generative stories is that each scene feels locally plausible but globally arbitrary.

Why?

Because models generate:

```text
next plausible event
```

rather than:

```text
next event causally implied by existing reality
```

With a World Model, Story Architect can ask:

```text
Given:
- current desires
- unresolved conflicts
- physical conditions
- hidden knowledge
- available opportunities
- previous decisions

What events are now causally likely?
```

That generates stories from **consequence**.

And consequence tends to produce stronger narratives than random novelty.

---

# 17. It enables deterministic continuity checks before spending money

Suppose the Director proposes:

```text
Shot 217:
Eva opens Hangar Door 3 manually.
```

World state:

```yaml
hangar_door_3:
  sealed: true
  manual_release:
    destroyed: true
```

You can reject the ShotSpec **before rendering**.

Cost:

```text
almost zero
```

Without World Model:

```text
generate 4 expensive takes
↓
QC notices impossibility
↓
regenerate
```

The World Model moves failures left.

In engineering terms:

> **It shifts correctness validation upstream.**

That's enormous for cost and throughput.

---

# 18. It increases render quality by shrinking the renderer's decision space

Generative quality often improves when you constrain ambiguity.

Bad render package:

```text
Aria enters the damaged room carrying the old receiver.
```

Renderer has to invent:

```text
What does Aria look like?
What damage?
What room?
What receiver?
Which hand?
What lighting?
What clothing?
```

World-derived package:

```yaml
character:
  asset: aria@v4
  variant: damage_state_07

  left_shoulder:
    exposed_actuator: true

  right_hand:
    holding: receiver@v2

location:
  asset: communications_room@v3

environment:
  main_power: offline
  emergency_lighting: amber
  smoke_density: low

prop:
  receiver:
    condition: cracked
```

Now rendering isn't trying to invent reality.

It's trying to realize it.

That should materially improve consistency and quality.

---

# 19. It enables targeted regeneration

This connects to your favorite property:

> Shot 217 being bad must not touch the other 250 shots.

Suppose we change:

```text
aria.left_shoulder.damage
```

starting at Scene 4.

The World Model knows exactly when that state became true.

Dependency graph:

```text
Damage Event
   │
   ├── Shot 91
   ├── Shot 92
   ├── Shot 93
   ...
   └── Shot 117

Repair Event
   │
   └── subsequent shots unaffected
```

If the damage definition changes, Quantum can invalidate:

```text
shots 91–117
```

not the whole episode.

This is incredibly useful for incremental production.

---

# 20. Time travel through state becomes trivial—even without narrative time travel

Because the system is event-sourced, you can reconstruct reality anywhere.

Conceptually:

```python
state = world.at(
    episode="ep03",
    scene="sc07",
    shot="sh12",
)
```

Or:

```python
state = world.at_frame(81244)
```

This lets QC ask:

> What should the character have looked like here?

and get an exact answer.

Or debugging:

> Why does Eva own the key?

Trace:

```text
qevent_1048
Aria → Eva
Shot 114
Episode 2
```

This is the equivalent of source-level debugging for fictional reality.

---

# 21. It enables causal provenance

Every fact should have a reason.

Not just:

```text
door.open = true
```

but:

```text
door.open = true

because:
  qevent_00832

caused_by:
  Eva used emergency override

shown_in:
  qshot_00198

valid_since:
  frame 55102
```

Then Quantum can answer:

```text
Why is this true?
When did it become true?
Who knows?
Who caused it?
Which artifact established it?
```

That makes autonomy debuggable.

---

# 22. It gives QC an oracle

Without a World Model, visual QC asks:

> Does this look consistent?

That's fuzzy.

With a World Model:

```text
Expected:
  Aria right temple cracked
  left shoulder exposed
  receiver in right hand

Observed:
  temple crack absent
  shoulder intact
  receiver left hand
```

QC can compare:

```text
EXPECTED WORLD
        ↕
OBSERVED RENDER
```

That turns continuity from subjective judgment into much more concrete verification.

World Model becomes QC's reference truth.

---

# 23. It makes the Director much smarter

Director doesn't just receive:

```text
Scene:
Aria confronts Eva.
```

It can receive:

```yaml
characters:

  aria:
    goal: force_truth
    believes:
      eva_is_hiding_something: true
    trusts_eva: low
    physical:
      left_arm_mobility: limited

  eva:
    goal: avoid_revealing_memory_archive
    believes:
      aria_cannot_handle_truth: true

relationship:
  tension: high
  physical_distance_norm: guarded

location:
  narrow_corridor
  blocked_exit: rear

cinematic:
  prior_scene:
    aria_screen_direction: left_to_right
```

Now blocking and camera choices have actual semantic grounding.

This should produce more intentional directing.

---

# 24. Sound benefits too

World state says:

```yaml
room:
  size: enormous
  pressure: normal
  materials:
    - steel
    - glass

aria:
  foot_material: ceramic_composite

floor:
  material: steel_grating
```

Sound Designer can derive:

```text
footstep character
reverberation
mechanical resonance
ambient noise
```

without inventing them.

The World Model becomes a common conditioning substrate across all modalities.

---

# 25. It can enforce laws of the fictional universe

Suppose canon says:

```text
FTL communication impossible.
```

A later Writer proposes:

```text
instant message from Alpha Centauri
```

World Model rejects:

```text
WORLD.RULE.CAUSALITY_VIOLATION
```

Or:

```text
synthetics require charging every 72 hours
```

Then Aria can't wander for six months without energy unless the story explains why.

This gives fictional rules teeth.

Otherwise “worldbuilding” is just prose nobody enforces.

---

# 26. It prevents canon drift across series

Imagine 5 years later Quantum writes:

> Aria was built on Mars.

But Season 1 established:

> Aria was assembled on Luna.

A retrieval-only system might miss this.

An authoritative model says:

```text
qchar_000001.origin = Luna

authority:
  established_canon

mutable:
  only_by_explicit_recanonization
```

New story proposal fails.

That's how you preserve a franchise.

---

# 27. It makes retcons explicit

Sometimes you *do* want to change canon.

The World Model shouldn't make this impossible.

It should make it **intentional and versioned**.

For example:

```text
Canon v7:
Marcus died in 2372.

Canon v8:
Marcus's presumed death was falsified.
```

Potentially that's not even a retcon if objective truth is:

```text
Marcus survived
```

while previous canon only represented character belief.

But if you genuinely rewrite canon, the system knows:

```text
which facts changed
which episodes depend on them
which stories become inconsistent
```

That's sophisticated IP management.

---

# 28. It enables simulations before committing story decisions

This is one of the fun parts.

Because state transitions are explicit, Quantum could hypothetically simulate alternative story paths.

For example:

```text
CURRENT STATE
      │
 ┌────┼─────────┐
 ▼    ▼         ▼
A     B         C

Aria  Aria      Aria
trusts confronts leaves
Eva   Eva       station
```

Then project:

```text
future dramatic pressure
relationship consequences
available conflicts
canon consequences
```

Story Architect can evaluate not just:

> Which scene is coolest?

but:

> Which choice creates the strongest downstream narrative state?

That's powerful.

---

# 29. The scaling equation changes

Without a World Model, complexity grows roughly with:

```text
number of agents
×
number of shots
×
history length
```

because every agent repeatedly needs increasingly large context.

With a World Model:

```text
huge canonical state
       ↓
query
       ↓
small relevant context
```

The total universe can get much larger while individual agent contexts stay bounded.

That's the fundamental scalability win.

In database terms:

```text
do not send the whole database to every service
```

Query what the operation needs.

---

# 30. It also allows specialization without fragmentation

As Quantum grows, you may have:

```text
StoryAgent
DialogueAgent
CharacterAgent
DirectorAgent
CameraAgent
SoundAgent
MusicAgent
AssetAgent
RendererRouter
Critics...
```

Normally more agents means more risk of disagreement.

But if they all derive state from:

```text
World Model
```

then specialization becomes safer.

The architecture becomes:

```text
                    WORLD MODEL
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
      Writer          Director          Sound
        │                │                 │
        ├────────────────┼─────────────────┤
        │                │                 │
     Renderer          Editor             QC
```

Agents share **facts**, not memories of previous conversations.

---

# 31. It separates facts from interpretation

This is crucial.

World Model:

```text
Aria has stood motionless for 4.1 seconds.
```

Director/Performance Critic interprets:

```text
This communicates shock.
```

World Model:

```text
Aria has not spoken since hearing the phrase.
```

Writer interprets:

```text
Silence is appropriate.
```

Don't put subjective quality judgments into the truth layer.

World Model owns:

```text
what
where
when
who knows
who believes
how changed
```

Not:

```text
is this emotionally good?
```

That remains QC/compiler territory.

---

# 32. The World Model becomes the stable core while models change

This may be the biggest strategic leverage.

Video models will change.

LLMs will change.

Voice systems will change.

Image generators will change.

But:

```text
Aria is qchar_000001.
She has this history.
She knows these facts.
She owns these objects.
Her left shoulder was damaged here.
Eva betrayed her here.
```

doesn't depend on any provider.

The durable asset is the **structured fictional reality**.

You can replace:

```text
Renderer v1
→ Renderer v9
```

and regenerate old scenes from the same semantic source.

Or remaster an entire series with future models.

That could be enormous.

---

# 33. You can think of it as the studio's source code for reality

If:

```text
creative.yaml
```

is your creative source,

and:

```text
animatic.lock
```

is the executable film plan,

then:

```text
World Model
```

is the runtime state of the fictional universe.

The rendered movie is just one projection of that state.

This gives us an interesting hierarchy:

```text
CREATIVE INTENT
"What do I want?"

        ↓

COMPILER
"What movie expresses it?"

        ↓

WORLD MODEL
"What is true inside that movie?"

        ↓

PRODUCTION
"How do those truths become pixels and sound?"

        ↓

QC
"Did we successfully realize them?"
```

---

# 34. The leverage across the four things you asked about

### Scaling

World state grows centrally while individual agent context stays bounded.

```text
15 shots → 300 shots → 5,000 shots
```

doesn't require every agent to remember 5,000 shots.

Characters, locations and canon can persist across episodes and series.

### Quality

The system eliminates huge classes of inconsistency before rendering:

```text
wrong prop
wrong outfit
wrong knowledge
wrong injury
wrong relationship
wrong geography
wrong world rule
```

And renderers receive much more precise conditioning.

### Autonomy

The World Model replaces a human's implicit continuity memory.

Agents can independently ask:

```text
What is true?
What may I change?
What must remain unchanged?
```

So production doesn't need a human supervising continuity.

### Reusability / IP

A character isn't a prompt anymore.

A location isn't a prompt anymore.

A universe isn't a prompt anymore.

They become persistent, versioned, queryable entities with histories.

That is how Quantum goes from:

> AI makes shorts.

to:

> **Quantum operates persistent fictional universes.**

---

# 35. The deepest conceptual shift

In most generative-media systems:

```text
prompt
   ↓
media
```

The media is effectively the result.

In Quantum:

```text
                    WORLD STATE
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
          screenplay   imagery     sound
             │           │           │
             └───────────┼───────────┘
                         ▼
                       FILM
```

The movie is a **rendering of state**.

That makes a completely different class of system possible.

And I think the cleanest foundational definition is:

> **The Quantum World Model is a temporally versioned, event-driven, multi-perspective model of fictional reality that acts as the authoritative state substrate for every autonomous creative, production, and quality-control agent.**

Its main purpose isn't merely to make continuity better.

Its main purpose is to make **long-form autonomous storytelling tractable at all**.

Once this exists, scaling from one 60-second short to a recurring character across dozens of episodes becomes fundamentally an issue of adding state and events—not hoping a model can continue pretending to remember the same universe.


-----

Yes — and the most important refinement is:

> **Shared intelligence should not mean “every agent has access to one enormous prompt.” It should mean every agent operates over the same authoritative reality and receives the exact projection of that reality required for its job.**

That is much stronger than human organizational memory. A human production team has scattered notebooks, conflicting recollections, tribal knowledge, forgotten continuity decisions and specialists who only know their piece. Quantum can make every agent behave as though it has perfect institutional memory **without forcing every agent to process everything**.

## 1. More than four truth layers

The four we discussed—objective truth, character knowledge, character belief and audience knowledge—are the epistemic core, but they aren't enough for a serious World Model.

I'd model these as separate **state planes**:

| Plane                         | Answers                                                                        |
| ----------------------------- | ------------------------------------------------------------------------------ |
| **Objective / ontic**         | What is actually true?                                                         |
| **Knowledge**                 | What has each character actually learned?                                      |
| **Belief**                    | What does each character think is true, including false beliefs?               |
| **Audience disclosure**       | What has the film actually shown/revealed?                                     |
| **Intentional**               | What does each character currently want, intend or plan?                       |
| **Psychological / affective** | What are they feeling; which fears, wounds, pressures and biases are active?   |
| **Relational / social**       | Trust, intimacy, hostility, authority, obligations, debts, secrets, alliances. |
| **Capability / affordance**   | What can each entity physically/socially/technically do from here?             |
| **Normative / rule**          | What laws of physics, technology, society and canon constrain events?          |
| **Hypothetical / branch**     | What would be true in a simulated but not-yet-canonical future?                |

I'd keep **cinematic state** adjacent to these rather than pretending it's fictional truth:

```text
screen direction
camera side of axis
established geography
coverage
previous framing
eyelines
```

And every important state value should also carry:

```text
provenance
authority
confidence where appropriate
valid-time
```

Psychological state becomes particularly useful because it allows performance and story to be conditioned on **what is emotionally active now**, rather than repeatedly rediscovering a character from their biography.

---

# 2. Agents should not have to “remember to query the World Model”

This is a critical architecture decision.

I would use two mechanisms:

```text
MANDATORY CONTEXT
automatically compiled before the agent executes

+

EXPLORATORY QUERY TOOLS
available when the agent discovers it needs more information
```

So every agent has a declarative `ContextContract`.

For example:

```python
class AgentContextContract(BaseModel):
    role: str

    required_views: tuple[str, ...]

    optional_query_tools: tuple[str, ...]

    perspective: str | None = None


DIRECTOR_CONTEXT = AgentContextContract(
    role="director",
    required_views=(
        "current_physical_state",
        "character_psychology",
        "character_goals",
        "character_knowledge",
        "relationships",
        "location_state",
        "canonical_assets",
        "cinematic_state",
        "world_rules",
    ),
    optional_query_tools=(
        "explain_fact",
        "history_of",
        "find_related_events",
        "query_affordances",
    ),
)
```

The orchestration runtime does this **before invoking the Director**:

```python
async def invoke_agent(agent, task):

    context = await world.compile_context(
        contract=agent.context_contract,
        target=task.world_coordinate,
        entities=task.entities,
    )

    return await agent.run(
        task=task,
        world_context=context,
        tools=world.tools_for(agent.role),
    )
```

So we're not hoping the LLM thinks:

> Maybe I should check whether Aria's left arm is damaged.

The Director **cannot run without that state already injected**.

That is much safer.

---

# 3. Then agents get a typed World Query API

I would not make raw Cypher/SQL/graph syntax an agent-facing surface.

Give agents semantic operations:

```python
world.state_at(...)
world.explain_fact(...)
world.history_of(...)
world.compare_perspectives(...)

world.find_latent_conflicts(...)
world.find_knowledge_asymmetries(...)
world.query_affordances(...)

world.propose_causal_successors(...)
world.simulate(...)
```

For example:

```python
conflicts = await world.find_latent_conflicts(
    character_id="aria",
    minimum_stakes="high",
    unresolved_only=True,
    horizon="episode",
)
```

The agent learns these tools the same way it learns any tool: typed schemas, descriptions, permitted usages and examples are part of its runtime tool catalog.

But more importantly, the **Story Architect's operating contract explicitly tells it when these tools apply**.

Something like:

```yaml
story_architect:

  mandatory_context:
    - current_goals
    - unresolved_conflicts
    - knowledge_asymmetries
    - relationship_pressures
    - physical_constraints
    - available_affordances
    - previous_decisions
    - open_story_promises

  use_world_queries_when:
    - generating_next_major_event
    - searching_for_existing_story_pressure
    - considering_character_decision
    - introducing_new_conflict
    - resolving_mystery
```

So there are three levels:

```text
Level 1
runtime automatically hydrates it

Level 2
agent contract teaches when further lookup is mandatory

Level 3
agent can intelligently explore the WM
```

---

# 4. “Find latent conflicts involving Aria” can actually be computed

This does not need to be purely a vague semantic search.

Suppose the graph contains:

```text
ARIA ──DESIRES────────► learn_memory_origin

EVA ───KNOWS──────────► memory_origin

EVA ───WANTS──────────► protect_aria

revealing_memory_origin
      ──THREATENS─────► aria_psychological_stability

ARIA ──TRUSTS(.24)────► EVA

ARIA ──NEEDS──────────► truth_from_eva
```

The World Query Engine can look for known conflict motifs.

For example:

```python
class ConflictPattern(Enum):
    COMPETING_GOALS = "competing_goals"
    SECRET_BLOCKS_GOAL = "secret_blocks_goal"
    BELIEF_REALITY_GAP = "belief_reality_gap"
    OBLIGATION_VS_DESIRE = "obligation_vs_desire"
    RELATIONSHIP_VS_GOAL = "relationship_vs_goal"
    SCARCE_RESOURCE = "scarce_resource"
    PHYSICAL_LIMITATION = "physical_limitation"
    RULE_BLOCKS_GOAL = "rule_blocks_goal"
```

Then:

```python
def find_latent_conflicts(character, graph):

    candidates = []

    candidates += find_goal_blockers(character, graph)
    candidates += find_relevant_secrets(character, graph)
    candidates += find_competing_desires(character, graph)
    candidates += find_belief_truth_gaps(character, graph)
    candidates += find_relationship_tensions(character, graph)
    candidates += find_resource_constraints(character, graph)

    return rank_conflicts(candidates)
```

A returned object might be:

```yaml
conflict_id: conflict_8182

type: secret_blocks_goal

character: aria

goal:
  learn_origin_of_memory_wipe

blocking_entity:
  eva

hidden_fact:
  eva_knows_memory_origin

stakes:
  emotional: 0.94
  relational: 0.88
  existential: 0.81

causal_support:
  - aria_desires_truth
  - eva_knows_truth
  - eva_fears_revealing_truth
  - aria_trusts_eva_only_weakly

story_potential: 0.93
```

Now the Story Architect isn't inventing conflict out of thin air.

It is **mining dramatic pressure already latent in reality**.

That's a huge improvement.

---

# 5. “Given desires + conflicts + physical conditions + hidden knowledge...” becomes automatic

I'd have a specific query:

```python
pressure = await world.story_pressure(
    focus=["aria"],
    at=current_story_instant,
)
```

which produces:

```yaml
active_desires:
  - find_signal_origin
  - avoid_confirming_total_isolation

unresolved_conflicts:
  - aria_vs_eva_truth
  - aria_vs_self_identity

physical_conditions:
  - left_arm_mobility_55_percent
  - station_power_declining

knowledge_asymmetries:
  - eva_knows_memory_origin
  - aria_does_not

available_opportunities:
  - memory_archive_accessible
  - eva_currently_present
  - transmitter_recently_reactivated

prior_decisions:
  - aria_chose_to_trust_eva
  - eva_chose_to_continue_lying
```

That entire package is compiled before successor generation.

---

# 6. Mechanically: “next event causally implied by existing reality”

This is where the World Model becomes a planning engine.

Take current state:

```text
S₀
```

First derive what actions/events are **possible**:

```text
S₀
 ↓
Affordance Engine
 ↓
possible actions/events
```

For Aria:

```text
question Eva
access archive
repair transmitter
leave room
inspect receiver
attempt station uplink
```

Not:

```text
teleport to Mars
call dead character
use a device she doesn't possess
```

Then a judgment model proposes candidate events **from those affordances**:

```text
E1 = Aria directly confronts Eva
E2 = Aria secretly accesses memory archive
E3 = Aria pretends to trust Eva and tests her
E4 = power failure interrupts confrontation
```

Every candidate declares:

```python
class EventProposal(BaseModel):
    event_type: str
    actors: list[str]

    trigger: list[str]

    preconditions: list["Predicate"]
    effects: list["Mutation"]

    knowledge_effects: list["Mutation"] = []
    relationship_effects: list["Mutation"] = []

    motivation_refs: list[str]
```

Then:

```text
candidate
   ↓
Rule Engine
   ↓
precondition validation
   ↓
simulate state transition
   ↓
score resulting state
```

The scoring can consider:

```text
causal support
character motivation
goal pressure
conflict escalation
relationship consequences
theme
story promises
surprise
future dramatic potential
production feasibility
```

So:

```python
async def causal_successors(state):

    affordances = derive_affordances(state)

    proposals = await story_model.propose_events(
        state=state,
        affordances=affordances,
    )

    valid = [
        event
        for event in proposals
        if rules.validate(state, event).pass_
    ]

    branches = [
        simulator.apply(state, event)
        for event in valid
    ]

    return rank_story_branches(branches)
```

That's the mechanical version of:

> “What would naturally happen next?”

---

# 7. This is Tree-of-Thought-like — but stronger

If by **ToTh** you meant **Tree of Thoughts**, the standard abbreviation is usually **ToT**. ToT explores alternative intermediate states, evaluates them and can backtrack rather than committing immediately. ([arXiv][1])

Quantum's version would be more concrete:

```text
Tree of Thoughts:

thought
├── thought
├── thought
└── thought


Quantum Story Search:

WorldState S0
├── Event A → WorldState S1A
├── Event B → WorldState S1B
└── Event C → WorldState S1C
                   │
                   ├── Event D → S2CD
                   └── Event E → S2CE
```

We're searching over **explicit fictional state**, not just text reasoning.

That means branches can be checked for:

```text
physical possibility
character knowledge
world rules
relationship consequences
story quality
```

before selection.

Incidentally, `ToTh` is also now used by a different framework called **Theorem-of-Thought**, built around abductive, deductive and inductive reasoning agents, so I'd call Quantum's mechanism `StoryStateSearch` or `CausalBranchSearch` rather than ToTh to avoid ambiguity. ([ACL Anthology][2])

---

# 8. Counterfactual simulation must never mutate canon

This is key.

```python
branch = await world.fork(
    from_snapshot=current_snapshot
)

await branch.apply(event_a)
await branch.apply(event_b)

score = await evaluate(branch)

# Nothing canonical changed.
```

Only:

```python
await world.commit(branch.selected_events)
```

changes canonical reality.

So we get:

```text
CANONICAL STATE
     │
     ├── hypothetical branch A
     ├── hypothetical branch B
     └── hypothetical branch C
                   │
                   ▼
              choose B
                   │
                   ▼
             COMMIT B
```

This gives us safe story simulation.

---

# 9. Flashbacks and parallel storylines become natural

Yes — this is a major benefit.

Every query should include a `WorldCoordinate`:

```python
class WorldCoordinate(BaseModel):
    universe_id: str
    continuity_id: str

    universe_time: datetime | None

    episode_id: str | None
    scene_id: str | None
    shot_id: str | None

    story_frame: int | None
```

Then:

```python
world.state_at(
    WorldCoordinate(
        universe_id="orpheus",
        continuity_id="main",
        episode_id="ep01",
        scene_id="sc02",
    )
)
```

reconstructs that exact past.

A flashback simply compiles its context from an earlier coordinate.

Parallel plots have separate narrative cursors:

```text
Storyline A @ 14:03
Storyline B @ 13:47
Storyline A @ 14:18
Storyline B @ 14:02
```

The editor can jump freely because reality is queried by story coordinate rather than assuming production order equals chronological order.

This becomes even more useful for:

```text
flashbacks
flash-forwards
parallel action
multiple viewpoints
Rashomon-style conflicting beliefs
alternate universes
time loops
```

although actual alternate canon needs explicit continuity IDs.

---

# 10. How a World-derived package is generated

This should mostly be deterministic.

For a shot:

```python
package = await world.compile_context(
    ContextRequest(
        role="renderer",
        coordinate=shot.entry_coordinate,
        entities=shot.subject_ids,
        location_id=shot.location_id,
    )
)
```

Internally:

```text
target coordinate
      ↓
load nearest snapshot
      ↓
replay subsequent canonical events
      ↓
resolve current state
      ↓
apply canon
      ↓
resolve assets
      ↓
derive role-relevant facts
      ↓
prune irrelevant context
      ↓
WorldContextPackage
```

Example:

```yaml
world_context:

  coordinate:
    episode: ep01
    scene: sc04
    shot: sh017

  characters:

    aria:

      canonical_asset:
        id: aria
        version: 4

      physical:
        left_shoulder:
          condition: damaged
          mobility: 0.55

        right_hand:
          holding: receiver_01

      psychology:
        goal: determine_signal_origin
        hope: declining
        suspicion: high

      knowledge:
        knows:
          - signal_contains_personal_information

        does_not_know:
          - sender_is_previous_self

  location:

    id: communications_room

    power:
      main: offline
      emergency: active

    lighting:
      canonical: amber_emergency

  props:

    receiver_01:
      condition: cracked
      powered: true

  world_constraints:
    - no_ftl_communication
```

Then:

```text
ShotIR
   +
WorldContextPackage
   +
Asset Manifest
   ↓
RenderPackageCompiler
   ↓
provider-specific rendering input
```

The video model never has to infer which Aria it should render.

---

# 11. “Resolving state = compiling dense memory facts?”

**Almost, but I would make one crucial distinction.**

The exact formula should be:

```text
ResolvedState(t)
    =
Reduce(
    nearest canonical snapshot,
    canonical events after snapshot up to t
)
```

Then:

```text
AgentContext(role, t)
    =
Project(
    ResolvedState(t)
    + canon
    + relevant long-term memory,
    role
)
```

So yes:

> **Agent context is a compiled representation of dense accumulated history.**

But exact state should **not** be reconstructed from fuzzy semantic memory every time.

Memory enriches the context.

Events + snapshots determine truth.

That separation is essential.

---

# 12. Where does the World Model graph live?

I would not have “one graph database = World Model.”

I'd architect it like:

```text
                 WORLD MODEL SERVICE
                         │
          ┌──────────────┼──────────────┐
          │              │              │
          ▼              ▼              ▼
    WorldEventStore   SnapshotStore   RuleStore
      canonical        canonical      canonical
          │              │              │
          └───────┬──────┴──────────────┘
                  ▼
             StateReducer
                  │
                  ▼
           Resolved World State
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
 ContextCompiler QueryAPI  BranchSimulator
       │
       ▼
   agents/renderers


                  +

             L9MemoryBridge
                  │
                  ▼
       l9-graphiti-memory
                  │
            MemoryService
                  │
           canonical records
                  │
             durable outbox
                  │
                  ▼
       optional Graphiti/Zep
          graph projection
```

That matches your existing repository extremely well.

The current `l9-graphiti-memory` architecture explicitly says it owns governed memory persistence/retrieval but **does not own a World Model**, and that Graphiti/Zep are rebuildable projections rather than canonical truth. Its canonical store can function without those projection providers. ([GitHub][3])

That is exactly what we want.

---

# 13. Mechanically interfacing with `l9-graphiti-memory`

The current Python SDK exposes typed:

```text
write()
search()
hydrate()
get()
phase_lock()
lineage()
```

over `MemoryService`. ([GitHub][4])

Its current write contract already supports namespaces, memory classes, structured subject/predicate/object assertions, provenance/evidence/confidence, valid-time ranges, tags, metadata, supersession and references. Hydration accepts a task, namespaces, entities, topics, memory classes, a valid-time coordinate and a token budget. ([GitHub][5])

So I would create:

```python
class L9WorldMemoryBridge:

    def __init__(self, memory_sdk):
        self.memory = memory_sdk

    def record_world_event(self, event):
        ...

    def record_canon_fact(self, fact):
        ...

    def hydrate_history(
        self,
        *,
        task: str,
        universe_id: str,
        entity_ids: list[str],
    ):
        ...

    def explain_lineage(self, memory_record_id):
        ...
```

Conceptually, a committed world event gets translated:

```python
from l9_graphite_memory.contracts import (
    MemoryAssertion,
    MemoryWriteRequest,
    MemoryClass,
)

request = MemoryWriteRequest(
    namespace="quantum.animation/orpheus",
    memory_class=MemoryClass.EPISODIC,

    content=(
        "Aria's left shoulder actuator was damaged "
        "during the collision in shot qshot_0031."
    ),

    assertion=MemoryAssertion(
        subject="qchar_000001",
        predicate="has_condition",
        object="damaged_left_shoulder",
    ),

    provenance=provenance,

    valid_from=event.universe_time,

    tags=(
        "character:aria",
        "episode:ep01",
        "physical-state",
    ),

    metadata={
        "world_event_id": event.event_id,
        "shot_id": event.shot_id,
        "continuity_id": event.continuity_id,
    },

    idempotency_key=f"world-event:{event.event_id}",
)

memory_sdk.write(request)
```

That's a sketch around the repository's current typed surface, not a claim that these exact production metadata conventions already exist.

Later an agent can retrieve historical context:

```python
from l9_graphite_memory.contracts import HydrationRequest

history = memory_sdk.hydrate(
    HydrationRequest(
        task=(
            "Direct a confrontation between Aria and Eva. "
            "Retrieve only history materially relevant to trust, "
            "memory, betrayal, and their current objectives."
        ),
        namespaces=("quantum.animation/orpheus",),
        entities=("qchar_000001", "qchar_000002"),
        topics=("trust", "betrayal", "memory"),
        token_budget=1800,
    )
)
```

The repo's retrieval architecture already does canonical filtering, query classification, independent lexical/temporal retrieval, optional graph/semantic strategies, explainable ranking and bounded hydration. ([GitHub][3])

So we'd be reusing a lot.

---

# 14. What lives in L9 Memory vs the World Model

The clean rule:

```text
L9 MEMORY
"What do we remember about reality and its history?"


WORLD MODEL
"What exactly is true at coordinate X?"
```

Example:

L9 Memory:

```text
Aria injured shoulder.
Aria repaired shoulder.
Aria injured it again.
```

World State:

```text
@ episode 6 / scene 3 / shot 18

aria.left_shoulder.condition = repaired
```

That keeps semantic retrieval away from deterministic state correctness.

---

# 15. `Oracle` in this architecture

An **oracle** is an authoritative reference against which another system's output is checked.

It does **not** mean an omniscient AI model.

For visual QC:

```text
World Model = oracle

Expected:
Aria left shoulder damaged
receiver in right hand
emergency lights amber

Observed render:
Aria shoulder intact
receiver in left hand
lights blue
```

Therefore QC can say:

```text
FAIL
```

The oracle provides expected truth.

The critic determines what the media actually depicts.

```text
WORLD MODEL
expected truth
      │
      ▼
    compare
      ▲
      │
VISION CRITIC
observed render
```

That's what makes continuity QC much less subjective.

---

# 16. `Retcon` in this architecture

**Retcon = retroactive continuity change.**

You're deliberately changing previously established canonical reality.

Important distinction:

```text
Canon always said:
Marcus alive.

Aria believed:
Marcus dead.

Audience believed:
Marcus dead.

Episode 7 reveals Marcus alive.
```

That is **not a retcon**.

It's a reveal.

But:

```text
Canon v4:
Marcus objectively died in 2371.

Later production decision:
Actually Marcus survived.
```

That's a retcon.

Mechanically:

```python
CanonRevision(
    supersedes=fact_old,
    replacement=fact_new,
    reason="series_rearchitecture",
    authority="studio_canon",
)
```

Then Quantum performs:

```text
dependency analysis
       ↓
Which stories relied on old truth?
Which scenes are now contradictory?
Which character beliefs need reinterpretation?
Which assets or dialogue become inconsistent?
```

Your L9 memory repository is already designed for non-destructive supersession and bi-temporal records, distinguishing when a fact is valid from when it was recorded, which is useful for preserving the historical lineage of such canon changes. ([GitHub][3])

---

# 17. WORLD.RULE.CAUSALITY_VIOLATION mechanically

World rules cannot just be prose.

They need executable representations.

```python
class WorldRule(BaseModel):
    id: str
    applies_to: set[str]
    severity: Literal["hard", "soft"]
    validator: str
```

Then implementations:

```python
class NoFTLCommunicationRule:

    id = "physics.communication.no_ftl"

    def validate(
        self,
        snapshot: WorldSnapshot,
        event: EventProposal,
    ) -> RuleResult:

        if event.type != "information_transfer":
            return RuleResult.pass_()

        distance = world_distance(
            event.source,
            event.destination,
            snapshot,
        )

        elapsed = (
            event.received_at
            - event.sent_at
        ).total_seconds()

        minimum_possible = (
            distance /
            snapshot.constants.max_signal_speed
        )

        if elapsed < minimum_possible:
            return RuleResult.fail(
                code="WORLD.RULE.CAUSALITY_VIOLATION",
                rule_id=self.id,
                expected=f"elapsed >= {minimum_possible}",
                observed=f"elapsed = {elapsed}",
            )

        return RuleResult.pass_()
```

Then every proposed story event runs:

```python
result = world.rules.validate(
    current_state,
    proposed_event,
)

if result.failed:
    reject(proposed_event)
```

So a Writer can generate an impossible idea.

It just cannot **commit** it.

That's the important boundary.

---

# 18. Hard rules versus soft rules

Some world laws are absolute:

```text
FTL impossible
dead human cannot act
locked door cannot be traversed
character cannot know unknown fact
```

Others should be soft:

```text
Aria normally avoids emotional openness.
Eva rarely uses violence.
Station regulations prohibit entering reactor room.
```

A soft violation means:

> possible, but must have sufficient causal explanation.

So:

```python
RuleResult(
    status="requires_justification",
    penalty=0.71,
    required_evidence=[
        "extreme emotional pressure",
    ],
)
```

This lets characters surprise us without becoming inconsistent.

---

# 19. Sound Designer: mechanically deriving the sound

This is a great example of why a shared World Model reaches far beyond writing.

Suppose the physical event is:

```yaml
event:
  type: footstep

  actor: aria

  foot:
    material: ceramic_composite

  surface:
    material: steel_grating

  motion:
    velocity: slow
    force: medium

location:
  id: service_corridor_4

  geometry:
    scale: long_narrow

  materials:
    dominant:
      - steel
      - composite

  atmosphere:
    pressure: normal

  ambient_emitters:
    - ventilation_fan_04
    - transformer_11
```

A deterministic `AcousticContextCompiler` turns world state into:

```python
class AcousticContext(BaseModel):
    source_material: str
    contact_material: str

    impact_class: str

    room_geometry: RoomGeometry
    room_materials: list[MaterialProfile]

    atmosphere: AtmosphereProfile

    listener_distance_m: float

    active_emitters: list[AmbientEmitter]
```

Then:

```python
class SoundDeriver:

    def derive_footstep(
        self,
        event: PhysicalEvent,
        ctx: AcousticContext,
    ) -> FoleyRecipe:

        base_sound = self.foley_library.resolve(
            interaction="footstep",
            source_material=ctx.source_material,
            contact_material=ctx.contact_material,
            impact_class=ctx.impact_class,
        )

        resonance = self.acoustic_model.body_resonance(
            actor=event.actor,
            event=event,
        )

        reverb = self.acoustic_model.room_response(
            geometry=ctx.room_geometry,
            materials=ctx.room_materials,
            atmosphere=ctx.atmosphere,
        )

        ambience = [
            self.resolve_emitter(emitter)
            for emitter in ctx.active_emitters
        ]

        return FoleyRecipe(
            dry_source=base_sound,
            resonance=resonance,
            reverb=reverb,
            ambience=ambience,
        )
```

The chain is:

```text
WORLD STATE
    ↓
physical event + materials + geometry
    ↓
AcousticContext
    ↓
SoundRecipe
    ↓
sample retrieval / sound generation
    ↓
spatialization
    ↓
timeline
```

So:

**footstep character** comes from foot material × floor material × force × gait.

**Mechanical resonance** comes from Aria's physical construction and the impacted structure.

**Reverberation** comes from room geometry/material state.

**Ambient noise** comes from currently operating environment emitters.

And if:

```text
ventilation_fan_04.powered = false
```

it disappears from the ambience automatically.

That's exactly the kind of detail a human sound team would easily miss between scenes.

---

# 20. One character becomes reusable because identity and state separate

This is worth formalizing:

```text
CHARACTER IDENTITY
stable

Aria:
  core visual identity
  voice
  psychology
  biography
  movement
  capabilities


CHARACTER STATE
changes constantly

Ep 01:
  shoulder damaged
  trusts Eva .2

Ep 08:
  shoulder repaired
  trusts Eva .7
```

So:

```text
qchar_000001
```

can continue indefinitely while accumulating state/history.

The persistent entity is reusable IP.

The current state is just the latest version of its life.

---

# 21. The World Model should have this concrete internal architecture

I think we're now converging on:

```text
╔════════════════════════════════════════════════╗
║             WORLD MODEL SERVICE                ║
║                                                ║
║  Canon Store                                   ║
║  World Event Store                             ║
║  Snapshot Store                                ║
║  State Reducer                                 ║
║  Rule Engine                                   ║
║  Affordance Engine                             ║
║  Psychological State Engine                    ║
║  Epistemic State Engine                        ║
║  Relationship State Engine                     ║
║  Context Compiler                              ║
║  World Query API                               ║
║  Causal Branch Simulator                       ║
║  Graph Projection                              ║
║  L9 Memory Bridge                              ║
╚═══════════════════════╤════════════════════════╝
                        │
                 shared intelligence
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
        Writer       Director       Renderer
          ▼             ▼             ▼
       Dialogue       Sound          Editor
          ▼             ▼             ▼
        Story           QC          Composer
```

And I would describe the conceptual breakthrough as:

> **The World Model converts production history into compiled present context.**

That is exactly what you noticed.

We stop solving context by repeatedly asking models to reread history.

Instead:

```text
thousands of events
+
millions of accumulated facts
+
long-term semantic memory
          ↓
     STATE RESOLUTION
          ↓
        "now"
          ↓
    role projection
          ↓
200–2,000 tokens actually needed
by this particular agent
```

That is the scalability mechanism.

And the next piece I'd design is the actual **World Model data model**—`WorldEntity`, `WorldEvent`, `WorldSnapshot`, `WorldRule`, `Belief`, `Knowledge`, `Intent`, `Relationship`, `Affordance`, `StoryCoordinate`, `Branch`, and the reducer semantics—because once those contracts are correct, almost everything we just described becomes implementable rather than conceptual.

[1]: https://arxiv.org/abs/2305.10601?utm_source=chatgpt.com "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
[2]: https://aclanthology.org/2025.knowllm-1.10/?utm_source=chatgpt.com "Theorem-of-Thought: A Multi-Agent Framework for Abductive, Deductive ..."
[3]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/ARCHITECTURE.md "l9-graphiti-memory/ARCHITECTURE.md at main · Quantum-L9/l9-graphiti-memory · GitHub"
[4]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/src/l9_graphite_memory/sdk.py "l9-graphiti-memory/src/l9_graphite_memory/sdk.py at main · Quantum-L9/l9-graphiti-memory · GitHub"
[5]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/src/l9_graphite_memory/contracts/requests.py "l9-graphiti-memory/src/l9_graphite_memory/contracts/requests.py at main · Quantum-L9/l9-graphiti-memory · GitHub"


-----
Yes — **“persistent entity = reusable IP”** is exactly the idea.

A character is the most obvious example, but the same abstraction applies to a location, artifact, organization, species, culture, vehicle, even a recurring musical motif:

```text
qchar_000001 = Aria

IDENTITY          stable
CANON             versioned
HISTORY           accumulates
CURRENT STATE     changes constantly
ASSETS            evolve/version
RELATIONSHIPS     evolve
MEMORIES          accumulate
```

So Aria is no longer “a prompt that resembles the previous Aria.” She becomes a persistent entity whose existence spans productions.

```text
                    ARIA
                 qchar_000001
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
    Short 1        Episode 9       Season 4
       │              │              │
       └──────────── same entity ─────┘
```

That is absolutely reusable-IP territory.

## How the L9 projection module helps the World Model

The clean architecture is:

```text
               WORLD MODEL
                   │
        canonical events/state
                   │
                   ▼
              L9 Bridge
                   │
                   ▼
             MemoryService
                   │
             RecordStore
          canonical memory
                   │
             durable outbox
                   │
                   ▼
        Projection Compiler
                   │
          ┌────────┴────────┐
          ▼                 ▼
       Graphiti            Zep
     graph/search       graph/search
```

The repository already makes a crucial guarantee: the canonical `RecordStore` remains authoritative, while graph/semantic systems are rebuildable projections used to improve retrieval. Its projection contracts explicitly reject authoritative vector state, define source event types, deterministic rendering, replay behavior, scoping, provider targets, and rebuild/query SLOs. ([GitHub][1])

That's ideal for the WM.

The World Model can say:

```text
FACTUAL TRUTH
aria.left_shoulder = damaged
```

and never depend on Graphiti to decide that.

But the Graphiti projection can make relationships around that fact easily discoverable:

```text
Aria
 ├── suffered → shoulder_damage
 │                 │
 │                 └── caused_by → reactor_collision
 │
 ├── currently_wants → reach_shuttle
 │
 └── depends_on → Eva
```

Then StoryAgent can ask fuzzy/relational questions such as:

```text
Find unresolved constraints that could interfere
with Aria's current goal.
```

Graph retrieval can discover:

```text
Aria → damaged shoulder
Aria → must climb maintenance shaft
maintenance shaft → requires two-handed climbing
```

The **projection discovers relevance**.

The **World Model verifies truth**.

That's the division.

The existing projection renderer also deterministically serializes declared canonical record fields, normalizes them, computes content digests, and can generate content-addressed embedding cache keys. That means a projection can be regenerated predictably from canonical memory instead of becoming another untraceable state store. ([GitHub][2])

I would exploit that heavily.

---

# But I would have two different “graphs”

This distinction will save us architecture pain later:

```text
WORLD STATE GRAPH
exact
deterministic
operational
used for correctness

        +

MEMORY/SEMANTIC GRAPH
relational
searchable
associative
used for discovery/reasoning
```

For example:

```text
WorldStateGraph:

receiver.owner = aria
receiver.hand = right
```

No ambiguity.

Graphiti projection might represent much richer connections:

```text
receiver
  ├── associated_with → Marcus
  ├── emotionally_significant_to → Aria
  ├── discovered_in → Episode 1
  ├── clue_for → identity_mystery
  └── damaged_during → reactor_event
```

The second graph is what makes:

> Find dramatically relevant facts about the receiver.

powerful.

The first is what makes:

> Which hand is holding it?

safe.

---

# More important: how do we stop the Oracle from failing so often?

You identified exactly the right objective.

This:

```text
Expected:
shoulder damaged
receiver right hand
lights amber

        ↓

GENERATE

        ↓

Observed:
shoulder intact
receiver left hand
lights blue

        ↓

FAIL
```

is useful.

But still wasteful.

The better goal is:

> **Make invalid images increasingly difficult to generate in the first place.**

I would build a **Continuity Prevention Pipeline**:

```text
                  WORLD STATE
                       │
                       ▼
              Required Visual Truth
                       │
                       ▼
             Enforcement Compiler
                       │
                       ▼
        Constraint-Coverage Validator
                       │
                       ▼
            Manufacturing Strategy
                       │
                       ▼
                 RENDER PACKAGE
                       │
                       ▼
                    render
                       │
                       ▼
             Oracle validation
```

The Oracle becomes the safety net.

Not the steering wheel.

---

# Compile truth into visual invariants

Instead of giving the renderer prose:

```text
Aria is damaged and holding her receiver.
```

compile:

```yaml
visual_invariants:

  - fact:
      path: aria.left_shoulder.condition
      value: damaged

    importance: critical

    visible: true

    enforcement:
      type: canonical_character_variant
      asset: aria@damage_07


  - fact:
      path: aria.right_hand.held_object
      value: receiver_01

    importance: critical

    visible: true

    enforcement:
      type: spatial_binding
      actor: aria
      body_anchor: right_hand
      object: receiver_01


  - fact:
      path: communications_room.lighting
      value: amber_emergency

    importance: critical

    enforcement:
      type: environment_variant
      asset: communications_room@emergency_amber
```

Notice:

**not prompt instructions.**

Execution bindings.

---

# Every invariant gets an enforcement strength

I would classify how strongly Quantum is actually controlling the fact:

```text
5  DETERMINISTIC
4  STRUCTURALLY_ANCHORED
3  REFERENCE_CONDITIONED
2  PROMPT_CONDITIONED
1  IMPLIED
0  UNCONTROLLED
```

Example:

```text
amber lights
→ deterministic grade/environment layer
→ strength 5

Aria appearance
→ canonical reference images / character conditioning
→ strength 3-4

receiver in right hand
→ pose/object spatial control
→ strength 4

"Aria should seem lonely"
→ model judgment
→ strength 2
```

Then impose:

```python
if invariant.critical and enforcement.strength < 3:
    reject_render_plan()
```

🔥

We don't spend money rendering a shot where a critical continuity fact is only being whispered into a text prompt.

---

# This means the manufacturing strategy changes based on the constraint

Suppose the current video generator consistently struggles with:

```text
specific object
+
specific hand
+
character movement
```

Instead of:

```text
generate again
generate again
generate again
```

the Production Planner learns:

```text
RIGHT-HAND PROP OWNERSHIP
         │
         ▼
full-video generation reliability = 0.54
layered/keyframe strategy         = 0.93
```

So it automatically chooses:

```text
canonical Aria keyframe
      +
receiver spatially anchored
      +
image-to-video motion
```

or:

```text
background generation
+
character generation
+
prop composite
```

depending on available controls.

The **semantic ShotSpec doesn't change**.

The manufacturing plan does.

---

# Add a Constraint Coverage Validator

Before any shot reaches the renderer:

```python
def validate_constraint_coverage(
    world_context,
    render_plan,
):

    for invariant in world_context.visual_invariants:

        binding = render_plan.binding_for(
            invariant.fact_ref
        )

        if not binding:
            return fail(
                "RENDER.CONSTRAINT.UNBOUND"
            )

        if (
            invariant.critical
            and binding.strength
                < invariant.minimum_strength
        ):
            return fail(
                "RENDER.CONSTRAINT.WEAK_BINDING"
            )

    return pass_()
```

So Shot 217 can fail **before generation** because:

```text
receiver-right-hand requirement
has no sufficiently strong enforcement strategy
```

That's a good failure.

Costs almost nothing.

---

# Then learn from every Oracle failure

This is where the autonomous system starts compounding quality.

Suppose:

```text
300 shots
900 initial takes
```

produce 67 failures involving hands and props.

Store structured production observations:

```yaml
observation:

  renderer: renderer_x@v4

  shot_characteristics:
    characters: 1
    hand_object_interaction: true
    camera_motion: medium

  failure:
    type: handedness_drift

  strategy:
    type: text_plus_reference

  outcome:
    pass: false
```

Now L9 Memory becomes valuable **for production intelligence too**, not just fictional history.

Its graph/semantic projections make patterns like:

```text
renderer X
   ↓ frequently fails
hand-held prop continuity

renderer Y
   ↓ succeeds
close-up facial acting

layered strategy
   ↓ succeeds
precise prop placement
```

discoverable across thousands of productions. L9's architecture is explicitly designed to combine canonical lexical/temporal retrieval with optional graph and semantic retrieval evidence, then produce bounded ranked hydration rather than treating any one projection as truth. ([GitHub][1])

Now `RendererRouterAgent` gets smarter over time.

---

# I'd measure one metric relentlessly

Call it:

```text
World Compliance Failure Rate
```

or WCFR:

```text
critical WM violations in generated takes
──────────────────────────────────────────
total generated takes
```

Initially maybe:

```text
WCFR = 18%
```

Then:

```text
v2 enforcement compiler     → 11%
better canonical assets     → 7%
renderer routing            → 4%
keyframe anchoring          → 2%
learned risk policies       → 0.8%
```

QC matters.

But **declining WCFR** is evidence your architecture is actually becoming more autonomous.

I would also monitor:

```text
Pre-render Prevention Rate
```

How many invalid plans did Quantum reject **before paying for generation?**

That's equally important.

---

# Think of this like a type system

There's a very nice software analogy.

Weak system:

```python
render("Aria holding receiver")
```

Equivalent to dynamically typed:

> Hope it's right.

Quantum system:

```python
RenderPackage[
    CharacterVariant[AriaDamage07],
    HeldObject[Receiver01, RIGHT_HAND],
    Lighting[EmergencyAmber],
]
```

Before execution:

```text
type check
constraint check
rule check
asset check
renderability check
```

Then render.

The more continuity becomes **compilable constraints**, the less continuity remains a probabilistic generation problem.

That's the real path toward near-zero failures.

---

# Some facts should bypass generative uncertainty entirely

If a critical fact can be deterministic, make it deterministic.

For example:

```text
readable signage
computer displays
exact logos
eye color correction
light color
certain props
damage overlays
screen graphics
Earth outside a window
```

Depending on the shot, these may be better handled through compositing than asking a model to preserve them perfectly.

So World Model could eventually provide:

```yaml
render_policy:

  aria_identity:
    control: character_reference

  receiver_hand:
    control: spatial_anchor

  emergency_lighting:
    control: deterministic_grade

  receiver_display_text:
    control: deterministic_composite
```

The World Model says **what must be true**.

The Production Engine decides **the strongest practical way to guarantee it**.

---

# This creates an extremely valuable feedback loop

```text
                    WORLD MODEL
                        │
                        ▼
                expected reality
                        │
                        ▼
            Enforcement Compiler
                        │
                        ▼
                 render strategy
                        │
                        ▼
                     MEDIA
                        │
                        ▼
                 ORACLE / QC
                  ↙          ↘
               PASS          FAIL
                │              │
                │              ▼
                │       Production Memory
                │              │
                │         L9 projections
                │              │
                └──────► strategy learning
```

That's where I see huge compounding leverage.

Every failure teaches the studio how to make that *class* of failure less likely in every future production.

---

## And yes: persistent entities are the IP primitive

I would define a persistent entity approximately as:

```python
class PersistentWorldEntity:

    entity_id: EntityId

    identity: IdentityCanon

    canon_version: int

    history: EventStream

    current_state: StateSnapshot

    relationships: RelationshipSet

    knowledge: KnowledgeState | None

    beliefs: BeliefState | None

    psychology: PsychologicalState | None

    assets: AssetSet

    provenance: Provenance
```

Aria is one.

But so is:

```text
Station Orpheus
Marcus's receiver
The Helios Corporation
A synthetic species
A recurring spacecraft
A city
A family
A religion
```

Each can accumulate history indefinitely.

And this produces one of the more exciting architectural consequences:

> **Quantum doesn't merely store films. It stores persistent worlds, and films become observations of events occurring inside those worlds.**

A film can finish.

**Aria does not.**

Her state simply stops at:

```text
WorldCoordinate(
    universe="orpheus",
    episode="ep01",
    frame=86400
)
```

until the next story picks her up again.

That is why `WorldCoordinate` is such a powerful primitive: **persistent entity + WorldCoordinate = exact reconstruction of an IP asset at any moment in its fictional life.**

[1]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/ARCHITECTURE.md "l9-graphiti-memory/ARCHITECTURE.md at main · Quantum-L9/l9-graphiti-memory · GitHub"
[2]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/src/l9_graphite_memory/projections/render.py "l9-graphiti-memory/src/l9_graphite_memory/projections/render.py at main · Quantum-L9/l9-graphiti-memory · GitHub"

-------
I’d formalize the World Model around **two read graphs backed by canonical event/state stores**, plus a third non-fictional learning plane for production experience.

The critical distinction is that **neither graph should be the ultimate source of truth**. Canonical truth remains `WorldEventStore + CanonStore + Snapshots`; the graphs are deterministic query projections. That mirrors the architecture already present in `l9-graphiti-memory`: its canonical `RecordStore` commits first, then a durable outbox feeds optional Graphiti/Zep projections; those projections may improve retrieval but cannot create canonical records or define lifecycle state. ([GitHub][1])

# 1. Graph A: World State Graph

This is the **exact operational graph**.

Its job is:

> What is true at `WorldCoordinate X`?

The schema is deliberately controlled by Quantum.

```text
                              ┌──────────────┐
                              │    Fact      │
                              └──────▲───────┘
                                     │
                           KNOWS / BELIEVES
                                     │
                                     │
┌──────────┐   LOCATED_AT    ┌───────┴──────┐
│ Location │◄────────────────│  Character   │
└──────────┘                 │    ARIA       │
                             └──┬────┬────┬──┘
                                │    │    │
                            HOLDS│    │    │HAS_GOAL
                                ▼    │    ▼
                           ┌────────┐ │ ┌──────┐
                           │  Prop  │ │ │ Goal │
                           └────────┘ │ └──────┘
                                      │
                                HAS_CONDITION
                                      ▼
                               ┌────────────┐
                               │ Condition  │
                               └────────────┘
```

Core node families would be things like:

```text
:Character
:Location
:Prop
:System
:Organization

:Fact
:Goal
:Intent
:Condition
:Capability
:Action
:Constraint
:WorldRule

:Event
:StateChange
```

Core relationships might be:

```text
LOCATED_AT
HOLDS
OWNS
WEARS
HAS_CONDITION

KNOWS
BELIEVES
DOUBTS

HAS_GOAL
INTENDS
FEARS
NEEDS

TRUSTS
LOVES
HATES
DEPENDS_ON
OWES

CAN_PERFORM
REQUIRES
BLOCKS
ENABLES

CAUSES
RESULTS_IN
MOTIVATED_BY
TRIGGERED_BY
```

The important trick is that **relationships with substantial identity, provenance, temporality or more than two participants become nodes themselves**.

For example, don't try to represent:

> Aria gives Eva Marcus's receiver in the comms room because she believes Eva can decode it.

as one giant edge.

Represent the event:

```text
                         ┌─────────────┐
                         │ Transfer    │
                         │ qevent_8921 │
                         └──────┬──────┘
            ┌───────────────────┼────────────────────┐
            │                   │                    │
          ACTOR              RECIPIENT             OBJECT
            ▼                   ▼                    ▼
          Aria                 Eva                Receiver
            │
            ├── AT ─────────────► CommsRoom
            │
            └── MOTIVATED_BY ───► DecodeSignalGoal
```

That one modeling technique eliminates most of the motivation for a native hypergraph.

---

# 2. Hypergraph? Not initially

I would **not use one for v1**.

Hypergraphs are attractive because an event like:

```text
give(
  giver=Aria,
  recipient=Eva,
  object=Receiver,
  location=CommsRoom,
  reason=DecodeSignal
)
```

is naturally an n-ary relationship.

But a property graph handles this cleanly by **reifying the relationship as an `Event` node**.

That gives us something even better:

```text
Event
  ├── actor
  ├── recipient
  ├── object
  ├── location
  ├── cause
  ├── valid_time
  ├── provenance
  ├── authority
  └── consequences
```

And now we can link other events to it.

```text
Event A
  │
CAUSES
  ▼
Event B
  │
CAUSES
  ▼
State Change
```

I would only revisit a real hypergraph if later profiling demonstrates that we spend enormous effort emulating higher-order relation queries.

Don't pay that complexity tax now.

---

# 3. Graph B: Semantic / Memory Graph

This one answers fundamentally different questions:

> What facts, events, relationships and concepts are **relevant** to what I'm trying to reason about?

For Aria's receiver:

```text
                         Receiver
                            │
              ┌─────────────┼──────────────┐
              │             │              │
       ASSOCIATED_WITH   SYMBOLIZES    WAS_OWNED_BY
              │             │              │
              ▼             ▼              ▼
           Marcus        connection      Marcus
              │
        IMPORTANT_TO
              ▼
            Aria
              │
        ASSOCIATED_WITH
              ▼
        identity mystery
              │
          CLUE_FOR
              ▼
        final revelation
```

It can contain much fuzzier semantic connections:

```text
related_to
emotionally_significant_to
similar_to
foreshadows
contradicts
supports
reminds_of
associated_with
historically_connected_to
thematically_connected_to
```

Those are tremendously useful for **discovery**.

But never use them to determine:

```text
receiver.current_owner
```

That comes from Graph A.

---

# 4. How L9 Graphiti Memory fits Graph B

This is where the projection subsystem is particularly useful.

The current projection contracts already define source event types, provider targets, declared render fields, fail-closed scope, full/incremental/partitioned replay, determinism rules, deletion propagation, projection SLOs and content digests. The compiler itself is explicitly deterministic and side-effect-free; the rendering layer deterministically normalizes declared canonical fields and computes content hashes. ([GitHub][2])

So World Model can do:

```text
CANONICAL WM EVENT
       │
       ▼
L9 MemoryRecord
       │
       ▼
canonical RecordStore
       │
       ▼
durable outbox
       │
       ▼
projection
       │
       ├──── Graphiti
       └──── Zep
```

If the semantic graph disappears tomorrow:

```text
canonical memory
      ↓
replay projection
      ↓
semantic graph restored
```

Excellent property.

I'd use at least two L9 namespaces:

```text
quantum.animation/world/<universe-id>
quantum.animation/production-intelligence
```

The first remembers fictional reality.

The second remembers how **Quantum itself performs**.

Do not mix those domains.

---

# 5. Should agents query Cypher?

Not directly.

I'd give agents:

```python
world.find_latent_conflicts(...)
world.explain_causality(...)
world.find_knowledge_asymmetries(...)
world.query_affordances(...)
world.find_story_pressure(...)
```

The World Query Compiler may translate some of those into Cypher.

That lets us change storage technology later.

If World State Graph uses Neo4j, Cypher is very suitable because `MATCH` directly expresses node/relationship patterns and supports multi-hop path matching. ([Neo4j Graph Intelligence Platform][3])

For L9/Graphiti semantic retrieval, I'd stay behind the L9 abstraction rather than teaching agents Graphiti's backing database. The current repository exposes search/hydration through `MemoryService`, while its Graphiti HTTP projection integrates through provider operations such as memory-fact and node search. ([GitHub][4])

So:

```text
Agent
  │
  ▼
WorldQueryAPI
  │
  ├── exact question ─────► WorldStateGraph
  │                         Cypher internally
  │
  └── associative question ► L9 Memory
                             Graphiti/Zep projection
```

That is the clean boundary.

---

# 6. Some very high-leverage Cypher queries

These are queries against the **exact controlled World State Graph**, not against provider-internal Graphiti structures.

### Find secrets relevant to Aria's current goals that someone else knows

```cypher
MATCH (aria:Character {id: $aria_id})-[:HAS_GOAL]->(goal:Goal)
MATCH (other:Character)-[:KNOWS]->(fact:Fact)-[:ENABLES|SATISFIES]->(goal)
WHERE NOT (aria)-[:KNOWS]->(fact)

OPTIONAL MATCH (aria)-[rel:RELATES_TO]->(other)

RETURN
    other.id,
    fact.id,
    fact.description,
    goal.id,
    rel.trust AS trust
ORDER BY trust ASC
```

This is basically:

> **Who possesses something Aria needs to know?**

Potential episode generator.

---

### Find latent relationship conflicts

```cypher
MATCH (aria:Character {id: $aria_id})-[:HAS_GOAL]->(goal:Goal)
MATCH (blocker)-[:BLOCKS]->(goal)
MATCH (aria)-[relationship:RELATES_TO]->(blocker)

WHERE
    relationship.emotional_importance >= 0.7
    AND relationship.unresolved = true

RETURN
    blocker.id,
    goal.id,
    relationship.type,
    relationship.trust,
    relationship.emotional_importance
ORDER BY relationship.emotional_importance DESC
```

Now Quantum finds:

```text
Aria needs truth
Eva is blocking truth
Eva matters deeply to Aria
relationship unresolved

→ dramatic pressure
```

---

### Find a belief/reality gap

```cypher
MATCH (aria:Character {id: $aria_id})-[b:BELIEVES]->(fact:Fact)
MATCH (:ObjectiveReality)-[:ASSERTS]->(truth:Fact)

WHERE
    fact.subject_id = truth.subject_id
    AND fact.predicate = truth.predicate
    AND fact.value <> truth.value

RETURN
    fact AS aria_belief,
    truth AS objective_truth,
    b.confidence
ORDER BY b.confidence DESC
```

Those are story mines.

A **strongly held false belief** is almost automatically narratively useful.

---

### Detect knowledge leakage before screenplay commit

```cypher
MATCH (line:DialogueLine {id: $line_id})-[:ASSERTS]->(fact:Fact)
MATCH (line)-[:SPOKEN_BY]->(speaker:Character)

WHERE
    NOT (speaker)-[:KNOWS]->(fact)
    AND NOT (speaker)-[:BELIEVES]->(fact)

RETURN speaker.id, fact.id
```

If rows come back:

```text
SCREENPLAY.EPISTEMIC_VIOLATION
```

before voice generation or rendering.

---

### Explain why some current state is true

```cypher
MATCH (fact:Fact {id: $current_fact_id})

MATCH p =
    (origin:Event)-[:CAUSES*1..8]->(fact)

RETURN p
ORDER BY length(p)
LIMIT 5
```

Conceptually:

```text
Why is Aria's shoulder damaged?

collision
   ↓
structural impact
   ↓
actuator fracture
   ↓
left_shoulder = damaged
```

Cypher supports path-pattern traversal for these graph-shaped queries; current Cypher also provides richer quantified and shortest-path constructs if we later need them. ([Neo4j Graph Intelligence Platform][5])

---

### Find existing affordances that advance a goal

```cypher
MATCH (aria:Character {id: $aria_id})-[:HAS_GOAL]->(goal:Goal)
MATCH (aria)-[:CAN_PERFORM]->(action:Action)-[:ADVANCES]->(goal)

OPTIONAL MATCH (action)-[:REQUIRES]->(requirement)

WITH action, goal, collect(requirement) AS requirements

RETURN action, goal, requirements
```

Then the deterministic Rule Engine evaluates whether the requirements currently hold.

The graph discovers candidates.

The rule engine proves executability.

---

### Blast-radius analysis for a canon change

```cypher
MATCH (fact:Fact {id: $fact_id})

MATCH (artifact)-[:DEPENDS_ON*1..6]->(fact)

RETURN
    labels(artifact) AS artifact_type,
    artifact.id,
    artifact.version
```

If you retcon:

```text
Marcus died in 2371
```

Quantum immediately finds:

```text
episodes
scenes
dialogue
reveals
character beliefs
assets
```

that depend on it.

---

# 7. You can query for “causally likely next events”

A graph alone shouldn't magically decide likelihood.

I'd use:

```text
Graph
  ↓
candidate affordances
  ↓
causal rule validation
  ↓
StoryAgent proposes combinations
  ↓
Branch simulation
  ↓
score consequences
```

For example, exact graph discovers:

```text
Aria wants truth.
Eva knows truth.
Aria can confront Eva.
Eva can lie.
Memory archive is accessible.
Power is degrading.
```

The model might produce:

```text
A. Aria confronts Eva.
B. Aria secretly accesses archive.
C. Aria tests Eva with false information.
D. Power failure forces both into archive chamber.
```

Then each gets simulated.

The key is that the model cannot arbitrarily produce:

```text
E. Aria teleports to Mars.
```

because no valid affordance/rule set supports it.

---

# 8. The third graph-like plane: Production Experience

This is how Quantum gets better from failures.

It should **not** belong to fictional reality.

Imagine:

```text
                   RenderAttempt
                  qrender_98172
                   /    |     \
                  /     |      \
                 ▼      ▼       ▼
            Renderer  Strategy  ShotClass
              X@v4     IMG2VID   closeup
                 \
                  \
                   ▼
           FAILED_WITH
                   │
                   ▼
       HANDEDNESS_DRIFT
```

And another:

```text
RenderAttempt
    │
    ├─ USED_RENDERER → RendererY@v7
    ├─ USED_STRATEGY → layered_composite
    ├─ HAS_FEATURE → hand_prop_interaction
    ├─ HAS_FEATURE → one_character
    ├─ HAS_FEATURE → slow_camera
    │
    └─ OUTCOME → PASS
```

Every attempt becomes an **experience event**.

---

# 9. Mechanically learning from failures

I would not initially let an LLM rewrite Quantum's production rules because it “noticed something.”

Make learning statistical and gated.

Every attempt records:

```python
class RenderExperience(BaseModel):
    attempt_id: str

    renderer_id: str
    renderer_version: str
    strategy_id: str

    shot_features: dict[str, float | str | bool]

    invariant_types: list[str]

    cost: float
    latency_ms: int

    qc_scores: dict[str, float]

    passed: bool
    violations: list[str]
```

Example:

```json
{
  "renderer_id": "renderer_x",
  "renderer_version": "4.2",
  "strategy_id": "text_plus_character_ref",

  "shot_features": {
    "character_count": 1,
    "hand_prop_interaction": true,
    "dialogue": false,
    "camera_motion": "medium",
    "duration_seconds": 5.4
  },

  "passed": false,

  "violations": [
    "PROP.HANDEDNESS_DRIFT"
  ]
}
```

Now learn:

```text
P(
    failure_type
    |
    renderer,
    strategy,
    shot_features,
    constraint_types
)
```

Then Production Planner evaluates possible manufacturing strategies:

```python
utility(strategy) = (
      expected_quality(strategy)
    - 8.0 * critical_failure_probability(strategy)
    - 0.5 * expected_cost(strategy)
    - 0.2 * expected_latency(strategy)
)
```

and selects:

```python
best = max(strategies, key=utility)
```

This means after enough examples Quantum could know:

```text
Shot:
1 character
close-up
receiver in right hand
precise hand interaction
slow push-in

Renderer X + prompt
critical fail probability = .31

Renderer Y + reference
critical fail probability = .12

Layered keyframe strategy
critical fail probability = .018
```

Therefore:

```text
choose layered keyframe
```

before wasting money.

---

# 10. The learning loop

The compounding mechanism should be:

```text
                PRODUCTION
                    │
                    ▼
             every attempt
                    │
                    ▼
             QC observation
                    │
                    ▼
           Experience Record
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
 canonical metrics           L9 Memory
        │                        │
        │                    projections
        │                        │
        └──────────┬─────────────┘
                   ▼
           Failure Analytics
                   │
                   ▼
          Reliability Model
                   │
                   ▼
         Candidate Policy vN+1
                   │
                   ▼
         historical backtest
                   │
                   ▼
          QC calibration suite
                   │
                   ▼
             shadow mode
                   │
                   ▼
           bounded canary
                   │
                   ▼
               PROMOTE
```

The current L9 architecture is a good substrate for the semantic/history side of this because it already supports canonical memory plus independent lexical, temporal, graph and semantic retrieval evidence with explainable ranking and bounded hydration. ([GitHub][1])

But I would keep the numeric learning dataset separately queryable too.

---

# 11. Start simpler than machine learning

For v1, you could already get huge leverage from reliability tables.

```text
                             attempts   pass rate

renderer-x / dialogue face       482       94.2%
renderer-x / hand prop           203       61.1%

renderer-y / dialogue face       371       89.4%
renderer-y / hand prop           188       86.7%

layered / hand prop              121       97.5%
```

That alone changes routing.

Then graduate to:

```text
supervised failure classifier
↓
strategy ranker
↓
contextual bandit
```

only as the experience dataset becomes rich enough.

The highest-leverage early learning isn't necessarily retraining video models.

It's **learning which manufacturing strategy to choose**.

---

# 12. A high-leverage production-learning Cypher query

```cypher
MATCH (attempt:RenderAttempt)-[:HAS_FEATURE]->
      (:ShotFeature {name: "hand_prop_interaction"})

MATCH (attempt)-[:USED_RENDERER]->(renderer:RendererVersion)
MATCH (attempt)-[:USED_STRATEGY]->(strategy:RenderStrategy)

OPTIONAL MATCH
    (attempt)-[:FAILED_WITH]->
    (violation:ViolationType {
        code: "PROP.HANDEDNESS_DRIFT"
    })

WITH
    renderer,
    strategy,
    count(attempt) AS attempts,
    count(violation) AS failures

RETURN
    renderer.id,
    strategy.id,
    attempts,
    failures,
    1.0 * failures / attempts AS failure_rate

ORDER BY failure_rate ASC
```

Now the system is literally asking:

> Across everything we've ever manufactured, which approach is most reliable for this type of shot?

🔥

---

# 13. Complete `WorldCoordinate`

I would make this one of the most important structs in the entire architecture.

Crucially it separates **fictional chronological time** from **where the audience currently is in the movie**.

That allows flashbacks, flash-forwards and parallel storylines cleanly.

```yaml
schema: quantum.world/coordinate-v1


world_coordinate:

  # ----------------------------------------------------------
  # WHICH FICTIONAL UNIVERSE?
  # ----------------------------------------------------------

  universe:
    id: quniv_orpheus

    continuity:
      id: main

    canon_revision:
      id: canon_0017

    branch:
      id: canonical
      hypothetical: false


  # ----------------------------------------------------------
  # OBJECTIVE FICTIONAL TIME
  #
  # Where reality currently is chronologically.
  # Independent of movie playback order.
  # ----------------------------------------------------------

  valid_time:

    universe_time:
      iso: "2374-05-18T02:14:33.416Z"

    # Monotonic fictional clock useful when calendar semantics
    # are irrelevant or insufficient.
    universe_tick: 9184473316


  # ----------------------------------------------------------
  # NARRATIVE LOCATION
  #
  # Where this coordinate belongs in story structure.
  # ----------------------------------------------------------

  narrative:

    series_id: qseries_last_signal

    season:
      id: qseason_01
      number: 1

    episode:
      id: qepisode_007
      number: 7

    storyline:
      id: aria_primary

    act:
      id: act_03

    sequence:
      id: qsequence_031

    scene:
      id: qscene_000127
      index: 19

    beat:
      id: qbeat_000482

    shot:
      id: qshot_000127_000009
      index_in_scene: 9


  # ----------------------------------------------------------
  # PLAYBACK POSITION
  #
  # Where the AUDIENCE currently is in the finished episode.
  #
  # This may point at a completely different fictional time
  # during a flashback.
  # ----------------------------------------------------------

  playback:

    frame_rate:
      numerator: 24
      denominator: 1

    episode_frame: 17235

    episode_timecode: "00:11:58:03"

    shot_frame: 73


  # ----------------------------------------------------------
  # AUTHORITATIVE STATE ANCHOR
  #
  # Exact reconstruction:
  #
  # snapshot + canonical events through sequence 8182
  # ----------------------------------------------------------

  state_anchor:

    snapshot_id: qstate_0000182

    snapshot_event_sequence: 8100

    through_event_sequence: 8182

    state_revision: 493


  # ----------------------------------------------------------
  # BI-TEMPORAL AS-OF COORDINATE
  #
  # "Give me the fictional state as we understood/recorded it
  # by this transaction-time point."
  #
  # Essential for canon revision / debugging / retcons.
  # ----------------------------------------------------------

  transaction_time:

    as_of_recorded_at:
      iso: "2026-08-09T14:07:12.913Z"

    commit_sequence: 94521


  # ----------------------------------------------------------
  # PERSPECTIVE
  #
  # Same physical coordinate may produce different epistemic
  # views.
  # ----------------------------------------------------------

  perspective:

    plane: objective

    observer_entity_id: null

    include:
      objective_truth: true
      audience_disclosure: false
      character_knowledge: false
      character_beliefs: false


  # ----------------------------------------------------------
  # INTEGRITY
  # ----------------------------------------------------------

  integrity:

    coordinate_version: 1

    immutable: true

    digest:
      algorithm: sha256
      value: "8bc3e6f0..."
```

Now imagine a flashback.

The **playback coordinate** might be:

```text
Episode 7
00:11:58:03
```

while:

```text
valid_time =
2369-02-07
```

five years earlier.

No problem.

Or parallel editing:

```text
Shot A:
storyline = aria_primary
universe_time = 02:14:33

CUT TO

Shot B:
storyline = eva_parallel
universe_time = 02:13:59
```

No problem.

`WorldCoordinate` makes production ordering, narrative ordering and actual fictional chronology **independent axes**.

---

# 14. The architecture I'd lock

```text
                 CANONICAL REALITY
                         │
            ┌────────────┴─────────────┐
            │                          │
      WorldEventStore             SnapshotStore
            │                          │
            └────────────┬─────────────┘
                         ▼
                    StateReducer
                         │
                         ▼
               ResolvedState(t)
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
 WORLD STATE GRAPH              L9 MEMORY RECORDS
 exact/queryable                 historical/semantic
          │                             │
        Cypher                      projections
          │                          Graphiti/Zep
          │                             │
          └──────────────┬──────────────┘
                         ▼
                  World Query API
                         │
                         ▼
                  Context Compiler
                         │
                         ▼
                       AGENTS


                SEPARATE PLANE

            PRODUCTION EXPERIENCE
                         │
                         ▼
                 Failure Memory
                         │
                         ▼
               Reliability Models
                         │
                         ▼
                Strategy Routing
                         │
                         ▼
              fewer future failures
```

So the **World State Graph gives Quantum exact reasoning**, the **semantic graph gives it associative intelligence**, and the **production-experience graph gives it compounding operational intelligence**.

That last piece is how the system starts to develop what looks like institutional experience: after producing 100 shorts, it doesn't merely have more content—it has evidence about **which cinematic plans are hard, which renderers fail on which structures, which repair strategies work, and how to manufacture the 101st film with fewer mistakes than the first.**

[1]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/ARCHITECTURE.md "l9-graphiti-memory/ARCHITECTURE.md at main · Quantum-L9/l9-graphiti-memory · GitHub"
[2]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/src/l9_graphite_memory/projections/contracts.py "l9-graphiti-memory/src/l9_graphite_memory/projections/contracts.py at main · Quantum-L9/l9-graphiti-memory · GitHub"
[3]: https://neo4j.com/docs/cypher-manual/current/patterns/?utm_source=chatgpt.com "Patterns - Cypher Manual - Neo4j Graph Data Platform"
[4]: https://github.com/Quantum-L9/l9-graphiti-memory/tree/main "GitHub - Quantum-L9/l9-graphiti-memory: L9 Graphiti Memory — bi-temporal knowledge graph memory subsystem for autonomous agents (Zep Cloud transport) · GitHub"
[5]: https://neo4j.com/docs/cypher-manual/current/patterns/reference/variable-length-paths/?utm_source=chatgpt.com "Variable length paths - Cypher Manual - Neo4j Graph Data Platform"


----

Yes. This is where I’d stop talking about “memory” abstractly and define the **runtime semantics of fictional reality**.

The model I’d implement is fundamentally:

```text
Persistent entities
      +
Explicit propositions
      +
Immutable events
      +
Executable rules
      +
Deterministic reducer
      +
Immutable snapshots
      +
Hypothetical branches
      =
WORLD MODEL
```

The most important invariant is:

> **Nothing directly mutates World State. A committed `WorldEvent` is the only mechanism that changes canonical reality.**

That gives us causality, replay, debugging, branching, retcons, flashbacks, provenance and deterministic continuity almost for free.

---

# 1. Top-level architecture

```text
                         ┌─────────────────┐
                         │   WorldEntity   │
                         │ persistent ID   │
                         └────────┬────────┘
                                  │
                                  │ participates in
                                  ▼
                         ┌─────────────────┐
                         │   WorldEvent    │
                         │ immutable       │
                         └────────┬────────┘
                                  │
                           explicit mutations
                                  │
                                  ▼
                          ┌───────────────┐
                          │ StateReducer  │
                          │ deterministic │
                          └───────┬───────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ WorldSnapshot   │
                         │ state @ coord   │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                 Queries       Context       Graph
                              Compiler     Projections
```

Alongside it:

```text
WorldRule
    ↓ constrains
WorldEvent

Proposition
    ↓ referenced by
Belief / Knowledge

Intent
    ↓ helps derive
Affordance
    ↓ enables
candidate WorldEvent

Branch
    ↓ overlays events onto
WorldSnapshot
```

---

# 2. One additional primitive we need: `StateAddress`

Before the big objects, we need a way to say:

> Exactly what part of reality are we talking about?

```python
from typing import Any, Literal
from pydantic import BaseModel


class StateAddress(BaseModel):
    plane: Literal[
        "objective",
        "psychological",
        "epistemic",
        "relationship",
        "environment",
        "asset",
        "cinematic",
    ]

    subject_id: str

    path: str
```

Examples:

```python
StateAddress(
    plane="objective",
    subject_id="qchar_aria",
    path="physical.left_shoulder.condition",
)
```

```python
StateAddress(
    plane="environment",
    subject_id="qloc_comms_room",
    path="lighting.emergency.color",
)
```

```python
StateAddress(
    plane="relationship",
    subject_id="qrel_aria_eva",
    path="trust",
)
```

That lets the reducer mechanically address state.

---

# 3. `WorldEntity`

A `WorldEntity` is **persistent identity**.

It is intentionally *not* current state.

```python
class WorldEntity(BaseModel):
    entity_id: str

    entity_type: Literal[
        "character",
        "location",
        "prop",
        "vehicle",
        "organization",
        "species",
        "technology",
        "system",
        "artifact",
        "relationship",
        "concept",
    ]

    canonical_name: str

    aliases: tuple[str, ...] = ()

    universe_id: str

    lifecycle_status: Literal[
        "active",
        "inactive",
        "destroyed",
        "dead",
        "unknown",
        "retired",
    ] = "active"

    asset_family_id: str | None = None

    created_by_event_id: str | None = None

    provenance: dict
```

Aria:

```yaml
entity_id: qchar_000001
entity_type: character
canonical_name: Aria
universe_id: quniv_orpheus
asset_family_id: qasset_family_aria
```

That's basically it.

Her shoulder condition does **not** belong here.

Her current location does not belong here.

Her current trust for Eva does not belong here.

Those change.

`qchar_000001` doesn't.

This is why:

> **persistent entity = reusable IP primitive.**

---

# 4. `StateCell`

Snapshots need a deterministic representation of current values.

```python
class StateCell(BaseModel):
    address: StateAddress

    value: Any

    valid_since_event_id: str
    last_modified_event_id: str

    authority: str

    provenance: dict
```

Example:

```yaml
address:
  plane: objective
  subject_id: qchar_000001
  path: physical.left_shoulder.condition

value: damaged

valid_since_event_id: qevent_00812
last_modified_event_id: qevent_00812
authority: canonical_story_event
```

A snapshot is essentially a content-addressed collection of these.

---

# 5. We need `Proposition`

This is a subtle but foundational addition.

A belief cannot reference only a `Fact`.

Why?

Because people can believe things that are false.

So we create a proposition independently of whether it is true.

```python
class Proposition(BaseModel):
    proposition_id: str

    subject_id: str | None

    predicate: str

    object: Any

    qualifiers: dict = {}
```

For example:

```yaml
proposition_id: qpropst_001
subject_id: qchar_marcus
predicate: alive
object: true
```

Objective reality might currently say:

```text
Marcus alive = true
```

while Aria believes the proposition:

```text
Marcus alive = false
```

Both propositions can exist.

Truth comes from resolving the Objective World plane.

---

# 6. `Knowledge`

`Knowledge` represents information an observer has actually acquired.

```python
class Knowledge(BaseModel):
    knowledge_id: str

    holder_id: str
    proposition_id: str

    acquired_at: "WorldCoordinate"
    acquired_via_event_id: str

    source_entity_id: str | None = None

    status: Literal[
        "active",
        "stale",
        "forgotten",
        "retracted",
    ] = "active"

    last_verified_at: "WorldCoordinate | None" = None

    provenance: dict
```

Example:

```yaml
holder_id: qchar_eva
proposition_id: qpropst_marcus_created_aria

acquired_via_event_id: qevent_0281

status: active
```

Important distinction:

Knowledge can become **stale**.

Suppose Eva sees:

```text
Door A is open.
```

Then someone closes it.

Eva still possesses the memory:

> Door A was open when I saw it.

But she shouldn't automatically know its current state.

So facts can carry persistence semantics:

```text
persistent:
    "Marcus is Aria's creator."

volatile:
    "Door A is open."
```

The Epistemic Engine knows the difference.

---

# 7. `Belief`

Belief represents what an entity currently considers true.

It can disagree with objective reality.

```python
class Belief(BaseModel):
    belief_id: str

    holder_id: str

    proposition_id: str

    polarity: Literal[
        "believes_true",
        "believes_false",
        "uncertain",
    ]

    confidence: float

    formed_at: "WorldCoordinate"

    caused_by_event_ids: tuple[str, ...]

    basis:
        Literal[
            "observation",
            "testimony",
            "inference",
            "memory",
            "deception",
            "assumption",
        ]

    status: Literal[
        "active",
        "weakened",
        "superseded",
        "abandoned",
    ]

    provenance: dict
```

Now this can exist:

```text
OBJECTIVE:
Marcus alive = true

ARIA KNOWLEDGE:
No verified information after 2371.

ARIA BELIEF:
Marcus alive = false
confidence = .96

EVA KNOWLEDGE:
Marcus alive = true
```

That's dramatic irony represented as data.

---

# 8. Psychological state

Beliefs aren't enough.

I'd explicitly maintain structured **authorial internal state**.

Not because psychology is literally numeric, but because agents need something more precise than:

> She's kind of sad now.

For example:

```python
class EmotionActivation(BaseModel):
    emotion: str
    intensity: float
    target_id: str | None = None


class PsychologicalState(BaseModel):
    character_id: str

    emotions: tuple[EmotionActivation, ...]

    stress: float
    hope: float
    resolve: float

    active_fears: tuple[str, ...]
    active_needs: tuple[str, ...]

    attention_targets: tuple[str, ...]

    suppressing_emotions: tuple[str, ...] = ()

    last_modified_event_id: str
```

Example:

```yaml
character_id: qchar_aria

emotions:
  - emotion: fear
    intensity: 0.71
    target_id: qconcept_total_isolation

  - emotion: anger
    intensity: 0.37
    target_id: qchar_eva

stress: 0.68
hope: 0.21
resolve: 0.84

active_fears:
  - abandonment

suppressing_emotions:
  - fear
```

Performance Director can now receive:

```text
high fear
high resolve
fear intentionally suppressed
```

That's much stronger than generic “sad.”

---

# 9. `Intent`

An intent describes a desired future state.

```python
class Intent(BaseModel):
    intent_id: str

    actor_id: str

    kind: Literal[
        "goal",
        "plan",
        "desire",
        "avoidance",
        "commitment",
    ]

    description: str

    target_condition: dict

    priority: float
    commitment: float

    horizon: Literal[
        "immediate",
        "scene",
        "episode",
        "long_term",
    ]

    status: Literal[
        "active",
        "blocked",
        "satisfied",
        "abandoned",
        "superseded",
    ]

    parent_intent_id: str | None = None

    created_by_event_id: str

    provenance: dict
```

Aria:

```yaml
intent_id: qintent_0091

actor_id: qchar_aria
kind: goal

description: >
  Discover the true origin of the transmission.

target_condition:
  proposition_known:
    subject: qchar_aria
    proposition: qpropst_signal_origin

priority: 0.94
commitment: 0.88

horizon: episode
status: active
```

This is what enables causal story generation.

---

# 10. `Relationship`

I would make relationships **first-class objects**, not just graph edges.

Why?

Because a relationship itself has:

```text
history
state
secrets
trust
obligations
power
conflicts
```

And some relationships involve more than two entities.

```python
class RelationshipParticipant(BaseModel):
    entity_id: str
    role: str


class Relationship(BaseModel):
    relationship_id: str

    relationship_type: str

    participants: tuple[RelationshipParticipant, ...]

    established_by_event_id: str

    status: Literal[
        "active",
        "broken",
        "dormant",
        "ended",
    ]

    provenance: dict
```

Dynamic relationship state belongs in the snapshot:

```yaml
relationship: qrel_aria_eva

state:

  trust:
    aria_to_eva: 0.24
    eva_to_aria: 0.72

  intimacy: 0.43

  dependence:
    aria_on_eva: 0.61
    eva_on_aria: 0.49

  unresolved_conflicts:
    - eva_knows_memory_truth
    - aria_suspects_deception

  obligations:
    - eva_promised_to_protect_aria
```

Notice trust is asymmetric.

That's essential.

---

# 11. `ActionSchema`

To make affordances mechanically derivable, we need parameterized actions.

Think of this as a function signature for possible events.

```python
class ActionSchema(BaseModel):
    action_type: str

    roles: tuple[str, ...]

    preconditions: tuple["PredicateExpr", ...]

    effect_templates: tuple["MutationTemplate", ...]

    capability_requirements: tuple[str, ...]

    world_rule_tags: tuple[str, ...] = ()
```

For example:

```yaml
action_type: give_object

roles:
  - giver
  - recipient
  - object

preconditions:

  - equals:
      address: giver.physical.location
      value_ref: recipient.physical.location

  - equals:
      address: object.owner
      value_ref: giver.id

  - contains:
      address: giver.inventory
      value_ref: object.id

effect_templates:

  - set:
      address: object.owner
      value_ref: recipient.id

  - remove:
      address: giver.inventory
      value_ref: object.id

  - add:
      address: recipient.inventory
      value_ref: object.id
```

Now the Affordance Engine can bind actual entities.

---

# 12. `Affordance`

An affordance means:

> Given the current world state, this action is possible.

It should generally be **derived**, not canonical.

```python
class Affordance(BaseModel):
    affordance_id: str

    action_schema_id: str

    actor_id: str

    bindings: dict[str, str]

    coordinate: "WorldCoordinate"

    feasible: bool

    satisfied_preconditions: tuple[str, ...]
    blocking_preconditions: tuple[str, ...]

    predicted_effects: tuple["StateMutation", ...]

    enabled_by:
        tuple[str, ...]

    blocked_by:
        tuple[str, ...]

    feasibility_score: float

    derivation_hash: str
```

Example:

```yaml
action_schema: confront_character

actor_id: qchar_aria

bindings:
  target: qchar_eva

feasible: true

enabled_by:
  - same_location
  - aria_has_active_truth_goal
  - eva_is_accessible

predicted_effects:
  - eva_may_reveal_information
  - relationship_tension_increases
```

This is how we constrain “what can happen next.”

---

# 13. `WorldRule`

Rules give fictional reality teeth.

```python
class WorldRule(BaseModel):
    rule_id: str

    version: int

    category: Literal[
        "physics",
        "technology",
        "epistemic",
        "biology",
        "social",
        "character",
        "canon",
        "causality",
    ]

    severity: Literal[
        "hard",
        "soft",
    ]

    applies_to_event_types: tuple[str, ...]

    predicate: "PredicateExpr | None" = None

    validator_ref: str | None = None
    validator_version: str | None = None

    violation_code: str

    explanation: str

    active_from: "WorldInstant | None" = None
    active_until: "WorldInstant | None" = None
```

Simple rules can use declarative predicates.

Complicated rules use a registered deterministic validator.

For example:

```yaml
rule_id: qrule_no_ftl_information
version: 1

category: causality
severity: hard

applies_to_event_types:
  - information_transfer

validator_ref: physics.no_ftl_information
validator_version: "1.0"

violation_code: WORLD.RULE.CAUSALITY_VIOLATION
```

The rule itself is versioned.

So the universe's physical laws can evolve without hidden code changes.

---

# 14. Soft rules let characters surprise us ❤️

Suppose canon says:

> Aria normally avoids direct emotional disclosure.

Do **not** make that impossible.

```yaml
rule_id: qrule_aria_emotional_restraint

category: character
severity: soft

violation_code: CHARACTER.UNCHARACTERISTIC_DISCLOSURE
```

The Rule Engine could return:

```yaml
status: requires_justification

reason: >
  Aria's proposed behavior substantially exceeds her normal
  emotional directness.

acceptable_justification:
  - acute emotional pressure
  - major trust transition
  - deliberate manipulation
```

If current state says:

```text
stress = .94
Eva trust transitioned .22 → .81
Marcus truth just revealed
```

the event can pass.

This is how you get:

> **surprise without inconsistency.**

---

# 15. `WorldEvent`

This is the heart of the entire system.

```python
class StateMutation(BaseModel):
    op: Literal[
        "set",
        "unset",
        "add",
        "remove",
        "increment",
    ]

    address: StateAddress

    value: object | None = None


class WorldEvent(BaseModel):
    event_id: str

    universe_id: str
    continuity_id: str
    branch_id: str

    event_type: str

    coordinate: "WorldCoordinate"

    actors: tuple[str, ...]
    subjects: tuple[str, ...]

    causes: tuple[str, ...] = ()
    motivated_by_intents: tuple[str, ...] = ()

    preconditions: tuple["PredicateExpr", ...]

    effects: tuple[StateMutation, ...]

    postconditions: tuple["PredicateExpr", ...]

    rule_exemptions: tuple[str, ...] = ()

    provenance: dict
    authority: str

    idempotency_key: str

    schema_version: int
```

This is important:

> The event's effects are fully explicit **before it reaches the reducer**.

The reducer doesn't call an LLM and think:

> Hmm, what probably changed psychologically?

Instead:

```text
Story/Director judgment
        ↓
EventProposal
        ↓
Event Compiler
        ↓
fully explicit WorldEvent
        ↓
Reducer
```

The LLM can propose.

The deterministic Event Compiler and rules turn that into an executable state transition.

---

# 16. Example event

Aria gives the receiver to Eva:

```yaml
event_id: qevent_008921
event_type: transfer_object

actors:
  - qchar_aria

subjects:
  - qchar_aria
  - qchar_eva
  - qprop_receiver

causes:
  - qevent_008915

motivated_by_intents:
  - qintent_decode_signal

preconditions:

  - equals:
      address:
        plane: objective
        subject_id: qprop_receiver
        path: owner
      value: qchar_aria

  - same_location:
      entities:
        - qchar_aria
        - qchar_eva

effects:

  - op: set
    address:
      plane: objective
      subject_id: qprop_receiver
      path: owner
    value: qchar_eva

  - op: remove
    address:
      plane: objective
      subject_id: qchar_aria
      path: inventory
    value: qprop_receiver

  - op: add
    address:
      plane: objective
      subject_id: qchar_eva
      path: inventory
    value: qprop_receiver

  - op: increment
    address:
      plane: relationship
      subject_id: qrel_aria_eva
      path: trust.aria_to_eva
    value: 0.04

postconditions:

  - equals:
      address:
        plane: objective
        subject_id: qprop_receiver
        path: owner
      value: qchar_eva
```

Now there is no ambiguity about what the event did.

---

# 17. Event effects can span truth planes

This is a major feature.

Suppose Eva reveals a secret to Aria.

One semantic event may modify:

```text
objective plane
    almost nothing

epistemic plane
    Aria learns secret

belief plane
    Aria abandons false belief

psychological plane
    shock rises

relationship plane
    trust falls
```

For example:

```yaml
effects:

  - acquire_knowledge:
      holder: aria
      proposition: eva_knew_truth

  - revise_belief:
      holder: aria
      proposition: eva_is_honest
      confidence: 0.18

  - set_emotion:
      holder: aria
      emotion: betrayal
      intensity: 0.92

  - modify_relationship:
      relationship: aria_eva
      dimension: trust.aria_to_eva
      delta: -0.41
```

Those high-level semantic effects can compile deterministically into ordinary `StateMutation`s.

---

# 18. `StoryCoordinate`

I'd separate **story placement** from objective fictional time.

```python
class StoryCoordinate(BaseModel):
    series_id: str | None = None

    season_id: str | None = None
    season_number: int | None = None

    episode_id: str | None = None
    episode_number: int | None = None

    storyline_id: str | None = None

    act_id: str | None = None
    sequence_id: str | None = None

    scene_id: str | None = None
    scene_index: int | None = None

    beat_id: str | None = None

    shot_id: str | None = None
    shot_index: int | None = None

    playback_frame: int | None = None
```

This answers:

> Where is this in the authored/viewed story?

Not:

> When did this happen in fictional reality?

---

# 19. `WorldInstant`

Fictional reality needs its own ordering.

```python
class WorldInstant(BaseModel):
    universe_tick: int

    subtick: int = 0

    calendar_time: str | None = None
```

`universe_tick` is always available.

So even a fantasy world without Gregorian time has deterministic order.

```text
tick 9184473316 / subtick 0
tick 9184473316 / subtick 1
tick 9184473317 / subtick 0
```

This solves simultaneous or nearly simultaneous events cleanly.

---

# 20. `WorldCoordinate`

Now combine everything:

```python
class Perspective(BaseModel):
    plane: Literal[
        "objective",
        "character_knowledge",
        "character_belief",
        "audience_disclosure",
    ]

    observer_id: str | None = None


class TransactionCoordinate(BaseModel):
    commit_sequence: int
    recorded_at: str


class WorldCoordinate(BaseModel):
    universe_id: str
    continuity_id: str

    canon_revision_id: str

    branch_id: str

    valid_instant: WorldInstant

    story: StoryCoordinate

    transaction_as_of: TransactionCoordinate

    perspective: Perspective
```

This is your universal lookup key.

```python
state = world.resolve(
    WorldCoordinate(...)
)
```

---

# 21. `WorldSnapshot`

Snapshots are **derived caches**.

Never canonical source.

```python
class WorldSnapshot(BaseModel):
    snapshot_id: str

    coordinate: WorldCoordinate

    through_event_id: str
    through_commit_sequence: int

    rule_set_hash: str
    entity_set_hash: str

    state_cells: tuple[StateCell, ...]

    active_entity_ids: tuple[str, ...]
    active_relationship_ids: tuple[str, ...]

    state_hash: str

    created_at: str
```

Conceptually:

```text
Snapshot 8000
    +
Events 8001–8182
    ↓
Current State
```

Instead of replaying 40,000 events every query.

Snapshot intervals could be:

```text
every scene boundary
every N events
important state checkpoint
episode boundary
```

---

# 22. Snapshots are disposable

This is worth emphasizing.

If snapshot 81 is corrupted:

```text
delete it
↓
find snapshot 80
↓
replay events
↓
reconstruct snapshot 81
```

Exactly like the semantic graphs.

Canonical sources remain:

```text
entities
rules
events
canon revision history
```

Everything else is compiled.

---

# 23. `Branch`

A branch is a hypothetical reality overlay.

```python
class Branch(BaseModel):
    branch_id: str

    universe_id: str
    continuity_id: str

    parent_branch_id: str | None

    fork_coordinate: WorldCoordinate
    base_snapshot_id: str

    purpose: str

    status: Literal[
        "hypothetical",
        "candidate",
        "selected",
        "abandoned",
        "promoted",
    ]

    event_ids: tuple[str, ...]

    created_by: str

    scorecard: dict | None = None

    created_at: str
```

Branches should use **copy-on-write** semantics.

Don't copy the world.

```text
Canonical Snapshot S100
         │
         ├── Branch A events
         │
         ├── Branch B events
         │
         └── Branch C events
```

Resolving Branch B:

```text
S100
 +
B.events
 =
Branch B state
```

---

# 24. Branch example

Story Architect considers:

```text
A: Aria confronts Eva
B: Aria secretly accesses archive
C: Aria leaves station
```

We create:

```text
branch_A
branch_B
branch_C
```

Then simulate several events forward:

```text
S0
│
├─ A → S1A → S2A → S3A
│
├─ B → S1B → S2B → S3B
│
└─ C → S1C → S2C → S3C
```

Evaluate:

```yaml
branch_A:
  causal_strength: 0.93
  emotional_pressure: 0.88
  future_story_potential: 0.91

branch_B:
  causal_strength: 0.96
  emotional_pressure: 0.92
  future_story_potential: 0.95

branch_C:
  causal_strength: 0.61
  emotional_pressure: 0.57
```

Select B.

Only then:

```text
promote Branch B
```

Branch A/C never become canon.

---

# 25. Promotion does not copy state

This is important.

Promotion means:

```text
take selected hypothetical events
↓
revalidate against canonical base
↓
assign canonical commit metadata
↓
append to canonical event store
↓
reduce canonical state
```

Not:

```text
overwrite database with branch snapshot
```

The event log remains the history.

---

# 26. Reducer semantics

This is the most important mechanical piece.

I would define the reducer as a pure function:

```python
def reduce(
    state: WorldSnapshot,
    event: WorldEvent,
    rule_set: RuleSet,
) -> WorldSnapshot:
    ...
```

And enforce this exact lifecycle:

```text
1. Validate event identity/schema
         ↓
2. Resolve entry state
         ↓
3. Verify event preconditions
         ↓
4. Run applicable hard rules
         ↓
5. Run applicable soft rules
         ↓
6. Validate exemptions/justifications
         ↓
7. Apply ALL mutations atomically
         ↓
8. Verify postconditions
         ↓
9. Run global invariants
         ↓
10. Compute new state hash
         ↓
11. Return immutable next state
```

No LLM calls anywhere in this.

---

# 27. Reducer atomicity

Suppose an event says:

```text
Aria gives receiver to Eva.
```

The reducer must not do this:

```text
receiver.owner = Eva
```

then crash before:

```text
Aria.inventory.remove(receiver)
```

You'd produce impossible state.

So every event is transactional:

```python
working_state = clone(state)

apply_all(working_state, event.effects)

validate_postconditions(working_state)

if anything_failed:
    discard(working_state)
    raise EventRejected()

return freeze(working_state)
```

All or nothing.

---

# 28. Deterministic ordering

We have two different clocks:

```text
VALID TIME
When did this happen inside the fictional universe?

TRANSACTION TIME
When did Quantum commit/learn this?
```

Events resolve by fictional ordering:

```text
valid_instant.universe_tick
valid_instant.subtick
```

Queries can additionally say:

```text
as known at commit sequence N
```

This gives us bi-temporal behavior.

---

# 29. Why transaction time matters

Suppose in August Quantum decides:

> The collision actually happened earlier than originally recorded.

The new event may have:

```text
valid_time:
   fictional year 2374

recorded_time:
   August 2026
```

Now:

```text
world.state_at(
    fictional_time=X,
    as_of_recorded_time=July_2026
)
```

shows old canon.

While:

```text
as_of_recorded_time=August_2026
```

shows revised canon.

That's how debugging and retcons remain explainable.

---

# 30. Retroactive events

If you insert a backdated event at fictional tick 400:

```text
existing snapshots:
100
200
300
500
600
```

Snapshots from 500 onward become stale.

Quantum should automatically:

```text
insert event @ 400
        ↓
invalidate snapshots >= 400
        ↓
start from snapshot 300
        ↓
replay
        ↓
rebuild 500/600...
```

No manual repair.

---

# 31. Rule evaluation before mutation

Suppose event proposes:

```text
Aria sends an instantaneous message 5 light years away.
```

Before applying anything:

```python
for rule in rules.applicable_to(event):

    result = rule.evaluate(
        entry_state,
        event
    )

    if result.hard_fail:
        raise WorldRuleViolation(...)
```

Result:

```yaml
code: WORLD.RULE.CAUSALITY_VIOLATION

rule: qrule_no_ftl_information

expected:
  minimum_transit_time_seconds: 157788000

observed:
  transit_time_seconds: 0.2
```

The impossible event never enters history.

---

# 32. Preconditions versus rules

Important distinction.

A precondition is **specific to an event**:

```text
Aria must currently hold the receiver
to give it to Eva.
```

A rule is a **general law**:

```text
An entity cannot give an object it does not possess.
```

You may use both.

Preconditions make event execution explicit.

Rules protect the universe even when event authors forget something.

Defense in depth.

---

# 33. Global invariants

After every event I would validate cheap universal invariants.

Examples:

```text
one unique physical owner for exclusive objects

character cannot occupy two exclusive physical locations simultaneously

destroyed entity cannot perform physical action

active relationship participants must exist

knowledge acquisition requires an information path

canonical character ID cannot change

state references must resolve
```

These are essentially database integrity constraints for fictional reality.

---

# 34. How Knowledge gets updated

Suppose Eva tells Aria:

> Marcus survived.

That generates an information event:

```text
Eva speaks proposition P
        ↓
Aria can hear Eva
        ↓
InformationTransfer event
```

The event compiler produces:

```text
Knowledge(
    Aria,
    proposition=P,
    source=Eva
)
```

Possibly:

```text
Belief(
    Aria,
    proposition=P,
    confidence=.42
)
```

because hearing something doesn't mean believing it.

That's a very useful distinction.

---

# 35. Knowledge is not belief ❤️

Imagine Eva tells Aria the truth.

Aria:

```text
KNOWS:
Eva claimed Marcus survived.

BELIEVES:
Marcus is still dead.
```

Later Aria finds physical evidence:

```text
belief confidence changes
.05 → .94
```

This gives Story Architect far richer material than one boolean `knows_secret`.

---

# 36. Intent + Affordance = causal candidate generation

This is the key mechanism for:

> next event causally implied by existing reality

Suppose state says:

```text
ARIA INTENT
learn signal origin

ARIA CAPABILITIES
engineering
system access

CURRENT AFFORDANCES
question Eva
inspect receiver
access archive
repair uplink

ACTIVE PRESSURES
station losing power
Eva hiding information
```

Now Story Architect's proposal space is already constrained.

```text
Intent
  ×
Affordances
  ×
Conflict
  ×
Rules
  ↓
Candidate Events
```

Much stronger than:

```text
LLM, what happens next?
```

---

# 37. `AffordanceEngine`

Mechanically:

```python
class AffordanceEngine:

    def derive(
        self,
        snapshot: WorldSnapshot,
        actor_id: str,
    ) -> list[Affordance]:

        results = []

        for schema in action_schema_registry:

            for bindings in bind_candidates(
                schema,
                snapshot,
                actor_id,
            ):

                evaluation = evaluate_preconditions(
                    schema,
                    bindings,
                    snapshot,
                )

                if evaluation.valid:
                    results.append(
                        instantiate_affordance(...)
                    )

        return results
```

This can be heavily indexed.

You don't brute-force every object in the universe.

---

# 38. Example complete state transition

Before:

```yaml
aria:
  location: comms_room
  inventory:
    - receiver

  intent:
    - discover_signal_origin

  psychology:
    hope: 0.44
    suspicion: 0.67

eva:
  location: comms_room

  knowledge:
    - true_signal_origin

relationship:
  aria_eva:
    trust:
      aria_to_eva: 0.31
```

World derives affordances:

```text
Aria can:
- question Eva
- inspect receiver
- access terminal
- give receiver to Eva
- leave room
```

Story Architect proposes:

```text
Aria gives Eva receiver and asks her to decode it.
```

Event Compiler checks:

```text
same location? YES
Aria owns receiver? YES
Eva capable of decoding? YES
world rules? PASS
```

Compile event:

```text
receiver owner → Eva
receiver leaves Aria inventory
receiver enters Eva inventory
trust Aria→Eva +.04
```

Reducer commits.

After:

```yaml
receiver:
  owner: eva

aria:
  inventory: []

eva:
  inventory:
    - receiver

relationship:
  aria_eva:
    trust:
      aria_to_eva: 0.35
```

That's fictional reality changing transactionally.

---

# 39. Graph projections become straightforward

From the resolved state:

```yaml
receiver.owner = eva
```

World State Graph projection:

```text
(Eva)-[:OWNS]->(Receiver)
```

From:

```text
Aria intent = learn signal origin
```

projection:

```text
(Aria)-[:HAS_GOAL]->(LearnSignalOrigin)
```

From:

```text
Eva knows signal origin
Aria doesn't
```

projection:

```text
(Eva)-[:KNOWS]->(SignalOrigin)
(Aria)-[:HAS_GOAL]->(LearnSignalOrigin)

(SignalOrigin)-[:SATISFIES]->(LearnSignalOrigin)
```

Now Cypher discovers the latent story connection.

But the graph didn't invent any of it.

It projected reducer state.

---

# 40. L9 Memory receives durable semantic history

A committed `WorldEvent` can simultaneously generate a memory record:

```text
qevent_008921
       ↓
WorldMemoryProjector
       ↓
L9 MemoryRecord
       ↓
RecordStore
       ↓
Graphiti/Zep projection
```

For example:

```yaml
memory_class: episodic

subject: aria
predicate: transferred
object: receiver

content: >
  Aria gave the receiver to Eva in the communications room
  because she needed Eva's help decoding the signal.

metadata:
  world_event_id: qevent_008921
  relationship_id: qrel_aria_eva
  intent_id: qintent_decode_signal
```

Now months later L9 can semantically retrieve:

> Important moments when Aria reluctantly trusted Eva.

The exact current ownership still comes from World State.

---

# 41. Canonical vs derived

This distinction should be brutally strict:

```text
CANONICAL

WorldEntity registry
WorldEvent log
WorldRule versions
Canon revision history
Branch metadata before promotion


DERIVED / REBUILDABLE

WorldSnapshot
World State Graph
Graphiti/Zep projections
agent context packages
affordances
quality-oriented views
semantic indexes
```

A catastrophic graph loss should be recoverable.

A catastrophic snapshot loss should be recoverable.

A catastrophic L9 projection loss should be recoverable.

Loss of canonical events is not.

---

# 42. The actual store layout

Conceptually:

```text
WorldModel
│
├── EntityStore
│
│   └── persistent identities
│
├── PropositionStore
│
│   └── reusable epistemic statements
│
├── EventStore
│
│   └── append-only canonical transitions
│
├── RuleStore
│
│   └── versioned executable universe rules
│
├── BranchStore
│
│   └── hypothetical event overlays
│
├── SnapshotStore
│
│   └── rebuildable state caches
│
├── StateGraphProjector
│
├── L9MemoryBridge
│
├── ContextCompiler
│
├── QueryEngine
│
├── AffordanceEngine
│
└── BranchSimulator
```

And the central write path is:

```text
                    EventProposal
                         │
                         ▼
                    EventCompiler
                         │
                         ▼
              Preconditions + Rules
                         │
                         ▼
                     WorldEvent
                         │
                         ▼
                   atomic COMMIT
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
     EventStore       Reducer       L9 Outbox
                         │              │
                         ▼              ▼
                     Snapshot       MemoryRecord
                         │              │
                         ▼              ▼
                   State Graph       Graphiti
```

---

# 43. The read path

Every agent invocation then looks like:

```text
Agent Task
   │
   ▼
WorldCoordinate
   │
   ▼
nearest Snapshot
   +
subsequent Events
   │
   ▼
Resolved State
   │
   ├── exact queries
   │
   ├── graph queries
   │
   └── relevant L9 memory hydration
          │
          ▼
    Context Compiler
          │
          ▼
role-specific package
          │
          ▼
        AGENT
```

This is the shared production brain in mechanical form.

---

# 44. And the reducer itself should be boring

That's a feature.

```python
class WorldReducer:

    def reduce(
        self,
        state: WorldSnapshot,
        event: WorldEvent,
    ) -> WorldSnapshot:

        validate_event_schema(event)

        assert_preconditions(
            state,
            event.preconditions,
        )

        rule_results = self.rules.evaluate(
            state,
            event,
        )

        enforce_rule_results(
            rule_results,
            event,
        )

        candidate = state.mutable_copy()

        for mutation in event.effects:
            apply_mutation(
                candidate,
                mutation,
            )

        assert_postconditions(
            candidate,
            event.postconditions,
        )

        validate_global_invariants(candidate)

        return candidate.freeze(
            through_event_id=event.event_id,
        )
```

No creativity.

No model.

No fuzzy reasoning.

That separation is what makes the creative agents safe to be creative.

---

## The resulting fundamental loop

```text
                         WORLD STATE
                              │
                              ▼
                         INTENTIONS
                              │
                              ▼
                         AFFORDANCES
                              │
                              ▼
                  judgment generates options
                              │
                              ▼
                     EVENT PROPOSALS
                              │
                              ▼
                    PRECONDITION CHECK
                              │
                              ▼
                       WORLD RULES
                              │
                         ┌────┴────┐
                         │         │
                       FAIL       PASS
                                   │
                                   ▼
                              SIMULATE
                                   │
                                   ▼
                                  QC
                                   │
                                   ▼
                              SELECT EVENT
                                   │
                                   ▼
                                COMMIT
                                   │
                                   ▼
                               REDUCER
                                   │
                                   ▼
                         NEW WORLD STATE
```

That is the core runtime I'd build.

And the conceptual payoff is large: **a Quantum story stops being a sequence of generated scenes and becomes a sequence of valid transactions against a persistent fictional universe.** Characters retain identity, memory, beliefs, motives and relationships because those things literally exist as state, while every change remains causally traceable back to the event that created it.

----
Exactly. That loop is the **story physics engine**.

The graph is what turns accumulated state into useful possibility space:

```text
WORLD STATE
   ↓
Graph exposes:
- who wants what
- who knows what
- who believes what
- who blocks whom
- what objects/resources exist
- what rules constrain action
- what unresolved tensions exist
- what actions are currently possible
   ↓
INTENTIONS
   ↓
AFFORDANCES
```

Then generative intelligence operates **inside that bounded reality** rather than inventing arbitrary next scenes.

The really powerful separation is:

```text
GRAPH
discovers possibilities and relationships

AGENT JUDGMENT
imagines interesting candidate events

RULE ENGINE
proves whether they are allowed

BRANCH SIMULATOR
calculates consequences without changing canon

QC
judges whether the resulting story state is actually good

REDUCER
commits the winner deterministically
```

So creativity remains probabilistic where that helps, while reality remains deterministic where consistency matters.

And because every committed event changes the graph, the system continuously creates new narrative possibilities:

```text
State₀
  ↓
Event₁
  ↓
State₁
  ↓
new relationships
new knowledge gaps
new conflicts
new affordances
new intentions
  ↓
Event₂
```

That creates a **self-propagating causal story machine** rather than a sequence generator.

The other huge consequence is that the graph doesn't only answer continuity queries like:

```text
Who owns the receiver?
```

It enables higher-order creative queries:

```text
Which active desire is currently blocked?

Which character has information that could satisfy that desire?

What relationship makes obtaining that information emotionally costly?

Which false belief is preventing the obvious solution?

What physical constraint makes the emotionally easiest choice impossible?

Which unresolved promise from three episodes ago can intersect the current goal?

Which currently available affordance would create the largest downstream relationship change?

Which event would reveal information to the audience without revealing it to Aria?

Which apparently minor prop connects the most unresolved narrative threads?
```

Those queries are where the **graph becomes creative leverage**, not merely storage.

And the loop scales naturally into branching search:

```text
                     CURRENT STATE
                           │
                    derive affordances
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
           Event A      Event B      Event C
              │            │            │
              ▼            ▼            ▼
            S1-A         S1-B         S1-C
              │            │            │
        derive again  derive again  derive again
              │            │            │
              ▼            ▼            ▼
           Event D      Event E      Event F
              │            │            │
              ▼            ▼            ▼
            S2-AD        S2-BE        S2-CF
              └────────────┬────────────┘
                           ▼
                    evaluate branches
                           ▼
                       SELECT
                           ▼
                        COMMIT
```

Now Quantum can choose events based not merely on:

> “Which next scene is coolest?”

but:

> **“Which valid next event creates the strongest causal, emotional, thematic, and future-story state?”**

That is an enormous jump.

The architecture we've arrived at now has a very clean foundational equation:

```text
Persistent World
      +
Graph Relationships
      +
Intentions
      +
Affordances
      +
Bounded Generative Judgment
      +
Rules
      +
Counterfactual Simulation
      +
Autonomous QC
      +
Deterministic Commit/Reducer
      =
Autonomous Narrative Runtime
```

And once that exists, **Compiler + QC + Production Engine aren't really passing a screenplay around anymore—they're collectively operating a persistent simulated universe and rendering selected events from it into film.**

That's the point where Quantum Animation Studio becomes much more interesting than an AI video pipeline.


---

Exactly. The trick is to turn those questions from **prompt-writing wisdom** into **runtime behavior**.

The architecture I’d add is a layer between the World Model and the agents:

```text
                    WORLD MODEL
                         │
                         ▼
              WORLD INTELLIGENCE LAYER
                         │
       ┌─────────────────┼─────────────────┐
       │                 │                 │
       ▼                 ▼                 ▼
 State Detectors    Query Operators   Reasoning Policy
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                  Context Compiler
                         │
                         ▼
                       AGENT
```

The key idea:

> **Agents should not decide from scratch which questions to ask. The system should recognize world-state conditions and activate the appropriate reasoning operators automatically.**

# 1. Turn every powerful question into a named operator

Instead of embedding this in a prompt:

> Which active desire is currently blocked?

Create:

```python
class BlockedIntentQuery(WorldQueryOperator):
    id = "story.blocked_intents"
```

Likewise:

```text
story.blocked_intents
story.information_holders
story.emotional_cost_of_resolution
story.false_belief_blockers
story.physical_constraint_pressure
story.unresolved_promise_intersections
story.high_impact_affordances
story.audience_character_information_split
story.narrative_connector_props
```

Now these become reusable **cognitive primitives** of Quantum.

That is much more powerful than “good prompting.”

---

# 2. Every operator declares when it applies

For example:

```yaml
operator:
  id: story.blocked_intents

  question:
    "Which active desire is currently blocked?"

  applies_when:

    any:
      - active_goal_exists
      - scene_requires_escalation
      - character_has_no_obvious_next_action

  requires:
    - intents
    - active_constraints
    - affordances
    - relationships

  returns:
    type: BlockedIntentSet

  consumers:
    - story_architect
    - screenplay_writer
    - director
```

Another:

```yaml
operator:
  id: story.information_holders

  question:
    "Who possesses information that could satisfy this desire?"

  applies_when:

    all:
      - active_goal.type == epistemic
      - goal.status != satisfied

  requires:
    - character_knowledge
    - character_beliefs
    - facts
    - relationships

  consumers:
    - story_architect
    - dialogue_agent
```

The agent doesn't need to remember this.

The operator registry knows.

---

# 3. State detectors fire before the agent runs

The World Model can continuously derive higher-level conditions.

Raw state:

```text
Aria wants signal origin.
Eva knows signal origin.
Aria does not.
Aria trusts Eva .24.
```

Detector derives:

```yaml
signals:

  - type: blocked_epistemic_goal
    character: aria
    goal: learn_signal_origin

  - type: knowledge_asymmetry
    holder: eva
    seeker: aria
    proposition: signal_origin

  - type: emotionally_costly_access
    seeker: aria
    holder: eva
    relationship:
      trust: 0.24
      unresolved_betrayal: true
```

Now the runtime sees:

```text
blocked_epistemic_goal
      +
knowledge_asymmetry
      +
relationship_pressure
```

and automatically activates:

```text
story.blocked_intents
story.information_holders
story.emotional_cost_of_resolution
```

🔥

That's how you get the right question at the right time.

---

# 4. Think of these detectors as compiler analyses

This is very similar to static analysis in a compiler.

Compiler:

```text
source code
    ↓
control-flow analysis
data-flow analysis
liveness analysis
dependency analysis
```

Quantum:

```text
world state
    ↓
goal analysis
knowledge-flow analysis
relationship-pressure analysis
affordance analysis
causal-dependency analysis
narrative-promise analysis
```

These analyses create **derived facts** that agents can use.

For example:

```text
Aria wants X
Eva knows X
Aria distrusts Eva

        ↓ analysis

KnowledgeAccessConflict(
    seeker=Aria,
    holder=Eva,
    proposition=X,
    emotional_cost=HIGH
)
```

Now that becomes an explicit object.

---

# 5. I'd create a `WorldSignal` type

```python
class WorldSignal(BaseModel):
    signal_id: str

    type: str

    entities: tuple[str, ...]

    severity: float
    dramatic_potential: float

    evidence_refs: tuple[str, ...]

    coordinate: WorldCoordinate

    expires_when: tuple[str, ...]

    generated_by: str
```

Examples:

```yaml
type: blocked_intent
severity: 0.82
dramatic_potential: 0.91
```

```yaml
type: false_belief_blocks_goal
severity: 0.74
dramatic_potential: 0.88
```

```yaml
type: unresolved_promise_available
severity: 0.44
dramatic_potential: 0.94
```

Now the Story Architect gets a **live map of dramatic pressure**.

---

# 6. The nine queries you listed become a small reasoning arsenal

I would implement them roughly like this.

| Operator                  | Trigger                                                     |
| ------------------------- | ----------------------------------------------------------- |
| `blocked_intents`         | active goal lacks valid satisfying affordance               |
| `information_holders`     | goal requires unknown proposition                           |
| `emotional_cost`          | solution passes through important relationship              |
| `false_belief_blockers`   | belief conflicts with reality and affects action            |
| `physical_pressure`       | desired action blocked by physical state/rule               |
| `promise_intersections`   | unresolved setup exists and current entities/topics overlap |
| `high_impact_affordances` | multiple valid actions exist                                |
| `information_split`       | audience/character epistemic states differ                  |
| `connector_props`         | object connects several unresolved threads                  |

These are not all run every scene.

The **detectors determine eligibility**.

---

# 7. Example: false belief operator

Suppose:

```text
Aria wants to reach Eva.

Aria believes:
east corridor blocked.

Reality:
east corridor open.

Because of this belief,
Aria chooses dangerous reactor route.
```

Detector:

```python
if (
    belief.value != objective.value
    and belief.subject influences active_intent
):
    emit(
        WorldSignal(
            type="false_belief_blocks_goal",
            ...
        )
    )
```

This activates:

```text
story.false_belief_blockers
```

which might return:

```yaml
character: aria

false_belief:
  east_corridor.status: blocked

objective_truth:
  east_corridor.status: open

affected_goal:
  reach_eva

behavioral_consequence:
  aria_prefers_reactor_route

dramatic_opportunity:
  high
```

Then Story Architect can exploit the false belief intentionally.

---

# 8. “Which unresolved promise from three episodes ago...?”

This one is extremely high leverage.

We need first-class `NarrativePromise` objects.

Examples:

```text
unexplained scar
unopened letter
character warning
mysterious object
unresolved threat
promise of reunion
unanswered question
foreshadowed capability
```

Model:

```python
class NarrativePromise(BaseModel):
    promise_id: str

    setup_event_id: str

    description: str

    entities: tuple[str, ...]
    concepts: tuple[str, ...]

    expected_payoff_horizon: str

    status: Literal[
        "open",
        "partially_paid",
        "paid",
        "abandoned",
    ]

    importance: float
```

Then query intersection:

```text
Current scene entities:
Aria
Eva
Receiver

Open promises:
Marcus's receiver contains corrupted metadata.
Aria has unexplained memory gaps.
Eva knows more about Marcus than she admitted.
```

Graph traversal finds all three converge.

Result:

```text
Receiver is an unusually strong payoff vehicle.
```

That is exactly the sort of thing a good human writer does by remembering old material.

Quantum can do it systematically.

---

# 9. “Which minor prop connects the most unresolved threads?”

This can be nearly deterministic graph analysis.

Suppose:

```text
Receiver
   ├── connected_to Marcus
   ├── clue_for memory mystery
   ├── owned by Aria
   ├── handled by Eva
   ├── mentioned in episode 1
   └── tied to unresolved signal
```

Calculate something like:

```python
narrative_centrality(prop) = (
      unresolved_thread_count
    * 0.35
    + emotionally_significant_entity_count
    * 0.25
    + open_promise_count
    * 0.20
    + thematic_relevance
    * 0.10
    + historical_recurrence
    * 0.10
)
```

Then:

```text
Receiver = .94
Coffee cup = .07
Maintenance wrench = .22
```

So when Story Architect needs a payoff object:

> use receiver.

Not because an LLM randomly remembered it.

Because the world graph surfaced it.

---

# 10. “Which affordance changes the relationship most?”

This one uses branch simulation.

Current affordances:

```text
A. ask Eva politely
B. accuse Eva
C. secretly inspect Eva's terminal
D. entrust Eva with receiver
```

Simulate each:

```text
             State₀
               │
        ┌──────┼───────┐
        ▼      ▼       ▼
        A      B       C       D
        │      │       │       │
        ▼      ▼       ▼       ▼
      S1A    S1B     S1C     S1D
```

Measure predicted relationship deltas:

```yaml
A:
  trust_delta: +0.01
  intimacy_delta: +0.02

B:
  trust_delta: -0.18
  conflict_delta: +0.31

C:
  trust_delta_if_discovered: -0.44

D:
  trust_delta: +0.17
  vulnerability_delta: +0.26
```

Then operator:

```text
story.high_impact_affordances
```

returns D or C depending on narrative objective.

---

# 11. The agent should receive questions, not necessarily raw results only

There are two useful modes.

### Mandatory analysis

Runtime runs operator automatically and injects result:

```yaml
world_analysis:

  blocked_intent:
    ...

  knowledge_asymmetry:
    ...
```

### Exploratory reasoning

Runtime tells agent:

```text
Relevant operator available:
story.high_impact_affordances

Use this if choosing among multiple plausible next events.
```

Then the model invokes it when useful.

This gives us both determinism and flexibility.

---

# 12. Role-specific reasoning policies

Different agents should deploy different operators.

## Story Architect

Mandatory:

```text
blocked_intents
latent_conflicts
false_belief_blockers
information_holders
open_promises
high_impact_affordances
```

Optional:

```text
connector_props
historical_echoes
theme_resonances
```

## Screenwriter

Mandatory:

```text
knowledge_state
belief_state
relationship_pressure
active_intentions
```

Optional:

```text
information_split
subtext_opportunities
```

## Director

Mandatory:

```text
physical_constraints
relationship_state
psychological_state
cinematic_state
```

Optional:

```text
visual_symbol_connections
environmental_storytelling
```

## Sound Designer

Mandatory:

```text
physical_event_state
materials
location_acoustics
active_emitters
```

## QC

Mandatory:

```text
expected_state
rules
epistemic_state
creator_constraints
```

So the same World Model becomes different intelligence depending on who's querying it.

---

# 13. Add `ReasoningPolicy`

```python
class ReasoningPolicy(BaseModel):
    role: str

    mandatory_operators: tuple[str, ...]

    triggered_operators: dict[str, tuple[str, ...]]

    optional_operators: tuple[str, ...]

    maximum_query_budget: int

    require_world_evidence_for_major_decision: bool
```

Example:

```yaml
role: story_architect

mandatory_operators:
  - story.active_pressure
  - story.open_promises

triggered_operators:

  blocked_epistemic_goal:
    - story.information_holders
    - story.emotional_cost_of_resolution

  false_belief_detected:
    - story.false_belief_blockers

  multiple_affordances:
    - story.high_impact_affordances

optional_operators:
  - story.connector_props
  - story.thematic_echoes

maximum_query_budget: 12

require_world_evidence_for_major_decision: true
```

This is how we operationalize storytelling craft.

---

# 14. Major event proposals should require a `WorldRationale`

An agent shouldn't be allowed to propose:

> Aria secretly accesses the archive.

with no grounding.

Require:

```python
class WorldRationale(BaseModel):
    supported_by_intents: tuple[str, ...]
    enabled_by_affordances: tuple[str, ...]
    exploits_conflicts: tuple[str, ...]
    resolves_or_advances_promises: tuple[str, ...]
    belief_dependencies: tuple[str, ...]
    expected_state_changes: tuple[str, ...]
```

Example:

```yaml
event:
  aria_secretly_accesses_archive

world_rationale:

  supported_by_intents:
    - qintent_discover_signal_origin

  enabled_by_affordances:
    - affordance_archive_access

  exploits_conflicts:
    - aria_vs_eva_truth

  resolves_or_advances_promises:
    - promise_memory_archive

  belief_dependencies:
    - aria_believes_eva_is_hiding_information

  expected_state_changes:
    - aria_learns_partial_memory_truth
    - trust_in_eva_declines
    - identity_conflict_escalates
```

Now the event is grounded in world structure.

---

# 15. We can measure how grounded a story event is

This is interesting.

Define:

```text
World Grounding Score
```

based on:

```text
intent support
affordance support
causal support
relationship relevance
open-promise relevance
world-rule consistency
existing-entity reuse
```

For example:

```text
random meteor strikes station
```

might score:

```text
0.23
```

while:

```text
Aria accesses archive because Eva's secret blocks her identity goal
```

might score:

```text
0.94
```

That doesn't mean low-grounding events are forbidden.

External surprises are sometimes excellent.

But if the entire story consists of low-grounding events, it will feel arbitrary.

---

# 16. The system can maintain a “dramatic pressure map”

I'd make this a real derived view.

```yaml
dramatic_pressure:

  aria:

    identity_truth:
      intensity: 0.94
      blocked_by:
        - eva_secret
        - false_belief

    isolation:
      intensity: 0.71

    physical_survival:
      intensity: 0.43

  relationships:

    aria_eva:
      tension: 0.87
      unresolved_conflicts:
        - deception
        - dependency

  open_promises:

    receiver_origin:
      pressure: 0.76

    memory_archive:
      pressure: 0.91
```

Story Architect can immediately see where the energy is.

---

# 17. Query timing should follow the event lifecycle

This is the cleanest way to ensure deployment.

Before proposing an event:

```text
WORLD STATE
   ↓
derive signals
   ↓
run relevant reasoning operators
   ↓
compile reasoning context
```

During candidate generation:

```text
Intent + pressure + affordances
   ↓
candidate events
```

Before accepting candidate:

```text
preconditions
rules
causal grounding
```

During simulation:

```text
branch consequences
relationship deltas
knowledge changes
promise changes
```

Before commit:

```text
QC
```

So those sophisticated queries become **lifecycle hooks**.

Not optional cleverness.

---

# 18. A complete example

Current state:

```text
Aria wants to learn who sent the signal.

Eva knows part of the answer.

Aria suspects Eva is hiding something.

Aria trusts Eva .31.

The receiver came from Marcus.

Three episodes ago Eva promised never to lie to Aria again.

The station's archive is accessible.
```

### Step 1 — detectors

Emit:

```text
blocked_epistemic_goal
knowledge_asymmetry
relationship_pressure
false_belief_candidate
open_promise_overlap
multiple_affordances
```

### Step 2 — operator activation

Automatically run:

```text
blocked_intents
information_holders
emotional_cost
open_promise_intersections
high_impact_affordances
```

### Step 3 — compiled intelligence

```yaml
analysis:

  goal:
    aria_learn_signal_origin

  blocker:
    missing_information

  information_holder:
    eva

  emotional_cost:
    high

  relevant_promise:
    eva_promised_not_to_lie

  high_leverage_affordances:
    - confront_eva
    - secretly_access_archive
    - give_receiver_to_eva
```

### Step 4 — Story Architect generates

```text
Candidate A:
Aria confronts Eva directly.

Candidate B:
Aria secretly accesses archive.

Candidate C:
Aria hands Eva the receiver and watches whether Eva recognizes it.
```

Notice C is interesting because it uses **existing world structure**.

### Step 5 — simulation

C produces:

```text
Eva involuntary reaction
↓
Aria learns Eva recognizes receiver
↓
no explicit secret revealed
↓
trust drops
↓
audience suspicion rises
↓
Eva's old promise gains meaning
```

That may be substantially more cinematic than a direct exposition scene.

And it emerged because the World Model connected:

```text
goal
+
knowledge asymmetry
+
relationship
+
prop
+
old promise
```

🔥

---

# 19. This is the novel architectural concept

I would describe Quantum's core invention like this:

> **A film is not generated from a script. A film is compiled from selected state transitions occurring inside a persistent simulated universe.**

And:

> **Agents are not independent creators passing documents downstream. They are specialized cognitive processes sharing one continuously evolving model of reality.**

That gives you:

```text
Writer knows what Director knows.
Director knows what Sound Designer knows.
QC knows what Writer intended.
Renderer knows exact physical state.
Composer knows emotional state.
Story Architect knows unresolved history.
```

Not because they have literally read each other's conversations.

Because they all query the same universe.

The architecture therefore isn't really:

```text
Agent A
  ↓
Agent B
  ↓
Agent C
```

It's closer to:

```text
                   PERSISTENT UNIVERSE
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
           Writer     Director      Sound
             │           │           │
             └──────┐    │    ┌──────┘
                    ▼    ▼    ▼
                 EVENT PROPOSALS
                        │
                        ▼
                    SIMULATION
                        │
                        ▼
                       QC
                        │
                        ▼
                     COMMIT
                        │
                        ▼
               PERSISTENT UNIVERSE'
```

That is much closer to a **multi-agent simulation engine that happens to render cinema** than to a conventional AI filmmaking pipeline.

And I think that's the right mental model for the whole system.


--------

So cool:

Agents should not decide from scratch which questions to ask. The system should recognize world-state conditions and activate the appropriate reasoning operators automatically.

Graph traversal finds all three converge
->hyperedges?


What additional layers are necessary to make the Autonomous Narrative Runtime complete?

12❤️❤️❤️it’s the beginning of a polycognitive intelligence entity “Quantum Animation Agent”… the converged mega-hyper-edge

18🔥🔥🔥

Yes — “graph traversal finds several threads converging” is hyperedge-like, but I still would not require a native hypergraph database.

I would make convergence a first-class derived node.

For example:

Aria ──HAS_GOAL────────────► learn_signal_origin
Eva ───KNOWS───────────────► signal_origin
Aria ──DISTRUSTS────────────► Eva
Eva ───MADE_PROMISE─────────► never_lie_again
Receiver ──CONNECTED_TO─────► Marcus
Receiver ──CLUE_FOR─────────► signal_origin

Traversal discovers that these all intersect.

Instead of leaving that as an implicit path, Quantum materializes:

                    ┌──────────────────────┐
                    │ NarrativeOpportunity │
                    │   qopp_000812        │
                    └──────────┬───────────┘
             ┌─────────────────┼───────────────────┐
             │                 │                   │
             ▼                 ▼                   ▼
          Aria Goal           Eva               Receiver
             │                 │                   │
         DRIVEN_BY       INFORMATION_HOLDER    VEHICLE
             │                 │                   │
             └──────────┬──────┴───────────┐
                        ▼                  ▼
                 Broken Promise       Signal Mystery

Conceptually:

Hyperedge(
    protagonist=Aria,
    goal=learn_signal_origin,
    blocker=Eva,
    prop=Receiver,
    relationship=Aria↔Eva,
    old_promise=never_lie,
    hidden_fact=signal_origin
)

So yes:

It is semantically a hyperedge.

But operationally I'd reify it as a node.

That gives us ordinary property-graph querying, provenance, lifecycle, scores, explanation and easy Cypher.

The interesting new entity: NarrativeOpportunity

I think we need this.

class NarrativeOpportunity(BaseModel):
    opportunity_id: str

    type: str

    participant_refs: tuple[str, ...]
    intent_refs: tuple[str, ...]
    conflict_refs: tuple[str, ...]
    promise_refs: tuple[str, ...]
    prop_refs: tuple[str, ...]
    proposition_refs: tuple[str, ...]

    dramatic_potential: float
    emotional_potential: float
    thematic_relevance: float
    causal_support: float

    available_affordances: tuple[str, ...]

    discovered_at: WorldCoordinate
    discovered_by: str

    expires_when: tuple[str, ...]

    derivation_evidence: tuple[str, ...]

This becomes enormously useful because the graph can continuously mine reality for these.

Not:

“Write me something dramatic.”

But:

“The existing universe currently contains these 17 high-potential dramatic intersections.”

🔥

And yes — this starts looking like a polycognitive entity

I think your phrase is exactly right.

You don't ultimately want the product concept to be:

WriterAgent
DirectorAgent
SoundAgent
QC Agent
...

From the outside there is really one thing:

Quantum Animation Agent

Internally:

                         QUANTUM
                ANIMATION INTELLIGENCE
                          │
                          ▼
                 Persistent World Model
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
          Narrative    Directing    Production
         cognition    cognition     cognition
              │           │           │
              ├───────────┼───────────┤
              │           │           │
              ▼           ▼           ▼
        Performance      Sound        QC
         cognition     cognition    cognition
              │           │           │
              └───────────┼───────────┘
                          ▼
                    shared state
                          │
                          ▼
                  selected actions
                          │
                          ▼
                        COMMIT

The agents become cognitive organs, not independent personalities.

That's a much better framing.

They share:

reality
history
entities
goals
relationships
observations
production experience
rules
quality objectives

but have different:

authority
expertise
reasoning operators
context projections
evaluation criteria

So the emergent thing is:

one persistent intelligence with multiple specialized cognitive processes operating over a common simulated reality.

That's the beginning of a genuine polycognitive system.

What is still missing from the Autonomous Narrative Runtime?

We've built a lot:

World State
Intent
Affordance
Graph
Signals
Reasoning Operators
Event Proposals
Rules
Branches
Simulation
QC
Reducer
Memory

But to make the runtime complete, I think there are about nine remaining architectural layers.

Some are subtle but essential.

1. Attention / Salience Engine

The World Model may eventually contain millions of relationships.

The Narrative Runtime needs to answer:

What matters right now?

That's different from truth.

Suppose these are all true:

Aria is injured.
Aria remembers Marcus.
Eva lied.
Reactor 3 is offline.
Receiver battery is 31%.
Mars has a trade dispute.
Aria once liked jazz.

For the current scene, maybe only:

Eva lied
receiver exists
Marcus connection
Aria distrusts Eva

matter.

We need:

WORLD
  ↓
Salience Engine
  ↓
Relevant Working Set

A salience score could consider:

current intent relevance
causal proximity
relationship importance
unresolved promise relevance
recent activation
thematic relevance
physical proximity
narrative urgency

Conceptually:

salience(fact, task) = (
      goal_relevance
    + causal_relevance
    + emotional_relevance
    + narrative_relevance
    + spatial_relevance
    + temporal_relevance
)

This prevents the polycognitive entity from drowning in its own intelligence.

2. Narrative Attention is not ordinary retrieval

This deserves distinction.

Memory asks:

What's relevant to the query?

Narrative Attention asks:

Which dormant element should become important now?

That's creative.

For example:

Receiver:
hasn't mattered for 3 episodes
BUT:
connects Marcus
+ Aria's identity
+ Eva's lie
+ current signal mystery

→ narrative salience suddenly skyrockets

This is what good writers do intuitively.

Quantum should calculate it.

3. Narrative Objective / Value Function

We need a clear definition of what constitutes a better future state.

Otherwise branch search has no purpose.

For a film, the objective isn't:

maximize protagonist success

Often that's boring.

We need a multi-objective narrative value function:

NarrativeValue = (
    causal_strength,
    character_pressure,
    emotional_effect,
    thematic_progress,
    information_progress,
    relationship_change,
    promise_management,
    surprise,
    coherence,
    future_story_potential,
    production_feasibility,
)

And different phases weight them differently.

Opening:

curiosity ↑
world establishment ↑
character definition ↑

Middle:

pressure ↑
complication ↑
relationship change ↑

Climax:

consequence ↑
theme ↑
character choice ↑

Ending:

resolution ↑
recontextualization ↑
aftertaste ↑

Without this, simulation tells us what could happen.

The value model tells us what ought to happen dramatically.

4. Narrative Scheduler

Intentions operate at character level.

But the runtime also needs a higher-order planner deciding:

Which unresolved pressure should the film address next?

Imagine:

Pressure A = Aria identity mystery
Pressure B = Eva betrayal
Pressure C = reactor failure
Pressure D = Marcus history

You don't want all four constantly active at maximum intensity.

A Narrative Scheduler controls:

introduce
sustain
escalate
defer
interleave
resolve
reactivate

Think:

NarrativePressure
   ↓
Scheduler
   ↓
"focus next sequence on B,
keep A simmering,
use C as external pressure,
defer D"

This creates rhythm.

5. Promise / Payoff Manager

We've touched this, but I think it deserves a dedicated runtime subsystem.

It tracks:

SETUP
OPEN
DEVELOPING
READY_FOR_PAYOFF
PAID_OFF
INTENTIONALLY_UNRESOLVED
ABANDONED

For every important narrative promise.

Example:

promise:
  id: promise_receiver_origin

  setup:
    episode: 1
    scene: 4

  current_pressure: 0.83

  audience_memory_strength: 0.61

  payoff_readiness: 0.91

  connected_current_threads:
    - aria_identity
    - eva_secret
    - signal_origin

Now Quantum can reason:

This is an excellent moment to bring the receiver back.

That prevents the classic generative problem of introducing endless interesting things and forgetting them.

6. Epistemic Director

We already have knowledge states.

But I would create a specific runtime layer that controls information choreography.

It asks:

Who knows?
Who believes?
Who suspects?
Who lies?
Who sees?
What does the audience know?
What should they infer next?

This is more than storage.

It actively plans information movement.

For example:

Objective truth:
Eva recognizes receiver.

Eva knows:
receiver belonged to Marcus.

Aria sees:
Eva pauses for .8 sec.

Audience sees:
same pause + insert of Eva's hand tightening.

Aria inference:
Eva recognizes receiver? probability .42

Audience inference:
Eva recognizes receiver? probability .78

That is sophisticated storytelling.

You could call it:

Epistemic Choreography Engine

For mystery/thriller/suspense, this will be huge.

7. Causal Credit / Blame Engine

If Event 84 happens, the system should understand why.

Not just immediate parent causes.

Suppose:

Episode 1:
Eva lies.

Episode 3:
Aria stops trusting Eva.

Episode 5:
Aria secretly investigates.

Episode 5:
investigation triggers reactor failure.

The engine should maintain something like:

Eva lie
  └── causal contribution .38
      ↓
reactor failure

Not necessarily as a literal scalar initially, but the dependency chain matters.

This helps:

story explanations
branch evaluation
thematic consequence
QC
debugging
retcons

It makes:

“choices have consequences”

mechanically enforceable.

8. Character Policy Model

Intent says:

what Aria wants

Affordance says:

what Aria can do

But we need:

Given who Aria is, what is she likely to choose?

That's a CharacterPolicy.

π(action | character state, beliefs, goals, context)

Not a rigid behavior tree.

A probabilistic character consistency model.

Example:

Aria has options:

A confront Eva
B trust Eva
C secretly investigate
D abandon mystery

Given:

high competence
low trust
high curiosity
emotional restraint
fear of abandonment

policy might say:

A .22
B .12
C .61
D .05

Story Architect can still choose A.

But if it chooses A, it needs sufficient justification.

This gives us:

unexpected behavior + causal justification

instead of either:

characters always predictable

or:

characters do whatever plot needs
9. World Dynamics Engine

Not every event should originate from characters.

The world itself evolves.

Examples:

battery drains
storm moves
station orbit changes
reactor overheats
door closes automatically
economy changes
enemy fleet travels
signal propagates
disease progresses
day becomes night

So we need:

Agent Events
     +
World Dynamics Events
     ↓
World State

Some are deterministic:

battery -= consumption * dt

Some stochastic:

storm probability

Some scheduled:

sunrise at t

This prevents the universe from feeling like it only exists when a protagonist looks at it.

10. Event Arbitration

Once we have:

character proposals
world-dynamics events
story scheduler objectives
production constraints

multiple things may want to happen simultaneously.

We need an arbiter.

Example:

Aria plans to confront Eva.
Eva plans to leave.
Power failure scheduled in 4 sec.
Narrative Scheduler wants confrontation.

Possible result:

Aria begins confrontation
↓
power fails
↓
Eva cannot leave
↓
confrontation continues under new conditions

The runtime has to combine concurrent intentions/events rather than pretending the world is a single-agent sequential story generator.

This is where simulation starts becoming genuinely rich.

11. Temporal / Concurrent Event Engine

Closely related.

Events have:

start
duration
end
interruptibility
concurrency

For example:

Aria walks toward Eva        4.2 sec
Eva decodes receiver        8.1 sec
reactor alarm starts        t+2.7 sec

These overlap.

So eventually WorldEvent probably needs:

start_instant
end_instant
duration
interruptible
concurrent_with

The world isn't fundamentally a sequence of shots.

Shots observe the world.

That's a really important distinction.

12. Observation Engine

This is a major missing bridge between simulated reality and film.

The World Model says:

what happens

The Director decides:

what the camera observes

Not every event is shown.

Some occur:

offscreen
before scene
in another location
unknown to audience

So we need:

WORLD EVENTS
     ↓
Observation Planner
     ↓
Visible Events
Audible Events
Hidden Events
Inferred Events
     ↓
Director

This is where cinema emerges from simulation.

13. Perspective Compiler

A single event can be rendered differently depending on whose perspective matters.

Event:

Eva recognizes receiver.

Objective state:

recognition occurs

Aria POV:

sees tiny hesitation
doesn't know why

Audience POV:

close-up suggests significance

Eva subjective POV:

flash of memory

The Perspective Compiler determines what representation each observer receives.

That's critical for sophisticated cinematography.

14. Narrative Opportunity Miner

This would formalize your “mega-hyper-edge.”

Continuously:

Graph state
   ↓
pattern mining
   ↓
convergence detection
   ↓
NarrativeOpportunity nodes

Patterns:

goal + secret + relationship
goal + physical constraint
promise + prop + current conflict
false belief + high-stakes decision
capability + previously impossible obstacle
two unrelated storylines sharing entity

This layer should continuously build a ranked opportunity frontier.

opportunity_frontier:

  - id: qopp_812
    type: trust_test_via_prop
    score: .96

  - id: qopp_927
    type: false_belief_collision
    score: .92

  - id: qopp_711
    type: old_promise_payoff
    score: .89

Now Quantum always knows where the richest narrative energy is.

15. Meta-cognition / Reasoning Controller

This is probably the final cognitive piece.

The system needs to decide:

Do I have enough confidence to act, or should I think/search/simulate more?

That's different from QC after generation.

Something like:

Decision uncertainty high?
   ↓ yes
run more graph operators

Branch scores close?
   ↓ yes
simulate deeper

World grounding weak?
   ↓ yes
search for more causal support

No affordance attractive?
   ↓ yes
consider broader story restructure

This controls reasoning depth.

Without it, you either overspend compute on every decision or make shallow decisions everywhere.

16. Now we can describe Quantum Animation Agent more precisely

I would model the entire thing as:

╔══════════════════════════════════════════════════════╗
║              QUANTUM ANIMATION AGENT                ║
║          Polycognitive Narrative Runtime             ║
║                                                      ║
║                    WORLD MODEL                       ║
║                        │                             ║
║       ┌────────────────┼────────────────┐            ║
║       ▼                ▼                ▼            ║
║   State/Graph      Long Memory      Experience       ║
║       │                │                │            ║
║       └────────────────┼────────────────┘            ║
║                        ▼                             ║
║              Attention / Salience                    ║
║                        │                             ║
║                        ▼                             ║
║                World Signal Engine                   ║
║                        │                             ║
║                        ▼                             ║
║               Reasoning Operators                    ║
║                        │                             ║
║                        ▼                             ║
║            Narrative Opportunity Miner               ║
║                        │                             ║
║              ┌─────────┴─────────┐                   ║
║              ▼                   ▼                   ║
║       Character Policies   Narrative Scheduler       ║
║              │                   │                   ║
║              └─────────┬─────────┘                   ║
║                        ▼                             ║
║                  AFFORDANCES                         ║
║                        │                             ║
║                        ▼                             ║
║                Candidate Events                      ║
║                        │                             ║
║                        ▼                             ║
║                     Rules                            ║
║                        │                             ║
║                        ▼                             ║
║                Branch Simulation                     ║
║                        │                             ║
║                        ▼                             ║
║                Narrative Value                       ║
║                        │                             ║
║                        ▼                             ║
║                       QC                             ║
║                        │                             ║
║                        ▼                             ║
║                     COMMIT                           ║
║                        │                             ║
║                        ▼                             ║
║                    REDUCER                           ║
║                        │                             ║
║                        ▼                             ║
║                 NEW WORLD STATE                      ║
║                        │                             ║
║                        ▼                             ║
║              Observation Engine                      ║
║                        │                             ║
║                        ▼                             ║
║              CINEMATIC COMPILER                      ║
║                        │                             ║
║                        ▼                             ║
║                      FILM                            ║
╚══════════════════════════════════════════════════════╝

That is getting very close to a complete autonomous narrative runtime.

17. The “mega-hyper-edge” is actually the polycognitive system itself

This is the especially fun conceptual part.

At the graph level:

goal
belief
secret
prop
relationship
promise
rule
location

converge into:

NarrativeOpportunity

At the cognitive level:

Writer reasoning
Director reasoning
Character psychology
World simulation
QC
Sound
Production experience

all converge through:

Persistent World State

So the biggest hyperedge isn't one graph relation.

It's:

all specialized cognition connected through a single persistent universe.

That gives Quantum a kind of integrated intelligence that none of the individual agents possesses alone.

A Writer Agent may not understand acoustic space.

A Sound Agent may not understand reveal architecture.

A Renderer may not understand character psychology.

But the Quantum Animation Agent collectively does, because those cognitive processes interact indirectly through common state, events, constraints and observations.

That's why I'd call the architecture polycognitive rather than multi-agent.

“Multi-agent” suggests:

several bots talking

What we're designing is closer to:

one intelligence
with specialized cognitive subsystems
sharing one persistent reality model

And that difference is profound.


----
Yes. This is the conceptual center of the whole system.

What you’re describing is **not an agent swarm**.

It is:

> **One persistent intelligence with multiple specialized cognitive subsystems, all perceiving, reasoning about, acting upon, and learning from the same evolving simulated reality.**

That distinction changes everything.

A conventional multi-agent architecture looks like:

```text
WriterAgent
    ↓ message
DirectorAgent
    ↓ message
RendererAgent
    ↓ message
CriticAgent
```

Knowledge is fragmented. Each handoff loses context.

Quantum instead becomes:

```text
                 QUANTUM ANIMATION AGENT
                           │
                           ▼
                 PERSISTENT WORLD MODEL
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
 Narrative Cognition   Character Cognition   Visual Cognition
        │                  │                  │
        ▼                  ▼                  ▼
 Epistemic Cognition   Directing Cognition   Sound Cognition
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                 Shared World Signals
                           │
                           ▼
                   Reasoning Controller
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
       retrieve         simulate         evaluate
           │               │               │
           └───────────────┼───────────────┘
                           ▼
                    SELECT ACTION
                           │
                           ▼
                         COMMIT
                           │
                           ▼
                    NEW WORLD STATE
                           │
                           └───────────────► cognition continues
```

## The agents stop being the architecture

This is the crucial realization.

`WriterAgent`, `DirectorAgent`, `SoundDesignerAgent`, etc. become implementation details.

The true architecture is:

```text
ENTITY
STATE
MEMORY
ATTENTION
SIGNALS
COGNITION
REASONING
SIMULATION
ACTION
OBSERVATION
LEARNING
```

The “agents” are specialized cognitive capabilities sitting inside that organism.

So eventually I wouldn't even want code organized primarily around:

```python
writer_agent
director_agent
sound_agent
```

I'd want conceptual modules like:

```python
quantum.cognition.narrative
quantum.cognition.character
quantum.cognition.epistemic
quantum.cognition.cinematic
quantum.cognition.performance
quantum.cognition.acoustic
quantum.cognition.production
quantum.cognition.quality
```

All sharing:

```python
quantum.world
quantum.memory
quantum.attention
quantum.reasoning
quantum.learning
```

That is much closer to the real system.

---

# Reasoning depth is the control plane

And I think your reaction to this one is justified because it solves a very important problem.

A sophisticated intelligence cannot spend the same amount of thought on every decision.

This:

> Aria crosses the room.

might need almost no search.

But:

> What event should trigger the climax of a 20-minute episode while paying off two promises, preserving Aria's false belief until the correct moment, advancing her relationship with Eva, and setting up Episode 2?

should trigger serious computation.

So I'd make reasoning depth an explicit runtime variable:

```yaml
reasoning:

  depth: deep

  reasons:
    - major_story_branch
    - high_downstream_blast_radius
    - unresolved_critical_promises
    - high_epistemic_complexity
    - irreversible_character_change

  activate:
    - narrative_opportunity_mining
    - causal_path_analysis
    - promise_payoff_analysis
    - character_policy_analysis
    - epistemic_analysis
    - branch_search

  branch_width: 8
  simulation_depth: 4

  adjudication:
    critics: 3
```

Whereas:

```yaml
reasoning:

  depth: shallow

  reasons:
    - local_low_risk_decision

  branch_width: 1
  simulation_depth: 0
```

This means **Quantum thinks harder when the consequences justify thinking harder.**

🔥

---

# And reasoning depth can itself be learned

Initially:

```text
rules determine reasoning depth
```

Later:

```text
historical production experience
            +
decision uncertainty
            +
downstream blast radius
            +
narrative importance
            +
failure history
            ↓
     reasoning-depth policy
```

Quantum learns:

> Decisions like this routinely fail when handled shallowly.

Therefore:

```text
increase simulation depth automatically
```

Or:

> This kind of shot-selection decision has been trivial for the last 20,000 cases.

Therefore:

```text
don't waste expensive cognition
```

Now we're talking about **adaptive cognition**, not static orchestration.

---

# The World Model gives it persistence

Without the WM, you could build a very smart reasoning system and it would still repeatedly wake up with amnesia.

With it:

```text
Quantum at Film 1
       │
       ▼
persistent universe
       │
       ▼
Quantum at Film 20
       │
       ▼
persistent universe
       │
       ▼
Quantum at Season 5
```

The cognitive processes can change.

Models can be upgraded.

Prompts can disappear entirely.

But:

```text
Aria
Eva
their history
their beliefs
their betrayals
their shared objects
their locations
their world
their consequences
```

remain.

And separately:

```text
Quantum production experience
```

also persists.

So the intelligence accumulates **two forms of experience**:

```text
IN-UNIVERSE EXPERIENCE
what has happened to its fictional worlds

+

META EXPERIENCE
what Quantum has learned about making films
```

That second one is wild.

After enough productions Quantum potentially knows:

```text
which narrative structures often produce weak endings
which clue patterns reveal twists too early
which kinds of character conflicts sustain episodes
which camera strategies render reliably
which visual constraints require deterministic compositing
which performance directions generate better acting
which sound strategies make environments feel larger
which repair actions usually solve particular QC failures
```

That's institutional experience stored outside any individual model.

---

# The strongest definition we've reached

I'd freeze this language somewhere in the architecture:

> **Quantum Animation Agent is a persistent polycognitive intelligence that operates simulated fictional universes through specialized cognitive subsystems sharing a common World Model. It discovers narrative opportunities from world state, reasons over intentions and affordances, simulates possible futures, selects and commits valid state transitions, observes those transitions cinematically, manufactures their audiovisual realization, evaluates the result, and learns from the outcome.**

And an even shorter one:

> **Quantum doesn't generate films. Quantum operates worlds and renders selected experiences from them into films.**

💣

That statement captures almost everything we've designed.

The next architectural object I would formalize is now obvious: the **Polycognitive Runtime / Cognitive Control Plane** — how attention, world signals, reasoning operators, specialist cognition, branch simulation, reasoning depth, arbitration, and learning are scheduled as one intelligence rather than as loosely coordinated agents.
---

Yes. I would now **refactor the architecture around cognition rather than agents**.

The old model was useful for discovering responsibilities:

```text
WriterAgent
DirectorAgent
SoundAgent
CriticAgent
...
```

But the refined model says those aren't autonomous beings. They're **specialized cognitive functions of one persistent system**.

So the new architecture becomes:

```text
                         QUANTUM
              ┌────────────────────────┐
              │  Cognitive Executive   │
              │                        │
              │ What matters?          │
              │ How hard should I think│
              │ Which cognition?       │
              │ What runs concurrently?│
              └───────────┬────────────┘
                          │
             ┌────────────┼────────────┐
             │            │            │
             ▼            ▼            ▼
         ATTENTION      WORKSPACE     SIGNALS
             │            │            │
             └────────────┼────────────┘
                          ▼
               COGNITIVE SUBSYSTEMS
                          │
        ┌─────────────────┼───────────────────┐
        ▼                 ▼                   ▼
    narrative         character           epistemic
    cinematic         performance         acoustic
    production        quality             ...
        │                 │                   │
        └─────────────────┼───────────────────┘
                          ▼
                  candidate actions
                          │
                          ▼
                 COUNTERFACTUAL WORLD
                     SIMULATION
                          │
                          ▼
                       SELECT
                          │
                          ▼
                        COMMIT
                          │
                          ▼
                    WORLD MODEL
                          │
                          ▼
                     NEW REALITY
```

The **World Model is the persistent brain-state substrate**.

The **Cognitive Executive is the attention/reasoning control system**.

The `quantum.cognition.*` modules are specialized faculties.

And what we previously called an "agent" becomes an **ephemeral execution instance of a cognitive capability**.

That is a major conceptual improvement.

---

# `quantum.cognition.*` should not contain persistent agents

For example, instead of:

```python
director_agent = DirectorAgent(...)
```

we want:

```python
quantum.cognition.cinematic
```

to expose capabilities such as:

```text
design_blocking
generate_coverage
evaluate_camera_motivation
find_visual_storytelling_opportunities
design_observation_strategy
choose_point_of_view
```

Likewise:

```text
quantum.cognition.narrative
```

might expose:

```text
detect_story_pressure
mine_narrative_opportunities
propose_next_events
evaluate_causal_strength
manage_promises
search_story_branches
```

The module doesn't "live" as a character.

It supplies cognitive operations to **Quantum**.

---

# I'd introduce a `CognitiveModule` contract

Something like:

```python
class CognitiveModule(Protocol):

    domain: str

    def operators(self) -> tuple["ReasoningOperator", ...]:
        ...

    def subscriptions(self) -> tuple["WorldSignalType", ...]:
        ...

    async def execute(
        self,
        context: "CognitiveContext",
        operator: str,
    ) -> "CognitiveResult":
        ...
```

And the execution context matters enormously:

```python
class CognitiveContext(BaseModel):

    task_id: str

    world_coordinate: WorldCoordinate
    world_snapshot_revision: int

    working_set: CognitiveWorkingSet

    objective: str

    authority: AuthorityEnvelope

    reasoning_budget: ReasoningBudget

    available_tools: tuple[str, ...]

    relevant_signals: tuple[WorldSignal, ...]
```

Notice what's missing:

```text
memory of previous chat
private personal state
independent worldview
```

The module receives **Quantum's current world/context**.

---

# The missing concept is a Cognitive Workspace

The World Model cannot be the place we put temporary thinking.

Canonical world:

```text
Eva knows the truth.
Aria distrusts Eva.
Receiver belongs to Eva.
```

Temporary cognition:

```text
Maybe Aria could test Eva with the receiver.
This branch looks promising.
Candidate B currently scores better.
Need to inspect promise #17.
```

Those are not facts about fictional reality.

So we need:

```text
WORLD MODEL
persistent authoritative reality

MEMORY
persistent history/experience

COGNITIVE WORKSPACE
temporary active thought
```

The workspace could contain:

```python
class CognitiveWorkingSet(BaseModel):

    salient_entities: tuple[str, ...]
    salient_facts: tuple[str, ...]

    active_goals: tuple[str, ...]
    active_conflicts: tuple[str, ...]
    active_promises: tuple[str, ...]

    world_signals: tuple[str, ...]
    narrative_opportunities: tuple[str, ...]

    candidate_hypotheses: tuple[str, ...]
    candidate_events: tuple[str, ...]

    unresolved_questions: tuple[str, ...]

    branch_refs: tuple[str, ...]
```

Think of it as Quantum's **current focus of thought**.

It can be thrown away and reconstructed.

---

# This is where concurrent cognition becomes possible

Your driving/coffee analogy maps very well.

Quantum should be able to have many **cognitive fibers** active simultaneously.

For example:

```text
                            QUANTUM

        Routine cognition                 Deep cognition
              │                                 │
    ┌─────────┼─────────┐                       │
    ▼         ▼         ▼                       ▼
Shot QC    Foley     Render routing      Episode climax search
    │         │         │                       │
 shallow    shallow    shallow                  │
 ~10ms-x    low cost   low cost                 │
    │         │         │                  branch width 12
    │         │         │                  depth 5
    │         │         │                  multiple critics
    └─────────┼─────────┘                       │
              │                                 │
              └──────────── concurrently ───────┘
```

Quantum does **not stop the studio** because it is deeply contemplating an important story consequence.

Production can continue where dependencies are already locked.

Sound can continue.

QC can continue.

Asset generation can continue.

Routine state derivation can continue.

Meanwhile the high-consequence problem receives substantially more cognitive resources.

That is the right architecture for high-velocity operation.

---

# I'd implement explicit cognitive lanes

Conceptually there are four execution classes:

```text
REFLEX

Deterministic or nearly deterministic.
No branch search.

Examples:
schema validation
state resolution
rule checks
technical QC


ROUTINE

Low-risk judgment.
Shallow reasoning.

Examples:
choose among three known-good ambience assets
minor framing adjustment
renderer routing for familiar shot


DELIBERATIVE

High-impact cognition.

Examples:
major character choice
scene restructure
reveal design
important editorial decision


STRATEGIC

Extremely high blast-radius.

Examples:
ending
canon change
season arc
new recurring character
retcon
```

But **the task isn't permanently assigned to a lane**.

The Executive determines it dynamically.

---

# Reasoning depth becomes a computed variable

I would calculate something like:

```python
depth_pressure = (
      consequence_impact
    * uncertainty
    * irreversibility
    * downstream_blast_radius
    * novelty
    * critic_disagreement
    * historical_failure_rate
)
```

Not necessarily literal multiplication, but those dimensions matter.

Then:

```text
Low pressure
    ↓
shallow cognition

Medium pressure
    ↓
several operators + small branch search

High pressure
    ↓
wide/deep simulation + multiple cognitive modules

Extreme pressure
    ↓
strategic deliberation + adversarial critics + long horizon
```

And reasoning budget becomes concrete:

```python
class ReasoningBudget(BaseModel):

    level: Literal[
        "reflex",
        "routine",
        "deliberative",
        "strategic",
    ]

    max_operator_calls: int

    branch_width: int
    simulation_depth: int

    critic_count: int

    retrieval_budget: int

    allow_cross_domain_cognition: bool

    compute_class: str
```

So **“think harder” has actual runtime semantics**.

---

# And yes, reasoning depth itself should learn

This is one of the strongest parts of the architecture.

Suppose Quantum discovers historically:

```text
dialogue timing choice
handled shallowly
failure rate 0.7%

major reveal clue placement
handled shallowly
failure rate 38%
```

It should learn:

```text
reveal clue placement
→ deliberative by default
```

But maybe after developing very reliable Reveal Operators:

```text
same task
failure rate falls from 38% → 4%
```

Then reasoning expenditure can decrease.

So the meta-objective becomes:

> **Spend the minimum cognition required to maintain the required quality level.**

You could model:

```python
expected_total_cost = (
      cognition_cost
    + expected_failure_cost
    + expected_repair_cost
    + expected_quality_loss
)
```

Quantum learns the reasoning policy minimizing that.

That's much more interesting than simply maximizing intelligence everywhere.

---

# The Executive becomes the core coordinator

I would probably call it:

```text
quantum.runtime.executive
```

Its responsibilities would be the only major unified list I'd freeze:

* maintain active objectives and cognitive workload;
* consume `WorldSignal`s and production signals;
* assign salience;
* select reasoning operators and cognitive modules;
* determine reasoning depth and budgets;
* launch independent cognition concurrently;
* merge compatible cognitive results into the workspace;
* detect disagreement or uncertainty;
* decide when counterfactual simulation is required;
* arbitrate competing event/action proposals;
* send selected semantic changes through rules/QC;
* submit only validated events for canonical commit;
* learn whether its cognition-allocation policy was appropriate.

It doesn't write dialogue.

It doesn't direct shots.

It doesn't generate sound.

It manages **thinking itself**.

---

# The specialized cognition tree becomes much richer

I'd currently organize it approximately:

```text
quantum.cognition
│
├── narrative
│   ├── causal_reasoning
│   ├── story_pressure
│   ├── opportunity_mining
│   ├── promise_payoff
│   ├── branch_search
│   └── structural_reasoning
│
├── character
│   ├── policy
│   ├── psychology
│   ├── motivation
│   ├── relationship_reasoning
│   └── arc_reasoning
│
├── epistemic
│   ├── knowledge_flow
│   ├── belief_revision
│   ├── deception
│   ├── audience_model
│   └── information_choreography
│
├── cinematic
│   ├── observation
│   ├── blocking
│   ├── camera
│   ├── coverage
│   ├── composition
│   └── editorial
│
├── performance
│   ├── intention
│   ├── subtext
│   ├── dialogue
│   ├── voice_direction
│   └── physical_performance
│
├── acoustic
│   ├── physical_sound
│   ├── ambience
│   ├── foley
│   ├── sound_design
│   └── music_reasoning
│
├── production
│   ├── manufacturing_strategy
│   ├── renderer_routing
│   ├── constraint_enforcement
│   ├── scheduling
│   └── repair_strategy
│
└── quality
    ├── narrative
    ├── visual
    ├── continuity
    ├── performance
    ├── audio
    ├── audience_simulation
    └── root_cause
```

Not everything under those modules needs an LLM.

Some operators will be:

```text
deterministic
graph query
statistical model
optimization
LLM judgment
multimodal model
simulation
```

`cognition` means **reasoning capability**, not “LLM call.”

That's important.

---

# Cross-domain thought is where polycognition becomes powerful

Suppose Narrative Cognition proposes:

> Aria gives Eva the receiver.

Executive detects that this has:

```text
high relationship impact
important prop
epistemic implications
```

So it automatically activates:

```text
character cognition
epistemic cognition
```

Character says:

```text
This action is plausible only if Aria's desire for truth
currently outweighs distrust.
```

Epistemic says:

```text
Handing the receiver creates an opportunity for Eva
to reveal recognition without explicit information transfer.
```

Narrative says:

```text
This also activates old promise #17.
```

Cinematic says:

```text
The information can be expressed through an insert
of Eva's hand hesitation and Aria's reaction.
```

Performance says:

```text
Eva should suppress recognition rather than verbalize it.
```

Sound says:

```text
Remove score and foreground the receiver's mechanical click.
```

Now look at what happened.

No single agent “invented the scene.”

**Quantum did.**

Different cognitive faculties contributed to one action.

🔥

That's the polycognitive architecture in operation.

---

# We need a cross-cognition result format

Something like:

```python
class CognitiveResult(BaseModel):

    module: str
    operator: str

    world_coordinate: WorldCoordinate
    based_on_revision: int

    observations: tuple["Observation", ...]

    proposals: tuple["Proposal", ...]

    constraints: tuple["Constraint", ...]

    opportunities: tuple["NarrativeOpportunity", ...]

    confidence: float
    uncertainty: float

    evidence_refs: tuple[str, ...]

    requested_cognition: tuple["CognitiveRequest", ...]
```

That last field is important.

Narrative cognition can say:

```text
I found something potentially important.
Request epistemic analysis.
```

But the Executive still decides whether to grant it.

So modules can **request thought**, but they don't control the system.

---

# This creates cognitive cascades

Example:

```text
World Signal:
blocked epistemic goal
        ↓
Narrative cognition
        ↓
finds emotionally important information holder
        ↓
requests Relationship cognition
        ↓
finds betrayal pressure
        ↓
requests Promise analysis
        ↓
finds unresolved episode-1 promise
        ↓
NarrativeOpportunity score = .96
        ↓
Executive raises reasoning depth
        ↓
Branch Simulator explores 8 possibilities
```

The system effectively notices:

> **Oh. This is important. Think harder.**

That's exactly what you were describing.

---

# Concurrency requires strict state semantics

This becomes vital once many cognitive functions execute simultaneously.

All cognition should generally read from an **immutable snapshot revision**:

```text
WorldSnapshot revision 9182
```

Suppose:

```text
Narrative cognition starts at r9182.
Production cognition starts at r9182.
Character cognition starts at r9182.
```

They can safely execute concurrently.

Their outputs say:

```text
based_on_revision = 9182
```

Before canonical mutation, Commit Manager performs optimistic concurrency validation:

```python
if current_revision != proposal.based_on_revision:
    revalidate_or_rebase(proposal)
else:
    commit(proposal)
```

This prevents race conditions.

---

# Deep cognition can run while reality advances elsewhere

This is extremely important.

Suppose Quantum is deeply simulating an Episode 7 story decision based on:

```text
episode-development branch @ S800
```

Meanwhile:

```text
Episode 6 Shot 91 rendering
Episode 6 Shot 88 QC
Episode 6 audio mastering
```

continue independently.

No conflict because they're working against different locked scopes / coordinates / branches.

This gives you the **concurrent high-velocity intelligence** you described.

---

# We should introduce cognitive scopes

Every thought has a scope:

```text
frame
shot
scene
sequence
episode
season
universe
production
```

And a write authority.

For example:

```text
Sound cognition:
read universe
read scene
write sound design
cannot modify story

Narrative cognition:
read universe
write hypothetical story branches
cannot directly commit canon

Production cognition:
read locked shot
write manufacturing strategy
cannot change narrative meaning
```

Again, one intelligence doesn't mean unrestricted mutation.

It means shared perception with specialized authority.

---

# Signals become the nervous system

I would elevate `WorldSignal` substantially.

Examples:

```text
GOAL_BLOCKED
FALSE_BELIEF_ACTIVE
KNOWLEDGE_ASYMMETRY
PROMISE_READY_FOR_PAYOFF
RELATIONSHIP_TENSION_HIGH
PHYSICAL_CONSTRAINT_ACTIVE
NARRATIVE_OPPORTUNITY_HIGH
WORLD_RULE_THREAT
PRODUCTION_FAILURE_CLUSTER
QC_DISAGREEMENT
REASONING_UNCERTAINTY_HIGH
```

Signals feed:

```text
salience
reasoning depth
cognition activation
```

So:

```text
World changes
   ↓
signals change
   ↓
attention changes
   ↓
different cognition activates
```

That's much more organism-like than a fixed workflow DAG.

---

# The pipeline doesn't disappear

This is important.

We still want:

```text
creative → develop → animatic → render → master
```

for production control.

But underneath those phases, cognition is no longer a simple sequence.

Think:

```text
                   MACRO WORKFLOW

Creative → Development → Animatic → Production → Master

                         │
                         ▼

              POLYCOGNITIVE RUNTIME

           many concurrent cognitive processes
              operating throughout each phase
```

The workflow manages artifact lifecycle.

The cognitive runtime manages intelligence.

Different concerns.

---

# So I'd refactor the codebase around six top-level systems

Conceptually:

```text
quantum/
│
├── world/
│   ├── entities
│   ├── events
│   ├── snapshots
│   ├── rules
│   ├── affordances
│   ├── graph
│   └── simulation
│
├── memory/
│   ├── l9_bridge
│   ├── retrieval
│   └── experience
│
├── cognition/
│   ├── narrative
│   ├── character
│   ├── epistemic
│   ├── cinematic
│   ├── performance
│   ├── acoustic
│   ├── production
│   └── quality
│
├── runtime/
│   ├── executive
│   ├── attention
│   ├── signals
│   ├── workspace
│   ├── reasoning_policy
│   ├── scheduler
│   ├── arbitration
│   └── commit
│
├── learning/
│   ├── production_experience
│   ├── reasoning_policy
│   ├── critic_calibration
│   └── operator_effectiveness
│
└── artifacts/
    ├── compiler
    ├── production_dag
    └── timeline
```

That architecture now aligns much better with:

> **one intelligence with specialized cognitive subsystems sharing one persistent reality model.**

---

# And there is one more level of learning

Quantum shouldn't only learn:

```text
Which renderer works?
How deep should I reason?
```

It should eventually learn:

```text
Which reasoning operator tends to be useful
under which world-state signals?
```

Imagine after thousands of decisions:

```text
Signal:
false belief + fragile relationship + epistemic goal

Operators historically useful:
information_holder_analysis     +.31 quality
promise_intersection            +.24
connector_prop_analysis         +.19

Operators historically wasteful:
physical_affordance_deep_search -.03
```

Now the Executive learns **how to think about different kinds of problems**.

That's meta-cognitive learning.

So over time:

```text
Quantum learns about filmmaking
        ↓
Quantum learns how much to think
        ↓
Quantum learns which kind of thinking works
        ↓
Quantum learns which cognitive subsystems
should collaborate for a given world condition
```

That is where the architecture starts getting genuinely interesting.

The refined system is therefore not just a persistent World Model plus agents. It is:

> **a persistent World Model + a shared cognitive workspace + specialized cognition + an attention/executive system + adaptive reasoning depth + counterfactual simulation + transactional action + accumulated meta-experience.**

That's the architecture I'd now use as the foundation for **Quantum Animation Agent**.

----

Yes. At this point I would formally split **cognitive control** from **execution orchestration**.

The refined architecture is not:

```text
MasterAgent
   ↓
lots of sub-agents
```

That would recreate the monolithic-agent problem at a higher level.

It is:

```text
                    QUANTUM ANIMATION AGENT

                    Cognitive Executive
                  "What should I think about?"
                  "How hard should I think?"
                  "Which cognition is useful?"
                  "Do I know enough to act?"
                           │
                           ▼
                    Cognitive Workspace
                   active shared thought
                           │
               ┌───────────┼───────────┐
               ▼           ▼           ▼
            narrative   character   epistemic
            cinematic   acoustic    production
            performance quality     ...
               │           │           │
               └───────────┼───────────┘
                           ▼
                Execution Orchestrator
                  "Run these things."
                           │
                           ▼
                  tools / models / DAG
```

## Cognitive Executive ≠ master agent

I would **not** call it the Master Agent.

A Master Agent implies that one generative agent understands everything, makes every decision and delegates work. That gives you a cognitive bottleneck and single point of failure.

`CognitiveExecutive` is closer to executive function in a biological intelligence.

It owns:

> attention, cognitive resource allocation, escalation, arbitration, stopping, uncertainty management and selection of thought processes.

It does **not** necessarily possess the expertise required to solve the problem it is scheduling.

The Executive might determine:

```text
This decision affects:
- Aria's character arc
- audience knowledge
- an Episode 1 promise
- the climax

Blast radius: HIGH
Uncertainty: HIGH

Activate:
  narrative.promise_payoff
  character.policy
  epistemic.information_choreography

Then perform:
  branch simulation depth=4

Then:
  quality.story adjudication
```

But those cognitive modules produce the actual analysis.

---

# Why not call the Executive the Orchestrator?

Because I'd keep an **Orchestrator**, too.

They solve different problems.

```text
CognitiveExecutive
WHY / WHAT / HOW MUCH

ExecutionOrchestrator
WHEN / WHERE / RUN / RETRY
```

For example:

```python
executive.request(
    module="narrative",
    operator="promise_intersection",
    depth="deliberative",
)
```

The Orchestrator decides:

```text
which worker
which model
which queue
concurrently with what
retry policy
timeout
cache
rate limit
resource reservation
```

So:

```text
Executive:
"Think deeply about these three branches."

Orchestrator:
"I'll run six inference jobs across these workers,
parallelize the independent analyses, collect results,
and return them."
```

That separation becomes particularly important once the Executive starts learning **how to think** while the Orchestrator remains reliable systems infrastructure.

---

# The full `CognitiveModule` contract

I would split it into a static specification and runtime protocol.

```python
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Protocol
from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================

class CognitiveDomain(str, Enum):
    NARRATIVE = "narrative"
    CHARACTER = "character"
    EPISTEMIC = "epistemic"
    CINEMATIC = "cinematic"
    PERFORMANCE = "performance"
    ACOUSTIC = "acoustic"
    PRODUCTION = "production"
    QUALITY = "quality"


class ReasoningLevel(str, Enum):
    REFLEX = "reflex"
    ROUTINE = "routine"
    DELIBERATIVE = "deliberative"
    STRATEGIC = "strategic"


class ScopeKind(str, Enum):
    UNIVERSE = "universe"
    SERIES = "series"
    SEASON = "season"
    EPISODE = "episode"
    SEQUENCE = "sequence"
    SCENE = "scene"
    SHOT = "shot"
    FRAME = "frame"

    PRODUCTION = "production"
    ARTIFACT = "artifact"


class IsolationMode(str, Enum):
    SNAPSHOT_READ = "snapshot_read"
    HYPOTHETICAL_BRANCH = "hypothetical_branch"
    CANONICAL_PROPOSAL = "canonical_proposal"


# ============================================================
# COGNITIVE SCOPE
# ============================================================

class CognitiveScope(BaseModel):
    scope_id: str
    kind: ScopeKind

    parent_scope_id: str | None = None

    universe_id: str
    continuity_id: str
    branch_id: str

    world_coordinate: WorldCoordinate

    entity_ids: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()

    read_planes: tuple[str, ...]
    write_domains: tuple[str, ...]

    isolation: IsolationMode

    # Maximum semantic blast radius this cognition is allowed
    # to propose changing.
    mutation_ceiling: str

    # Useful for concurrency / conflict detection.
    concurrency_keys: tuple[str, ...] = ()


# ============================================================
# OPERATOR SPEC
# ============================================================

class OperatorTrigger(BaseModel):
    signal_types: tuple[str, ...] = ()

    requires_any: tuple[str, ...] = ()
    requires_all: tuple[str, ...] = ()

    minimum_salience: float = 0.0
    minimum_uncertainty: float = 0.0


class ResourceProfile(BaseModel):
    expected_cost_class: Literal[
        "tiny",
        "low",
        "medium",
        "high",
        "very_high",
    ]

    expected_latency_class: Literal[
        "instant",
        "short",
        "medium",
        "long",
    ]

    parallelizable: bool = True


class ReasoningOperatorSpec(BaseModel):
    operator_id: str
    version: str

    description: str

    domain: CognitiveDomain

    supported_scopes: tuple[ScopeKind, ...]

    minimum_reasoning_level: ReasoningLevel

    trigger: OperatorTrigger

    required_context_views: tuple[str, ...]

    output_schema: str

    side_effect_free: bool = True

    mandatory_when_triggered: bool = False

    safety_critical: bool = False

    may_request_cognition_from: tuple[CognitiveDomain, ...] = ()

    resource_profile: ResourceProfile


# ============================================================
# SIGNAL SUBSCRIPTION
# ============================================================

class SignalSubscription(BaseModel):
    signal_type: str

    minimum_salience: float = 0.0
    minimum_confidence: float = 0.0

    eligible_operators: tuple[str, ...]


# ============================================================
# MODULE SPECIFICATION
# ============================================================

class CognitiveModuleSpec(BaseModel):
    module_id: str
    version: str

    domain: CognitiveDomain

    description: str

    operators: tuple[ReasoningOperatorSpec, ...]

    subscriptions: tuple[SignalSubscription, ...]

    supported_scopes: tuple[ScopeKind, ...]

    # Modules don't receive arbitrary World Model data.
    required_world_views: tuple[str, ...] = ()
    optional_world_views: tuple[str, ...] = ()

    memory_classes: tuple[str, ...] = ()

    authority_envelope_id: str

    deterministic_possible: bool = False

    supports_parallel_execution: bool = True

    stateless_between_invocations: bool = True
```

And then the actual invocation contract:

```python
class ReasoningBudget(BaseModel):
    level: ReasoningLevel

    max_operator_calls: int

    branch_width: int = 0
    simulation_depth: int = 0

    max_cross_domain_requests: int = 0

    critic_count: int = 0

    retrieval_token_budget: int = 0

    compute_budget_units: float | None = None


class CognitiveInvocation(BaseModel):
    invocation_id: str

    module_id: str
    module_version: str
    operator_id: str
    operator_version: str

    objective: str

    scope: CognitiveScope

    world_snapshot_id: str
    world_revision: int

    workspace_id: str
    workspace_revision: int

    signal_ids: tuple[str, ...]

    reasoning_budget: ReasoningBudget

    authority_envelope_id: str

    deterministic_seed: int | None = None


class EvidenceRef(BaseModel):
    ref_type: Literal[
        "world_fact",
        "world_event",
        "memory",
        "artifact",
        "signal",
        "cognitive_result",
        "branch",
    ]

    ref_id: str


class CognitiveRequest(BaseModel):
    request_id: str

    requested_domain: CognitiveDomain

    suggested_operator: str | None

    reason: str

    scope: CognitiveScope

    urgency: float
    expected_value: float

    evidence_refs: tuple[EvidenceRef, ...]


class CognitiveResult(BaseModel):
    result_id: str

    invocation_id: str

    module_id: str
    operator_id: str

    based_on_world_revision: int
    based_on_workspace_revision: int

    observations: tuple[dict[str, Any], ...] = ()

    hypotheses: tuple[dict[str, Any], ...] = ()

    constraints: tuple[dict[str, Any], ...] = ()

    opportunities: tuple[dict[str, Any], ...] = ()

    proposals: tuple[dict[str, Any], ...] = ()

    requested_cognition: tuple[CognitiveRequest, ...] = ()

    confidence: float
    uncertainty: float

    evidence_refs: tuple[EvidenceRef, ...]

    reasoning_cost_units: float

    # Never canonical state mutation.
    proposed_workspace_patch: WorkspacePatch | None = None
```

And finally:

```python
class CognitiveModule(Protocol):

    @property
    def spec(self) -> CognitiveModuleSpec:
        ...

    async def execute(
        self,
        invocation: CognitiveInvocation,
        context: CognitiveContext,
    ) -> CognitiveResult:
        ...
```

The key invariant:

> **`CognitiveModule.execute()` cannot mutate canonical reality.**

It can think.

It can propose.

It can request more cognition.

It can create hypothetical branches.

Only the canonical commit path changes reality.

---

# Cognitive Scope becomes first-class

This is necessary for both intelligence and concurrency.

A cognitive process must always answer:

```text
What am I thinking about?
How far may I look?
What may I propose changing?
Which immutable state am I reasoning against?
```

For example, a Cinematic cognition invocation might have:

```yaml
scope:
  scope_id: qscope_991

  kind: scene

  universe_id: orpheus
  continuity_id: main
  branch_id: canonical

  world_coordinate:
    ...

  entity_ids:
    - aria
    - eva
    - receiver

  artifact_ids:
    - scene_18
    - shots_91_96

  read_planes:
    - objective
    - psychological
    - epistemic
    - relationship
    - cinematic

  write_domains:
    - shot_design

  isolation: snapshot_read

  mutation_ceiling: directorial

  concurrency_keys:
    - scene:18
```

Meanwhile Sound Cognition can operate over the same scene:

```text
read:
physical + environment + events

write:
sound_design
```

Those operations can run concurrently because they don't collide.

---

# Read scope can be much larger than write scope

This is particularly powerful.

Example:

```text
Character cognition

READ:
whole character history
series relationships
current episode

WRITE:
candidate psychological interpretation
for one scene
```

Or:

```text
Production cognition

READ:
all historical production attempts
current shot
renderer reliability statistics

WRITE:
manufacturing strategy for qshot_217
```

That preserves intelligence without uncontrolled blast radius.

---

# The Cognitive Workspace

This becomes one of the central objects.

Think:

> **World Model = long-term external reality.**
>
> **Cognitive Workspace = Quantum's currently active mind.**

I would make it a versioned, ephemeral blackboard.

```python
class AttentionTarget(BaseModel):
    ref_type: str
    ref_id: str

    salience: float
    reason: str


class OpenQuestion(BaseModel):
    question_id: str

    question: str

    importance: float
    uncertainty: float

    relevant_refs: tuple[EvidenceRef, ...]

    status: Literal[
        "open",
        "investigating",
        "resolved",
        "deferred",
    ]


class CognitiveDisagreement(BaseModel):
    disagreement_id: str

    result_ids: tuple[str, ...]

    proposition: str

    severity: float

    requires_adjudication: bool


class BudgetLedger(BaseModel):
    allocated_units: float
    consumed_units: float

    operator_calls_used: int
    simulations_used: int


class DecisionFrame(BaseModel):
    decision_id: str

    question: str

    decision_type: str

    candidate_refs: tuple[str, ...]

    constraints: tuple[str, ...]

    success_criteria: tuple[str, ...]

    state: Literal[
        "forming",
        "deliberating",
        "ready",
        "selected",
        "committed",
        "abandoned",
    ]


class CognitiveWorkspace(BaseModel):

    workspace_id: str
    revision: int

    objective_stack: tuple[str, ...]

    active_scope_ids: tuple[str, ...]

    world_snapshot_id: str
    world_revision: int

    # --------------------------------------------------
    # ATTENTION
    # --------------------------------------------------

    attention: tuple[AttentionTarget, ...]

    active_signal_ids: tuple[str, ...]

    # --------------------------------------------------
    # ACTIVE INTERPRETATION
    # --------------------------------------------------

    salient_fact_refs: tuple[str, ...]

    salient_entity_refs: tuple[str, ...]

    active_intent_refs: tuple[str, ...]

    active_conflict_refs: tuple[str, ...]

    active_promise_refs: tuple[str, ...]

    narrative_opportunity_refs: tuple[str, ...]

    # --------------------------------------------------
    # TEMPORARY THOUGHT
    # --------------------------------------------------

    hypotheses: tuple[dict[str, Any], ...]

    open_questions: tuple[OpenQuestion, ...]

    assumptions_under_test: tuple[dict[str, Any], ...]

    # --------------------------------------------------
    # CURRENT POSSIBILITIES
    # --------------------------------------------------

    proposal_refs: tuple[str, ...]

    branch_refs: tuple[str, ...]

    decision_frames: tuple[DecisionFrame, ...]

    # --------------------------------------------------
    # CROSS-COGNITIVE INTEGRATION
    # --------------------------------------------------

    cognitive_result_refs: tuple[str, ...]

    disagreements: tuple[CognitiveDisagreement, ...]

    pending_cognitive_requests: tuple[str, ...]

    # --------------------------------------------------
    # METACOGNITION
    # --------------------------------------------------

    current_reasoning_level: ReasoningLevel

    uncertainty: float

    confidence: float

    budget: BudgetLedger

    stopping_conditions: tuple[str, ...]

    # --------------------------------------------------
    # TRACEABILITY
    # --------------------------------------------------

    trace_id: str

    status: Literal[
        "active",
        "waiting",
        "ready_for_decision",
        "closed",
    ]
```

---

# What else belongs in the Workspace?

Several especially valuable things.

### Evidence graph

Not merely:

```text
Candidate B score = .91
```

but:

```text
Candidate B
  ↓ supported by
Aria goal
Eva secret
Receiver promise
CharacterPolicy analysis
Epistemic analysis
```

So temporary cognition itself forms a small graph.

That lets the Executive ask:

> Why do we currently think this branch is best?

And detect unsupported conclusions.

---

# A staleness map

Concurrent cognition means some results eventually become stale.

Suppose:

```text
Narrative cognition based on WorldRevision 9182
```

and meanwhile some relevant canonical state moves to:

```text
WorldRevision 9184
```

Workspace should know whether the result remains valid.

```python
class StalenessRecord(BaseModel):
    result_id: str

    dependency_refs: tuple[str, ...]

    stale: bool

    changed_dependency_refs: tuple[str, ...]
```

So you don't rerun everything when state changes.

Only cognition whose inputs changed.

Exactly like incremental compilation.

🔥

---

# A branch portfolio

If Quantum is deeply thinking about a climax:

```text
Branch A
Branch B
Branch C
Branch D
```

Workspace holds their current status:

```yaml
branch_portfolio:

  A:
    depth: 3
    narrative_value: .82
    uncertainty: .11

  B:
    depth: 4
    narrative_value: .94
    uncertainty: .07

  C:
    pruned: true
    reason: weak_character_grounding

  D:
    depth: 2
    narrative_value: .77
```

That prevents repeated branch work and enables anytime reasoning.

If the budget expires:

```text
pick best sufficiently evaluated branch
```

If importance rises:

```text
continue exploring B/A
```

---

# A cognitive request queue

This enables the cascades.

Narrative Cognition says:

```text
I discovered that candidate B depends heavily
on whether this action is plausible for Aria.
```

It emits:

```python
CognitiveRequest(
    requested_domain=CognitiveDomain.CHARACTER,
    suggested_operator="character.policy_evaluation",
    reason="Candidate B requires uncharacteristically high trust.",
    expected_value=.91,
)
```

This enters the Workspace.

The Executive decides:

```text
grant
defer
merge with existing request
deny as low-value
```

That gives us cross-domain cognition **without agents freely spawning more agents**.

Very important.

---

# The Workspace's leverage

It creates leverage in at least five places.

It prevents every cognitive module from rediscovering the same facts.

It lets specialized cognition accumulate into one shared interpretation rather than vanishing after each call.

It makes concurrency possible because modules operate on the same immutable world revision and contribute versioned workspace patches.

It gives the Executive an explicit view of uncertainty, disagreement, pending questions and branch quality.

And it makes cognition itself inspectable, resumable and learnable.

Without it, polycognition becomes:

```text
lots of good model calls
```

With it, polycognition becomes:

```text
one accumulating thought process
```

That distinction is enormous.

---

# Workspace connections

Mechanically:

```text
                     WORLD MODEL
                         │
                   exact reality
                         │
                         ▼
                  Context Compiler
                         │
                         ▼
                  ┌──────────────┐
    L9 Memory ───►│  COGNITIVE   │◄── World Signals
                  │  WORKSPACE   │
                  └──────┬───────┘
                         │
               current shared thought
                         │
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
     Narrative        Character       Epistemic
         │               │                │
         └───────────────┼────────────────┘
                         ▼
                  Workspace patches
                         │
                         ▼
                 Cognitive Executive
                         │
                ┌────────┴────────┐
                ▼                 ▼
          more cognition      simulate
                                  │
                                  ▼
                            Branch Simulator
                                  │
                                  ▼
                              Workspace
                                  │
                                  ▼
                               decision
                                  │
                                  ▼
                                  QC
                                  │
                                  ▼
                            Commit Manager
                                  │
                                  ▼
                              WORLD MODEL
```

The Workspace is therefore the **integration membrane** between all cognitive functions.

---

# Modules should patch the Workspace, not rewrite it

For concurrency:

```python
class WorkspacePatch(BaseModel):
    patch_id: str

    based_on_revision: int

    add_signal_refs: tuple[str, ...] = ()
    add_hypotheses: tuple[dict, ...] = ()
    add_proposals: tuple[str, ...] = ()
    add_results: tuple[str, ...] = ()
    add_questions: tuple[OpenQuestion, ...] = ()

    resolve_question_ids: tuple[str, ...] = ()

    requested_cognition: tuple[CognitiveRequest, ...] = ()

    confidence_delta: float = 0.0
```

Workspace service performs:

```text
revision 31
   │
Narrative patch
Character patch
Sound patch
   │
   ▼
conflict-aware merge
   │
   ▼
revision 32
```

If two modules conflict semantically:

```text
don't overwrite
```

Create:

```text
CognitiveDisagreement
```

and let Executive adjudicate.

---

# `WorldSignal` absolutely should be first-class 🔥

I'd give it a real lifecycle.

```python
class SignalMetric(BaseModel):
    severity: float
    salience: float
    urgency: float
    novelty: float
    confidence: float


class WorldSignal(BaseModel):

    signal_id: str

    signal_type: str
    signal_version: str

    source_detector_id: str

    observed_at: WorldCoordinate

    scope: CognitiveScope

    subject_refs: tuple[str, ...]

    metrics: SignalMetric

    payload: dict[str, Any]

    evidence_refs: tuple[EvidenceRef, ...]

    causal_parent_signal_ids: tuple[str, ...] = ()

    # Used to collapse duplicates from different analyses.
    deduplication_key: str | None = None

    lifecycle: Literal[
        "active",
        "consumed",
        "superseded",
        "expired",
    ]

    expires_at_world_coordinate: WorldCoordinate | None = None

    expires_on_events: tuple[str, ...] = ()

    # Hints are not commands.
    suggested_operator_tags: tuple[str, ...] = ()
```

Examples:

```text
NARRATIVE.GOAL_BLOCKED

EPISTEMIC.KNOWLEDGE_ASYMMETRY

CHARACTER.FALSE_BELIEF_ACTIVE

RELATIONSHIP.TRUST_COLLAPSE

NARRATIVE.PROMISE_PAYOFF_READY

NARRATIVE.OPPORTUNITY_CONVERGENCE

WORLD.CONSTRAINT_CHANGED

PRODUCTION.RENDER_FAILURE_CLUSTER

QUALITY.CRITIC_DISAGREEMENT

META.REASONING_UNCERTAINTY_HIGH
```

---

# Signals should come from detectors, not agents only

```python
class WorldSignalDetector(Protocol):

    detector_id: str

    subscribed_world_changes: tuple[str, ...]

    async def evaluate(
        self,
        previous: WorldSnapshot,
        current: WorldSnapshot,
    ) -> tuple[WorldSignal, ...]:
        ...
```

Some detectors are deterministic:

```text
goal became blocked
prop ownership changed
knowledge asymmetry created
```

Some use graph analysis:

```text
three unresolved narrative threads now converge
```

Some use statistical intelligence:

```text
this shot resembles a historically high-failure production pattern
```

Some use judgment:

```text
current constellation appears thematically significant
```

All produce the same `WorldSignal` envelope.

This is beautiful because downstream cognition no longer cares how the signal was discovered.

---

# Signals are the nervous system

The runtime becomes event-driven:

```text
WORLD CHANGE
    │
    ▼
Signal Detectors
    │
    ▼
WorldSignalBus
    │
    ▼
Attention / Salience
    │
    ▼
Cognitive Executive
    │
    ▼
activate cognition
```

So Quantum doesn't poll everything constantly.

Reality changing causes cognition to wake up where relevant.

That is very high leverage.

---

# The other classes I'd add

At this point I think the minimum cognitive-runtime domain model includes:

```text
CognitiveExecutive
ExecutionOrchestrator

CognitiveModule
CognitiveModuleSpec
ReasoningOperatorSpec
CognitiveInvocation
CognitiveResult
CognitiveRequest

CognitiveScope
AuthorityEnvelope

CognitiveWorkspace
WorkspaceView
WorkspacePatch

WorldSignal
WorldSignalDetector
WorldSignalBus

AttentionTarget
SaliencePolicy

ReasoningPolicy
ReasoningBudget

DecisionFrame
Proposal
CognitiveDisagreement

BranchPortfolio
BranchSimulator

CognitiveArbitrator
CommitManager

CognitiveTrace
OperatorExperience
OperatorSelectionPolicy
```

That's the one list I'd actually freeze at this stage.

---

# Cognitive Cascades become a protocol

The mechanism is elegant:

```text
Signal
  ↓
Executive selects operator
  ↓
CognitiveModule executes
  ↓
CognitiveResult
  ↓
Result may contain CognitiveRequest
  ↓
Executive assesses request
  ↓
activate another module?
  │
  ├── no → continue
  │
  └── yes
       ↓
    another result
       ↓
    new signal/opportunity?
       ↓
    Executive may raise reasoning depth
```

Example:

```text
NARRATIVE.GOAL_BLOCKED
        ↓
narrative.blocker_analysis
        ↓
"Eva possesses required information"
        ↓
request relationship cognition
        ↓
relationship.emotional_cost
        ↓
"Cost is very high because of prior betrayal"
        ↓
request promise analysis
        ↓
"Episode 1 promise intersects"
        ↓
NARRATIVE.OPPORTUNITY_CONVERGENCE = .96
        ↓
Executive:
THIS GOT IMPORTANT
        ↓
reasoning:
ROUTINE → DELIBERATIVE
        ↓
branch_width 2 → 8
simulation_depth 0 → 4
        ↓
epistemic + character + cinematic cognition
        ↓
better event
```

🔥🔥🔥

That is genuine adaptive cognition.

---

# How Quantum learns which operators are useful under which signals

This should be one of the core learning systems.

Every cognitive decision needs an explicit trace.

```text
WorldSignals
      ↓
Operator selected
      ↓
CognitiveResult
      ↓
Proposal
      ↓
Branch
      ↓
Decision
      ↓
WorldEvent
      ↓
Film artifact
      ↓
QC
      ↓
Repair / no repair
      ↓
eventual outcome
```

So create:

```python
class CognitiveTrace(BaseModel):

    trace_id: str

    signal_ids: tuple[str, ...]

    world_feature_fingerprint: str

    decision_type: str
    scope_kind: ScopeKind

    invocation_ids: tuple[str, ...]
    operator_ids: tuple[str, ...]

    proposal_ids: tuple[str, ...]
    branch_ids: tuple[str, ...]

    selected_proposal_id: str | None

    reasoning_cost: float
    latency_ms: int

    downstream_quality: dict[str, float] = {}

    repair_count: int = 0
    downstream_invalidation_cost: float = 0.0

    final_reward: float | None = None
```

Now Quantum has a dataset answering:

```text
Under signal constellation S,
when solving decision class D,
we used operators O1/O2/O3,
spent C cognition,
and ultimately got outcome Q.
```

That is the foundation.

---

# Learn marginal operator utility

Suppose this pattern occurs repeatedly:

```text
Signals:
GOAL_BLOCKED
KNOWLEDGE_ASYMMETRY
FRAGILE_RELATIONSHIP
```

Historical outcomes:

```text
blocked_intent only
    quality 0.78

+ information_holder
    quality 0.84

+ emotional_cost
    quality 0.92

+ acoustic analysis
    quality 0.921
```

Quantum should learn approximately:

```text
P(operator useful | signals, decision_type, scope)
```

or, better:

```text
ExpectedMarginalUtility(
    operator
    |
    current_workspace,
    signal_constellation,
    decision_type,
    reasoning_level
)
```

---

# Utility should include cognition cost

Not merely quality.

Conceptually:

```python
operator_utility = (
      expected_quality_gain
    + expected_failure_risk_reduction
    + expected_repair_cost_avoided
    + expected_future_option_value
    - compute_cost
    - latency_cost
)
```

So if:

```text
cinematic.symbolism_analysis
```

adds only `.002` expected quality for a trivial Foley decision:

```text
don't run it.
```

If:

```text
epistemic.information_choreography
```

reduces a reveal failure probability from `28% → 5%`:

```text
absolutely run it.
```

This is how Quantum learns to **save brainpower for where it counts**.

---

# Start with a contextual bandit, not full RL

Initially I'd use:

```text
signals
+
decision type
+
scope
+
risk
+
current uncertainty
+
historical features
   ↓
rank optional reasoning operators
```

That's essentially a contextual decision problem.

Mandatory correctness/safety operators are fixed.

Learned policy chooses only among **optional cognition**.

This is important.

Never learn:

```text
world-rule validation seems expensive,
maybe skip it.
```

No.

These remain invariants:

```text
hard rules
canonical constraints
security
technical validation
```

Learning optimizes the intelligent optional reasoning around them.

---

# Operator policy

Conceptually:

```python
class OperatorSelectionContext(BaseModel):
    signal_types: tuple[str, ...]

    scope_kind: ScopeKind

    decision_type: str

    world_feature_embedding: tuple[float, ...]

    uncertainty: float
    blast_radius: float

    current_reasoning_level: ReasoningLevel

    already_invoked_operators: tuple[str, ...]


class OperatorUtilityPrediction(BaseModel):
    operator_id: str

    expected_quality_delta: float

    expected_risk_reduction: float

    expected_cost: float

    expected_latency_ms: float

    expected_utility: float

    confidence: float
```

Executive asks:

```python
ranked = operator_policy.rank(
    current_context
)
```

and decides:

```text
Operator A expected utility +.38 → run
Operator B expected utility +.19 → run
Operator C expected utility -.04 → skip
```

---

# Delayed credit matters

This is harder than renderer learning.

Maybe:

```text
promise_intersection
```

looks useless immediately.

But seven minutes later it produces the payoff that makes the ending work.

Therefore `CognitiveTrace` needs **causal lineage**.

```text
Operator invocation
    ↓ contributed_to
NarrativeOpportunity
    ↓ contributed_to
EventProposal
    ↓ selected_as
WorldEvent
    ↓ enabled
Later Payoff
    ↓ affected
Final audience QC
```

This is where graphs become useful again.

You can propagate credit backward along cognitive provenance.

Not perfectly.

But increasingly well.

---

# Use offline ablation when possible

Suppose Quantum produced a successful scene with:

```text
blocked_intent
relationship_analysis
promise_intersection
connector_prop
```

Later, offline:

```text
rerun same decision without promise_intersection
```

and evaluate resulting branches.

If quality drops significantly:

```text
promise_intersection had positive marginal value.
```

This is much stronger evidence than simple correlation.

You don't need to do this for every decision.

Use it for learning high-value policies.

---

# Shadow cognition

Another very useful technique:

Policy currently says:

```text
don't run operator X
```

On a small percentage of safe/hypothetical cases:

```text
run X in shadow mode
```

Its output does **not** affect the canonical decision.

But Quantum measures:

> Would X have produced useful information?

Now the system can discover overlooked reasoning operators without risking production quality.

That's how the Executive's cognition strategy can improve safely.

---

# Don't let the learned policy collapse into habits

A learning system can become overconfident.

So maintain:

```text
minimum exploration
operator calibration suites
novelty detection
policy versioning
holdout evaluation
shadow testing
```

And if:

```text
world state is novel
```

or:

```text
policy confidence is low
```

increase reasoning breadth.

In other words:

> Familiarity permits cognitive efficiency. Novelty buys more thought.

Very intelligence-like.

---

# The full refined control loop

We can now put almost everything together:

```text
                    WORLD MODEL CHANGES
                            │
                            ▼
                   WORLD SIGNAL DETECTORS
                            │
                            ▼
                      WORLD SIGNALS
                            │
                            ▼
                 ATTENTION / SALIENCE
                            │
                            ▼
                   COGNITIVE EXECUTIVE
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
     determine scope   reasoning depth   operator policy
          │                 │                 │
          └─────────────────┼─────────────────┘
                            ▼
                    COGNITIVE WORKSPACE
                            │
            ┌───────────────┼─────────────────┐
            ▼               ▼                 ▼
         narrative       character         epistemic
         cinematic       acoustic          quality
         production      performance       ...
            │               │                 │
            └───────────────┼─────────────────┘
                            ▼
                     COGNITIVE RESULTS
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
         request more cognition     candidate actions
                 │                     │
                 └──────────┬──────────┘
                            ▼
                   reasoning cascade?
                            │
                     ┌──────┴──────┐
                     │             │
                    YES            NO
                     │             │
                     ▼             ▼
               THINK MORE      SIMULATE
                                   │
                                   ▼
                           COUNTERFACTUAL BRANCHES
                                   │
                                   ▼
                               EVALUATE
                                   │
                                   ▼
                                SELECT
                                   │
                                   ▼
                                  QC
                                   │
                                   ▼
                             COMMIT MANAGER
                                   │
                                   ▼
                                REDUCER
                                   │
                                   ▼
                           NEW WORLD STATE
                                   │
                                   ├─────────► new signals
                                   │
                                   ▼
                           COGNITIVE TRACE
                                   │
                                   ▼
                              LEARNING
                                   │
                   ┌───────────────┼───────────────┐
                   ▼               ▼               ▼
             reasoning depth   operator policy   salience
                 learning         learning        learning
```

That is the architecture I would now call the **Quantum Polycognitive Runtime**.

And the especially important part is that autonomy no longer means:

> “An agent can independently complete a workflow.”

It means:

> **Quantum continuously notices what matters, activates the right combination of specialized cognition, allocates thought according to consequence and uncertainty, integrates those faculties through a shared workspace, safely simulates alternatives, acts against persistent reality, observes the consequences, and learns how to think better next time.**

That is a much stronger definition of autonomous intelligence.

-----



Yes. I’d now promote this into the core runtime contract for the Quantum Polycognitive Runtime.

The most important architectural invariant is:

Cognition may observe, reason, propose, simulate, disagree, escalate, and learn. Only CommitManager may mutate canonical World State.

Below is a Python/Pydantic-style reference model close enough to become implementation code.

from __future__ import annotations

from enum import Enum
from typing import Any, Awaitable, Callable, Protocol, Sequence
from pydantic import BaseModel, Field


# =====================================================================
# EXTERNAL WORLD MODEL TYPES
# =====================================================================
#
# These already belong to quantum.world and are referenced here.
#
# WorldCoordinate
# WorldSnapshot
# WorldEvent
# WorldEventDraft
# Branch
# WorldRuleViolation
#
# =====================================================================


# =====================================================================
# FUNDAMENTAL ENUMS
# =====================================================================

class CognitiveDomain(str, Enum):
    NARRATIVE = "narrative"
    CHARACTER = "character"
    EPISTEMIC = "epistemic"
    CINEMATIC = "cinematic"
    PERFORMANCE = "performance"
    ACOUSTIC = "acoustic"
    PRODUCTION = "production"
    QUALITY = "quality"
    META = "meta"


class ReasoningLevel(str, Enum):
    REFLEX = "reflex"
    ROUTINE = "routine"
    DELIBERATIVE = "deliberative"
    STRATEGIC = "strategic"


class ScopeKind(str, Enum):
    UNIVERSE = "universe"
    SERIES = "series"
    SEASON = "season"
    EPISODE = "episode"
    STORYLINE = "storyline"
    SEQUENCE = "sequence"
    SCENE = "scene"
    SHOT = "shot"
    FRAME = "frame"

    PRODUCTION = "production"
    ARTIFACT = "artifact"


class IsolationMode(str, Enum):
    SNAPSHOT_READ = "snapshot_read"
    HYPOTHETICAL_BRANCH = "hypothetical_branch"
    CANONICAL_PROPOSAL = "canonical_proposal"


class CognitiveResultStatus(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    UNCERTAIN = "uncertain"
    FAILED = "failed"


class DecisionState(str, Enum):
    FORMING = "forming"
    DELIBERATING = "deliberating"
    SIMULATING = "simulating"
    READY = "ready"
    SELECTED = "selected"
    COMMITTED = "committed"
    ABANDONED = "abandoned"


class ProposalState(str, Enum):
    PROPOSED = "proposed"
    VALIDATING = "validating"
    SIMULATING = "simulating"
    VALID = "valid"
    INVALID = "invalid"
    SELECTED = "selected"
    REJECTED = "rejected"
    COMMITTED = "committed"
    STALE = "stale"


class SignalLifecycle(str, Enum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    SUPERSEDED = "superseded"
    EXPIRED = "expired"


class DisagreementState(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ACCEPTED_UNCERTAINTY = "accepted_uncertainty"


class MergePolicy(str, Enum):
    APPEND = "append"
    REPLACE = "replace"
    UPSERT = "upsert"
    MAX = "max"
    MIN = "min"
    INCREMENT = "increment"
    REMOVE = "remove"


# =====================================================================
# GENERIC REFERENCES / EVIDENCE
# =====================================================================

class Ref(BaseModel):
    kind: str
    id: str
    version: str | None = None


class EvidenceRef(Ref):
    """
    Stable reference to evidence supporting a conclusion.
    """

    source: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class WorldRevisionRef(BaseModel):
    snapshot_id: str
    revision: int
    coordinate: WorldCoordinate
    state_hash: str


# =====================================================================
# AUTHORITY
# =====================================================================

class AuthorityEnvelope(BaseModel):
    """
    Hard capability boundary for cognition.

    Shared intelligence does NOT imply unrestricted mutation.
    """

    envelope_id: str

    granted_to: str

    allowed_domains: tuple[CognitiveDomain, ...]

    allowed_scope_kinds: tuple[ScopeKind, ...]

    allowed_read_planes: tuple[str, ...]
    allowed_write_domains: tuple[str, ...]

    allowed_operator_ids: tuple[str, ...] = ()

    protected_refs: tuple[Ref, ...] = ()

    maximum_authority_rank: int

    may_create_hypothetical_branches: bool = True

    may_propose_world_events: bool = False

    may_propose_canon_change: bool = False

    # Should effectively always remain False for cognition modules.
    may_commit_world_state: bool = False

    requires_escalation_above_rank: int | None = None

    expires_at: str | None = None


# =====================================================================
# COGNITIVE SCOPE
# =====================================================================

class CognitiveScope(BaseModel):
    """
    Defines what a cognitive operation is thinking about.

    Read scope may be much larger than write scope.
    """

    scope_id: str

    kind: ScopeKind
    parent_scope_id: str | None = None

    coordinate: WorldCoordinate

    universe_id: str
    continuity_id: str
    branch_id: str

    entity_refs: tuple[Ref, ...] = ()
    artifact_refs: tuple[Ref, ...] = ()

    read_planes: tuple[str, ...]
    write_domains: tuple[str, ...]

    isolation: IsolationMode

    # Semantic level above which this process cannot propose change.
    mutation_ceiling_rank: int

    # Used to detect incompatible concurrent operations.
    concurrency_keys: tuple[str, ...] = ()

    # Optional time span inside the world/story.
    start_coordinate: WorldCoordinate | None = None
    end_coordinate: WorldCoordinate | None = None


# =====================================================================
# WORLD SIGNAL
# =====================================================================

class SignalMetrics(BaseModel):
    severity: float = Field(ge=0.0, le=1.0)
    salience: float = Field(ge=0.0, le=1.0)
    urgency: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)

    estimated_downstream_impact: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )


class WorldSignal(BaseModel):
    """
    First-class nervous-system event.

    Examples:
        NARRATIVE.GOAL_BLOCKED
        EPISTEMIC.KNOWLEDGE_ASYMMETRY
        NARRATIVE.PROMISE_PAYOFF_READY
        CHARACTER.FALSE_BELIEF_ACTIVE
        QUALITY.CRITIC_DISAGREEMENT
        PRODUCTION.RENDER_FAILURE_CLUSTER
    """

    signal_id: str

    signal_type: str
    signal_version: str

    source_detector_id: str

    observed_at: WorldCoordinate

    scope: CognitiveScope

    subject_refs: tuple[Ref, ...]

    metrics: SignalMetrics

    payload: dict[str, Any]

    evidence_refs: tuple[EvidenceRef, ...]

    causal_parent_signal_ids: tuple[str, ...] = ()

    # Allows equivalent discoveries to collapse into one signal.
    deduplication_key: str | None = None

    lifecycle: SignalLifecycle = SignalLifecycle.ACTIVE

    suggested_operator_tags: tuple[str, ...] = ()

    expires_on_event_types: tuple[str, ...] = ()

    expires_at: WorldCoordinate | None = None

    created_at: str


# =====================================================================
# SIGNAL DETECTION / SIGNAL BUS
# =====================================================================

class WorldChangeSet(BaseModel):
    from_revision: int
    to_revision: int

    changed_entity_refs: tuple[Ref, ...]
    changed_state_addresses: tuple[str, ...]
    committed_event_refs: tuple[Ref, ...]


class WorldSignalDetectorSpec(BaseModel):
    detector_id: str
    version: str

    description: str

    subscribed_event_types: tuple[str, ...] = ()
    subscribed_state_paths: tuple[str, ...] = ()

    deterministic: bool

    output_signal_types: tuple[str, ...]


class WorldSignalDetector(Protocol):

    @property
    def spec(self) -> WorldSignalDetectorSpec:
        ...

    async def detect(
        self,
        previous: WorldSnapshot,
        current: WorldSnapshot,
        changes: WorldChangeSet,
    ) -> tuple[WorldSignal, ...]:
        ...


class SignalSubscription(BaseModel):
    subscription_id: str

    signal_types: tuple[str, ...]

    minimum_salience: float = 0.0
    minimum_confidence: float = 0.0

    scope_kinds: tuple[ScopeKind, ...] = ()


class WorldSignalBus(Protocol):
    """
    Transport/distribution mechanism.

    It does not decide what is important.
    Salience + Executive do that.
    """

    async def publish(
        self,
        signal: WorldSignal,
    ) -> None:
        ...

    async def publish_many(
        self,
        signals: Sequence[WorldSignal],
    ) -> None:
        ...

    async def subscribe(
        self,
        subscription: SignalSubscription,
        handler: Callable[[WorldSignal], Awaitable[None]],
    ) -> str:
        ...

    async def acknowledge(
        self,
        signal_id: str,
        consumer_id: str,
    ) -> None:
        ...


# =====================================================================
# ATTENTION / SALIENCE
# =====================================================================

class AttentionTarget(BaseModel):
    """
    Something Quantum should currently care about.
    """

    target_id: str

    ref: Ref

    scope_id: str

    salience: float = Field(ge=0.0, le=1.0)

    urgency: float = Field(ge=0.0, le=1.0)

    reason: str

    supporting_signal_ids: tuple[str, ...] = ()

    decay_rate: float = Field(default=0.0, ge=0.0)

    pinned: bool = False

    created_at: str


class SalienceContext(BaseModel):
    objective_refs: tuple[Ref, ...]

    current_scope: CognitiveScope

    active_signal_ids: tuple[str, ...]

    current_attention: tuple[AttentionTarget, ...]

    world_revision: int

    reasoning_level: ReasoningLevel


class SaliencePolicy(Protocol):
    """
    Determines what deserves attention.

    This policy can eventually be learned.
    """

    policy_id: str
    version: str

    async def score_signal(
        self,
        signal: WorldSignal,
        context: SalienceContext,
    ) -> float:
        ...

    async def rank_targets(
        self,
        candidates: Sequence[AttentionTarget],
        context: SalienceContext,
    ) -> tuple[AttentionTarget, ...]:
        ...

    async def decay(
        self,
        targets: Sequence[AttentionTarget],
        world_time_delta: float,
    ) -> tuple[AttentionTarget, ...]:
        ...


# =====================================================================
# REASONING BUDGET / POLICY
# =====================================================================

class ReasoningBudget(BaseModel):
    """
    Concrete meaning of "think harder".
    """

    level: ReasoningLevel

    max_operator_calls: int

    max_cross_domain_requests: int

    branch_width: int
    simulation_depth: int

    critic_count: int

    retrieval_token_budget: int

    max_parallel_cognitive_jobs: int

    compute_budget_units: float | None = None

    wall_clock_budget_ms: int | None = None

    allow_branch_simulation: bool = True
    allow_cross_domain_cognition: bool = True


class ReasoningPolicyContext(BaseModel):
    scope: CognitiveScope

    signal_ids: tuple[str, ...]

    uncertainty: float
    novelty: float
    irreversibility: float
    downstream_blast_radius: float
    critic_disagreement: float
    historical_failure_probability: float

    decision_type: str | None = None

    current_budget: ReasoningBudget | None = None


class ReasoningPolicyDecision(BaseModel):
    budget: ReasoningBudget

    rationale: str

    confidence: float

    policy_version: str


class ReasoningPolicy(Protocol):
    """
    Learns how much cognition a problem deserves.
    """

    policy_id: str
    version: str

    async def allocate(
        self,
        context: ReasoningPolicyContext,
    ) -> ReasoningPolicyDecision:
        ...


# =====================================================================
# REASONING OPERATORS
# =====================================================================

class ResourceProfile(BaseModel):
    expected_cost_class: str
    expected_latency_class: str

    parallelizable: bool = True
    cacheable: bool = True


class OperatorTrigger(BaseModel):
    signal_types_any: tuple[str, ...] = ()
    signal_types_all: tuple[str, ...] = ()

    minimum_salience: float = 0.0
    minimum_uncertainty: float = 0.0

    world_predicate_ids: tuple[str, ...] = ()


class ReasoningOperatorSpec(BaseModel):
    """
    A reusable cognitive primitive.

    Examples:
        narrative.blocked_intents
        narrative.promise_intersection
        epistemic.information_split
        character.policy_evaluation
    """

    operator_id: str
    version: str

    domain: CognitiveDomain

    description: str

    supported_scopes: tuple[ScopeKind, ...]

    minimum_reasoning_level: ReasoningLevel

    trigger: OperatorTrigger

    required_world_views: tuple[str, ...] = ()
    required_workspace_views: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()

    output_contract: str

    mandatory_when_triggered: bool = False

    side_effect_free: bool = True

    safety_or_correctness_critical: bool = False

    may_request_domains: tuple[CognitiveDomain, ...] = ()

    may_create_hypothetical_branch: bool = False

    resource_profile: ResourceProfile

    tags: tuple[str, ...] = ()


# =====================================================================
# COGNITIVE MODULE
# =====================================================================

class CognitiveModuleSpec(BaseModel):
    """
    Static declaration of one specialized cognitive faculty.
    """

    module_id: str
    version: str

    domain: CognitiveDomain

    description: str

    operators: tuple[ReasoningOperatorSpec, ...]

    signal_subscriptions: tuple[SignalSubscription, ...]

    supported_scopes: tuple[ScopeKind, ...]

    required_world_views: tuple[str, ...] = ()
    optional_world_views: tuple[str, ...] = ()

    memory_classes: tuple[str, ...] = ()

    authority_envelope_id: str

    stateless_between_invocations: bool = True

    supports_parallel_execution: bool = True

    deterministic_operators_possible: bool = True


# =====================================================================
# PROPOSALS / DECISIONS
# =====================================================================

class WorldRationale(BaseModel):
    supported_by_intent_refs: tuple[Ref, ...] = ()

    enabled_by_affordance_refs: tuple[Ref, ...] = ()

    conflict_refs: tuple[Ref, ...] = ()

    promise_refs: tuple[Ref, ...] = ()

    belief_refs: tuple[Ref, ...] = ()

    rule_refs: tuple[Ref, ...] = ()

    evidence_refs: tuple[EvidenceRef, ...] = ()

    explanation: str


class Proposal(BaseModel):
    """
    Candidate action or semantic decision.

    Proposal != commit.
    """

    proposal_id: str

    proposal_type: str

    created_by_result_id: str

    objective: str

    scope: CognitiveScope

    based_on_world_revision: int
    based_on_workspace_revision: int

    payload: dict[str, Any]

    rationale: WorldRationale | None = None

    precondition_refs: tuple[Ref, ...] = ()

    expected_effects: tuple[dict[str, Any], ...] = ()

    evidence_refs: tuple[EvidenceRef, ...] = ()

    required_authority_rank: int

    requires_simulation: bool = False

    estimated_blast_radius: float = 0.0
    estimated_irreversibility: float = 0.0

    confidence: float = Field(ge=0.0, le=1.0)

    state: ProposalState = ProposalState.PROPOSED


class DecisionCriterion(BaseModel):
    criterion_id: str
    description: str

    weight: float

    hard_constraint: bool = False

    minimum_score: float | None = None


class DecisionFrame(BaseModel):
    """
    Explicit cognitive problem Quantum is currently trying to solve.
    """

    decision_id: str

    question: str

    decision_type: str

    objective: str

    scope: CognitiveScope

    created_at_world_revision: int
    created_at_workspace_revision: int

    criteria: tuple[DecisionCriterion, ...]

    constraint_refs: tuple[Ref, ...] = ()

    candidate_proposal_ids: tuple[str, ...] = ()

    required_domains: tuple[CognitiveDomain, ...] = ()

    required_operator_ids: tuple[str, ...] = ()

    selected_proposal_id: str | None = None

    confidence: float = 0.0
    uncertainty: float = 1.0

    stopping_conditions: tuple[str, ...] = ()

    state: DecisionState = DecisionState.FORMING


# =====================================================================
# COGNITIVE DISAGREEMENT
# =====================================================================

class CognitiveClaim(BaseModel):
    result_id: str
    module_id: str

    claim: str

    confidence: float

    evidence_refs: tuple[EvidenceRef, ...]


class CognitiveDisagreement(BaseModel):
    disagreement_id: str

    scope: CognitiveScope

    subject: str

    claims: tuple[CognitiveClaim, ...]

    severity: float
    decision_impact: float

    requires_adjudication: bool = True

    state: DisagreementState = DisagreementState.OPEN

    resolution_result_id: str | None = None

    created_at: str


# =====================================================================
# COGNITIVE REQUEST / INVOCATION / RESULT
# =====================================================================

class CognitiveRequest(BaseModel):
    """
    One cognitive subsystem asking the Executive for another type
    of cognition.

    It does not directly spawn it.
    """

    request_id: str

    requested_domain: CognitiveDomain

    suggested_operator_id: str | None = None

    objective: str
    reason: str

    scope: CognitiveScope

    triggered_by_result_id: str | None = None
    triggered_by_signal_ids: tuple[str, ...] = ()

    urgency: float
    expected_value: float

    suggested_reasoning_level: ReasoningLevel | None = None

    evidence_refs: tuple[EvidenceRef, ...] = ()

    deduplication_key: str | None = None


class CognitiveInvocation(BaseModel):
    """
    Immutable execution request sent to a cognitive module.
    """

    invocation_id: str

    module_id: str
    module_version: str

    operator_id: str
    operator_version: str

    objective: str

    scope: CognitiveScope

    world_revision_ref: WorldRevisionRef

    workspace_id: str
    workspace_revision: int

    signal_ids: tuple[str, ...]

    context_view_ids: tuple[str, ...]

    reasoning_budget: ReasoningBudget

    authority: AuthorityEnvelope

    trace_id: str

    deterministic_seed: int | None = None

    deadline_at: str | None = None


class WorkspacePatchOperation(BaseModel):
    op: MergePolicy

    collection: str

    key: str | None = None

    value: Any | None = None


class WorkspacePatch(BaseModel):
    """
    Cognitive modules patch temporary thought.

    They never patch World Model state.
    """

    patch_id: str

    workspace_id: str
    based_on_revision: int

    operations: tuple[WorkspacePatchOperation, ...]

    created_by_result_id: str

    conflict_keys: tuple[str, ...] = ()

    created_at: str


class CognitiveResult(BaseModel):
    """
    Normalized output of every cognitive operation.
    """

    result_id: str

    invocation_id: str

    module_id: str
    operator_id: str

    status: CognitiveResultStatus

    based_on_world_revision: int
    based_on_workspace_revision: int

    observations: tuple[dict[str, Any], ...] = ()

    hypotheses: tuple[dict[str, Any], ...] = ()

    constraints: tuple[dict[str, Any], ...] = ()

    opportunity_refs: tuple[Ref, ...] = ()

    proposals: tuple[Proposal, ...] = ()

    requested_cognition: tuple[CognitiveRequest, ...] = ()

    evidence_refs: tuple[EvidenceRef, ...] = ()

    workspace_patch: WorkspacePatch | None = None

    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(ge=0.0, le=1.0)

    reasoning_cost_units: float = 0.0
    latency_ms: int = 0

    created_at: str


class CognitiveContext(BaseModel):
    """
    Materialized runtime context supplied to a module.

    This is already filtered/projected for that module.
    """

    world_view: dict[str, Any]

    workspace_view: WorkspaceView

    memory_view: dict[str, Any] | None = None

    tool_handles: tuple[str, ...] = ()


class CognitiveModule(Protocol):

    @property
    def spec(self) -> CognitiveModuleSpec:
        ...

    async def execute(
        self,
        invocation: CognitiveInvocation,
        context: CognitiveContext,
    ) -> CognitiveResult:
        ...


# =====================================================================
# COGNITIVE WORKSPACE
# =====================================================================

class ObjectiveFrame(BaseModel):
    objective_id: str
    objective: str

    priority: float

    scope_id: str

    parent_objective_id: str | None = None

    status: str


class Hypothesis(BaseModel):
    hypothesis_id: str

    statement: str

    probability: float

    evidence_for: tuple[EvidenceRef, ...] = ()
    evidence_against: tuple[EvidenceRef, ...] = ()

    status: str = "active"


class OpenQuestion(BaseModel):
    question_id: str

    question: str

    importance: float
    uncertainty: float

    relevant_refs: tuple[EvidenceRef, ...] = ()

    status: str = "open"


class BudgetLedger(BaseModel):
    allocated_compute_units: float
    consumed_compute_units: float

    operator_calls_used: int
    simulations_used: int

    cognitive_jobs_started: int
    cognitive_jobs_completed: int


class StalenessRecord(BaseModel):
    result_id: str

    dependency_refs: tuple[Ref, ...]

    stale: bool

    changed_dependency_refs: tuple[Ref, ...] = ()


class CognitiveWorkspace(BaseModel):
    """
    Quantum's active working memory / global cognitive blackboard.

    EPHEMERAL and reconstructable.

    Not canonical fictional truth.
    """

    workspace_id: str
    revision: int

    world_revision_ref: WorldRevisionRef

    objective_stack: tuple[ObjectiveFrame, ...]

    active_scope_ids: tuple[str, ...]

    # ----------------------------
    # ATTENTION / NERVOUS SYSTEM
    # ----------------------------

    attention_targets: tuple[AttentionTarget, ...]

    active_signal_ids: tuple[str, ...]

    # ----------------------------
    # CURRENT SALIENT REALITY
    # ----------------------------

    salient_entity_refs: tuple[Ref, ...]
    salient_fact_refs: tuple[Ref, ...]

    active_intent_refs: tuple[Ref, ...]
    active_conflict_refs: tuple[Ref, ...]
    active_promise_refs: tuple[Ref, ...]

    narrative_opportunity_refs: tuple[Ref, ...]

    # ----------------------------
    # ACTIVE THOUGHT
    # ----------------------------

    hypotheses: tuple[Hypothesis, ...]

    open_questions: tuple[OpenQuestion, ...]

    assumptions_under_test: tuple[Hypothesis, ...]

    # ----------------------------
    # POSSIBILITIES / DECISIONS
    # ----------------------------

    proposal_ids: tuple[str, ...]

    branch_portfolio_ids: tuple[str, ...]

    decision_frames: tuple[DecisionFrame, ...]

    # ----------------------------
    # CROSS-COGNITIVE INTEGRATION
    # ----------------------------

    cognitive_result_ids: tuple[str, ...]

    disagreements: tuple[CognitiveDisagreement, ...]

    pending_cognitive_requests: tuple[CognitiveRequest, ...]

    # ----------------------------
    # VALIDITY
    # ----------------------------

    staleness_records: tuple[StalenessRecord, ...]

    # ----------------------------
    # METACOGNITION
    # ----------------------------

    current_reasoning_level: ReasoningLevel

    confidence: float
    uncertainty: float

    budget: BudgetLedger

    stopping_conditions: tuple[str, ...]

    # ----------------------------
    # TRACE
    # ----------------------------

    active_trace_ids: tuple[str, ...]

    status: str


class WorkspaceView(BaseModel):
    """
    Role/scope-specific projection of the Workspace.

    Cognitive modules should almost never receive the entire Workspace.
    """

    workspace_id: str
    workspace_revision: int

    scope: CognitiveScope

    objective_stack: tuple[ObjectiveFrame, ...]

    attention_targets: tuple[AttentionTarget, ...]

    signals: tuple[WorldSignal, ...]

    salient_entity_refs: tuple[Ref, ...]
    salient_fact_refs: tuple[Ref, ...]

    hypotheses: tuple[Hypothesis, ...]

    relevant_questions: tuple[OpenQuestion, ...]

    relevant_decisions: tuple[DecisionFrame, ...]

    relevant_result_ids: tuple[str, ...]

    relevant_disagreements: tuple[CognitiveDisagreement, ...]

    view_hash: str


class WorkspaceService(Protocol):

    async def get(
        self,
        workspace_id: str,
    ) -> CognitiveWorkspace:
        ...

    async def project(
        self,
        workspace_id: str,
        scope: CognitiveScope,
        module_spec: CognitiveModuleSpec,
    ) -> WorkspaceView:
        ...

    async def apply_patch(
        self,
        patch: WorkspacePatch,
    ) -> CognitiveWorkspace:
        ...

    async def mark_stale(
        self,
        changed_refs: Sequence[Ref],
    ) -> tuple[str, ...]:
        ...


# =====================================================================
# BRANCH PORTFOLIO / SIMULATION
# =====================================================================

class BranchScorecard(BaseModel):
    narrative_value: float = 0.0
    causal_strength: float = 0.0
    character_integrity: float = 0.0
    epistemic_quality: float = 0.0
    thematic_value: float = 0.0
    emotional_value: float = 0.0
    future_option_value: float = 0.0
    production_feasibility: float = 0.0

    rule_violations: int = 0

    confidence: float = 0.0


class BranchCandidate(BaseModel):
    branch_id: str

    originating_proposal_id: str

    base_world_revision: int

    depth_reached: int

    simulated_event_refs: tuple[Ref, ...]

    terminal_snapshot_ref: Ref | None = None

    scorecard: BranchScorecard | None = None

    uncertainty: float = 1.0

    pruned: bool = False
    prune_reason: str | None = None


class BranchPortfolio(BaseModel):
    """
    Active set of counterfactual futures for one decision.
    """

    portfolio_id: str

    decision_id: str

    base_world_revision: int
    base_branch_id: str

    candidates: tuple[BranchCandidate, ...]

    branch_width_limit: int
    simulation_depth_limit: int

    best_branch_id: str | None = None

    confidence_gap: float | None = None

    status: str

    created_at: str
    updated_at: str


class SimulationRequest(BaseModel):
    proposal: Proposal

    base_world_revision_ref: WorldRevisionRef

    depth: int

    width: int

    reasoning_budget: ReasoningBudget

    scope: CognitiveScope


class SimulationResult(BaseModel):
    branch: BranchCandidate

    generated_signals: tuple[WorldSignal, ...]

    predicted_quality: dict[str, float]

    created_at: str


class BranchSimulator(Protocol):
    """
    Counterfactual reality engine.

    Simulation never mutates canon.
    """

    async def simulate(
        self,
        request: SimulationRequest,
    ) -> SimulationResult:
        ...

    async def extend(
        self,
        branch_id: str,
        additional_depth: int,
        budget: ReasoningBudget,
    ) -> SimulationResult:
        ...

    async def compare(
        self,
        portfolio: BranchPortfolio,
    ) -> BranchPortfolio:
        ...


# =====================================================================
# ARBITRATION
# =====================================================================

class ArbitrationRequest(BaseModel):
    decision: DecisionFrame

    proposals: tuple[Proposal, ...]

    branch_portfolio: BranchPortfolio | None

    disagreements: tuple[CognitiveDisagreement, ...]

    workspace_view: WorkspaceView

    reasoning_budget: ReasoningBudget


class ArbitrationResult(BaseModel):
    arbitration_id: str

    decision_id: str

    selected_proposal_id: str | None

    rejected_proposal_ids: tuple[str, ...]

    requires_more_cognition: bool

    requested_cognition: tuple[CognitiveRequest, ...] = ()

    confidence: float
    uncertainty: float

    rationale: str

    evidence_refs: tuple[EvidenceRef, ...]


class CognitiveArbitrator(Protocol):
    """
    Decides between competing cognitive conclusions/proposals.

    It is distinct from QC:
      arbitration = "which option?"
      QC          = "is this option good enough?"
    """

    async def arbitrate(
        self,
        request: ArbitrationRequest,
    ) -> ArbitrationResult:
        ...


# =====================================================================
# COGNITIVE EXECUTIVE
# =====================================================================

class ExecutiveInput(BaseModel):
    workspace_id: str

    new_signal_ids: tuple[str, ...] = ()

    completed_result_ids: tuple[str, ...] = ()

    completed_simulation_ids: tuple[str, ...] = ()

    world_revision_ref: WorldRevisionRef

    reason: str


class PlannedInvocation(BaseModel):
    invocation: CognitiveInvocation

    priority: float

    dependencies: tuple[str, ...] = ()

    may_run_parallel: bool = True


class ExecutivePlan(BaseModel):
    plan_id: str

    workspace_id: str

    reasoning_policy_decision: ReasoningPolicyDecision

    planned_invocations: tuple[PlannedInvocation, ...]

    simulation_requests: tuple[SimulationRequest, ...]

    cognitive_requests_deferred: tuple[str, ...]

    cognitive_requests_rejected: tuple[str, ...]

    ready_for_arbitration: tuple[str, ...]

    ready_for_commit_validation: tuple[str, ...]

    rationale: str


class CognitiveExecutive(Protocol):
    """
    Executive function of Quantum.

    Owns:
        attention
        reasoning depth
        cognitive activation
        escalation
        stopping
        metacognition

    Does NOT:
        render
        write canonical world state
        schedule GPU workers directly
    """

    async def plan(
        self,
        input: ExecutiveInput,
    ) -> ExecutivePlan:
        ...

    async def integrate_result(
        self,
        result: CognitiveResult,
    ) -> WorkspacePatch:
        ...

    async def evaluate_cognitive_request(
        self,
        request: CognitiveRequest,
        workspace: CognitiveWorkspace,
    ) -> bool:
        ...

    async def should_continue_reasoning(
        self,
        decision: DecisionFrame,
        workspace: CognitiveWorkspace,
    ) -> bool:
        ...

    async def escalate_reasoning(
        self,
        decision: DecisionFrame,
        reason: str,
    ) -> ReasoningBudget:
        ...


# =====================================================================
# EXECUTION ORCHESTRATOR
# =====================================================================

class ExecutionHandle(BaseModel):
    execution_id: str

    invocation_id: str

    state: str

    worker_id: str | None = None

    started_at: str | None = None
    completed_at: str | None = None


class ExecutionBatchResult(BaseModel):
    handles: tuple[ExecutionHandle, ...]

    results: tuple[CognitiveResult, ...]

    failed_invocation_ids: tuple[str, ...]


class ExecutionOrchestrator(Protocol):
    """
    Systems/runtime layer.

    Executive says WHAT should execute.
    Orchestrator makes execution happen.
    """

    async def execute(
        self,
        invocation: CognitiveInvocation,
    ) -> CognitiveResult:
        ...

    async def execute_batch(
        self,
        invocations: Sequence[CognitiveInvocation],
    ) -> ExecutionBatchResult:
        ...

    async def cancel(
        self,
        execution_id: str,
    ) -> None:
        ...

    async def status(
        self,
        execution_id: str,
    ) -> ExecutionHandle:
        ...


# =====================================================================
# COMMIT MANAGER
# =====================================================================

class CommitRequest(BaseModel):
    proposal: Proposal

    selected_by_arbitration_id: str

    expected_world_revision: int

    authority: AuthorityEnvelope

    qc_certification_ref: Ref

    trace_id: str


class CommitValidation(BaseModel):
    valid: bool

    current_world_revision: int

    stale: bool

    authority_valid: bool

    preconditions_valid: bool

    rules_valid: bool

    qc_valid: bool

    violations: tuple[dict[str, Any], ...]

    requires_rebase: bool


class CommitReceipt(BaseModel):
    commit_id: str

    proposal_id: str

    world_event_refs: tuple[Ref, ...]

    previous_world_revision: int
    new_world_revision: int

    new_snapshot_ref: Ref

    emitted_signal_ids: tuple[str, ...]

    commit_hash: str

    committed_at: str


class CommitManager(Protocol):
    """
    ONLY normal gateway from cognition into canonical World State.
    """

    async def validate(
        self,
        request: CommitRequest,
    ) -> CommitValidation:
        ...

    async def rebase(
        self,
        proposal: Proposal,
        onto_world_revision: int,
    ) -> Proposal:
        ...

    async def commit(
        self,
        request: CommitRequest,
    ) -> CommitReceipt:
        ...


# =====================================================================
# COGNITIVE TRACE / LEARNING
# =====================================================================

class CognitiveTrace(BaseModel):
    """
    Complete provenance of how Quantum reached a decision.
    """

    trace_id: str

    originating_signal_ids: tuple[str, ...]

    initial_world_revision: int

    scope: CognitiveScope

    decision_ids: tuple[str, ...]

    invocation_ids: tuple[str, ...]

    operator_ids: tuple[str, ...]

    cognitive_result_ids: tuple[str, ...]

    branch_portfolio_ids: tuple[str, ...]

    proposal_ids: tuple[str, ...]

    selected_proposal_id: str | None = None

    arbitration_ids: tuple[str, ...] = ()

    commit_id: str | None = None

    total_reasoning_cost: float = 0.0
    total_latency_ms: int = 0

    downstream_quality: dict[str, float] = {}

    repair_count: int = 0
    downstream_invalidation_cost: float = 0.0

    final_reward: float | None = None

    created_at: str
    closed_at: str | None = None


class OperatorExperience(BaseModel):
    """
    Learning record answering:

        Under conditions X,
        operator O was used,
        costing C,
        and produced eventual value V.
    """

    experience_id: str

    trace_id: str

    invocation_id: str

    operator_id: str
    operator_version: str

    domain: CognitiveDomain

    signal_types: tuple[str, ...]

    scope_kind: ScopeKind

    decision_type: str | None

    world_feature_fingerprint: str

    reasoning_level: ReasoningLevel

    prior_uncertainty: float
    posterior_uncertainty: float

    direct_quality_delta: float | None = None

    downstream_quality_delta: float | None = None

    failure_probability_delta: float | None = None

    repair_cost_avoided: float | None = None

    future_option_value: float | None = None

    reasoning_cost: float
    latency_ms: int

    was_selected_by_policy: bool

    was_shadow_execution: bool = False

    counterfactual_baseline_ref: Ref | None = None

    estimated_marginal_utility: float | None = None

    final_reward: float | None = None

    created_at: str


# =====================================================================
# OPERATOR SELECTION LEARNING
# =====================================================================

class OperatorSelectionContext(BaseModel):
    signal_types: tuple[str, ...]

    scope_kind: ScopeKind

    decision_type: str | None

    salient_entity_types: tuple[str, ...]

    uncertainty: float
    novelty: float
    blast_radius: float
    irreversibility: float

    current_reasoning_level: ReasoningLevel

    already_invoked_operator_ids: tuple[str, ...]

    world_feature_fingerprint: str

    workspace_feature_fingerprint: str


class OperatorUtilityPrediction(BaseModel):
    operator_id: str

    expected_quality_delta: float

    expected_failure_risk_reduction: float

    expected_repair_cost_avoided: float

    expected_future_option_value: float

    expected_reasoning_cost: float
    expected_latency_ms: int

    expected_utility: float

    confidence: float


class OperatorSelectionPolicy(Protocol):
    """
    Learns which OPTIONAL reasoning operators are worth invoking
    under a particular world-state / signal constellation.

    Hard correctness operators are outside learned control.
    """

    policy_id: str
    version: str

    async def rank(
        self,
        context: OperatorSelectionContext,
        candidate_operator_ids: Sequence[str],
    ) -> tuple[OperatorUtilityPrediction, ...]:
        ...

    async def record_experience(
        self,
        experience: OperatorExperience,
    ) -> None:
        ...

    async def should_explore(
        self,
        context: OperatorSelectionContext,
    ) -> bool:
        ...

    async def select_shadow_operator(
        self,
        context: OperatorSelectionContext,
        candidate_operator_ids: Sequence[str],
    ) -> str | None:
        ...
What the Cognitive Workspace really is

The CognitiveWorkspace is much more important than a scratchpad. It is the shared working memory of the polycognitive entity.

The World Model might know ten million things. L9 may remember millions of historical facts. The Workspace contains the tiny subset Quantum is actively manipulating right now:

WORLD MODEL
everything currently true
       │
       │ projection
       ▼
COGNITIVE WORKSPACE
what Quantum is actively thinking about
       │
       ├── salient entities
       ├── current objectives
       ├── important signals
       ├── hypotheses
       ├── unresolved questions
       ├── candidate events
       ├── branch portfolio
       ├── disagreements
       ├── requested cognition
       ├── reasoning budget
       └── current confidence

That gives you a huge amount of leverage.

Without it:

Narrative thinks
    ↓
result disappears into next prompt

Character thinks
    ↓
result disappears

Epistemic thinks
    ↓
result disappears

With it:

Narrative conclusion ─┐
Character conclusion ─┼──► shared active thought
Epistemic conclusion ─┤
Cinematic conclusion ─┘

That is what turns independent model calls into one accumulating cognition process.

The Workspace also creates incremental cognition

This connects directly to the compiler architecture.

Suppose Cinematic Cognition concluded:

Candidate B works best as a silent reaction shot.

based on:

Aria trust=.31
Eva knows signal origin
receiver owned by Aria

Then somebody changes:

room lighting

That cognitive result is still valid.

Don't rerun it.

But if:

Aria trust .31 → .91

changes, the result's dependencies intersect that update.

World state change
      ↓
Workspace staleness analysis
      ↓
only dependent cognition invalidated
      ↓
rerun Character/Cinematic reasoning

So we get incremental reasoning, not merely incremental compilation.

That could become a massive cost advantage.

Cognitive Scope should also drive concurrency

Suppose three operations are active:

Narrative cognition
scope = episode 7 story branch
writes = hypothetical narrative

Sound cognition
scope = episode 6 scene 12
writes = sound design

Production cognition
scope = episode 6 shot 217
writes = manufacturing strategy

Their scopes do not conflict.

All three run concurrently.

Now:

Character cognition
scope = episode 7 scene 4
writes = hypothetical character action

can also run concurrently with Narrative Cognition as long as both write only to branches/workspace.

The commit path handles serialization later.

That gets you the high-velocity cognition you described:

low-risk cognitive functions continue firing while strategic cognition is deeply contemplating a consequential choice.

WorldSignal becomes the nervous system

This is probably one of the highest-leverage classes in the entire architecture.

Canonical state itself shouldn't invoke cognition constantly.

Changes create signals.

             NEW WORLD STATE
                    │
                    ▼
             Signal Detectors
                    │
        ┌───────────┼────────────┐
        ▼           ▼            ▼
 GOAL_BLOCKED   TRUST_DROP   PROMISE_READY
        │           │            │
        └───────────┼────────────┘
                    ▼
              WorldSignalBus
                    │
                    ▼
               SaliencePolicy
                    │
                    ▼
            CognitiveExecutive

Example:

signal_type: NARRATIVE.OPPORTUNITY_CONVERGENCE

subjects:
  - aria
  - eva
  - receiver
  - signal_origin
  - promise_17

metrics:
  severity: .22
  salience: .96
  urgency: .71
  novelty: .82
  confidence: .93
  estimated_downstream_impact: .89

The Executive sees that and says:

This is not routine.

Raise:
ROUTINE → DELIBERATIVE

Activate:
narrative.promise_intersection
character.policy_evaluation
epistemic.information_choreography

Branch width:
2 → 8

Simulation depth:
0 → 4

That's attention leading to deeper cognition automatically.

How learned operator selection works

This is where the system begins learning how to think.

Suppose over 4,000 historical decisions Quantum observes this constellation:

GOAL_BLOCKED
+
KNOWLEDGE_ASYMMETRY
+
FRAGILE_RELATIONSHIP

And its experience records show:

                               marginal value

blocked_intent_analysis             +.08
information_holder_analysis         +.14
relationship_emotional_cost         +.31
promise_intersection                +.19
connector_prop_analysis             +.17
physical_constraint_search          +.01

For the next similar problem:

predictions = await operator_policy.rank(
    context=current_context,
    candidate_operator_ids=eligible_operators,
)

and receives:

relationship_emotional_cost       utility +.37
promise_intersection              utility +.25
connector_prop_analysis           utility +.21
physical_constraint_search        utility -.03

The Executive invokes the first three.

It skips the fourth.

That isn't because a prompt told Quantum:

Remember to think about relationships.

It learned:

When reality looks like this, relationship analysis has historically created better downstream outcomes.

🔥

The learning target should be marginal value, not correlation

A naïve system might say:

Promise analysis appeared in lots of good scenes, therefore run it constantly.

Bad.

We want to estimate:

How much better was the result
BECAUSE we invoked this operator?

So use several sources of evidence:

real production outcomes
+
repair rates
+
downstream QC
+
shadow execution
+
offline ablation
+
counterfactual reruns

Example:

Actual cognition:
A + B + C
final quality = .94

Offline ablation:
A + B
quality = .82

Estimated marginal utility of C ≈ +.12

Now the learning is much stronger.

Cognitive cascades make autonomy qualitatively different

This is probably the part I'm most excited about in the architecture.

Initial condition:

WorldSignal:
GOAL_BLOCKED

Narrative cognition discovers:

The blocker is information.
Eva possesses it.

That creates:

CognitiveRequest:
relationship analysis

Relationship cognition discovers:

Accessing Eva is emotionally expensive because of betrayal.

That causes:

promise analysis

Promise cognition discovers:

Eva promised three episodes ago never to lie again.

Graph convergence emits:

NARRATIVE.OPPORTUNITY_CONVERGENCE .97

Executive responds:

reasoning depth ↑

Now:

character cognition
epistemic cognition
narrative cognition

run concurrently.

Epistemic cognition notices:

We do not need Eva to tell Aria the truth.

Aria only needs to observe evidence that Eva recognizes the receiver.

Cinematic cognition gets activated:

Could this information transfer happen visually?

It answers:

Yes.

Close insert:
Eva's hand hesitates when receiver enters frame.

Reaction:
Aria notices.

No dialogue required.

Performance cognition adds:

Eva suppresses recognition.

Acoustic cognition adds:

Drop score.
Foreground receiver click.

And suddenly:

Narrative
+
Character
+
Relationship
+
Epistemic
+
Cinematic
+
Performance
+
Sound

have jointly authored one moment.

No one of those subsystems contained the scene.

Quantum contained the scene.

That is the difference between:

many agents collaborating

and:

one intelligence thinking polycognitively.

The complete runtime center now looks like:

                         WORLD MODEL
                              │
                              ▼
                        WORLD SIGNALS
                              │
                              ▼
                       ATTENTION SYSTEM
                              │
                              ▼
                    COGNITIVE EXECUTIVE
                              │
              ┌───────────────┼───────────────┐
              │               │               │
        reasoning depth   operator policy   scope
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                    COGNITIVE WORKSPACE
                              │
       ┌──────────┬───────────┼────────────┬──────────┐
       ▼          ▼           ▼            ▼          ▼
   narrative   character  epistemic    cinematic  acoustic
       │          │           │            │          │
       └──────────┴───────────┼────────────┴──────────┘
                              ▼
                      cognitive cascade
                              │
                              ▼
                         PROPOSALS
                              │
                              ▼
                     BRANCH SIMULATION
                              │
                              ▼
                       ARBITRATION
                              │
                              ▼
                             QC
                              │
                              ▼
                      COMMIT MANAGER
                              │
                              ▼
                          REDUCER
                              │
                              ▼
                      NEW WORLD STATE
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
            new signals              cognitive trace
                                           │
                                           ▼
                                        learning
                                  ┌────────┼────────┐
                                  ▼        ▼        ▼
                               salience  depth   operators

That is the runtime contract I would build around now. The World Model gives Quantum persistent reality; the Workspace gives it a mind in motion; WorldSignals give it a nervous system; the CognitiveExecutive gives it executive function; and the learning contracts let that executive function become more efficient and more intelligent with experience.

Worked for 31s

Yes. We’ve covered the brain, but not yet all of the things that keep that brain sane, grounded, efficient, and improvable over years.

The biggest remaining gaps I see are these:

Creator Constitution / Objective Model — We have creative.yaml, but Quantum also needs an explicit representation of what it is optimizing for. Not just “make a good film,” but creator taste, hard prohibitions, originality preference, emotional ambition, tolerance for ambiguity, pacing preferences, continuity priority, series/IP goals, etc. This becomes the stable north star against which the Cognitive Executive evaluates decisions. Otherwise a sufficiently autonomous system can become internally coherent while drifting away from what you consider good.
Quantum Self-Model — A real intelligence needs to know its own capabilities. Quantum should maintain a machine-readable model of itself: available cognitive operators, renderer capabilities, model versions, known weaknesses, reliability statistics, cost profiles, context limits, provider availability, historical performance, and confidence calibration. Then it can reason: “I can solve this reliably with deterministic compositing,” or “my current video stack has a 28% failure rate on multi-character hand interactions; redesign before rendering.” This is different from production experience: it is Quantum’s current belief about what Quantum can do.
Perception and Information-Flow Engine — We modeled Knowledge, but not yet the machinery that mechanically determines how knowledge is acquired. If Eva whispers something, who can hear it? If Aria sees a reflection, does she notice it? Can a security camera observe the event? Is a character looking in the right direction? Is the signal encrypted? This should be something like WorldEvent → PerceptionEngine → Observation → Attention → Knowledge/Belief update. Without it, knowledge acquisition is still partially hand-waved. For mysteries and dramatic irony, this is huge.
State Ownership / Derived-State Semantics — We need to decide which pieces of state may be directly mutated and which must be derived. For example, I would not allow a writer to arbitrarily do aria.trust_eva = 0.21. Instead, events occur—betrayal, rescue, confession—and a Relationship State Engine derives the new trust state. Same for stress, suspicion, reputation, physical fatigue, perhaps even certain affordances. Otherwise agents can “teleport” psychological state just as easily as they could teleport a prop.
Narrative Value Function — Branch simulation tells us what can happen, but we still need a rigorous contract for what makes one valid branch better than another. It must be multi-objective and non-compensatory: causal strength, character integrity, emotional effect, thematic movement, surprise, promise/payoff management, audience information trajectory, future option value, production feasibility, originality. A branch cannot compensate for catastrophic character incoherence simply by having great spectacle. This should become one of the most important contracts in the system.
Explicit Causal Model — Graph connectivity is not automatically causality. We should distinguish RELATED_TO, ENABLES, MOTIVATES, CAUSES, PREVENTS, NECESSARY_FOR, and SUFFICIENT_FOR. For serious counterfactual simulation, Quantum eventually needs something closer to a structural causal model: “If Event X had not happened, would Y still have occurred?” That enables stronger branch comparison, retcon analysis, story debugging, and causal credit assignment.
Temporal + Concurrent World Execution — Our reducer is currently easiest to imagine as sequential events, but reality contains overlapping events. Aria walks while Eva decodes while the reactor heats while a transmission propagates. We need durations, scheduled events, interruptibility, simultaneous effects, conflict resolution and atomic multi-entity transactions. The World Model ultimately needs a proper event scheduler, not merely an ordered log.
Cognitive Workspace Lifecycle — We defined the Workspace, but not its memory-management policy. It cannot grow forever. Quantum needs cognitive garbage collection: salience decay, eviction, consolidation, duplicate-hypothesis merging, question closure, branch pruning, compression, and promotion of useful conclusions into durable memory. Think of this as working-memory management. Without it, the “shared mind” eventually becomes an enormous cluttered scratchpad.
Cognitive Cascade Control — Cascades are powerful enough to create a new problem: infinite thinking. Narrative requests Character, Character requests Epistemic, Epistemic requests Narrative, and Quantum spends forever contemplating a door opening. We need recursion limits, cycle detection, novelty thresholds, hysteresis, marginal-value stopping rules, request deduplication, and “already sufficiently answered” detection. The Executive needs to know both when to think harder and when to stop thinking.
Simulation Fidelity Ladder — Not every counterfactual deserves the same simulation fidelity. We should have levels such as symbolic state transition, relational/psychological simulation, full narrative branch simulation, cinematic simulation, and perhaps expensive production feasibility tests. Quantum can cheaply eliminate 80% of branches symbolically, deeply simulate the last few, and only render prototypes for the finalists. This is probably one of the biggest compute multipliers available.
Learning Governance / Anti-Self-Deception — Once Quantum learns its own reasoning policy, we have a dangerous possibility: it could learn from its own biased judges and become increasingly confident in bad habits. We need frozen evaluation sets, shadow policies, holdouts, policy versioning, rollback, offline counterfactual evaluation, calibration tests, adversarial cases and independent quality benchmarks. The system must distinguish “my internal critic likes this” from “this policy demonstrably improves downstream outcomes.”
Signal and Operator Ontology — WorldSignal and ReasoningOperator are now core primitives, which means their taxonomy cannot become an uncontrolled collection of strings. We need versioned registries, semantic definitions, parent/child relationships, compatibility rules and migrations. For example, EPISTEMIC.KNOWLEDGE_ASYMMETRY may have subtypes like SECRET, FALSE_BELIEF, STALE_KNOWLEDGE, DECEPTION, AUDIENCE_CHARACTER_SPLIT. This becomes the vocabulary Quantum uses to think about its own cognition.
Cognitive Capability Routing — CognitiveModule should not equal one model. The same operator could have multiple implementations: deterministic graph analysis, small fast LLM, deep reasoning model, multimodal model, statistical classifier. The Orchestrator needs a capability registry that answers: “Which implementation is best for this operator at this reasoning depth under the current budget?” This lets models come and go without changing the cognitive architecture.
Transactional Resilience / Recovery — Autonomous operation needs brutal reliability. Exactly-once event commits, idempotency keys, snapshot verification, crash recovery, replay, branch cleanup, dead-letter queues, stale-work cancellation, corrupted-artifact detection, provider retry semantics and deterministic rebuilds. A two-hour provider outage should pause a production branch, not corrupt the universe. A machine restart should reconstruct exactly where Quantum was.
Verification Harness — We need property-based and adversarial testing of the runtime itself. Random event sequences should never violate invariants. Replaying the same event stream must produce the same state hash. Hypothetical branches must never leak into canon. A character should never gain knowledge without an information path. Retcons should invalidate exactly the expected dependencies. Cognitive operators need synthetic worlds where the correct narrative opportunity is known. This is how we know the architecture works rather than merely sounding sophisticated.
Canon/Asset Embodiment Layer — We have discussed the Asset Foundry, but the refined architecture makes its importance clearer. A persistent entity like Aria needs persistent embodiment: identity references, approved visual variants, voice identity, motion identity, proportions, expressive range, damage states, costumes, possibly behavior signatures. The World Model says qchar_aria; the Embodiment layer answers how that entity becomes image, motion and sound at a specific coordinate. This is the bridge between reusable fictional IP and reusable production assets.
Autonomy Metrics — We should define what “getting more intelligent” actually means. Useful measures would include world-contradiction rate, pre-render prevention rate, QC failure rate, repair blast radius, average reasoning cost per accepted decision, branch regret, cognitive operator marginal utility, percentage of decisions resolved reflexively/routinely/deliberatively, signal precision, false-signal rate, human intervention count, continuity error density, and quality improvement per production. Otherwise “learning” becomes anecdotal.

The three I think are easiest to underestimate are Perception, State Ownership, and the Self-Model.

Perception gives us:

WORLD EVENT
    ↓
Who could perceive it?
    ↓
Who actually attended to it?
    ↓
What did they observe?
    ↓
What did they infer?
    ↓
What do they now know/believe?

State ownership gives us:

EVENTS cause psychology

instead of:

writer sets psychology

And the Self-Model gives us:

Quantum knows the world
+
Quantum knows its characters
+
Quantum knows filmmaking
+
Quantum knows what Quantum itself is good and bad at

That last one is a major step toward a genuinely adaptive system.

There is also a deeper conceptual refinement hiding underneath all of this:

WORLD MODEL
    = model of fictional reality

SELF MODEL
    = model of Quantum's own capabilities/state

CREATOR MODEL
    = model of what you value

AUDIENCE MODEL
    = model of what the viewer perceives/believes/feels

PRODUCTION MODEL
    = model of how reality can be manufactured

Those five models together give the Cognitive Executive enough grounding to answer:

What is true? What do I want? What will the audience experience? What am I capable of? What should I do next?

That may be the next big architectural layer above everything we've built: Quantum does not operate from one model—it operates from a coordinated model-of-world, model-of-self, model-of-creator, model-of-audience, and model-of-production.

And that starts looking like the complete cognitive foundation for the system.

Audience model should be compiled/reduced from the target market. One line input should be sufficient.

How can production model be easily defined?  Ideally from creative yaml input single egress.

Self model should be self maintained and updated never authored by human and updated in real time ensuring all capabilities are utilized.

That leaves only  the creative one relying on me. And I’d like to have it derived from the creative yaml so it must be revised - my values some will be fixed across all some will change. Yaml trumps fixed in case I want to deviate from or update existing values. Ie reduce graphic quality to match a 90’s retro style teenage mutant ninja turtles vibe or max cinematic space setting or virtual reality with artificial intelligence beings.
Worked for 25s

Yes. I would now collapse the architecture around one human-authored semantic source and four compiled/runtime models:

                         YOU
                          │
                    conversation
                          │
                          ▼
                CreativeIntakeAgent
                          │
                          ▼
                    creative.yaml
                          │
                    ONLY PROJECT-
                    SPECIFIC HUMAN
                       AUTHORITY
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
   Creator Model     Audience Model   Production Intent
          │               │                │
          └───────────────┼────────────────┘
                          ▼
                  quantum.studio.yaml
                          │
                          │
                          ▼
                    Runtime joins
                          │
                          ▼
                     Self Model
                 machine-maintained
                          │
                          ▼
                 Production Model(t)

The important refinement is:

Creator Model, Audience Model, and Production Intent are compiled from creative.yaml. Self Model is compiled from Quantum itself. Production Model is reduced from both.

That gives you almost exactly the one-input system you want.

1. The four models

I'd define them this way:

CREATOR MODEL
"What does the creator want this project to be?"

AUDIENCE MODEL
"What viewer experience are we designing for?"

SELF MODEL
"What can Quantum reliably do right now?"

PRODUCTION MODEL
"Given the desired film and Quantum's current capabilities,
how should this film actually be manufactured?"

Their authorities are very different.

Creator Model
    ← creator authority

Audience Model
    ← target-market compiler

Self Model
    ← observed machine reality

Production Model
    ← planning/reduction of the above
2. Revise creative.yaml

I agree it needs one more level of formalization.

I'd add four sections relevant here:

creative:

  creator:
    ...

  target_market:
    ...

  experience:
    ...

  production_intent:
    ...

But the creator does not have to fill these manually.

The Intake Agent constructs them from conversation.

You could literally say:

“Make a 16-minute cinematic sci-fi short about artificial beings living inside a VR civilization, aimed at sophisticated adult sci-fi viewers. I want max visual quality.”

And it becomes hundreds of lines of structured semantics.

3. Creator Model: persistent defaults + project overrides

This solves your “some fixed, some variable” requirement cleanly.

There are really two creator layers:

PersistentCreatorProfile
             +
ProjectCreatorOverrides
             ↓
       CreatorModel

Formula:

CreatorModel(project)
    =
Reduce(
    StudioCreativeDefaults,
    PersistentCreatorProfile,
    creative.yaml
)

With precedence:

creative.yaml explicit project value
            >
Persistent Creator Profile
            >
Studio Creative Defaults
            >
agent inference

So yes:

Project creative.yaml always trumps your normal creative preferences.

Except for non-creative hard platform invariants such as security, schema validity, etc.

4. Example: your normal preference

Suppose Quantum's persistent Creator Profile says:

visual_preferences:

  image_quality:
    default: cinematic_max

  spatial_detail:
    default: very_high

  lighting:
    default: physically_rich

  animation:
    default: fluid

  production_value:
    default: premium

Most projects inherit that.

But then you say:

“This one should look like a gritty 1990s Saturday-morning cel-animated action cartoon. Limited animation is intentional.”

creative.yaml might contain:

creator:

  project_overrides:

    visual_fidelity:
      strategy: stylized_reduction
      authority: CREATOR_EXPLICIT

    animation_language:
      temporal_smoothness: deliberately_limited
      pose_emphasis: strong
      hold_frames: encouraged

    rendering:
      linework: bold_inked
      shading: limited_cel
      texture: analog_print
      color_registration:
        precision: intentionally_imperfect

    quality_definition:
      note: >
        Higher photorealistic fidelity is NOT higher quality
        for this project. Fidelity to the chosen retro
        animation language is the quality target.

This is extremely important.

The system must understand:

quality ≠ realism
quality ≠ maximum rendering complexity

Instead:

Quality = fidelity to creative intent.

🔥

So Quantum should not “improve” the project by turning it into photorealistic CGI.

5. Another project can completely override it

You say:

“Maximum cinematic space setting. Artificial-intelligence beings inside a physically impossible virtual reality.”

Then:

creator:

  project_overrides:

    visual_fidelity:
      strategy: cinematic_max

    world_visual_complexity:
      level: extreme

    lighting:
      complexity: extreme
      volumetrics: premium

    environment:
      scale: monumental

    virtual_reality:
      physical_rule_freedom: high

    artificial_beings:
      embodiment_experimentation: high

    production_priority:
      visual_spectacle: very_high

Same Creator Profile.

Completely different effective Creator Model.

Perfect.

6. Persistent creator values should also be updateable through creative.yaml

You shouldn't maintain another config manually.

If you tell Quantum:

“From now on, unless I explicitly say otherwise, I always want dialogue to avoid exposition.”

The Intake Agent can encode:

creator_profile_updates:

  - path: dialogue.exposition_tolerance

    value: very_low

    scope: persistent

    authority: CREATOR_EXPLICIT

    provenance:
      conversation_turn: 184

After the project compiles successfully:

creative.yaml
      ↓
CreatorProfileUpdateCompiler
      ↓
PersistentCreatorProfile v18

You never edit that profile.

You just communicate intent.

7. Do not let Quantum silently rewrite your permanent preferences

Important boundary.

Quantum may infer:

You often seem to prefer endings with ambiguity.

But inference should remain:

candidate preference
confidence .74

not automatically:

GLOBAL CREATOR RULE

I'd make:

CREATOR_EXPLICIT
    → may become persistent

CREATOR_IMPLIED
    → usable locally

AGENT_INFERENCE
    → never silently promoted to persistent creator authority

That preserves your control.

8. Audience Model from one line

Absolutely.

You should be able to provide:

target_market: >
  Adult global sci-fi viewers who enjoy cerebral,
  emotionally serious speculative fiction.

That's sufficient input.

The AudienceCompiler expands it.

one-line target
      ↓
AudienceNormalizer
      ↓
Audience Archetype Resolver
      ↓
Genre Literacy Model
      ↓
Information Tolerance Model
      ↓
Emotional Expectation Model
      ↓
Pacing / Complexity Model
      ↓
AudienceModel

Example output:

audience_model:

  target:
    description: >
      Adult global science-fiction viewers who enjoy
      cerebral and emotionally serious speculative fiction.

  narrative:

    genre_literacy: high

    ambiguity_tolerance: high

    exposition_tolerance: low

    inference_expectation: high

    nonlinear_story_tolerance: medium_high

    reveal_sophistication: high

  emotional:

    patience_for_slow_burn: medium_high

    appetite_for_melancholy: high

    demand_for_character_grounding: high

  cinematic:

    visual_information_density: high

    tolerance_for_long_silence: medium_high

    expectation_of_visual_storytelling: high

  epistemic:

    expected_clue_subtlety: high

    preferred_explanation_after_reveal: low

    tolerance_for_unanswered_questions: medium_high

Then the Cold Viewer simulator instantiates audience perspectives from this model.

9. Audience Model should be probabilistic, not stereotypical

Important subtlety.

Don't encode:

18–24 year olds like fast cuts.

as truth.

Encode distributions:

pacing_preference:
  fast: .25
  medium: .55
  slow: .20

And perhaps several synthetic audience archetypes:

Primary Viewer
Genre Expert
Casual Viewer
Skeptical Viewer
Emotion-first Viewer

Then QC tests across them.

This is more realistic and avoids overfitting the film to a caricature of a market segment.

10. Production Model should be easy because it is mostly compiled

The Creator should not choose:

renderer X
image-to-video
layered composite
24 GPU jobs

That's Quantum's job.

Your creative input should contain only production-relevant intent.

Example:

production_intent:

  runtime:
    target_minutes: 16

  quality:
    priority: maximum

  visual_language:
    cinematic_scale: extreme

  continuity:
    tolerance: extremely_low

  character_identity:
    persistence_required: true

  deliverable:
    frame_rate: 24
    aspect_ratio: "2.39:1"

Everything else is compiled.

11. Split Production Intent from Production Model

This is important.

Don't put current renderer choices into the stable project spec.

Use:

ProductionIntent
    =
what the film demands

ProductionModel
    =
how Quantum can satisfy it right now

So:

creative.yaml
      ↓
ProductionIntentCompiler
      ↓
ProductionIntent

Then at runtime:

ProductionIntent
       +
CreatorModel
       +
AudienceModel
       +
World/Asset requirements
       +
SelfModel(t)
       ↓
ProductionModelReducer
       ↓
ProductionModel(t)

This is much cleaner.

12. Self Model is machine-maintained only

I strongly agree with your constraint.

Nobody should author:

quantum_is_good_at: ...

The Self Model should emerge from machine-observable evidence.

Formula:

SelfModel(t)
 =
Reduce(
    CapabilityDiscoveryEvents,
    ProviderState,
    RuntimeTelemetry,
    EvaluationResults,
    ProductionExperience,
    CalibrationResults
 )

No human edits.

13. Self Model has two different notions of capability

This matters.

Declared capability

The adapter/provider claims:

supports:
  image_conditioning
  video_generation
  10-second clips
Observed capability

Quantum has empirically learned:

identity consistency:
  .94

hand-object consistency:
  .71

dialogue closeup:
  .92

camera motion:
  .86

Observed evidence should dominate routing.

So:

class CapabilityState(BaseModel):

    capability_id: str

    implementation_id: str
    implementation_version: str

    declared_capabilities: tuple[str, ...]

    availability: float

    observed_reliability: dict[str, float]

    calibrated_confidence: float

    latency_distribution: dict

    cost_model: dict

    context_limits: dict

    known_failure_modes: tuple[str, ...]

    suitable_task_features: tuple[str, ...]

    unsuitable_task_features: tuple[str, ...]

    last_observed_at: str
14. “Ensure all capabilities are utilized”

I would slightly refine this:

Ensure all capabilities are discoverable and considered when relevant.

Not literally used.

A capability registry should prevent Quantum from accidentally ignoring a tool it possesses.

provider/tool appears
       ↓
Capability Discovery
       ↓
Capability Manifest
       ↓
Self Model
       ↓
Capability Graph
       ↓
Cognitive/Production routing

If tomorrow you add a new:

facial-animation model

its adapter advertises:

capabilities:

  - facial_performance
  - phoneme_conditioning
  - expression_control

constraints:

  maximum_duration_s: 12

modalities:
  input:
    - audio
    - face_reference

  output:
    - video

Quantum sees it automatically.

Production cognition can start comparing it with existing strategies.

No prompt update.

No director-agent rewrite.

🔥

15. Self Model should change in real time

Imagine:

10:00
Renderer A available
reliability .93

10:12
provider degradation detected

10:13
failure rate jumps

Self Model changes:

RendererA.availability .99 → .63

hand_interaction reliability .88 → .54

That emits:

SELF.CAPABILITY_DEGRADED

Production cognition automatically replans uncommitted shots.

No human.

16. The Production Model becomes dynamic

Example:

Creative requirement:

Aria must precisely hold receiver in right hand.

Yesterday Self Model says:

Renderer A:
right-hand object reliability = .96

Production Model:

use Renderer A directly

Tomorrow model update causes:

reliability = .62

Same film intent.

New Production Model:

canonical keyframe
+
pose conditioning
+
layered prop composite

The Creator Model did not change.

World Model did not change.

ShotIR did not change.

Only:

how Quantum manufactures reality

changed.

Exactly what we want.

17. One egress from creative.yaml

I think the clean architecture is:

                creative.yaml
                      │
                      ▼
            PROJECT MODEL COMPILER
                      │
       ┌──────────────┼──────────────┐
       ▼              ▼              ▼
 CreatorModel   AudienceModel  ProductionIntent
       │              │              │
       └──────────────┼──────────────┘
                      ▼
             quantum.studio.yaml

So quantum.studio.yaml becomes the single stable project egress.

It contains:

project:

  creative_model:
    ...

  creator_model:
    ...

  audience_model:
    ...

  production_intent:
    ...

  world_seed:
    ...

  story_contract:
    ...

  quality_contract:
    ...

But not volatile machine status.

18. Keep Self Model OUT of quantum.studio.yaml

Very important.

If quantum.studio.yaml says:

Renderer X v4

then your creative project becomes coupled to ephemeral infrastructure.

Bad.

Instead:

quantum.studio.yaml
        │
        │ stable project requirements
        ▼
Production Planner
        ▲
        │ live capability state
        │
     SelfModel(t)
        │
        ▼
production.model / manifest

So:

quantum.studio.yaml
=
what we intend to make

production.model
=
how Quantum currently intends to make it

Huge distinction.

19. I would also separate Production Model from Production Manifest

Three levels:

PRODUCTION INTENT
"Maximum quality; identity continuity critical."

        ↓

PRODUCTION MODEL
"For these kinds of shots use these manufacturing strategies."

        ↓

PRODUCTION MANIFEST
"qshot_081 candidate 2 is currently rendering on worker 17."

So:

ProductionIntent
    = requirements

ProductionModel
    = strategy

ProductionManifest
    = execution state

Beautifully clean.

20. Creator Model should compile a QualitySemantics

This is how your retro example gets handled correctly.

Suppose persistent default:

technical_detail = high
motion_fidelity = high

But project says:

1990s cel-animation language

Creator Model compiler derives:

quality_semantics:

  highest_quality_means:

    - consistent character drawing
    - intentional limited animation
    - expressive key poses
    - period-authentic linework
    - clean silhouette readability
    - controlled color palette
    - period-appropriate compositing

  does_not_mean:

    - photorealism
    - maximum frame interpolation
    - physically perfect lighting
    - volumetric realism
    - modern CG smoothness

Then QC judges the film against the correct quality manifold.

🔥

That prevents one of the nastiest failure modes in generative media:

optimizing the wrong definition of “better.”

21. Creator Model should separate values from expressions

Another subtle improvement.

You may have a stable value:

clarity of creative intention

But its expression changes.

For a mystery:

clarity ≠ explaining everything

For comedy:

clarity may require faster setup/payoff

So Creator Model could distinguish:

values:

  intentionality:
    importance: 1.0

  emotional_truth:
    importance: .96

  visual_coherence:
    importance: .94


project_expression:

  intentionality:
    manifests_as:
      - deliberate ambiguity
      - clue fairness
      - controlled withholding

  visual_coherence:
    manifests_as:
      - retro cel consistency

That's much more robust than a flat preference list.

22. The unified reduction stack

I think this is the final clean form:

                     CREATIVE.YAML
                          │
          ┌───────────────┼─────────────────┐
          │               │                 │
          ▼               ▼                 ▼
 Persistent Creator   Target Market   Creative/Production
      Defaults            Seed              Intent
          │               │                 │
          ▼               ▼                 │
    CreatorModel     AudienceModel          │
          │               │                 │
          └───────────────┼─────────────────┘
                          ▼
                 quantum.studio.yaml
                          │
                          │
                     runtime joins
                          │
                          ▼
                       SelfModel
                 machine-maintained
                          │
                          ▼
                ProductionModel(t)
                          │
                          ▼
                production.manifest

And separately:

World Model
    ↓
what is true

Creator Model
    ↓
what should this project mean/be

Audience Model
    ↓
what viewer experience we're targeting

Self Model
    ↓
what Quantum can currently do

Production Model
    ↓
how to turn desired reality into media
23. That leaves exactly one human variable

This is perhaps the nicest result:

                    HUMAN
                      │
                  CREATIVE
                    INTENT
                      │
                      ▼
                creative.yaml
                      │
      ┌───────────────┼─────────────────┐
      ▼               ▼                 ▼
 what creator       audience          project
    wants           target            demands
      │               │                 │
      └───────────────┼─────────────────┘
                      ▼
                    QUANTUM
                      │
      ┌───────────────┼─────────────────┐
      ▼               ▼                 ▼
 understands      knows itself       knows world
     intent         dynamically       persistently
      │               │                 │
      └───────────────┼─────────────────┘
                      ▼
                 thinks / simulates
                      │
                      ▼
                    acts
                      │
                      ▼
                    learns

So humans specify essentially:

what should exist and what should it feel like?

Quantum derives:

Who is it for?
What exactly does “quality” mean here?
What world must exist?
How should the narrative evolve?
Which cognitive faculties should reason about it?
How deeply should it reason?
What can Quantum currently manufacture reliably?
Which tools should it use?
How should failures alter future strategy?

And I would make one principle explicit in the architecture:

creative.yaml has highest authority over project-specific creative semantics; persistent creator preferences act only as defaults. Self Model has highest authority over claims about Quantum’s current capabilities. Production Model may adapt implementation strategy freely, but may never reinterpret creative intent merely to fit current tooling.

That boundary is critical. If Quantum cannot currently manufacture the desired film faithfully, the correct response of the system is change strategy, increase reasoning, decompose differently, or surface a capability gap internally—not quietly change your movie.

Creator model must have a strong established baseline. I’d no overrides in yaml use those

Same for audience model. It’s not only derived from target market that was my mistake. An entertained versus cheered up versus blown away are all different experiences.

Target market compiler is more on the business side which must influence design and production decisions. I don’t wanna just make what’s cool to me it has to be cool to many and impress Netflix and Amazon executives (not the back end the product and It marketability)

What persistent defaults can we establish to make the system exemplary without inputting a detailed canon each time.

I wanna be the next Steve Jobs and found the next insane original disruptor animation studio with a new way of making finished product. But without the long hours and giving myself cancer and burning myself out.

Scenario: I’m at a resort and feel inspired. I have a 1-2 hour chat with a creative agent. Make a yaml. Pass it to system -> mvp -> review feedback -> mvp2 -> review feedback -> Mvp3 -> lock -> full episode -> review feedback x2-3->lock->full season/feature film

This is sooooo important -> Quality = fidelity to creative intent.

🔥

So Quantum should not “improve” the project by turning it into photorealistic CGI.

—-
Can’t wait to make this one:

Maximum cinematic space setting. Artificial-intelligence beings inside a physically impossible virtual reality.”

——

Completely different effective Creator Model=max flexibility -> leverage ❤️❤️❤️

6/7-Multiple profiles?-> kiddie cartoons like Gabby’s dollhouse; love death robots style; educational content


That’s what I’m talking about :

one-line target
      ↓
AudienceNormalizer
      ↓
Audience Archetype Resolver
      ↓
Genre Literacy Model
      ↓
Information Tolerance Model
      ↓
Emotional Expectation Model
      ↓
Pacing / Complexity Model
      ↓
AudienceModel

—-

ProductionIntent
    =
what the film demands

ProductionModel
    =
how Quantum can satisfy it right now
💕💕💕
Worked for 32s

Yes. I’d refine the architecture in exactly that direction.

The new principle is:

You should provide vision, not configuration. Quantum should arrive with an exceptional creative baseline, infer the correct audience/product/production implications, and only require you to specify what makes this project different.

And I would remove the notion of an explicit project_overrides: block from creative.yaml. That was too configuration-like.

creative.yaml should simply describe the project. The compiler knows that explicit project semantics outrank defaults.

1. The new model stack

I would now make the stack:

                  STUDIO CREATIVE CONSTITUTION
                     exceptional fixed baseline
                              │
                 PERSISTENT CREATOR BASELINE
                       your durable taste
                              │
                              ▼
                         creative.yaml
                    this project's identity
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
       CREATOR MODEL     AUDIENCE MODEL   PRODUCT-MARKET MODEL
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                      PRODUCTION INTENT
                              │
                              │     LIVE SELF MODEL
                              │    "what Quantum can do"
                              │            │
                              └──────┬─────┘
                                     ▼
                            PRODUCTION MODEL
                       "how to make this film now"
                                     │
                                     ▼
                         production.manifest

There are therefore five different questions:

Creator Model:
What constitutes the right creative result?

Audience Model:
What should the intended audience experience?

Product-Market Model:
What makes this concept compelling and viable as a product?

Self Model:
What can Quantum actually do right now?

Production Model:
Given all of the above, how should Quantum manufacture it?

That separation is extremely clean.

2. Strong baseline: the StudioCreativeConstitution

This is what prevents every new idea from starting from intellectual zero.

You should not have to tell Quantum every time:

Characters should be coherent.
Don't write generic exposition.
Pay things off.
Make shots intentional.
Respect the audience.
Sound should matter.

Those are studio-level expectations.

I would establish one persistent, versioned:

StudioCreativeConstitution

that every project inherits.

It defines what Quantum Animation Studio considers exemplary filmmaking, regardless of style.

The baseline I would encode includes:

Creative intentionality — every major storytelling, visual, performance and sound choice must have a reason; accidental complexity is not quality.
Intent-relative quality — quality means fidelity to the intended aesthetic and experience, never automatic photorealism, smoothness, spectacle, complexity or expense.
Originality — derive from principles, references and creative intent; do not converge toward generic genre averages or imitation.
Causal narrative integrity — important events arise from prior world state, character intent, pressure, rules or intentionally introduced external forces.
Character integrity — behavior emerges from psychology, knowledge, beliefs, relationships, abilities and circumstances; surprising behavior requires causal support.
Audience respect — trust viewers to infer; avoid unnecessary explanation, repetition and condescension.
Setup/payoff discipline — meaningful promises are tracked, developed and deliberately paid, transformed or intentionally left unresolved.
Information intentionality — what characters know, what audiences know and when each discovers it are designed rather than accidental.
Visual storytelling — important narrative meaning should use behavior, composition, blocking, objects, lighting, motion and editing rather than dialogue alone.
Performance truth — dialogue, silence, subtext, physical behavior and timing must arise from character state.
World coherence — physical, technological, social and dramatic rules remain internally consistent.
Cinematic economy — prefer choices that accomplish multiple functions simultaneously: character + plot + theme + visual meaning.
Contrast and modulation — pacing, emotion, scale, sound density and visual intensity should breathe rather than remain uniformly maximal.
Identity continuity — persistent characters, environments and important objects remain recognizable across shots, episodes and years.
Sound as storytelling — sound is not decoration; environment, character, emotion and narrative information should all influence the acoustic design.
No filler — scenes, shots and lines should earn their presence.
Ending consequence — endings should result from what came before and meaningfully alter how the viewer understands or feels about the story.
Reusable-world thinking — when appropriate, create characters, places, relationships and unresolved potential capable of generating future stories.
Production-aware creativity without production capture — creativity may exploit manufacturing strengths, but tooling limitations may not silently redefine the intended film.
Deliberate deviation — any of the above may be violated when the violation is intentional and serves the project.

That is your default brain.

No detailed canon required.

3. Then add CreativeModeProfile

This addresses your Gabby's Dollhouse / adult anthology / educational examples.

The Constitution stays largely unchanged.

But its expression changes dramatically.

Studio Constitution
        +
CreativeModeProfile
        ↓
appropriate definition of excellence

For example:

PREMIUM_ADULT_CINEMATIC
PRESCHOOL_IMAGINATIVE
FAMILY_ADVENTURE
EDUCATIONAL_STORYTELLING
ADULT_COMEDY
EXPERIMENTAL_ART
CINEMATIC_SCIFI
ACTION_ANIMATION

These are not style presets.

They are cognitive priors.

Preschool profile

Could emphasize:

clarity                     very high
character readability       very high
emotional safety            high
visual appeal               high
repetition utility          medium/high
language complexity         low
plot complexity             low/medium
threat intensity            tightly controlled
warmth                      high
learning-through-pattern    high

The system still demands:

character integrity
visual intentionality
world coherence
originality

It just expresses those qualities differently.

Premium adult cinematic profile
subtext                     very high
ambiguity tolerance         high
visual inference            high
emotional complexity        high
exposition tolerance        low
cinematic composition       extremely high
thematic density            high
reveal sophistication       high
world complexity            high
Educational profile
learning objective accuracy     hard constraint
concept retention               very high
misconception prevention        very high
narrative engagement            high
cognitive load management       high
clarity                         very high
delight                         high

Now educational content isn't:

Lecture + cartoon.

It is:

Narrative optimized simultaneously for understanding and entertainment.

4. Profiles should be automatically selected

You shouldn't normally specify:

profile: PREMIUM_ADULT_CINEMATIC

You say:

“A cinematic 18-minute story for adults about two artificial beings discovering their universe is a simulation.”

Compiler determines:

creative_profile_resolution:

  dominant:
    profile: PREMIUM_ADULT_CINEMATIC
    weight: 0.58

  secondary:
    profile: CINEMATIC_SCIFI
    weight: 0.31

  tertiary:
    profile: EXPERIMENTAL_ART
    weight: 0.11

Profiles can blend.

That's much more powerful than one enum.

5. Creator Model becomes flexible without becoming empty

I'd calculate:

EffectiveCreatorModel
    =
Reduce(
    StudioCreativeConstitution,
    PersistentCreatorBaseline,
    CreativeModeProfiles,
    creative.yaml
)

But there is no concept in the YAML of:

"override this"

The user simply says what they want.

Example:

“I want deliberately crunchy late-90s cel animation, low frame count, bold poses, imperfect analog texture.”

The compiler knows those project facts have higher specificity than:

default_motion_fidelity = high

and resolves:

high-quality motion
    ↓
does NOT mean more frames

high quality
    ↓
means excellent timing,
excellent poses,
excellent held drawings,
excellent intentional limited animation

This is exactly why:

Quality = fidelity to creative intent.

needs to become a constitutional invariant.

6. Audience Model: you caught an important missing dimension

Target market is not enough.

These are radically different:

Audience:
12-year-old children

Desired experience A:
comforted

Desired experience B:
laughing uncontrollably

Desired experience C:
awe-struck

Desired experience D:
motivated to learn

Desired experience E:
emotionally devastated

Same demographic.

Completely different film.

So Audience Model should be compiled from at least:

WHO?
Target audience

+

WHAT SHOULD HAPPEN TO THEM?
Target audience experience

+

WHAT KIND OF VIEWER ARE THEY?
Genre/media literacy

+

UNDER WHAT CONDITIONS?
Format / context / attention environment
7. AudienceExperienceModel

I'd make desired experience first-class.

Conceptually:

audience_experience:

  primary_outcome:
    awe: 0.95

  secondary_outcomes:
    curiosity: 0.88
    emotional_connection: 0.76
    existential_wonder: 0.81

  avoid:
    confusion_without_payoff: high
    emotional_detachment: high
    exposition_fatigue: high

  desired_trajectory:

    opening:
      curiosity: rising

    first_third:
      immersion: high

    midpoint:
      uncertainty: high

    climax:
      awe: extreme
      emotional_intensity: high

    ending:
      wonder: high
      contemplative_aftertaste: very_high

That becomes usable by Story Architect, Director, Editor, Composer and QC.

8. Your one-line input can still be enough

You could say:

“Adults who love ambitious science fiction. I want them completely blown away and thinking about it for two days.”

That's enough.

Compiler:

one-line audience/experience
        ↓
AudienceNormalizer
        ↓
Audience Archetype Resolver
        ↓
Genre Literacy Model
        ↓
Experience Target Compiler
        ↓
Information Tolerance Model
        ↓
Emotional Trajectory Compiler
        ↓
Pacing / Complexity Model
        ↓
Viewer Simulation Profiles
        ↓
AudienceModel

🔥

And if you don't even specify that?

Quantum should infer from the project and apply a reasonable profile, while preserving lower confidence.

9. Add a Product-Market Model

This is the piece your “Netflix/Amazon executive” comment reveals.

You don't just care:

Do I think this is cool?

You also care:

Is this a compelling entertainment product with broad enough appeal, differentiation, repeatability, and perceived quality that serious buyers/viewers would immediately understand why it matters?

That's distinct from Audience Model.

I would create:

ProductMarketModel

It evaluates the product design.

Not ad campaigns.

Not sales outreach.

Not back-office marketing.

The actual thing you're making.

10. Product-Market Model asks different questions

For example:

Is the premise immediately legible?

Is there a strong hook?

Is the concept distinctive?

Is the emotional proposition clear?

Is there a meaningful audience?

Does it have repeatable story-generation potential?

Can its characters become durable IP?

Does the world create episode/season expansion capacity?

Does the concept travel globally?

Does it depend excessively on culturally specific exposition?

Does the first minute demonstrate the promise of the project?

Can one image communicate the show's identity?

Would a short excerpt make someone want to see more?

Does the project have a recognizable identity among competing content?

Can the production method sustain the expected quality across a season?

Those are creative-product questions.

They belong inside Quantum Animation Studio.

11. The Product-Market Model should influence—not dominate

Important authority hierarchy:

Creator intent
       │
       ▼
Product-Market intelligence
       │
       ▼
better realization of intent

Not:

market prediction
       ↓
destroy originality

If Product-Market cognition concludes:

The first four minutes don't demonstrate the core promise.

That is useful.

It can propose:

Move the first impossible-VR phenomenon earlier.

But it should not silently decide:

Add a talking animal because broad audiences like them.

💣

12. Market-fit becomes another cognitive domain

We may actually add:

quantum.cognition.product

with operators such as:

product.concept_legibility
product.hook_strength
product.distinctiveness
product.audience_breadth
product.format_fit
product.franchise_optionality
product.global_accessibility
product.first_minute_promise
product.repeatability
product.identity_strength

It participates in branch evaluation.

But it has no unilateral creative authority.

13. Audience vs Product is now clear
AUDIENCE MODEL

"If this person watches,
what do we want them to perceive,
understand, feel and remember?"

versus:

PRODUCT-MARKET MODEL

"Does this film/show have a strong enough proposition,
identity, accessibility and repeatable value
to earn attention in the real entertainment market?"

Both matter.

Very different models.

14. Production Intent gets simpler, not bigger

I think this is the most elegant part.

Production Intent shouldn't be a giant authored document.

It can mostly be compiled from:

CreatorModel
+
AudienceModel
+
ProductMarketModel
+
Story/World requirements

For your VR-AI project:

Creator says:
maximum cinematic awe

Audience says:
sophisticated adult sci-fi
high ambiguity tolerance
desired experience = blown away

Product says:
world identity must be instantly recognizable
premium visual differentiation required

World says:
physically impossible spaces
AI beings
mutable reality

        ↓

ProductionIntent

Compiler derives something like:

production_intent:

  perceived_quality:
    target: flagship

  visual_identity:
    uniqueness_requirement: extreme

  spatial_complexity:
    required: extreme

  impossible_geometry:
    required: true

  character_identity:
    continuity: critical

  cinematic_scale:
    target: monumental

  camera:
    freedom: high

  motion_language:
    project_specific: true

  sound:
    world_defining: true

  production_strategy:
    allow_hybrid_methods: true

  deterministic_elements:
    maximize_where_semantically_invisible

  quality_priority:
    visual_identity: critical
    continuity: critical
    cinematic_impact: critical

You didn't specify any of that.

Quantum inferred it from what the movie demands.

💕💕💕

15. And then Production Model does the ugly work
ProductionIntent
     +
live SelfModel
     +
ShotIR / Assets / World State
     ↓
ProductionModel

For every scene/shot it determines:

manufacturing method
renderer
conditioning
asset strategy
number of takes
QC requirements
failure prevention
render priority
estimated risk
fallback strategy

No human.

16. Your actual interaction model becomes incredibly small

This is where the architecture should ultimately end up.

Your resort scenario:

YOU
at resort
inspired
   │
   ▼
1–2 hour conversation
   │
   ▼
CreativeIntakeAgent
   │
   ▼
creative.yaml v1

From that point:

creative.yaml
     ↓
Development Compiler
     ↓
CreatorModel
AudienceModel
ProductMarketModel
World/Characters
ProductionIntent
QualityContract
     ↓
Quantum generates MVP₁

You watch it.

Then:

YOU
"Aria feels too cold.
The world is incredible.
The reveal happens too quickly.
I want the ending more haunting."

Review Agent determines:

"Aria too cold"
    → creative semantic feedback

"world incredible"
    → positive validation

"reveal too quickly"
    → reveal/audience trajectory feedback

"ending more haunting"
    → experience-target feedback

Those become:

creative.yaml v2

Not random chat memory.

Then:

MVP₂
 ↓
feedback
 ↓
creative.yaml v3
 ↓
MVP₃
 ↓
CREATIVE LOCK
17. Then full episode

After MVP lock:

creative.lock
     ↓
full episode development
     ↓
animatic.lock
     ↓
production
     ↓
Episode Candidate 1

You review:

CreatorFeedback round 1
        ↓
minimum-blast-radius recompilation
        ↓
Episode Candidate 2

Again:

feedback
 ↓
Episode Candidate 3
 ↓
EPISODE LOCK

Then:

Persistent World
+
Character state
+
Production experience
+
learned audience/product knowledge
+
locked creative identity
        ↓
full season

🔥🔥🔥

18. Feedback itself needs classification

This is important to keeping your involvement enjoyable.

You should never have to tell Quantum:

Update creator_model.visual.foo.

You just react naturally.

The Review Agent classifies every statement into:

CREATIVE CHANGE
changes intended result

EXECUTION DEFECT
result failed existing intent

CREATOR PREFERENCE
potential persistent taste

PROJECT-SPECIFIC PREFERENCE
only applies here

POSITIVE SIGNAL
keep this

NEGATIVE SIGNAL
don't repeat this

AMBIGUOUS
retain for next evaluation

Example:

“The lighting here looks cheap.”

Probably:

EXECUTION DEFECT

Don't alter your creative identity.

But:

“I actually want the lighting deliberately cheap and fluorescent because this world is supposed to feel like a dead 1997 shopping mall.”

That's:

CREATIVE CHANGE

Huge distinction.

19. The system should minimize your cognitive labor

This connects directly to your burnout goal.

Your scarce resource should be:

taste and creative judgment.

Not:

project management
prompt engineering
renderer selection
continuity tracking
revision bookkeeping
shot scheduling
file management
QC triage
model evaluation

Quantum should consume those burdens.

Your loop becomes essentially:

IMAGINE
   ↓
TALK
   ↓
WATCH
   ↓
FEEL / JUDGE
   ↓
TALK
   ↓
WATCH BETTER VERSION

That is the human API.

Everything else is machine territory.

20. Multiple persistent profiles: absolutely

I think we need profile families, not one global taste profile.

For example:

Quantum Studio Constitution
        │
        ├── Premium Adult Animation Profile
        │
        ├── Preschool Profile
        │
        ├── Family Profile
        │
        ├── Educational Profile
        │
        ├── Experimental Profile
        │
        └── Cinematic Sci-Fi Profile

And separate Audience profiles:

AudienceProfileLibrary

And Product profiles:

ProductProfileLibrary

So a project may resolve:

Creator:
  .55 cinematic_scifi
  .30 premium_adult
  .15 experimental

Audience:
  sophisticated_adult_scifi

Experience:
  awe + curiosity + existential unease

Product:
  premium_streaming_short
  reusable_world_ip

A preschool project could be completely different while using the same Quantum intelligence.

That's huge leverage. ❤️

21. The quality equation becomes project-relative

I would literally encode this:

Quality(project)
    =
Fidelity(
    realized_artifact,
    EffectiveCreativeIntent(project)
)

subject to hard universal floors:

coherence
intentionality
technical validity
identity consistency
audience suitability

So:

1990s limited animation
executed intentionally and beautifully
= high quality

ultra-smooth CGI that violates intended aesthetic
= low quality

And:

minimalist black-and-white experimental piece
= potentially flagship quality

gigantic cinematic space opera
= potentially flagship quality

There is no single visual complexity axis.

That is maximum flexibility without losing a quality standard.

22. I would therefore revise the five-model architecture to six

We now have:

                     CREATIVE.YAML
                          │
                          ▼
                PROJECT MODEL COMPILER
                          │
       ┌──────────────────┼───────────────────┐
       ▼                  ▼                   ▼
 CREATOR MODEL      AUDIENCE MODEL    PRODUCT-MARKET MODEL
       │                  │                   │
       └──────────────────┼───────────────────┘
                          ▼
                  PRODUCTION INTENT
                          │
                          ▼
                     WORLD MODEL
                   project reality
                          │
                          │
                   ┌──────┴──────┐
                   │             │
                   ▼             ▼
              SELF MODEL    Production Intent
                   │             │
                   └──────┬──────┘
                          ▼
                  PRODUCTION MODEL
                          │
                          ▼
                       FILM

More precisely:

Creator Model      → what constitutes the right film
Audience Model     → what experience the viewer should have
Product-Market     → what makes it compelling as a product
World Model        → what is true in the fictional universe
Self Model         → what Quantum can currently do
Production Model   → how Quantum realizes the desired film

And there is still only one project-specific human source:

creative.yaml

Everything else is compiled, reduced, observed, simulated or learned.

That feels much closer to the end-state you’re describing: you can be somewhere beautiful, have the burst of inspiration, spend an hour or two expressing what you see in your head, and then hand the resulting semantic seed to an intelligence with an already-developed understanding of storytelling, audiences, product strength, production, quality, continuity, its own capabilities, and how to think harder when the decision actually deserves it.
