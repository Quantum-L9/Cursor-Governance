
-----
Yes. The architecture I would pursue is essentially:

**creative brief YAML → production compiler → shot DAG → parallel render farm → editorial timeline → audio mix → QC/repair loop → master MP4**

The important conceptual shift is that **Quantum Animation Studio should not be an “agent that makes a movie.”** It should be a production system that converts increasingly concrete intermediate representations into assets. Agents/models can make creative decisions inside stages, but the orchestration, state, timing, continuity, retry behavior, and final assembly should be deterministic software.

## 1. Treat the movie like compiled software

Your source file might be surprisingly small:

```yaml
project:
  id: last_signal
  title: The Last Signal
  runtime_seconds: 900
  fps: 24
  resolution: [1920, 1080]
  seed: 847221

creative:
  premise: >
    A maintenance android on an abandoned orbital station
    discovers that the final transmission from Earth is a love letter.

  genre:
    - science-fiction
    - drama

  tone:
    - intimate
    - melancholic
    - mysterious

  themes:
    - memory
    - loneliness
    - what survives us

  ending:
    type: bittersweet_twist

  visual_language:
    medium: cinematic stylized 3D animation
    lighting: high contrast practical lighting
    palette: cold cyan environments with warm amber memories
    camera: restrained, deliberate, cinematic

characters:
  - id: aria
    role: protagonist
    description: >
      Humanoid maintenance android, scratched white ceramic shell,
      expressive mechanical face, small amber status light.
    personality:
      - curious
      - methodical
      - quietly lonely

production:
  target_avg_shot_seconds: 5
  max_shot_seconds: 8
  takes_per_shot: 3
  shot_handles_frames: 12
  max_repair_attempts: 2

audio:
  dialogue: true
  ambience: true
  foley: true
  score: true
  target_lufs: -14

autonomy:
  allow_story_revisions: true
  allow_shot_revisions: true
  allow_asset_revisions: false
```

Then:

```bash
quantum render last_signal.yaml
```

eventually produces:

```text
build/last_signal/master.mp4
```

But internally, a lot happened.

Think of the pipeline as:

```text
project.yaml
    ↓
CreativeBible
    ↓
Screenplay
    ↓
ProductionBreakdown
    ↓
AssetBible
    ↓
DialogueAudio
    ↓
ShotPlan
    ↓
Animatic
    ↓
ShotRenders
    ↓
SelectedTakes
    ↓
Timeline
    ↓
SoundDesign + Music
    ↓
Mix
    ↓
QC / Repair
    ↓
master.mp4
```

Those intermediate representations are the real product.

---

## 2. Make `Shot` your fundamental execution unit

Trying to maintain coherence across a 20-minute generated clip is the wrong abstraction.

Generate **shots**.

At an average five seconds per shot:

```text
12 minutes ≈ 144 shots
24 minutes ≈ 288 shots
```

That gives you an embarrassingly parallel rendering problem.

A shot should be a strict data structure, not prose buried in an LLM conversation.

```python
from typing import Literal
from pydantic import BaseModel


class CameraSpec(BaseModel):
    framing: str
    lens_mm: int | None = None
    movement: str = "locked"
    subject: str | None = None


class DialogueCue(BaseModel):
    character_id: str
    audio_asset_id: str
    start_ms: int
    end_ms: int
    text: str


class Shot(BaseModel):
    id: str
    scene_id: str

    duration_ms: int
    transition_in: str = "cut"
    transition_out: str = "cut"

    location_id: str
    character_ids: list[str]

    visual_description: str
    action: str
    emotional_intent: str

    camera: CameraSpec

    character_reference_ids: list[str]
    environment_reference_id: str | None = None
    prop_reference_ids: list[str] = []

    dialogue: list[DialogueCue] = []

    continuity_from: str | None = None
    continuity_notes: str | None = None

    render_seed: int
```

For example:

```json
{
  "id": "sc04_sh017",
  "scene_id": "sc04",
  "duration_ms": 4300,
  "location_id": "observation_deck",
  "character_ids": ["aria"],
  "visual_description": "Aria stands before the dark observation window.",
  "action": "She raises one damaged hand toward the reflected Earth recording.",
  "emotional_intent": "recognition and grief",
  "camera": {
    "framing": "medium close-up",
    "lens_mm": 50,
    "movement": "slow push-in",
    "subject": "aria"
  },
  "character_reference_ids": [
    "asset://characters/aria/v4"
  ],
  "environment_reference_id": "asset://locations/observation_deck/v2",
  "continuity_from": "sc04_sh016",
  "render_seed": 81742
}
```

Now you've transformed filmmaking into something schedulable.

---

# 3. Audio should drive your timeline

A subtle but very important ordering decision:

**generate dialogue before final shot timing.**

Suppose the screenplay contains:

```text
ARIA
I kept waiting for someone to answer.
```

You synthesize that voice first.

Perhaps it becomes:

```text
00:00.000 → 00:03.760
```

Now your director knows that the reaction sequence has to accommodate at least 3.76 seconds.

You might produce:

```text
SHOT 104      1.8 sec
Aria looks toward receiver

SHOT 105      3.9 sec
ARIA: "I kept waiting for someone to answer."

SHOT 106      2.2 sec
Receiver status light goes dark
```

Instead of generating video and subsequently discovering the dialogue doesn't fit.

This also makes captions trivial because your dialogue system already owns precise timing.

---

# 4. Separate creative intelligence from execution

I'd create adapters around all generative systems.

```python
from typing import Protocol


class StoryModel(Protocol):
    async def generate_structured(
        self,
        system_prompt: str,
        input: dict,
        schema: type,
    ):
        ...


class ImageGenerator(Protocol):
    async def generate(
        self,
        *,
        prompt: str,
        references: list[str],
        seed: int,
    ) -> str:
        ...


class VideoGenerator(Protocol):
    async def generate(
        self,
        *,
        prompt: str,
        references: list[str],
        duration_ms: int,
        seed: int,
    ) -> str:
        ...


class SpeechGenerator(Protocol):
    async def synthesize(
        self,
        *,
        text: str,
        voice_id: str,
        performance: dict,
    ) -> str:
        ...


class MusicGenerator(Protocol):
    async def compose(
        self,
        *,
        description: str,
        duration_ms: int,
    ) -> str:
        ...
```

Quantum doesn't care who actually implements them.

That is critical because the underlying models will change constantly.

Your architecture stays:

```text
VideoGenerator
```

while implementation A, B or C can be swapped out.

---

# 5. Your orchestrator becomes relatively boring

And boring orchestration is good.

```python
async def render_project(spec: ProjectSpec):

    bible = await cached_task(
        "creative_bible",
        spec,
        create_creative_bible,
    )

    screenplay = await cached_task(
        "screenplay",
        bible,
        write_screenplay,
    )

    breakdown = await cached_task(
        "production_breakdown",
        screenplay,
        create_production_breakdown,
    )

    assets = await build_assets(
        spec,
        bible,
        breakdown,
    )

    dialogue = await render_dialogue(
        screenplay,
        assets.voices,
    )

    shots = await direct_episode(
        screenplay=screenplay,
        dialogue=dialogue,
        assets=assets,
    )

    animatic = await build_animatic(
        shots=shots,
        dialogue=dialogue,
        assets=assets,
    )

    shots = await revise_from_animatic(
        shots,
        animatic,
    )

    rendered = await render_all_shots(
        shots,
        assets,
    )

    selected = await select_best_takes(
        rendered,
        shots,
        assets,
    )

    timeline = await edit_episode(
        shots=shots,
        selected_takes=selected,
        dialogue=dialogue,
    )

    sound = await sound_design(
        timeline,
        screenplay,
    )

    score = await score_episode(
        timeline,
        screenplay,
    )

    master = await finish_episode(
        timeline,
        dialogue,
        sound,
        score,
    )

    return await quality_control(master)
```

The intelligence exists inside:

```python
write_screenplay()
direct_episode()
select_best_takes()
sound_design()
```

The overall system remains a state machine.

---

# 6. The asset bible solves a huge amount of continuity

Before rendering production footage, generate canonical representations of everything that matters.

You want concepts like:

```text
character:aria:v4
environment:observation_deck:v2
prop:receiver:v1
costume:aria_repair_harness:v1
```

And each should have structured metadata plus visual references.

Something like:

```json
{
  "id": "character:aria:v4",
  "physical": {
    "height_cm": 171,
    "shell": "matte off-white ceramic",
    "eyes": "dim amber",
    "damage": [
      "cracked right temple",
      "exposed left shoulder actuator"
    ]
  },
  "prohibited_variation": [
    "human skin",
    "hair",
    "different eye colors",
    "clean undamaged shell"
  ],
  "reference_images": [
    "front.png",
    "three_quarter.png",
    "profile.png",
    "full_body.png"
  ]
}
```

Your director shouldn't repeatedly describe Aria.

It should say:

```text
character_reference_ids:
    - character:aria:v4
```

This is analogous to referencing a shared library rather than copy/pasting its source into every function.

---

# 7. Generate multiple takes and let another model direct

For an important shot, don't assume generation #1 is production-ready.

```python
async def render_shot(shot, renderer, critic):

    takes = await asyncio.gather(*[
        renderer.generate(
            shot=shot,
            seed=shot.render_seed + i,
        )
        for i in range(3)
    ])

    scores = await critic.evaluate(
        shot_spec=shot,
        candidates=takes,
    )

    best = max(scores, key=lambda x: x.total)

    if best.total >= 0.85:
        return best

    repaired = await repair_shot(
        shot=shot,
        critique=best.problems,
    )

    return await render_shot(
        repaired,
        renderer,
        critic,
    )
```

The critic isn't asking:

> Is this a cool video?

It evaluates dimensions like:

```text
identity consistency        0.94
environment consistency     0.87
action correctness          0.91
composition                 0.82
camera instruction          0.97
temporal artifacts          0.71
continuity                  0.89
```

Then your repair planner can specifically address:

```text
temporal_artifacts < threshold
```

instead of regenerating randomly.

This is how I would define **autonomy** here: bounded corrective loops, not unrestricted agents chatting with each other.

---

# 8. Build an animatic before expensive final rendering

This could save enormous amounts of wasted computation.

Use cheap frames/stills plus dialogue:

```text
screenplay
    ↓
storyboards
    ↓
rough dialogue
    ↓
storyboards + camera movement
    ↓
900-second cheap animatic
```

Then let a critic inspect the entire episode for:

```text
pacing
scene duration
exposition density
visual repetition
dialogue gaps
establishing geography
emotional progression
ending impact
```

If scene 3 drags, change the **shot manifest**, not expensive finished footage.

Once the animatic passes:

```text
LOCK PICTURE PLAN
```

and expensive rendering begins.

This is basically applying traditional animation economics to generative animation.

---

# 9. Make rendering completely resumable

Never make:

```python
render_movie()
```

an atomic operation.

Every task should have an input hash.

Conceptually:

```python
def task_key(name: str, payload: object) -> str:
    data = canonical_json(payload)
    return sha256(
        f"{name}:{data}".encode()
    ).hexdigest()
```

Then:

```python
async def cached_task(name, payload, fn):
    key = task_key(name, payload)

    if artifact_store.exists(key):
        return artifact_store.load(key)

    result = await fn(payload)

    artifact_store.save(
        key=key,
        value=result,
    )

    return result
```

If shot 217 is bad, regenerating shot 217 should not touch the other 250 shots.

This becomes indispensable at featurette length.

---

# 10. Keep the final edit deterministic

Eventually all your AI output should stop being AI problems.

You have:

```text
sc01_sh001.mp4
sc01_sh002.mp4
sc01_sh003.mp4
...
dialogue.wav
ambience.wav
foley.wav
music.wav
captions.srt
```

Now the editor generates something like:

```json
{
  "tracks": {
    "video": [
      {
        "asset": "sc01_sh001.mp4",
        "start": 0,
        "duration": 4100
      },
      {
        "asset": "sc01_sh002.mp4",
        "start": 4100,
        "duration": 5200
      }
    ],
    "dialogue": [],
    "foley": [],
    "ambience": [],
    "music": []
  }
}
```

That can become an OpenTimelineIO-style timeline or your own timeline IR.

After that, ordinary media software takes over.

For example:

```bash
ffmpeg \
  -i picture.mp4 \
  -i dialogue.wav \
  -i foley.wav \
  -i ambience.wav \
  -i score.wav \
  -filter_complex "..." \
  -map 0:v \
  -map "[mixed_audio]" \
  -c:v libx264 \
  -c:a aac \
  master.mp4
```

You can do music ducking, fades, EQ, normalization, limiting, letterboxing and delivery encoding here without involving a model.

That's desirable.

---

# 11. I would structure the repo this way

```text
quantum/
│
├── cli.py
├── config.py
├── models/
│   ├── project.py
│   ├── screenplay.py
│   ├── shot.py
│   ├── assets.py
│   └── timeline.py
│
├── compiler/
│   ├── bible.py
│   ├── writer.py
│   ├── breakdown.py
│   ├── director.py
│   └── continuity.py
│
├── providers/
│   ├── language.py
│   ├── image.py
│   ├── video.py
│   ├── speech.py
│   ├── music.py
│   └── vision.py
│
├── production/
│   ├── assets.py
│   ├── dialogue.py
│   ├── shots.py
│   ├── animatic.py
│   └── renderer.py
│
├── editorial/
│   ├── timeline.py
│   ├── transitions.py
│   ├── captions.py
│   └── ffmpeg.py
│
├── audio/
│   ├── dialogue.py
│   ├── foley.py
│   ├── ambience.py
│   ├── score.py
│   └── mixer.py
│
├── qc/
│   ├── visual.py
│   ├── continuity.py
│   ├── audio.py
│   └── master.py
│
└── runtime/
    ├── dag.py
    ├── queue.py
    ├── cache.py
    ├── artifacts.py
    └── provenance.py
```

And builds look like:

```text
build/last_signal/
├── project.json
├── bible.json
├── screenplay.json
├── breakdown.json
│
├── assets/
│   ├── characters/
│   ├── locations/
│   └── props/
│
├── dialogue/
├── storyboard/
├── animatic/
│
├── shots/
│   ├── sc01_sh001/
│   │   ├── spec.json
│   │   ├── take_01.mp4
│   │   ├── take_02.mp4
│   │   ├── take_03.mp4
│   │   └── selected.json
│   └── ...
│
├── audio/
│   ├── dialogue.wav
│   ├── foley.wav
│   ├── ambience.wav
│   └── score.wav
│
├── timeline.json
├── subtitles.srt
└── master.mp4
```

That filesystem alone would make the system dramatically easier to debug.

---

# 12. The hardest engineering problem is actually continuity

Rendering video is increasingly commoditized.

The valuable IP in Quantum would be the **production intelligence around the models**.

Your continuity engine needs to understand facts such as:

```text
Shot 81:
ARIA holds receiver in RIGHT hand.

Shot 82:
camera crosses behind her.

Shot 83:
receiver must still be RIGHT hand.

Scene 6:
ARIA loses receiver.

Scene 9:
receiver therefore cannot magically reappear.
```

I would maintain a world-state ledger:

```python
class WorldState(BaseModel):
    scene_id: str

    character_locations: dict[str, str]
    character_costumes: dict[str, str]
    character_conditions: dict[str, list[str]]

    prop_locations: dict[str, str]
    prop_ownership: dict[str, str]

    environmental_state: dict[str, str]
```

The screenplay compiler produces state transitions:

```text
STATE 109

aria.location = engineering_bay
aria.right_hand = receiver
receiver.owner = aria

EVENT

aria drops receiver

STATE 110

aria.right_hand = empty
receiver.location = engineering_bay_floor
```

Now the shot director receives both:

```text
narrative intent
+
world state
```

That's a serious architecture advantage.

---

# 13. The deeper abstraction

I think Quantum ultimately wants three different graphs.

```text
NARRATIVE GRAPH

Character
   ↓
Goal
   ↓
Conflict
   ↓
Event
   ↓
State change
```

```text
PRODUCTION GRAPH

Scene
   ↓
Shot
   ↓
Asset references
   ↓
Render tasks
```

```text
TIMELINE GRAPH

Video clips
Dialogue clips
Foley
Ambience
Music
Transitions
       ↓
     Master
```

The language model moves you from:

```text
creative brief → narrative graph
```

The directing system moves:

```text
narrative graph → production graph
```

The render farm executes:

```text
production graph → media
```

The editor converts:

```text
media + production graph → timeline graph
```

FFmpeg converts:

```text
timeline graph → master.mp4
```

That division of responsibilities is clean enough that I think you could genuinely build it.

---

## Where I'd start

I would **not** start by trying to make a 12-minute movie.

Build the complete vertical stack for a **60-second short with 10–15 shots**.

The milestone is not “AI generated a cool clip.” The milestone is:

```bash
quantum render episode.yaml
```

with no human interaction produces:

```text
1. coherent script
2. recurring character
3. synthesized performances
4. 10–15 individually generated shots
5. coherent edit
6. synchronized dialogue
7. ambience + SFX
8. score
9. captions
10. normalized final MP4
```

Then make it 3 minutes.

Then 6.

Then 12.

What you'll discover is that **the core scaling challenge isn't generating more video; it's maintaining narrative, visual and physical state over hundreds of shots**.

And that's the interesting part of Quantum Animation Studio: it starts looking much less like a video-generation wrapper and much more like an **autonomous virtual animation studio operating against a typed production graph**.

----
Yes — those can be the “agents,” with one architectural qualification: I would make them **bounded production agents**, not free-roaming conversational agents.

```text
WriterAgent        → write_screenplay()
DirectorAgent      → direct_episode()
TakeSelectorAgent  → select_best_takes()
SoundAgent         → sound_design()
CriticAgent        → evaluate(...)
```

They should consume typed state, produce typed state, and have explicit authority boundaries.

And yes: **animatic ≠ storyboard**, although they are closely related.

```text
Storyboard = ordered still images showing intended shots

Animatic =
    storyboard frames
  + actual shot durations
  + cuts
  + camera approximations
  + dialogue
  + temporary sound/music
```

The animatic answers, “Does the episode actually work over time?” That makes it vastly more useful for autonomous production.

For Quantum Animation Studio, where **you are the only human and production itself is 100% autonomous**, the central technical problem becomes this:

# Persistent canonical state

Everything else is downstream of that.

To maintain narrative, visual, and physical consistency across hundreds of shots, Quantum fundamentally needs **one authoritative representation of reality** that every agent and renderer must obey.

I would divide that reality into five interacting state systems.

---

## 1. Narrative State

This represents what is true about the *story*.

Not pixels. Not prompts.

Things like:

```yaml
narrative_state:
  current_time: "day_3_22:14"

  mysteries:
    origin_of_signal:
      status: partially_revealed
      known_by:
        - aria

  character_arcs:
    aria:
      belief:
        initial: "Someone will eventually answer."
        current: "Nobody may be left."
      emotional_state:
        loneliness: 0.84
        hope: 0.23
        fear: 0.47

  audience_knowledge:
    knows_signal_is_from_earth: true
    knows_sender_identity: false

  unresolved:
    - sender_identity
    - why_station_was_abandoned
```

This prevents screenplay-level contradictions.

For example, the Director cannot stage Aria reacting to information she hasn't learned yet.

That means your story itself becomes a state machine:

```text
S0
 ↓ event
S1
 ↓ revelation
S2
 ↓ decision
S3
```

A scene isn't just prose.

It's:

```text
NarrativeState(before)
    +
events
    =
NarrativeState(after)
```

That is enormously powerful.

---

# 2. World / Physical State

This is what physically exists and where it is.

For example:

```yaml
world_state:
  aria:
    location: observation_deck
    pose: standing

    body:
      temple_crack: true
      left_arm:
        condition: damaged
        mobility: 0.55

    clothing:
      repair_harness: true

    inventory:
      right_hand: receiver
      left_hand: null

  receiver:
    owner: aria
    condition: functional
    battery: 0.18

  observation_deck:
    main_lights: offline
    emergency_lights: active
    window_shutters: open
```

Then shot 217 inherits that state.

If shot 217 contains:

```text
ARIA holding receiver in left hand
```

the validation system catches:

```text
CONSTRAINT VIOLATION

Expected:
aria.inventory.right_hand = receiver

Rendered:
aria.inventory.left_hand = receiver
```

This should trigger automatic repair/regeneration.

The model doesn't “remember.”

**Quantum remembers.**

That's the distinction.

---

# 3. Canonical Visual State

This is your shared library idea, and yes, it's one of the biggest scalability wins.

Every recurring entity gets a permanent identity.

```text
qasset://character/aria
qasset://location/station_observation_deck
qasset://prop/receiver
qasset://vehicle/shuttle_01
```

And versions:

```text
qasset://character/aria/base/v1
qasset://character/aria/damaged/v3
qasset://character/aria/post_repair/v1
```

A character asset would include much more than several pictures.

Something like:

```yaml
character:
  id: aria

  topology:
    height_cm: 171
    proportions: reference/proportions.json

  identity_features:
    shell_color: "#E8E3D7"
    eye_color: "#E79227"
    temple_crack: right

  reference_images:
    - front.png
    - rear.png
    - left_profile.png
    - right_profile.png
    - three_quarter.png
    - closeup.png

  expressions:
    neutral: neutral.png
    concerned: concerned.png
    grief: grief.png

  prohibited:
    - hair
    - human_skin
    - blue_eyes
    - symmetrical_temple

  voice:
    id: aria_voice_v1

  motion_profile:
    normal_walk: slow_precise
    damaged_walk: asymmetric_left
```

Now Aria can appear in:

```text
Short 001
Short 002
Season 1
Season 2
Feature film
Game
```

without redefining her.

That is how **a generated character becomes IP instead of a prompt**.

And yes, this is exactly why a hit can turn into a series.

---

# 4. Temporal State

This is easy to underestimate.

Quantum has to understand not only **what exists**, but **when it became true**.

Consider:

```text
Shot 101
Aria has clean face.

Shot 102
Explosion.

Shot 103
Aria gets soot on face.

Shot 104
Soot remains.

...

Shot 130
Aria washes face.

Shot 131
Soot no longer exists.
```

You need something effectively resembling event sourcing:

```text
EVENT 8182
type: explosion
affects:
  aria.face.soot = true

EVENT 8467
type: wash_face
affects:
  aria.face.soot = false
```

Then state at shot 120 can be reconstructed by replaying state transitions.

Conceptually:

```python
state_120 = replay(
    initial_state,
    events[:shot_120]
)
```

That provides both debugging and continuity.

You can ask:

> Why does Aria have a damaged shoulder in shot 217?

And Quantum can trace:

```text
Scene 2 Shot 31
    ↓
collision event
    ↓
left_shoulder.damage = true
    ↓
persists through scenes 3–8
```

This is much stronger than storing an increasingly enormous prompt.

---

# 5. Cinematic State

There's another kind of continuity that's neither narrative nor physical:

**film grammar.**

Quantum should know what the camera has established.

For example:

```yaml
cinematic_state:
  current_scene: observation_deck

  screen_direction:
    aria: left_to_right

  spatial_relationships:
    aria: left
    console: center
    observation_window: rear

  previous_shot:
    size: medium
    lens_mm: 50
    camera_height: eye

  coverage_available:
    wide_master: true
    aria_closeup: true
    console_insert: false
```

Otherwise autonomous editing will produce ugly things like:

```text
ARIA looking screen-left

CUT

ARIA apparently looking screen-left from the opposite side

→ accidental axis violation
```

or:

```text
wide
wide
wide
wide
wide
```

with monotonous visual rhythm.

Your Director needs a representation of:

```text
180° axis
screen direction
shot size
camera position
lens
eyelines
coverage
visual rhythm
```

That's production intelligence.

---

# The key architecture

These states converge into what I would call your:

# Quantum World Model

```text
                       ┌──────────────────┐
                       │ Narrative State  │
                       └────────┬─────────┘
                                │
 ┌──────────────────┐           │          ┌──────────────────┐
 │ Character/Asset  │───────────┼──────────│ Physical State   │
 │     Library      │           │          │ / World State    │
 └──────────────────┘           │          └──────────────────┘
                                │
                       ┌────────▼────────┐
                       │ Quantum World   │
                       │     Model       │
                       └────────┬────────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
           ┌───────▼────────┐       ┌────────▼────────┐
           │ Temporal State │       │ Cinematic State │
           └───────┬────────┘       └────────┬────────┘
                   │                         │
                   └────────────┬────────────┘
                                ↓
                         DirectorAgent
                                ↓
                            ShotSpec
                                ↓
                            Renderer
```

The Director should never receive only:

> “Generate a shot of Aria walking down the hall.”

It receives something closer to:

```text
Narrative intent
+
Current world state
+
Character asset references
+
Location asset references
+
Previous shot state
+
Desired next state
+
Cinematic constraints
+
Shot objective
```

Then generates.

---

# Every shot should have preconditions and postconditions

This is perhaps the most important implementation detail.

Shot 217:

```yaml
shot:
  id: s05_sh217

  narrative_goal:
    aria_discovers_receiver_is_dead

  preconditions:
    aria.location: comms_room
    aria.right_hand: receiver
    receiver.powered: true
    aria.emotion.hope: "> 0.2"

  action:
    - receiver_indicator_flickers
    - receiver_indicator_dies
    - aria_lowers_receiver

  postconditions:
    receiver.powered: false
    aria.emotion.hope: 0.05

  cinematic:
    framing: close_up
    subject: aria
    camera_motion: slow_push
```

The render is merely one visual realization of that transformation:

```text
WORLD STATE 216
       ↓
    Shot 217
       ↓
WORLD STATE 217
```

That lets you validate both sides.

---

# Then Critic becomes much more interesting

Your `Critic()` shouldn't be one general model.

I'd eventually implement something like:

```python
critics = [
    NarrativeCritic(),
    IdentityCritic(),
    PhysicalContinuityCritic(),
    CinematographyCritic(),
    TemporalArtifactCritic(),
    PerformanceCritic(),
    DialogueSyncCritic(),
]
```

They return structured evaluations:

```yaml
shot: s05_sh217

scores:
  identity: 0.97
  world_state: 0.92
  cinematography: 0.88
  performance: 0.91
  temporal_integrity: 0.61

violations:
  - type: temporal_artifact
    severity: high
    frames: [48, 79]
    description: receiver geometry mutates

decision:
  status: regenerate
  preserve:
    - camera
    - performance
    - lighting
  repair:
    - receiver_geometry
```

That's far better than:

```text
Critic: "I don't like take 2."
```

---

# And this is where multiple takes shine

For shot 217:

```text
                 ShotSpec
                    │
          ┌─────────┼─────────┐
          ↓         ↓         ↓
       Take A     Take B     Take C
          │         │         │
          └─────────┼─────────┘
                    ↓
                 Critics
                    ↓
              weighted scores
                    ↓
              TakeSelector
                    ↓
                Take B
```

If none passes:

```text
all takes fail
      ↓
failure classification
      ↓
modify generation constraints
      ↓
render new takes
```

No human.

---

# But don't let critics arbitrarily rewrite the movie

Important autonomy principle:

```text
Critic observes.
Planner decides repair.
Renderer executes repair.
```

Not:

```text
Critic rewrites whatever it wants.
```

For example:

```python
class Critique(BaseModel):
    violations: list[Violation]
    confidence: float


class RepairPlan(BaseModel):
    operation: Literal[
        "select_other_take",
        "rerender_shot",
        "adjust_prompt",
        "adjust_camera",
        "adjust_timing",
        "rebuild_scene",
    ]

    affected_shots: list[str]
```

This makes autonomy controlled and debuggable.

---

# State scopes are also essential

Not every fact should be handed to every shot.

You want hierarchical state:

```text
UNIVERSE
│
├── Series
│   │
│   ├── Season
│   │   │
│   │   ├── Episode
│   │   │   │
│   │   │   ├── Scene
│   │   │   │   │
│   │   │   │   └── Shot
```

For example:

### Universe state

```text
Earth was destroyed in 2197.
Androids require reactor charging.
```

### Series state

```text
Aria survived the station.
Marcus is missing.
```

### Episode state

```text
Aria currently believes Marcus is dead.
```

### Scene state

```text
Power is currently offline.
```

### Shot state

```text
Aria is holding the receiver.
```

Then your state resolver computes:

```python
shot_context = resolve(
    universe,
    series,
    episode,
    scene,
    shot
)
```

This is how you get a character that can live across **years of generated episodes**, not just one clip.

---

# You also need immutable IDs

Do not allow the system to identify concepts primarily using prose.

Bad:

```text
"the damaged white robot woman"
```

Good:

```text
character_id = qchar_000001
variant_id   = qchar_000001_damage_03
```

Similarly:

```text
qchar_000001    Aria
qloc_000014     Observation Deck
qprop_000031    Receiver
qscene_0081
qshot_0081_0042
qvoice_000003
```

This sounds mundane.

It's foundational.

Language changes.

IDs don't.

---

# The render manifest becomes your reproducibility contract

Shot 217 should be recreatable years later.

```yaml
shot_id: qshot_0217

inputs:
  world_state_hash: 082af...
  narrative_state_hash: f73cb...
  character_asset_version: aria@4
  location_asset_version: comms_room@2

generation:
  video_provider: provider_x
  model_version: v17
  seed: 871726
  prompt_hash: 17ff2...

output:
  take: 3
  asset_hash: ae781...

qc:
  version: qc_v6
  score: 0.934
  accepted: true
```

Now your studio can answer:

```text
Why does this shot exist?
Which inputs generated it?
Which model generated it?
What state was true?
Which take won?
Why did it win?
```

That is how an autonomous system stays manageable.

---

# The minimum system I would implement for the 60-second MVP

Don't build the entire ontology yet.

For your 10–15-shot first production, implement only:

```text
1. Character Bible
2. Location Bible
3. Prop Bible

4. NarrativeState
5. WorldState

6. SceneSpec
7. ShotSpec

8. immutable IDs

9. preconditions/postconditions

10. Character/reference injection

11. Three takes per shot

12. structured visual critic

13. automatic rerender

14. persistent artifact cache

15. deterministic timeline
```

That's enough to establish Quantum's architectural DNA.

---

# The fundamental loop

Ultimately, I would want Quantum Animation Studio to operate every shot through this exact loop:

```text
             CURRENT WORLD STATE
                      │
                      ↓
              Narrative Intent
                      │
                      ↓
                 Director
                      │
                      ↓
                  ShotSpec
                      │
          ┌───────────┴───────────┐
          ↓                       ↓
    State Validator          Asset Resolver
          │                       │
          └───────────┬───────────┘
                      ↓
                   Render
                      ↓
                 3–N Takes
                      ↓
                    QC
                 ↙      ↘
              FAIL      PASS
               │          │
             Repair       ↓
               │      Select Take
               └───────┐  │
                       │  ↓
                       │ COMMIT
                       │  │
                       └──┤
                          ↓
                NEXT WORLD STATE
                          ↓
                      Shot 218
```

That **COMMIT** concept matters.

Once shot 217 passes, its state transition becomes authoritative.

Very database-like.

```text
render → validate → commit
```

instead of:

```text
generate → hope
```

And that is probably the single sentence I'd use to define the core engineering philosophy of **Quantum Animation Studio**:

> **Treat autonomous filmmaking as a transactional state-transition system whose rendered frames are outputs of an authoritative cinematic world model.**

If you nail that layer at 60 seconds, the path from **15 shots → 50 → 150 → 300+** becomes mostly an orchestration and compute-scaling problem rather than the whole architecture collapsing under continuity errors.

----
**Yes: YAML → animatic should be the first major compilation target.**

I’d actually formalize the product interface this way:

```bash
quantum compile episode.yaml --target animatic
```

produces:

```text
build/episode/
    story.json
    world.json
    assets.json
    dialogue/
    shots.json
    storyboard/
    timeline.json
    animatic.mp4
    animatic.lock
```

Then only after that passes autonomous QC:

```bash
quantum render build/episode/animatic.lock
```

produces the expensive final movie.

That separation gives you something very similar to:

```text
source code       → intermediate executable      → optimized binary
episode.yaml      → animatic                     → master.mp4
```

## And yes: `l9-graphiti-memory` can simplify this substantially

But I would **not** make it the Quantum World Model itself.

The repository's architecture explicitly defines itself as the owner of governed memory contracts, canonical persistence, retrieval, curation and projection integration—and explicitly says that it **does not own a world model or agent execution**. That's a very good boundary for Animation Studio. ([GitHub][1])

I'd change our diagram to this:

```text
                         episode.yaml
                              │
                              ▼
                    ┌──────────────────┐
                    │ Quantum Compiler │
                    └────────┬─────────┘
                             │
                             ▼
                ┌────────────────────────┐
                │ Quantum Animation      │
                │ World Model            │
                │                        │
                │ NarrativeState         │
                │ PhysicalState          │
                │ CinematicState         │
                │ AssetState             │
                │ StoryClock             │
                └───────┬────────┬───────┘
                        │        │
        exact state     │        │ long-lived memory
                        │        │
               ┌────────▼──┐   ┌─▼──────────────────┐
               │ State     │   │ L9 Graphiti Memory │
               │ Reducer   │   │                    │
               │ + Snapshot│   │ temporal facts     │
               │ Store     │   │ relationships      │
               └───────────┘   │ history            │
                               │ conflicts          │
                               │ provenance         │
                               │ semantic recall    │
                               └─────────┬──────────┘
                                         │
                                         │ hydration
                                         ▼
                                  DirectorAgent
                                         │
                                         ▼
                                     ShotSpec
                                         │
                               ┌─────────▼─────────┐
                               │ Storyboard Render │
                               └─────────┬─────────┘
                                         ▼
                                      ANIMATIC
```

The distinction is:

> **World Model = what is true right now.**
>
> **L9 Memory = what has been true, why, when, according to whom, how it changed, and what related knowledge should be recalled.**

That's a powerful combination.

### Where your existing repo maps cleanly

| Animation problem            | L9 Memory fit      | What I would do                            |
| ---------------------------- | ------------------ | ------------------------------------------ |
| Narrative facts              | Excellent          | Store relationships/assertions             |
| Character canon              | Excellent          | Store canonical identity facts + versions  |
| Series continuity            | Excellent          | Persist across episodes/seasons            |
| Temporal changes             | Excellent          | Use temporal/supersession machinery        |
| Provenance                   | Excellent          | Know which story event created a fact      |
| Contradictions               | Excellent          | Surface canon conflicts                    |
| Agent context hydration      | Excellent          | Give Writer/Director only relevant history |
| Asset binary storage         | Wrong abstraction  | Store URI/hash only                        |
| Exact current physical state | Needs domain layer | Deterministic reducer/snapshot             |
| Exact cinematic state        | Needs domain layer | Shot/scene state structs                   |
| Frame/timeline data          | Wrong abstraction  | Timeline/OTIO-style IR                     |

The existing `MemoryRecord` already has several things we'd otherwise have to invent: immutable records, optional subject/predicate/object assertions, namespaces, metadata, evidence, confidence, references, supersession and conflict relationships. ([GitHub][2])

And its memory taxonomy already includes `identity`, `constraint`, `decision`, `episodic`, `semantic`, `procedural`, `observation`, and related classes. Those map unusually well to a long-running fictional universe. ([GitHub][3])

---

# Example: Aria gets injured

Suppose the story contains:

```text
Shot 31:
Explosion throws Aria against wall.
Her left shoulder actuator is damaged.
```

The **World Model** performs a deterministic transition:

```python
before = WorldState(
    aria=CharacterState(
        left_shoulder="functional"
    )
)

event = DamageEvent(
    character_id="aria",
    component="left_shoulder",
    condition="damaged",
    caused_by="qshot_0031"
)

after = reduce(before, event)
```

Giving:

```text
aria.left_shoulder = damaged
```

That state is exact.

No semantic search.

No LLM.

No graph inference.

---

Meanwhile, Quantum can persist semantic knowledge through L9 Memory:

```text
subject:   character:aria
predicate: has_condition
object:    damaged_left_shoulder
```

with metadata:

```json
{
    "series_id": "last_signal",
    "episode_id": "ep01",
    "scene_id": "sc02",
    "shot_id": "qshot_0031",
    "cause": "explosion",
    "world_event_id": "evt_8291"
}
```

Now five episodes later the Writer can ask effectively:

```text
What persistent injuries does Aria have?
```

and retrieve it.

The renderer doesn't need to search for the fact because:

```text
WorldState
```

already says she's damaged.

That's the architectural distinction I'd preserve.

---

# This makes Graphiti especially useful for a series

Imagine you've produced:

```text
Season 1    8 episodes
Season 2    8 episodes
Season 3    8 episodes
```

At 15 minutes each, you could easily have thousands of shots.

You absolutely do **not** want this:

```text
Director prompt =
    entire history of the universe
```

Instead:

```text
                          L9 Memory
                              │
           ┌──────────────────┼────────────────────┐
           │                  │                    │
           ↓                  ↓                    ↓
     Character facts    Relevant history    Relationships
           │                  │                    │
           └──────────────────┼────────────────────┘
                              ↓
                      bounded hydration
                              ↓
                    Director context
```

The repo already implements bounded hydration and retrieval that can combine canonical lexical/temporal retrieval with optional graph/semantic projections; importantly, those projections are rebuildable rather than the canonical truth. ([GitHub][1])

That philosophy aligns extremely well with Quantum.

---

# Bi-temporal memory has an interesting use here

`l9-graphiti-memory` explicitly distinguishes when a fact is valid from when it was recorded, through `valid_from`, `valid_to`, `recorded_at`, and related temporal coordinates. ([GitHub][4])

That's useful for canon.

Suppose Episode 7 reveals:

```text
Marcus was never actually dead.
```

Quantum previously had:

```text
aria believes Marcus is dead
```

Notice these are different truths:

```text
WORLD TRUTH
Marcus.status = alive

ARIA'S BELIEF
Marcus.status = dead

AUDIENCE KNOWLEDGE
Marcus.status = unknown
```

This leads me to an important addition to our architecture.

## Don't have just one Narrative State

Have perspectives:

```text
NarrativeState
│
├── ObjectiveWorld
│
├── AudienceKnowledge
│
└── CharacterKnowledge
    │
    ├── Aria
    ├── Marcus
    └── ...
```

Now:

```text
ObjectiveWorld:
    marcus.alive = true

AriaKnowledge:
    marcus.alive = false

AudienceKnowledge:
    marcus.alive = unknown
```

This is how you prevent a WriterAgent from accidentally giving a character knowledge they shouldn't possess.

And a temporal graph becomes extremely valuable here because those beliefs evolve.

---

# I would not store the actual asset library in Graphiti

Instead:

```text
                Character Canon
                      │
              ┌───────┴───────┐
              │               │
              ▼               ▼
         L9 Memory       Asset Registry
              │               │
        semantic facts    actual artifacts
                          │
                          ├── front.png
                          ├── profile.png
                          ├── voice.ref
                          ├── style.ref
                          ├── model.ref
                          └── embeddings/etc
```

Memory says:

```text
aria
  HAS_CANONICAL_ASSET
aria@v4
```

Asset Registry says:

```json
{
  "asset_id": "qchar_000001",
  "version": 4,
  "manifest_uri": "qasset://characters/aria/v4/manifest.json",
  "content_hash": "sha256:...",
  "status": "canonical"
}
```

The video renderer resolves the asset registry directly.

No retrieval uncertainty.

---

# `TemporalState` probably disappears as its own box

This is one change I'd make after seeing your existing memory architecture.

Originally we had:

```text
Narrative
Physical
Assets
Temporal
Cinematic
```

I'd refactor that to:

```text
                        Quantum World Model

               ┌─────────────────────────────┐
               │                             │
        NarrativeState                 PhysicalState
               │                             │
               ├──────────┐      ┌───────────┤
               │          │      │           │
         KnowledgeState   │      │      AssetState
                          │      │
                          ▼      ▼
                         StoryClock
                              │
                              ▼
                       CinematicState
```

**Time becomes a coordinate applying to all states**, rather than another independent state domain.

L9 Memory handles historical temporal knowledge.

The World Model handles exact current story position:

```python
class StoryClock(BaseModel):
    episode_id: str
    scene_index: int
    shot_index: int

    timeline_frame: int

    universe_time: datetime | None
```

That's cleaner.

---

# Then YAML → animatic looks like this

```text
episode.yaml
     │
     ▼
┌─────────────┐
│ Parse/Check │
└──────┬──────┘
       ▼
┌─────────────────┐
│ WriterAgent     │
│                 │
│ Story Graph     │
└───────┬─────────┘
        │
        ▼
┌─────────────────┐
│ Canon Resolver  │◄────────────── L9 Memory
└───────┬─────────┘
        │
        ▼
┌──────────────────┐
│ Initial World    │
│ Model            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Dialogue         │
│ performances     │
└────────┬─────────┘
         │ durations
         ▼
┌──────────────────┐
│ DirectorAgent    │◄────────────── L9 Memory
└────────┬─────────┘
         │
         ▼
     ShotSpecs
         │
         ▼
┌──────────────────┐
│ State Simulator  │
│                  │
│ validate every   │
│ transition       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Storyboard       │
│ generation       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Timeline Builder │
│                  │
│ storyboard       │
│ + dialogue       │
│ + temp FX        │
│ + temp score     │
└────────┬─────────┘
         │
         ▼
     animatic.mp4
         │
         ▼
    Critic swarm
         │
     FAIL│     │PASS
         │     ▼
         │ animatic.lock
         │
         └── targeted rewrite
```

That would be **MVP #1** for me.

Not final generative video yet.

Get this command excellent first:

```bash
quantum compile short.yaml --target animatic
```

and require that it autonomously produces a genuinely watchable 60-second animatic.

---

## One particularly strong consequence

Once `animatic.lock` exists, it should contain something equivalent to:

```text
story locked
dialogue locked
character versions locked
locations locked
props locked
shot count locked
shot durations locked
world transitions locked
camera plan locked
edit locked
```

Then final generation becomes an implementation problem:

```text
ShotSpec 001 → video
ShotSpec 002 → video
ShotSpec 003 → video
...
```

A bad shot 217 stays **shot 217**.

It doesn't reopen the screenplay.

It doesn't alter Aria's history.

It doesn't move a later cut.

It doesn't rewrite the episode.

It simply:

```text
render(217)
    ↓
critic
    ↓
reject
    ↓
render(217)
```

That is the property that makes a 300-shot autonomous studio tractable.

### My resulting core stack

```text
Quantum Animation Studio
│
├── Quantum Compiler
│
├── Animation World Model
│   ├── StateReducer
│   ├── SnapshotStore
│   └── StoryClock
│
├── l9-graphiti-memory
│   └── long-term universe/agent/canon memory
│
├── Asset Registry
│   └── characters/locations/props
│
├── Production Agents
│   ├── Writer
│   ├── Director
│   ├── Critic
│   ├── TakeSelector
│   └── Sound
│
├── Render DAG
│
└── Timeline Compiler
```

So you already have a meaningful piece of the infrastructure: **I would reuse `l9-graphiti-memory` rather than inventing a second autonomous-memory subsystem**, while deliberately keeping deterministic animation state one layer above it. The repository's current canonical-write-path, immutable-record, temporal, supersession, lineage and projection design is well aligned with that role. ([GitHub][5])

That reduces the truly novel Quantum Animation work to the pieces that actually *should* be novel: **Animation World Model + Story/Shot compiler + autonomous QC + render/timeline execution.**

[1]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/ARCHITECTURE.md "l9-graphiti-memory/ARCHITECTURE.md at main · Quantum-L9/l9-graphiti-memory · GitHub"
[2]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/src/l9_graphite_memory/contracts/memory.py "l9-graphiti-memory/src/l9_graphite_memory/contracts/memory.py at main · Quantum-L9/l9-graphiti-memory · GitHub"
[3]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/src/l9_graphite_memory/contracts/enums.py "l9-graphiti-memory/src/l9_graphite_memory/contracts/enums.py at main · Quantum-L9/l9-graphiti-memory · GitHub"
[4]: https://github.com/Quantum-L9/l9-graphiti-memory/blob/main/src/l9_graphite_memory/contracts/temporal.py "l9-graphiti-memory/src/l9_graphite_memory/contracts/temporal.py at main · Quantum-L9/l9-graphiti-memory · GitHub"
[5]: https://github.com/Quantum-L9/l9-graphiti-memory/tree/main "GitHub - Quantum-L9/l9-graphiti-memory: L9 Graphiti Memory — bi-temporal knowledge graph memory subsystem for autonomous agents (Zep Cloud transport) · GitHub"

----
Yes. I would make **`YAML → animatic` the first real product boundary** and treat the animatic as a compiled artifact, not a preview someone manually edits.

For now I’d deliberately leave the World Model behind a tiny interface and focus on compiler mechanics.

# 1. Compiler contract

The fundamental command:

```bash
quantum compile episode.yaml --target animatic
```

should mean:

```text
Human creative intent
        │
        ▼
   episode.yaml
        │
        ▼
╔═══════════════════════╗
║   QUANTUM COMPILER    ║
╚═══════════════════════╝
        │
        ├── validate
        ├── normalize
        ├── expand creative brief
        ├── design story
        ├── write screenplay
        ├── synthesize temp dialogue
        ├── direct scenes
        ├── design shots
        ├── resolve assets
        ├── create storyboards
        ├── edit timeline
        ├── add temp sound / score
        ├── QC
        ├── repair
        └── lock
        │
        ▼
    animatic.mp4
    animatic.lock
```

The important distinction is that `episode.yaml` is **intent**, while everything after it is generated production data.

You should not have to manually specify 15 shots in the YAML.

You say:

```yaml
premise: >
  A synthetic soldier learns that the enemy she has been
  hunting is another version of herself.

ending:
  desired_effect: devastating realization
```

and the compiler figures out the screenplay, scenes, coverage, cuts, timings, etc.

---

# 2. Internally: compiler passes

I would structure it as:

```text
                 SOURCE
                   │
                   ▼
             EpisodeSpec
                   │
          ┌────────▼────────┐
          │ Frontend        │
          │ validate/migrate│
          └────────┬────────┘
                   ▼
             CanonicalSpec
                   │
          ┌────────▼────────┐
          │ Creative Pass   │
          └────────┬────────┘
                   ▼
              StoryIntentIR
                   │
          ┌────────▼────────┐
          │ Story Pass      │
          └────────┬────────┘
                   ▼
                StoryIR
                   │
          ┌────────▼────────┐
          │ Screenwriter    │
          └────────┬────────┘
                   ▼
             ScreenplayIR
                   │
          ┌────────▼────────┐
          │ Dialogue Pass   │
          └────────┬────────┘
                   ▼
           PerformanceIR
                   │
          ┌────────▼────────┐
          │ Director Pass   │
          └────────┬────────┘
                   ▼
                ShotIR
                   │
          ┌────────▼────────┐
          │ Asset Resolver  │
          └────────┬────────┘
                   ▼
             ProductionIR
                   │
          ┌────────▼────────┐
          │ Storyboard Pass │
          └────────┬────────┘
                   ▼
             StoryboardIR
                   │
          ┌────────▼────────┐
          │ Editor Pass     │
          └────────┬────────┘
                   ▼
              TimelineIR
                   │
          ┌────────▼────────┐
          │ Animatic Render │
          └────────┬────────┘
                   ▼
             animatic.mp4
                   │
          ┌────────▼────────┐
          │ Autonomous QC   │
          └────────┬────────┘
                FAIL│PASS
                    │
           repair   ▼
                 LOCK
```

The models are implementation details inside passes.

---

# 3. Agents become compiler passes

This gives us a cleaner definition of the agents we discussed.

| Agent/pass          | Consumes                   | Produces                      |
| ------------------- | -------------------------- | ----------------------------- |
| Creative Director   | `CanonicalSpec`            | `StoryIntentIR`               |
| Writer              | `StoryIntentIR`            | `StoryIR` / `ScreenplayIR`    |
| Dialogue Director   | screenplay dialogue        | timed voice performances      |
| Director            | screenplay + timings       | `ShotIR`                      |
| Production Designer | characters/locations/props | asset requirements            |
| Storyboarder        | `ShotIR` + assets          | storyboard frames             |
| Editor              | shots + dialogue           | `TimelineIR`                  |
| Sound Designer      | timeline                   | temp audio timeline           |
| Critic              | any generated IR/media     | structured critique           |
| Repair Planner      | critique                   | bounded compiler re-execution |

So yes, they're agents.

But architecturally:

> **An agent is a compiler pass with judgment.**

Not an autonomous process wandering around the filesystem deciding what to do next.

---

# 4. Every pass has a strict interface

Something like:

```python
from typing import Generic, TypeVar, Protocol

I = TypeVar("I")
O = TypeVar("O")


class CompilerPass(Protocol, Generic[I, O]):
    name: str
    version: str

    async def compile(
        self,
        ctx: "CompileContext",
        source: I,
    ) -> O:
        ...
```

Then:

```python
class ScreenplayPass:
    name = "screenplay"
    version = "1.0"

    async def compile(
        self,
        ctx: CompileContext,
        source: StoryIR,
    ) -> ScreenplayIR:
        ...
```

And:

```python
class DirectorPass:
    name = "director"
    version = "1.0"

    async def compile(
        self,
        ctx: CompileContext,
        source: DirectorInput,
    ) -> ShotIR:
        ...
```

Agents don't pass paragraphs to each other.

They pass validated structs.

---

# 5. The compiler IRs are incredibly important

I would avoid having one giant JSON representation.

Use increasingly concrete IRs.

### `StoryIntentIR`

Still fairly abstract:

```python
class StoryIntentIR(BaseModel):
    premise: str
    protagonist_id: str

    dramatic_question: str
    protagonist_goal: str
    protagonist_need: str

    central_conflict: str

    emotional_start: str
    emotional_end: str

    intended_audience_experience: list[str]

    ending_type: str
```

### `StoryIR`

Now temporal structure exists:

```python
class StoryBeat(BaseModel):
    id: str
    function: str
    description: str
    duration_budget_ms: int


class SceneIR(BaseModel):
    id: str
    location_id: str
    beat_ids: list[str]
    objective: str
    conflict: str
    turn: str
    duration_budget_ms: int


class StoryIR(BaseModel):
    beats: list[StoryBeat]
    scenes: list[SceneIR]
```

### `ScreenplayIR`

Now performances exist:

```python
class DialogueLine(BaseModel):
    id: str
    character_id: str
    text: str

    intention: str
    subtext: str
    delivery: str


class ScreenplayScene(BaseModel):
    id: str
    action: list[str]
    dialogue: list[DialogueLine]
```

Notice that dialogue has:

```text
text
intention
subtext
delivery
```

because the speech generator eventually needs performance direction, not just words.

---

# 6. Dialogue is compiled before final shots

The compiler then synthesizes temporary/final dialogue:

```text
DialogueLine
     │
     ▼
 Voice Generator
     │
     ▼
audio/dialogue/dlg_0042.wav
     │
     ├── duration = 3271 ms
     ├── word timings
     ├── phoneme timings
     └── performance metadata
```

Giving:

```python
class PerformanceCue(BaseModel):
    dialogue_id: str
    character_id: str

    audio_uri: str

    duration_ms: int

    word_timings: list["WordTiming"]
    phoneme_timings: list["PhonemeTiming"]
```

Now the Director knows the actual line lasts:

```text
3.271 seconds
```

instead of guessing.

This should happen **before ShotIR compilation**.

---

# 7. Director compiles screenplay → ShotIR

The Director isn't rendering anything.

It's designing coverage.

For example:

```python
class ShotIR(BaseModel):
    id: str
    scene_id: str

    narrative_function: str
    emotional_function: str

    duration_ms: int

    subject_ids: list[str]

    action: str

    framing: str
    lens_mm: int | None
    camera_motion: str

    dialogue_ids: list[str]

    asset_ids: list[str]

    entry_state_ref: str
    exit_state_ref: str

    render_constraints: dict
```

One generated shot:

```yaml
id: sc03_sh007
scene_id: sc03

narrative_function: reveal_aria_notices_signal
emotional_function: uncertainty_to_hope

duration_ms: 4200

subjects:
  - aria
  - receiver

action: >
  Aria notices the receiver indicator flicker,
  freezes, and slowly reaches toward it.

camera:
  framing: medium_close_up
  lens_mm: 65
  motion: subtle_push_in

dialogue: []

assets:
  - character:aria
  - prop:receiver
  - location:communications_room
```

This becomes the atomic unit of production.

---

# 8. The Director owns runtime budgeting

This should be mathematical rather than vibes.

If:

```yaml
runtime:
  target_seconds: 60
  tolerance_seconds: 3
```

then StoryIR might allocate:

```text
Opening        7 sec
Setup         11 sec
Inciting      8 sec
Escalation    16 sec
Climax        12 sec
Resolution     6 sec
──────────────────
              60 sec
```

Then scenes consume those budgets.

Then shots consume scene budgets.

By the time we compile `TimelineIR`:

```python
abs(total_duration_ms - target_duration_ms) <= tolerance_ms
```

must hold.

If not:

```text
DurationConstraintViolation
      ↓
RuntimeRebalancer
      ↓
modify ShotIR / ScreenplayIR
```

No human editor trimming clips.

---

# 9. Storyboard compilation

At this point we have enough information to create frames.

For each shot:

```text
ShotIR
  +
canonical character references
  +
location references
  +
composition
  +
lighting
  +
emotion
         ↓
Storyboard Generator
         ↓
shot_001/frame.png
```

For more complex shots I might eventually produce:

```text
shot_001/
    start.png
    key.png
    end.png
```

rather than one image.

That will improve the animatic substantially because you can approximate motion.

---

# 10. Storyboard vs animatic

The storyboard is still:

```text
IMAGE
IMAGE
IMAGE
IMAGE
IMAGE
```

The compiler turns it into:

```text
        VIDEO TRACK

SHOT01──────────┐
                SHOT02─────────────┐
                                SHOT03─────┐


       DIALOGUE TRACK

     ┌── Aria dialogue ──────────┐


       AMBIENCE

────────────────────────────────────────────────


       TEMP MUSIC

       ┌─────────────────────────────────────┐
```

Now it becomes an animatic.

The editor can also compile:

```text
slow zoom
pan
crop
rack simulation
crossfade
hard cut
dip to black
```

using static storyboard images.

So you get some sense of camera motion before generating video.

---

# 11. TimelineIR should be provider-independent

Something like:

```python
class Clip(BaseModel):
    id: str
    asset_uri: str

    timeline_start_ms: int
    duration_ms: int

    source_start_ms: int = 0

    effects: list[dict] = []


class Track(BaseModel):
    type: str
    clips: list[Clip]


class TimelineIR(BaseModel):
    fps: float
    width: int
    height: int

    tracks: list[Track]
```

You can later translate this into an actual editorial interchange format or directly into FFmpeg commands.

But Quantum owns the semantic timeline.

---

# 12. Then compile the actual animatic

Conceptually:

```python
async def compile_animatic(
    source: EpisodeSpec,
) -> AnimaticLock:

    canonical = await frontend.compile(source)

    intent = await creative.compile(canonical)

    story = await story_pass.compile(intent)

    screenplay = await screenplay_pass.compile(story)

    performances = await dialogue_pass.compile(
        screenplay
    )

    shots = await director.compile(
        DirectorInput(
            story=story,
            screenplay=screenplay,
            performances=performances,
        )
    )

    production = await assets.compile(shots)

    storyboard = await storyboard_pass.compile(
        StoryboardInput(
            shots=shots,
            production=production,
        )
    )

    timeline = await editor.compile(
        EditorInput(
            shots=shots,
            storyboard=storyboard,
            performances=performances,
        )
    )

    animatic = await renderer.render(timeline)

    return await qc_and_lock(
        source=source,
        animatic=animatic,
    )
```

That's basically the heart of Quantum Animation v0.

---

# 13. Incremental compilation 🔥

This is where the compiler architecture becomes extremely valuable.

Each pass gets hashed:

```python
key = sha256(
    pass_name
    + pass_version
    + input_hash
    + config_hash
    + seed
)
```

Suppose you change:

```yaml
music:
  mood: melancholic
```

to:

```yaml
music:
  mood: ominous
```

Quantum should **not** rerun:

```text
story
screenplay
dialogue
shots
storyboards
```

Only:

```text
sound
timeline
animatic render
QC
```

Similarly, changing:

```yaml
visual:
  palette: cold_blue
```

should leave the screenplay untouched.

Changing the premise invalidates nearly everything.

That's compiler dependency tracking.

---

# 14. Separate semantic fields to improve invalidation

This matters even inside a character.

Don't do:

```yaml
characters:
  aria:
    description: >
      damaged robot with amber eyes,
      cynical but secretly hopeful...
```

because changing eye color could invalidate narrative compilation.

Instead:

```yaml
characters:
  aria:

    story:
      role: protagonist
      personality:
        - analytical
        - quietly hopeful

    visual:
      species: synthetic
      eyes: amber
      shell: ivory

    voice:
      quality: low intimate contralto
```

Now dependency tracking knows:

```text
story.personality change
    → screenplay invalidated

visual.eye_color change
    → storyboard/render invalidated

voice change
    → dialogue/timing/director invalidated
```

Much cleaner.

---

# 15. Build output

One compile could look like:

```text
build/the_last_signal/
│
├── source/
│   └── episode.yaml
│
├── ir/
│   ├── canonical.json
│   ├── intent.json
│   ├── story.json
│   ├── screenplay.json
│   ├── performance.json
│   ├── shots.json
│   ├── production.json
│   ├── storyboard.json
│   └── timeline.json
│
├── assets/
│   ├── dialogue/
│   ├── storyboard/
│   ├── ambience/
│   └── temp_music/
│
├── qc/
│   └── animatic_report.json
│
├── manifest.json
├── animatic.mp4
└── animatic.lock
```

Every intermediate representation is inspectable.

That is hugely important during development.

---

# 16. `animatic.lock`

This file is effectively the production contract.

```yaml
schema: quantum.animatic-lock/v0.1

project_id: last_signal
build_id: build_000184

source_hash: "sha256:..."

locked:
  story: "sha256:..."
  screenplay: "sha256:..."
  dialogue: "sha256:..."
  shot_plan: "sha256:..."
  assets: "sha256:..."
  storyboard: "sha256:..."
  timeline: "sha256:..."

runtime_ms: 60187
shot_count: 13

qc:
  status: pass
  score: 0.934

compiler:
  version: 0.1.0
```

Final production consumes **this**, not the original YAML.

```bash
quantum render animatic.lock
```

That gives us:

```text
episode.yaml

     compile
        ↓

animatic.lock

     render
        ↓

master.mp4
```

Beautifully clean boundary.

---

# 17. Now the source YAML

I would deliberately make the first YAML **creative and pleasant to write**.

You shouldn't feel like you're filling out a database.

I propose:

```text
schema: quantum.animation/episode-v0.1
```

Here's the version I'd start putting ideas into today:

```yaml
schema: quantum.animation/episode-v0.1


# ============================================================
# IDENTITY
# ============================================================

project:
  id: my_short_001
  title: "Untitled"
  series: null
  episode: null

  seed: 847221


# ============================================================
# FORMAT
# ============================================================

format:
  type: short

  runtime:
    target_seconds: 60
    tolerance_seconds: 3

  aspect_ratio: "16:9"
  resolution: "1920x1080"
  fps: 24

  language: en


# ============================================================
# THE IDEA
# This is the most important section.
# ============================================================

concept:

  premise: >
    Put the central idea here.

  hook: >
    What makes this concept immediately interesting,
    strange, emotional, frightening, funny, etc.

  genre:
    - science_fiction

  tone:
    - cinematic
    - intimate

  themes:
    - memory
    - identity

  audience_experience:
    - curiosity
    - tension
    - emotional_payoff

  inspiration_notes:
    - >
      Free-form thoughts about the kind of experience
      you want this to create.


# ============================================================
# STORY INTENT
# These are creative constraints, not screenplay instructions.
# Everything can be "auto".
# ============================================================

story:

  protagonist: auto

  central_question: auto

  conflict: auto

  opening:
    idea: auto

  ending:
    idea: auto

    desired_effect:
      - surprise
      - emotional_resonance

  structure: auto

  dialogue:
    amount: light

  pacing:
    overall: deliberate
    ending: accelerating

  must_include: []

  must_not_include: []


# ============================================================
# CHARACTERS
# Recurring characters should have stable IDs.
# ============================================================

characters:

  - id: protagonist

    name: auto

    story:
      role: protagonist

      description: >
        Describe who this person/entity is.

      personality:
        - curious
        - restrained

      motivation: auto

      flaw: auto

      arc: auto

    visual:
      description: >
        Describe their appearance if you already have
        something in mind.

      age_apparent: auto

      palette: auto

      distinctive_features: []

    voice:
      description: >
        Describe how the character should sound.

      performance:
        - natural
        - emotionally_restrained


# ============================================================
# RELATIONSHIPS
# Optional in simple shorts.
# ============================================================

relationships: []

# Example:
#
# relationships:
#   - from: aria
#     to: marcus
#     type: former_partner
#     description: >
#       Aria believes Marcus died three years ago.


# ============================================================
# LOCATIONS
# Define known locations or let Quantum invent them.
# ============================================================

locations:

  - id: primary_location

    description: auto

    visual:
      architecture: auto
      lighting: auto
      palette: auto
      atmosphere: auto


# ============================================================
# OBJECTS / PROPS
# Only put things here when they matter.
# ============================================================

props: []

# Example:
#
# props:
#   - id: old_receiver
#
#     description: >
#       A battered analog communications receiver.
#
#     narrative_importance: high


# ============================================================
# VISUAL LANGUAGE
# ============================================================

visual:

  medium: stylized_cinematic_animation

  realism: stylized_realism

  overall_description: >
    Describe the desired visual feeling here.

  palette:
    dominant: auto
    accent: auto

  lighting:
    style: cinematic
    contrast: high

  camera:
    style: deliberate

    movement:
      frequency: restrained

    handheld: false

    preferred_framing:
      - medium
      - close_up
      - wide_environmental

  editing:
    style: cinematic
    cut_frequency: moderate

  avoid:
    - excessive_camera_motion
    - random_visual_style_changes


# ============================================================
# SOUND
# ============================================================

sound:

  dialogue:
    enabled: true

  ambience:
    enabled: true
    style: immersive

  foley:
    enabled: true

  sound_effects:
    enabled: true

  music:
    enabled: true

    style: auto

    emotional_arc: auto

    vocals: false

  silence:
    allowed: true
    use_dramatically: true


# ============================================================
# PRODUCTION LANGUAGE
#
# These guide the autonomous Director.
# They are NOT hardcoded shots.
# ============================================================

production:

  shots:
    target_count: auto

    average_duration_seconds: 5

    min_duration_seconds: 1.5
    max_duration_seconds: 9

  coverage:
    establish_locations: true
    reaction_shots: true
    inserts_when_narratively_useful: true

  storyboard:
    frames_per_shot: auto

  animatic:
    camera_motion_simulation: true
    temp_dialogue: true
    temp_ambience: true
    temp_sound_effects: true
    temp_music: true
    captions: true


# ============================================================
# AUTONOMY
# Quantum-branded production is autonomous.
# ============================================================

autonomy:

  mode: full

  human_approval_gates: false

  allow:

    story_expansion: true

    dialogue_rewrite: true

    scene_rewrite: true

    shot_rewrite: true

    shot_split: true

    shot_merge: true

    pacing_changes: true

    camera_changes: true

    autonomous_asset_creation: true

  preserve:

    premise: true

    must_include: true

    must_not_include: true

  repair:

    enabled: true

    max_story_attempts: 3

    max_scene_attempts: 3

    max_shot_attempts: 4

    allow_simplification: true


# ============================================================
# QUALITY TARGET
#
# Exact scoring model comes later in Autonomous QC.
# ============================================================

quality:

  minimum_animatic_score: 0.85

  priorities:
    narrative_coherence: critical
    emotional_effectiveness: high
    pacing: high
    visual_clarity: high
    continuity: critical
    originality: high


# ============================================================
# HARD CONSTRAINTS
# Unlike creative guidance, these cannot be violated.
# ============================================================

constraints:

  content: []

  narrative: []

  visual: []

  audio: []


# ============================================================
# FREEFORM NOTEBOOK
#
# Deliberately unstructured.
# Put random ideas here without changing the schema.
# The Creative Director is allowed to interpret these.
# ============================================================

notes: |
  Throw ideas down here.

  Interesting images.
  Dialogue fragments.
  Endings.
  Character ideas.
  Weird concepts.
  Things you absolutely want to see.

  This area can be messy.
```

That last `notes` field is intentional.

I want the format to support both:

```yaml
story:
  ending:
    desired_effect:
      - existential_dread
```

and:

```yaml
notes: |
  I keep seeing this image where somebody opens an elevator
  and instead of another floor it's the ocean.

  No idea what it means yet.

  Maybe the elevator has been going down for 20 years?
```

Quantum should be capable of turning **that** into structured production intent.

---

# 18. The YAML should have three semantic strengths

I would give values implicit meanings based on where they're placed:

```text
notes / inspiration
        ↓
SOFT
Quantum may interpret freely.


concept / story / visual
        ↓
INTENT
Quantum should preserve the meaning,
but can creatively implement it.


constraints / must_include / must_not_include
        ↓
HARD
Compiler cannot violate it.
```

That's important because you don't want to add:

```yaml
themes:
  - loneliness
```

and accidentally make `"loneliness"` a rigid requirement checked on every scene.

But:

```yaml
must_include:
  - protagonist willingly destroys the transmitter
```

is different.

That's a compiler invariant.

---

# 19. `auto` should be first-class

I'd use `auto` aggressively.

For example:

```yaml
characters:

  - id: creature

    story:
      role: antagonist

    visual:
      description: auto

    voice:
      description: auto
```

This tells Quantum:

> This concept exists, but I deliberately delegate the creative decision.

That's better than fields being missing because the compiler can distinguish:

```text
unset accidentally
```

from:

```text
explicitly delegated to Quantum
```

Later the canonicalizer turns every `auto` into concrete values.

So:

```text
episode.yaml
```

might contain:

```yaml
music:
  emotional_arc: auto
```

while:

```text
canonical.json
```

contains:

```json
{
  "music": {
    "emotional_arc": [
      {
        "start": 0.0,
        "mood": "isolation"
      },
      {
        "start": 0.55,
        "mood": "growing wonder"
      },
      {
        "start": 0.87,
        "mood": "tragic recognition"
      }
    ]
  }
}
```

The source remains pleasant.

The compiled IR becomes obsessive.

Exactly what we want.

---

# 20. I would also support tiny source files

The schema should not force you to fill everything in.

This should compile:

```yaml
schema: quantum.animation/episode-v0.1

project:
  id: elevator_ocean
  title: "Below"

format:
  runtime:
    target_seconds: 60

concept:
  premise: >
    A woman rides an elevator downward every night,
    but tonight the doors open onto the bottom of an ocean.

  genre:
    - science_fiction
    - psychological_horror

  tone:
    - mysterious
    - beautiful
    - unsettling

story:
  ending:
    desired_effect:
      - awe
      - existential_dread

characters:
  - id: woman

    story:
      role: protagonist

    visual:
      description: >
        Exhausted office worker in her late thirties.

notes: |
  Almost no dialogue.

  I want the ocean reveal to feel beautiful rather than like
  a monster jump scare.

  Maybe something enormous passes far away outside the elevator.

  End before explaining anything.
```

That's enough.

Quantum fills in everything else.

That is the experience I would optimize for.

---

# 21. Source YAML versus studio configuration

Longer-term, I would **not** put model/provider/infrastructure settings in this file.

Keep:

```text
episode.yaml
```

about the movie.

Separately:

```text
quantum.studio.yaml
```

would eventually control things like:

```yaml
compiler:
  concurrency: 32

providers:
  language: ...
  image: ...
  speech: ...

render:
  worker_pool: ...

storage:
  artifact_store: ...
```

So creative IP doesn't become coupled to today's generation providers.

Five years from now:

```bash
quantum compile below.yaml
```

should still mean the same creative thing even though every model behind Quantum has changed.

---

# 22. And leave exactly one World Model seam for later

For now the compiler only knows this:

```python
class WorldModelPort(Protocol):

    async def initialize(
        self,
        story: StoryIR,
    ) -> "WorldSnapshot":
        ...

    async def context_for_shot(
        self,
        shot_id: str,
    ) -> "ShotWorldContext":
        ...

    async def validate_shot(
        self,
        shot: ShotIR,
    ) -> list["WorldViolation"]:
        ...

    async def commit_shot(
        self,
        shot: ShotIR,
    ) -> "WorldSnapshot":
        ...
```

**Stop there.**

Don't design its internals yet.

That gives the compiler somewhere to call it without prejudicing the much more interesting architecture we'll design when we get to the World Model.

---

## The resulting MVP architecture

```text
                       YOUR IDEA
                          │
                          ▼
                     episode.yaml
                          │
                          ▼
                 ┌─────────────────┐
                 │ Quantum Compiler│
                 └────────┬────────┘
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
        Agents           IRs           Asset Library
          │               │                │
          └───────────────┼────────────────┘
                          │
                          ▼
                     Shot Plan
                          │
                          ▼
                     Storyboards
                          │
                          ▼
                      Timeline
                          │
                          ▼
                     ANIMATIC
                          │
                          ▼
                   Autonomous QC
                      ↙       ↘
                  repair      pass
                     │         │
                     └────┐    ▼
                          │ animatic.lock
                          │
                          └──── compiler
                                iteration
```

And then:

```text
INPUT:
one YAML containing your idea

OUTPUT:
one locked, timed, voiced, scored,
sound-designed 60-second animatic
```

**That is the first Quantum Animation Studio product I would actually build.**

After the compiler, I'd tackle **Autonomous QC** next, because QC determines whether “no human interaction” is genuinely possible. Then **Render/Timeline Execution**. And only after those two, the World Model—which can then be designed against concrete demands from the other three systems rather than theoretically.

----
Yes. I’d change one important thing from the earlier design:

> **Quantum should develop the creative universe before it writes the plot.**

For reusable characters and series potential, the pipeline should not be `premise → screenplay → invent whatever characters are needed`. It should be closer to:

```text
YOUR CREATIVE YAML
        │
        ▼
Creative Seed
        │
        ├───────────────┐
        ▼               ▼
   World/Setting     Character
   Development       Development
        │               │
        └───────┬───────┘
                ▼
         Relationship Graph
                │
                ▼
      Theme / Dramatic Engine
                │
                ▼
       Ending / Reveal Design
                │
                ▼
          CANON BIBLE v1
                │
        ───── STORY BEGINS ─────
                │
                ▼
         Story Architecture
                │
                ▼
            Screenplay
                │
                ▼
        Dialogue Performance
                │
                ▼
             Director
                │
                ▼
              Shots
                │
                ▼
           Storyboards
                │
                ▼
            Animatic
```

That gives Quantum something much closer to a real studio's development process.

---

# “An agent is a compiler pass with judgment”

The **judgment** part is the critical piece.

A normal compiler pass is deterministic:

```text
input
 ↓
apply exact rules
 ↓
output
```

For example:

```text
60 seconds × 24 fps = 1,440 frames
```

No judgment required.

Or:

```text
Shot A duration = 3.2 sec
Shot B duration = 4.7 sec

A starts at 0
B starts at 3.2
```

Again: deterministic.

A creative compiler pass is different.

Suppose the Director gets this:

```text
Narrative objective:
Aria discovers the transmission is personal.

Emotion:
Suspicion → recognition.

Duration budget:
8 seconds.

Previous shot:
Wide establishing shot.

Dialogue:
None.

Available characters:
Aria

Available props:
Receiver
```

There isn't one mathematically correct shot.

The Director has choices:

```text
A. Close-up of Aria's face.

B. Insert of receiver followed by reaction.

C. Over-the-shoulder toward receiver.

D. Slow dolly toward Aria while receiver audio plays.

E. Reflection of Aria in receiver screen.
```

**Judgment means choosing which valid realization is best.**

So mechanically, I define judgment as:

> **bounded search + evaluation + selection under constraints.**

Conceptually:

```text
                         INPUT
                           │
                           ▼
                   Generate candidates
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     Candidate A      Candidate B      Candidate C
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                   Hard constraints
                           │
                   reject violations
                           │
                           ▼
                     Score valid
                      candidates
                           │
                           ▼
                        SELECT
                           │
                           ▼
                     typed output
```

For the Director, a scoring function could conceptually be:

```text
score =
    narrative_clarity       × 0.25
  + emotional_effect        × 0.20
  + cinematic_quality       × 0.15
  + continuity              × 0.15
  + visual_variety          × 0.10
  + renderability           × 0.10
  + timing_fit              × 0.05
```

with hard constraints such as:

```text
character identity must remain valid
story information cannot be revealed early
duration <= scene budget
physical continuity cannot be violated
required prop must be visible
```

A beautiful candidate that violates canon gets rejected regardless of its score.

## That's the “agent”

Internally the DirectorAgent might do:

```python
async def direct_scene(scene: SceneIR) -> ShotPlanIR:

    candidates = await propose_shot_plans(
        scene,
        count=6,
    )

    valid = [
        candidate
        for candidate in candidates
        if hard_constraints_pass(candidate)
    ]

    evaluations = await evaluate_candidates(valid)

    winner = select_best(evaluations)

    if winner.score < MIN_DIRECTOR_SCORE:
        return await revise_and_retry(
            scene,
            evaluations,
        )

    return winner.shot_plan
```

So the model is providing judgment, but **Quantum controls the decision process**.

That's extremely important for your human-free requirement.

You don't want:

```text
LLM:
"I think I'll rewrite Scene 4 while I'm here."
```

You want:

```text
DirectorAgent authority:

CAN:
- choose camera
- choose coverage
- split a beat into shots
- choose shot duration

CANNOT:
- kill a character
- change the ending
- invent new lore
- modify canon
```

Each judgment agent has an **authority envelope**.

That keeps autonomous creativity from becoming autonomous chaos.

---

# There are actually three kinds of passes

I'd distinguish them internally.

### Deterministic passes

No AI judgment.

```text
YAML validation
schema migration
timeline arithmetic
asset resolution
hashing
cache lookup
FFmpeg assembly
duration validation
ID generation
dependency resolution
```

### Judgment passes

AI makes bounded creative choices.

```text
CharacterDesigner
WorldDesigner
Writer
Director
Editor
Composer
SoundDesigner
TakeSelector
```

### Critic passes

AI evaluates rather than creates.

```text
StoryCritic
CharacterCritic
ContinuityCritic
CinematographyCritic
PerformanceCritic
AnimaticCritic
```

A very healthy pattern is:

```text
Creator
   ↓
Critic
   ↓
Repair Planner
   ↓
Creator
```

rather than asking one model to generate something and declare itself brilliant.

---

# What is IR?

**IR = Intermediate Representation.**

It's a compiler term.

Instead of going directly:

```text
YAML → movie
```

we translate through increasingly concrete representations:

```text
YAML

 ↓

CreativeSeedIR

 ↓

CanonBibleIR

 ↓

StoryIR

 ↓

ScreenplayIR

 ↓

PerformanceIR

 ↓

ShotIR

 ↓

StoryboardIR

 ↓

TimelineIR

 ↓

video
```

Each IR answers a different question.

For example:

### CreativeSeedIR

> What does Alex want this movie to be?

```json
{
  "theme": ["identity", "grief"],
  "tone": ["beautiful", "unsettling"],
  "ending_effect": "mindfuck"
}
```

### CharacterBibleIR

> Who exactly is Aria?

```json
{
  "id": "aria",
  "desire": "find another survivor",
  "need": "accept that connection can exist without presence",
  "fear": "being the final conscious being",
  "contradiction": "claims not to care but constantly searches"
}
```

### StoryIR

> What happens?

```text
Beat 1
Aria discovers an anomalous transmission.

Beat 2
She determines it originated on Earth.

Beat 3
She realizes it was intended specifically for her.
```

### ScreenplayIR

> What happens scene-by-scene and what gets said?

### ShotIR

> How will the screenplay be photographed?

### TimelineIR

> Exactly when does every visual/audio element occur?

So an IR is effectively a **stage of understanding between your idea and the final pixels**.

---

# And “structs”?

A **struct** is just a structured piece of typed data.

Different languages use different terminology:

```text
Python       dataclass / Pydantic model
Rust         struct
TypeScript   interface/type
Go           struct
C#           class/record
```

Instead of an agent outputting:

```text
"Aria should probably be in a close-up and it should
feel sad and maybe take around four seconds."
```

we make it return:

```python
class ShotSpec(BaseModel):
    id: str
    duration_ms: int

    framing: Literal[
        "extreme_wide",
        "wide",
        "medium",
        "close_up",
        "extreme_close_up",
    ]

    emotional_intent: str
    subject_ids: list[str]
    action: str
```

Giving:

```json
{
  "id": "sc04_sh007",
  "duration_ms": 4300,
  "framing": "close_up",
  "emotional_intent": "recognition_and_grief",
  "subject_ids": ["aria"],
  "action": "Aria recognizes the voice."
}
```

That's a struct.

It matters because now software can reliably:

```text
validate it
store it
hash it
compare it
query it
version it
send it to another agent
reject it
regenerate it
```

Free-form prose is terrible infrastructure.

Typed structs are excellent infrastructure.

---

# Characters before storyline: yes

I think you caught a genuine gap in the earlier compiler.

For **Quantum Animation Studio**, I would introduce a substantial **Development Compiler** before the Story Compiler.

The flow becomes:

```text
                    CreativeSeedIR
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
       WorldDesigner             CharacterDesigner
             │                         │
             ▼                         ▼
       WorldBibleIR              CharacterBibleIR
             │                         │
             └────────────┬────────────┘
                          ▼
                RelationshipDesigner
                          │
                          ▼
                  RelationshipIR
                          │
                          ▼
                  DramaticDesigner
                          │
                          ▼
                 DramaticEngineIR
                          │
                          ▼
                   RevealArchitect
                          │
                          ▼
                    RevealPlanIR
                          │
                          ▼
                    CanonCritic
                          │
                          ▼
                    CANON BIBLE
                          │
                     STORY STARTS
```

## CharacterDesigner

Before a storyline exists, Aria could have:

```text
Identity
Biography
Psychology
Values
Beliefs
Contradictions
Desires
Needs
Fear
Wound
Secret
Competencies
Weaknesses
Behavior
Speech patterns
Humor
Relationships
Visual identity
Movement identity
Voice identity
Possible character arc
Narrative boundaries
```

And importantly:

```text
What makes this character capable of generating stories?
```

That's different from merely serving one plot.

A series-grade character should contain **dramatic potential**.

For example:

```text
Aria wants connection.

But:

Aria is terrified of depending on anyone.

Therefore:

Every relationship naturally produces conflict.
```

That's story-generating machinery.

---

# Setting before story: absolutely

Same thing.

Instead of screenplay saying:

> We need a sci-fi room, invent a spaceship.

Quantum develops a real place first.

`WorldDesignerAgent` creates something closer to a production/world bible:

```text
Universe
Era
History
Civilization
Politics where narratively relevant
Economics where relevant
Technology
Science rules
Artificial intelligence
Culture
Architecture
Transportation
Communication
Daily life
Geography
Climate
Locations
Social conventions
Taboos
Language
Visual motifs
Historical scars
Current conflicts
Rules that may never be broken
```

Not all of that must appear onscreen.

That's the point.

The visible story should feel like it exists inside something larger.

---

# Then we need a Relationship pass

Characters in isolation aren't enough.

Quantum should explicitly develop:

```text
ARIA ───── loves ───── MARCUS

ARIA ───── distrusts ── EVA

MARCUS ─── created ──── EVA

EVA ────── needs ────── ARIA
```

But relationships themselves need dramatic state:

```yaml
aria_marcus:
  surface: estranged partners

  aria_believes:
    marcus_abandoned_her: true

  actual_truth:
    marcus_left_to_protect_her: true

  unresolved:
    - betrayal
    - grief
    - dependence

  dramatic_pressure:
    high
```

Now the Writer has combustible material.

---

# Theme needs its own development pass too

Theme should not simply be:

```yaml
themes:
  - identity
```

That's only a keyword.

Quantum should expand that into a **thematic argument**.

For example:

```text
TOPIC
Identity

QUESTION
Are we defined by memory or by choices?

PROTAGONIST INITIAL BELIEF
Without her memories, she would stop being herself.

ANTAGONISTIC ARGUMENT
Memory is merely stored information.

COUNTERARGUMENT
Identity emerges from the choices we repeatedly make.

ENDING PROOF
Aria loses the memories but independently makes the same
sacrificial choice.
```

Now theme becomes executable.

The screenplay can test it.

---

# And your “mind fuck ending” deserves an entire agent

I am serious about this one.

I'd have something like:

```text
RevealArchitectAgent
```

whose responsibility is specifically:

```text
hidden truth
audience assumption
character assumption
clue placement
misdirection
fairness
reveal mechanism
recontextualization
post-reveal meaning
final image
```

For a good mindfuck ending, you ideally want:

```text
FIRST WATCH

"This means X."


REVEAL

"Oh shit, it actually means Y."


RETROSPECTIVE

"Wait—the evidence for Y was there the entire time."
```

That's structurally designable.

A `RevealPlanIR` might contain:

```yaml
hidden_truth:
  description: >
    Aria isn't receiving a message from Earth.
    She is replaying the transmission she sent before her memory wipe.

audience_model:
  expected_belief:
    first_half: "someone on Earth survived"
    second_half: "the sender knows Aria personally"

reveal:
  occurs_at_percent: 0.88

  mechanism:
    Aria hears her own voice complete a phrase
    before the transmission says it.

clues:
  - at_percent: 0.18
    clue: receiver timestamp formatting
    visibility: subliminal

  - at_percent: 0.44
    clue: phrase Aria unconsciously repeats
    visibility: noticeable_but_unexplained

  - at_percent: 0.69
    clue: transmission knows information only Aria knows
    visibility: suspicious

recontextualizes:
  - opening_image
  - aria_behavior
  - title

explanation_after_reveal:
  amount: minimal
```

Now that's proper machinery for the type of stories you're talking about.

---

# Your YAML should therefore be creative-first

The previous YAML mixed **creator input** with **compiler configuration** too much.

I would split them.

The system-wide technical defaults belong in:

```text
quantum.studio.yaml
```

You shouldn't normally touch them while creating.

Your actual film file should be something closer to:

```text
story.yaml
```

and overwhelmingly contain creative material.

Here's the direction I'd use.

```yaml
schema: quantum.animation/story-v0.2


project:
  id: last_signal
  title: "The Last Signal"

  # Optional if this belongs to existing IP.
  universe: null
  series: null


# ============================================================
# CORE IDEA
# ============================================================

concept:

  premise: >
    A maintenance android alone on an abandoned orbital station
    receives what appears to be the final transmission from Earth.

  hook: >
    The transmission appears to know her personally.

  why_it_is_interesting: >
    What begins as a survival mystery gradually becomes an intimate
    story about memory, identity, and loneliness.

  genre:
    - science_fiction
    - psychological_drama
    - mystery

  tone:
    - intimate
    - melancholic
    - mysterious
    - beautiful
    - unsettling

  scale:
    physical: contained
    emotional: large


# ============================================================
# THEMATIC CORE
# ============================================================

theme:

  topics:
    - identity
    - memory
    - loneliness
    - connection

  central_question: >
    If your memories disappear, are you still the same person?

  thesis: auto

  opposing_view: auto

  desired_subtext: >
    Connection may matter even when the person on the other side
    no longer exists.


# ============================================================
# AUDIENCE EXPERIENCE
# ============================================================

experience:

  desired_emotions:
    opening:
      - isolation
      - curiosity

    middle:
      - hope
      - unease

    climax:
      - recognition
      - dread

    ending:
      - awe
      - sadness
      - recontextualization

  mystery_level: high

  explanation_level: low

  intellectual_demand:
    trust_the_audience: true

  aftertaste: >
    The viewer should want to immediately replay the film.


# ============================================================
# ENDING / REVEAL
# ============================================================

ending:

  type: mindfuck

  desired_effect:
    - surprise
    - emotional_hit
    - recontextualize_entire_story

  hidden_truth: auto

  audience_should_believe: auto

  reveal_mechanism: auto

  final_image: auto

  requirements:
    reveal_must_be_fair: true
    clues_must_exist: true
    no_exposition_dump: true

  explain_after_reveal: false


# ============================================================
# TIME AND SETTING
# ============================================================

world:

  time:

    era: >
      Several centuries from now.

    exact_year: auto

    story_duration: >
      The events occur over several hours.

  setting:

    primary: >
      A largely abandoned orbital station above a silent Earth.

    atmosphere:
      - empty
      - enormous
      - decaying
      - strangely_beautiful

    civilization_state: >
      Humanity appears to have vanished, although the reason
      is initially unknown.

  history: auto

  society: auto

  technology:

    level: advanced

    constraints:
      - technology should feel engineered rather than magical
      - analog remnants should coexist with advanced systems

  rules:
    - no faster-than-light travel
    - artificial intelligence is embodied rather than omniscient

  important_locations:

    - id: observation_deck

      idea: >
        Vast dark chamber overlooking Earth.

      emotional_function: >
        Loneliness and scale.

    - id: communications_room

      idea: >
        Old, cramped communications center filled with obsolete
        hardware and physical controls.

      emotional_function: >
        Intimacy and mystery.

  unanswered_questions:
    - Why was the station abandoned?
    - What happened to Earth?


# ============================================================
# CHARACTERS
# These are developed BEFORE plot generation.
# ============================================================

characters:

  - id: aria

    name: Aria

    role: protagonist

    concept: >
      An android maintenance engineer who has spent years
      keeping an empty station alive.

    dramatic_potential: >
      She insists that she does not experience loneliness,
      yet nearly everything she does is an attempt to find
      another conscious being.

    biography:
      origin: auto
      history: auto

    psychology:

      surface_personality:
        - precise
        - reserved
        - curious
        - dryly_funny

      desire: >
        Discover whether anyone else is alive.

      need: auto

      fear: >
        Discover that she truly is alone.

      wound: auto

      false_belief: auto

      secret: auto

      contradictions:
        - >
          Claims attachment is irrational while preserving
          tiny objects belonging to former crew members.

    capabilities:
      - station maintenance
      - engineering
      - forensic analysis

    weaknesses:
      - emotionally avoidant
      - physically deteriorating

    behavior:
      movement: >
        Economical and controlled, becoming less mechanically
        precise as emotion increases.

      habits:
        - repairs things that no longer matter
        - speaks aloud despite being alone

    speech:
      style:
        - concise
        - observational
        - understated

      humor: dry

    visual:

      overall: >
        Humanoid maintenance android with an ivory ceramic shell
        marked by years of repairs.

      silhouette: slender

      eyes: amber

      distinctive_features:
        - cracked right temple
        - exposed actuator on left shoulder
        - faded maintenance markings

      condition:
        worn: true

    voice:

      overall: >
        Intimate low female voice; restrained rather than robotic.

      performance:
        - subtle
        - intelligent
        - emotionally_guarded

    arc:
      starting_state: auto
      ending_state: auto


# ============================================================
# RELATIONSHIPS
# ============================================================

relationships:

  # Leave empty if Quantum should derive them.
  # Existing-series characters can have detailed relationships here.


# ============================================================
# STORY INTENT
# Not the actual plot yet.
# ============================================================

story:

  story_source:
    derive_from:
      - concept
      - world
      - characters
      - theme
      - ending

  opening_image: >
    Aria performing an absurdly mundane repair while the
    dead Earth fills the window behind her.

  central_conflict: auto

  escalation: auto

  midpoint: auto

  climax: auto

  resolution: auto

  dialogue:

    amount: sparse

    style:
      - natural
      - restrained

    avoid:
      - exposition_dialogue
      - characters_explaining_the_theme

  pacing:

    opening: slow
    middle: controlled
    climax: accelerating
    ending: abrupt

  must_include:
    - the transmission
    - Earth visible from the station
    - Aria discovering something personally meaningful

  must_not_include:
    - monster_jump_scare
    - omniscient_AI_villain
    - explanatory_final_monologue


# ============================================================
# VISUAL DIRECTION
# ============================================================

visual:

  medium: cinematic_animation

  overall: >
    Highly cinematic stylized realism with restrained composition
    and strong silhouettes.

  visual_contrast: >
    Cold industrial station interiors contrasted with warm
    remnants of human memory.

  palette:

    environment:
      - cold_cyan
      - desaturated_gray

    emotional_accent:
      - warm_amber

  lighting:
    - practical
    - high_contrast
    - volumetric_when_motivated

  camera:

    philosophy: >
      Camera movement should always have narrative motivation.

    tendencies:
      - deliberate
      - composed
      - restrained

  imagery:
    recurring_motifs:
      - reflections
      - empty_chairs
      - blinking_status_lights
      - Earth_through_glass

  avoid:
    - constant_camera_motion
    - generic_sci_fi_holograms
    - visual_clutter


# ============================================================
# SOUND / MUSIC CREATIVE DIRECTION
# ============================================================

sound:

  philosophy: >
    Silence and machinery should make the station feel enormous.

  ambience:
    - ventilation
    - distant_metal_stress
    - electrical_hum
    - structural_vibration

  music:

    philosophy: >
      Minimal score that initially feels almost absent.

    instrumentation:
      - synthetic_texture
      - sparse_piano
      - low_strings

    emotional_arc: auto

  silence:
    narratively_important: true


# ============================================================
# CANON / NON-NEGOTIABLES
# ============================================================

canon:

  immutable:
    - Aria is an android.
    - Earth appears uninhabited at the beginning.
    - The story must work emotionally even if the viewer does
      not fully decode the twist.

  forbidden:
    - magical solutions
    - deus_ex_machina


# ============================================================
# CREATOR NOTEBOOK
#
# Put absolutely anything here.
# Quantum develops it rather than requiring you to structure it.
# ============================================================

notebook: |
  Possible image:
  Aria holds her hand against the observation window and Earth
  fits inside the shape of her palm.

  Maybe the signal begins with just breathing.

  I want some sort of realization where the viewer understands
  something one second before Aria does.

  Could the transmission somehow actually be from Aria herself?

  I don't know yet if I want that to be literal time travel.
  Probably not. Avoid time travel unless there's a much smarter idea.

  The last 5 seconds need to fuck with your head.

  No cheesy speech at the end.

  Let the final image do most of the work.
```

**That's the YAML I think you actually want to write.**

Notice what's almost completely absent:

```text
retry counts
model names
hash configuration
render providers
worker counts
take counts
FFmpeg options
cache settings
```

Those are Quantum's problem.

---

# Then Quantum expands your creative YAML

Your 200-line creative document might compile into tens of thousands of lines of structured internal material.

For example:

```text
story.yaml
   │
   ▼
CreativeSeedIR
   │
   ▼
WorldBibleIR
   │
   ├── 18 historical events
   ├── 7 technology rules
   ├── 11 location definitions
   ├── cultural details
   └── environmental canon
   │
   ▼
CharacterBibleIR
   │
   ├── psychology
   ├── biographies
   ├── relationships
   ├── visual models
   ├── speech profiles
   └── arc possibilities
   │
   ▼
DramaticEngineIR
   │
   ├── thematic argument
   ├── dramatic question
   ├── conflict machinery
   └── emotional trajectory
   │
   ▼
RevealPlanIR
   │
   ├── actual truth
   ├── assumed truth
   ├── clues
   ├── misdirection
   └── reveal
   │
   ▼
StoryIR
```

You write **creative intent**.

Quantum manufactures **production specificity**.

---

# What else did we leave out?

There are several important pieces between “compiler” and “full autonomous studio.” Saving the World Model for last as requested, I now see the complete execution-side architecture as:

| System                            | Responsibility                                                              |
| --------------------------------- | --------------------------------------------------------------------------- |
| **Creative Development Compiler** | Concept, themes, characters, worlds, relationships, endings/reveals         |
| **Story Compiler**                | Beats, scenes, screenplay, dialogue                                         |
| **Canon/Asset Foundry**           | Character model sheets, environments, props, voices, reusable visual assets |
| **Performance Engine**            | Voice acting, timing, emotion, phonemes/lip synchronization                 |
| **Director**                      | Blocking, coverage, camera, shot design                                     |
| **Storyboard/Layout Engine**      | Composition and visual planning                                             |
| **Animatic Compiler**             | Timing, temp edit, dialogue, score, SFX                                     |
| **Autonomous QC + Repair**        | Story, image, continuity, sound, performance and technical validation       |
| **Shot Production Engine**        | Multiple takes, video generation, targeted regeneration                     |
| **Editorial Engine**              | Final take selection, timing, transitions, pacing                           |
| **Sound Studio**                  | Foley, ambience, designed SFX, score, dialogue edit                         |
| **Finishing Engine**              | VFX repair, color consistency, grading, mix, loudness, subtitles, mastering |
| **Render DAG / Artifact System**  | Parallel jobs, caching, reproducibility, restartability                     |
| **World Model**                   | The big one: persistent truth/state across all of the above                 |

A particularly important addition is the **Canon/Asset Foundry**.

Because if Aria becomes a hit, we don't want Episode 2 to “generate Aria again.”

We want:

```text
CHARACTER DEVELOPMENT
        ↓
Canonical Aria
        ↓
Asset Foundry
        ↓
┌──────────────────────────────┐
│ aria@v1                     │
│                             │
│ canonical visual identity   │
│ turnaround references       │
│ expressions                 │
│ body proportions            │
│ damage states               │
│ movement signature          │
│ voice identity              │
│ speech characteristics      │
│ wardrobe                    │
│ canonical metadata          │
└──────────────────────────────┘
        │
        ├──── Short 001
        ├──── Short 002
        ├──── Episode 001
        ├──── Episode 002
        └──── Season 2...
```

That is where **reusable generated IP** starts becoming technically real.

And I think this gives us a much better top-level decomposition than where we started:

```text
                   YOU
                    │
                    ▼
              Creative YAML
                    │
                    ▼
       ╔════════════════════════╗
       ║ DEVELOPMENT COMPILER   ║
       ║                        ║
       ║ Concept                ║
       ║ Theme                  ║
       ║ World                  ║
       ║ Characters             ║
       ║ Relationships          ║
       ║ Reveal/Ending          ║
       ╚═══════════╤════════════╝
                   │
                   ▼
                CANON
                   │
          ┌────────┴─────────┐
          ▼                  ▼
     Asset Foundry      Story Compiler
          │                  │
          └────────┬─────────┘
                   ▼
              Director
                   ▼
             Storyboard
                   ▼
              Animatic
                   ▼
           Autonomous QC
                   ▼
            Shot Production
                   ▼
               Editorial
                   ▼
             Sound / Music
                   ▼
               Finishing
                   ▼
              master.mp4
```

And threaded through essentially all of that, when we're ready to design the most interesting piece:

```text
                    WORLD MODEL
```

That is the architecture I'd now consider the real starting point for **Quantum Animation Studio**.

----
Yes — that is cleaner.

**You author exactly one thing: `creative.yaml`.** Everything else, including `quantum.studio.yaml`, is generated by Quantum.

That changes the architecture in a useful way:

```text
YOU
 │
 ▼
creative.yaml
 │
 │  human creative intent
 ▼
╔════════════════════════════╗
║ DEVELOPMENT COMPILER       ║
║                            ║
║ interpret                  ║
║ expand                     ║
║ resolve ambiguity          ║
║ develop characters         ║
║ develop world              ║
║ develop themes             ║
║ design relationships       ║
║ design reveal/ending       ║
║ establish canon            ║
║ choose production strategy ║
╚═════════════╤══════════════╝
              │
              ▼
       quantum.studio.yaml
              │
              │ canonical machine-ready
              │ production specification
              ▼
╔════════════════════════════╗
║ ANIMATION COMPILER         ║
╚═════════════╤══════════════╝
              ▼
           animatic
              ▼
        autonomous QC
              ▼
        animatic.lock
              ▼
       production/render
              ▼
          master.mp4
```

I like this substantially more.

## `creative.yaml` = what you mean

It should contain only things you might naturally think about while inventing a film:

```yaml
title: The Last Signal

concept: >
  An android alone on an abandoned orbital station receives
  what appears to be the final transmission from Earth.

themes:
  - identity
  - memory
  - loneliness

tone:
  - intimate
  - melancholic
  - unsettling

setting:
  time: several centuries from now
  place: abandoned orbital station above Earth

characters:

  aria:
    concept: >
      A maintenance android who insists she doesn't experience
      loneliness despite spending years searching for another
      conscious being.

    personality:
      - precise
      - restrained
      - dryly funny

    visual: >
      Ivory ceramic humanoid chassis, amber eyes,
      visibly repaired over many years.

ending:
  kind: mindfuck

  intent: >
    Recontextualize what the audience believes the transmission
    actually is.

  constraints:
    - fair clues
    - no exposition dump
    - emotional payoff matters more than puzzle mechanics

visual_feel: >
  Cold industrial spaces with small areas of warm human memory.

sound_feel: >
  Vast silence, mechanical ambience, extremely restrained score.

notebook: |
  Maybe the message is actually from Aria herself.

  I want the audience to understand the reveal about one second
  before she does.

  Earth through glass should be a recurring visual.

  Final five seconds need to completely change what the viewer
  thinks they just watched.
```

That's your interface.

No:

```text
render retries
frame rates
take counts
critic thresholds
shot budgets
provider configuration
cache strategy
model selection
```

unless you explicitly want creative control over something.

---

# Then Compiler 1 creates `quantum.studio.yaml`

This is where Quantum turns *your idea* into **its plan for making the film**.

I'd make it substantially more detailed.

For example:

```yaml
schema: quantum.studio/v1

source:
  creative_file: creative.yaml
  source_hash: sha256:8ad71...

production:
  id: last_signal
  title: The Last Signal

  format:
    runtime_target_ms: 60000
    fps: 24
    aspect_ratio: "16:9"

  autonomy:
    mode: fully_autonomous
    human_gates: false


development:

  concept:
    logline: >
      An isolated maintenance android investigating Earth's final
      transmission discovers that its sender is intimately connected
      to her erased past.

    dramatic_question: >
      Is identity something remembered or something repeatedly chosen?

  theme:
    topic: identity

    central_question: >
      If memory disappears, does the person remain?

    thesis: >
      Identity manifests through recurring choices rather than
      memory alone.

    counter_argument: >
      A person without their memories is effectively someone new.

  audience:
    intended_experience:
      - isolation
      - curiosity
      - hope
      - mounting_unease
      - recognition
      - recontextualization

  ending:
    type: identity_reveal

    hidden_truth: >
      Aria is listening to a transmission recorded by a previous
      version of herself before her memory was erased.

    audience_initial_belief: >
      The transmission comes from a surviving human on Earth.

    reveal_strategy:
      style: progressive_recontextualization
      exposition_after_reveal: minimal

    clue_plan:
      - phase: early
        clue: transmission uses maintenance phrase also used by Aria
        salience: low

      - phase: middle
        clue: sender knows station details impossible for Earth
        salience: medium

      - phase: late
        clue: Aria unconsciously completes sender's sentence
        salience: high


canon:

  world:

    era:
      year: 2374

    earth:
      observable_state: apparently_uninhabited

    station:
      id: station_orpheus
      function: orbital_infrastructure_platform

    technology_rules:
      - artificial consciousness is embodied
      - no faster-than-light communication
      - memory alteration is technically possible
      - technology must have physically plausible interfaces

  characters:

    aria:
      canonical_id: qchar_000001

      role: protagonist

      biography:
        original_function: maintenance_engineer
        operational_age_years: 41
        memory_discontinuity: true

      psychology:
        desire: find_another_conscious_being
        need: accept_connection_without_continuity_of_memory
        fear: absolute_loneliness

        contradiction: >
          Denies emotional attachment while preserving artifacts
          belonging to former crew.

        false_belief: >
          Memory continuity is necessary for identity.

      speech:
        verbosity: low
        humor: dry
        emotional_expression: restrained

      visual:
        chassis: humanoid
        shell: worn_ivory_ceramic
        eyes: amber
        temple_damage: right_side
        shoulder_damage: left

      motion:
        baseline: economical_precise
        emotional_change: increasingly_human_irregularity

      voice:
        archetype: intimate_low_female
        delivery: restrained


assets:

  required:

    characters:
      - aria

    locations:
      - observation_deck
      - communications_room
      - maintenance_corridor

    props:
      - communications_receiver
      - crew_keepsake

  character_asset_strategy:
    aria:
      generate_turnaround: true
      generate_expression_set: true
      generate_pose_set: true
      generate_voice_identity: true
      lock_before_storyboard: true


story:

  runtime_ms: 60000

  structure:

    - id: beat_01
      function: establish_isolation
      target_ms: 8000

    - id: beat_02
      function: signal_discovery
      target_ms: 9000

    - id: beat_03
      function: investigation
      target_ms: 17000

    - id: beat_04
      function: realization
      target_ms: 16000

    - id: beat_05
      function: final_recontextualization
      target_ms: 10000

  dialogue:
    density: sparse
    estimated_word_count: 72

  scenes:
    target_count: 4


directing:

  target_shots: 13

  average_shot_ms: 4600

  camera_language:
    movement: restrained
    composition: deliberate

  coverage_rules:
    establish_new_geography: true
    favor_reactions_over_exposition: true
    inserts_only_when_story_relevant: true

  visual_motifs:
    - reflections
    - earth_through_glass
    - empty_human_spaces
    - amber_status_lights


sound:

  dialogue:
    enabled: true

  ambience:
    importance: high

  score:
    density: sparse
    instrumentation:
      - synthetic_texture
      - felt_piano
      - low_strings

    climax_strategy: withdraw_before_reveal

  silence:
    use_as_structural_element: true


execution:

  storyboard:
    candidate_frames_per_shot: 3
    select_best: true

  shots:
    takes_per_shot: 3

  qc:
    autonomous: true

    thresholds:
      story: 0.90
      character: 0.92
      continuity: 0.95
      visual: 0.88
      audio: 0.90

    repair:
      max_local_attempts: 4
      escalate_scope_automatically: true


compiler:

  development_pass:
    version: 1

  canon_locked: true

  seed: 847221
```

You never wrote that.

Quantum did.

---

# This gives us two very different abstraction levels

### Human source

```text
creative.yaml
```

asks:

> What do I want?

### Machine source

```text
quantum.studio.yaml
```

asks:

> Given what Alex wants, exactly what movie are we making and how will Quantum make it?

That distinction is excellent.

---

# And `quantum.studio.yaml` should become the canonical production source

Once Compiler 1 produces it:

```text
creative.yaml
      │
      ▼
Development Compiler
      │
      ▼
quantum.studio.yaml
      ▲
      │
CANONICAL PRODUCTION SPEC
```

Everything downstream consumes **that**, not your original creative notes.

So:

```bash
quantum develop creative.yaml
```

produces:

```text
quantum.studio.yaml
```

Then:

```bash
quantum compile quantum.studio.yaml --target animatic
```

Although normally you'd just run:

```bash
quantum make creative.yaml
```

and Quantum internally performs both stages.

---

# More importantly: Compiler 1 is where enormous amounts of judgment happen

This compiler is not just translating fields.

It's **developing your film**.

For example, you might write:

```yaml
ending:
  kind: mindfuck

notebook: |
  Maybe she's actually listening to herself?
  No time travel unless it's genuinely brilliant.
```

Compiler 1 explores candidates:

```text
Candidate A
Time loop.

Candidate B
Memory-erased previous self.

Candidate C
Simulation recursion.

Candidate D
Transmission generated from station telemetry.

Candidate E
Aria herself is the transmitter and receiver separated
by a failed consciousness backup.
```

Then evaluates:

```text
                    A     B     C     D     E

theme fit          .71   .96   .79   .63   .91
emotional impact   .74   .94   .72   .58   .86
originality        .59   .82   .65   .83   .90
fair clueability   .72   .95   .69   .81   .76
60-sec feasibility .48   .92   .61   .86   .69
no time travel     FAIL  PASS  PASS  PASS  PASS
```

And chooses:

```text
B
```

Then **commits it into `quantum.studio.yaml`**.

This is exactly what I mean by an agent/compiler pass exercising judgment.

---

# Character development belongs here too

Your input could be minimal:

```yaml
characters:

  aria:
    concept: >
      Maintenance android alone for years.

    personality:
      - restrained
      - curious

    visual: >
      Worn ivory robot with amber eyes.
```

Compiler 1 expands it:

```text
                     ARIA SEED
                         │
                         ▼
              CharacterDesigner
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
      Psychology      Biography      Visual ID
          │              │              │
          ▼              ▼              ▼
        Speech        Dramatic       Movement
        Profile       Potential      Profile
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                  CharacterCritic
                         │
                         ▼
                  CharacterBible
                         │
                         ▼
              quantum.studio.yaml
```

Same for the world.

---

# So `quantum.studio.yaml` is basically the Studio's interpretation of your intent

This leads to a nice conceptual naming system:

```text
creative.yaml
    =
Creator Intent


quantum.studio.yaml
    =
Studio Interpretation +
Canonical Creative Decisions +
Production Strategy


*.IR.json
    =
Compiler Internals


animatic.lock
    =
Locked Film Plan


master.mp4
    =
Film
```

The hierarchy is extremely clean.

---

## One thing I'd make mandatory: provenance

Every major generated decision in `quantum.studio.yaml` should know whether it came directly from you or Quantum.

Internally:

```yaml
theme:
  central_question:
    value: >
      If memory disappears, does the person remain?

    provenance:
      source: compiler
      derived_from:
        - creative.theme
        - creative.characters.aria
        - creative.notebook

    confidence: 0.94
```

The pretty YAML doesn't necessarily need all that inline—the metadata can live alongside it—but the system should retain it.

Then Quantum knows:

```text
Alex explicitly said this.
        ≠
Quantum inferred this.
        ≠
Quantum invented this.
```

That will matter enormously when repair agents start modifying things.

For example:

```text
USER CREATIVE DECISION
premise
        ↓
protected


QUANTUM DECISION
scene count
        ↓
freely replaceable
```

That gives us a very useful authority hierarchy:

```text
1. Your explicit creative constraints
       ↓ highest authority

2. Quantum-developed canon

3. Story decisions

4. Directorial decisions

5. Production decisions

6. Individual generated takes
       ↓ cheapest/easiest to replace
```

So if shot 217 fails, Quantum changes level 6 before level 5, level 5 before level 4, etc.

It only climbs toward your original creative intent when something fundamentally cannot work.

That's exactly the behavior I'd want from a **100% autonomous studio under a single human creator**.

So yes — I'd lock this in:

> **`creative.yaml` is the only human-authored source. `quantum.studio.yaml` is the Development Compiler's fully resolved, canonical studio plan. Everything else compiles from there.**

----
Yes. I would change the role of `creative.yaml` substantially.

It should **not** be a convenient form for you to fill out manually.

It should be the **loss-minimized semantic representation of the entire creative conversation**.

You talk naturally like we are now. A `CreativeIntakeAgent` turns that conversation into a very large, explicit, structured creative dossier. Then the Development Compiler turns that dossier into `quantum.studio.yaml`.

```text
                 YOU
                  │
                  │ conversation
                  ▼
        ┌─────────────────────┐
        │ CreativeIntakeAgent │
        │                     │
        │ extracts            │
        │ disambiguates       │
        │ structures          │
        │ preserves nuance    │
        │ marks uncertainty   │
        └──────────┬──────────┘
                   │
                   ▼
             creative.yaml
                   │
           ~~~ VERY RICH ~~~
                   │
                   ▼
        ┌─────────────────────┐
        │ DevelopmentCompiler │
        │                     │
        │ explores            │
        │ judges              │
        │ resolves            │
        │ develops            │
        │ canonizes           │
        └──────────┬──────────┘
                   │
                   ▼
          quantum.studio.yaml
                   │
             fully resolved
                   ▼
            Story Compiler
                   ▼
              Animatic
```

That means `creative.yaml` can easily be **hundreds or thousands of lines**.

That's fine.

In fact, it's desirable.

---

# The key distinction

I would define these three layers very precisely:

### Conversation

Messy human thinking.

> I want something a little Blade Runner-ish but not cyberpunk. Maybe the character is a robot. I want the ending to fuck with your understanding of who she is. No time travel though. Unless there's some insanely clever reason. I keep imagining Earth outside this huge window...

This is valuable—but difficult for downstream software.

### `creative.yaml`

Structured **semantic intent**.

It captures:

* exactly what you said
* what you strongly implied
* possibilities you're considering
* things you've rejected
* unresolved questions
* relative importance
* emotional goals
* aesthetic intent
* character ideas
* world ideas
* thematic questions
* contradictions
* ambiguity
* creative latitude

But it doesn't pretend every question is resolved.

### `quantum.studio.yaml`

Quantum has now made the decisions.

No more:

```text
maybe
could
possibly
I don't know
auto
```

It contains a concrete interpretation of the movie Quantum has decided to make.

---

# We need explicit decision semantics

This becomes essential.

I would give creative concepts statuses like:

```text
LOCKED
    Creator explicitly requires this.

STRONG_PREFERENCE
    Preserve unless there is a compelling reason not to.

PREFERENCE
    Meaningful direction but flexible.

CANDIDATE
    An idea under consideration.

OPEN
    Deliberately unresolved.

DELEGATED
    Quantum should decide.

FORBIDDEN
    Must never happen.
```

And provenance:

```text
CREATOR_EXPLICIT
CREATOR_IMPLIED
AGENT_INTERPRETATION
AGENT_SUGGESTION
```

That prevents a downstream agent from treating:

> "Maybe the transmission is actually from herself"

as equivalent to:

> "The transmission must be from herself."

Huge distinction.

---

# I'd give important creative decisions envelopes

For example:

```yaml
ending_concept:

  statement: >
    The transmission may originate from an earlier version
    of Aria herself.

  status: candidate

  priority: high

  provenance:
    type: creator_explicit

  rationale: >
    Supports the desired identity/memory theme and provides
    strong potential for whole-story recontextualization.

  constraints:
    - no conventional time travel
    - reveal must be emotionally meaningful
    - reveal must be fairly foreshadowed

  alternatives_allowed: true
```

This is verbose.

**Good.**

No human has to maintain it.

---

# So I'd make `creative.yaml` look much more like this

Below is roughly the conceptual schema I'd want the intake agent producing.

```yaml
schema: quantum.creative/v1


# ==============================================================
# DOCUMENT IDENTITY
# ==============================================================

document:

  project_id: last_signal
  working_title: "The Last Signal"

  generated_from:
    type: conversation
    conversation_id: conv_...

  creative_dossier_version: 1

  status: development

  creator:
    role: sole_human_creative_authority


# ==============================================================
# CREATIVE AUTHORITY
# Tells downstream agents what they are allowed to reinterpret.
# ==============================================================

creative_authority:

  hierarchy:

    - creator_explicit_constraints
    - creator_explicit_preferences
    - creator_implied_intent
    - established_canon
    - quantum_interpretation
    - quantum_invention

  interpretation_policy:

    preserve_creator_meaning: strict

    allow_literal_reinterpretation: true

    allow_creative_expansion: true

    silently_override_creator_constraints: false

  ambiguity_policy:

    preserve_meaningful_ambiguity: true

    distinguish_unknown_from_delegated: true

    distinguish_candidate_from_requirement: true


# ==============================================================
# CREATIVE NORTH STAR
#
# If all downstream context were lost except one section,
# this should let an intelligent director understand the film.
# ==============================================================

north_star:

  one_sentence_vision:
    statement: >
      A visually beautiful, emotionally intimate science-fiction
      short in which an isolated synthetic consciousness discovers
      something about a mysterious transmission that radically
      changes both her understanding of herself and the viewer's
      understanding of the film.

    status: strong_preference
    provenance: creator_implied

  desired_identity:
    statement: >
      Premium cinematic adult animation with the narrative density,
      visual confidence, thematic ambition and rewatchability of
      prestige anthology science fiction.

    status: strong_preference

  reason_to_exist:
    statement: >
      The film should deliver both an emotional experience and
      an intellectual recontextualization rather than existing
      primarily as a visual technology demonstration.

    status: locked

  success_feeling:
    statement: >
      Viewer sits silently for a moment after the final frame,
      then immediately wants to replay the short to inspect
      everything they misunderstood.

    status: locked


# ==============================================================
# CORE CONCEPT
# ==============================================================

concept:

  premise:

    statement: >
      A maintenance android living alone aboard an abandoned
      orbital station receives what appears to be the final
      transmission originating from Earth.

    status: strong_preference
    provenance: creator_and_agent_synthesis

  hook:

    statement: >
      The transmission eventually demonstrates knowledge that
      suggests an impossible personal connection to the protagonist.

    status: strong_preference

  conceptual_engine:

    statement: >
      Begin as a mystery about whether somebody else survived.
      Gradually transform into a mystery about the protagonist's
      own identity.

  novelty_target:

    statement: >
      Familiar science-fiction ingredients are acceptable,
      but their combination, emotional meaning and ultimate
      explanation should feel non-obvious.

    priority: high

  scale:

    physical:
      value: contained

    temporal:
      value: short

    conceptual:
      value: large

    emotional:
      value: intimate_then_large


# ==============================================================
# GENRE
# ==============================================================

genre:

  primary:
    - science_fiction

  secondary:
    - mystery
    - psychological_drama

  tertiary:
    - existential_horror

  avoid_drifting_into:
    - conventional_horror
    - action_thriller
    - superhero_story
    - generic_space_adventure

  genre_progression:

    opening:
      dominant: atmospheric_science_fiction

    middle:
      dominant: mystery

    climax:
      dominant: psychological_revelation

    ending:
      dominant: existential_drama


# ==============================================================
# THEMATIC ARCHITECTURE
# ==============================================================

theme:

  primary_topics:
    - identity
    - memory
    - loneliness
    - consciousness
    - connection

  central_question:

    statement: >
      If your memories disappear but you independently make the
      same choices, in what meaningful sense are you still you?

    status: preferred
    provenance: agent_interpretation

  secondary_questions:

    - >
      Does consciousness require continuity?

    - >
      Can connection remain meaningful when the other party
      exists only as information?

    - >
      Are memories evidence of identity or merely records of it?

  desired_thematic_behavior:

    show_not_explain: locked

    emerge_from_character_choice: locked

    permit_multiple_interpretations: preferred

    explicitly_state_theme_in_dialogue: forbidden

  thematic_argument:

    creator_position:
      status: open

    protagonist_initial_position:
      status: delegated

    opposing_position:
      status: delegated

    ending_implication:
      status: delegated


# ==============================================================
# AUDIENCE EXPERIENCE
# ==============================================================

audience_experience:

  primary_goal:
    statement: >
      Manipulate the audience's model of reality rather than
      merely surprise them with hidden information.

  emotional_curve:

    - phase: opening
      target:
        - isolation
        - fascination
        - serenity

    - phase: signal_discovery
      target:
        - curiosity
        - fragile_hope

    - phase: investigation
      target:
        - unease
        - anticipation

    - phase: pre_reveal
      target:
        - pattern_recognition
        - dread

    - phase: reveal
      target:
        - recognition
        - shock
        - sadness

    - phase: final_image
      target:
        - awe
        - existential_aftertaste

  viewer_relationship:

    trust_viewer_intelligence: locked

    explain_everything: forbidden

    intentional_questions_remaining: preferred

  replay_value:
    priority: critical

    mechanism:
      - planted_visual_information
      - dialogue_double_meanings
      - recontextualized_behavior
      - repeated_motifs


# ==============================================================
# REVEAL / "MIND FUCK" DOCTRINE
# ==============================================================

reveal:

  importance: critical

  type:
    preferred:
      - identity_recontextualization
      - reality_model_recontextualization

    avoid:
      - it_was_all_a_dream
      - arbitrary_simulation_reveal
      - protagonist_was_dead_all_along
      - unexplained_time_loop
      - information_hidden_only_to_trick_viewer

  creator_intent:

    statement: >
      The final five seconds should materially alter the viewer's
      interpretation of the preceding film.

    status: locked

  fairness:

    reveal_should_be_deducible: true

    evidence_required: true

    evidence_should_be_misinterpretable: true

    contradiction_with_prior_evidence: forbidden

  ideal_reaction:

    first:
      value: "Wait."

    second:
      value: "Oh shit."

    third:
      value: "It was there the whole time."

  explanation_after_reveal:

    preference: minimal_to_none

  candidate_hidden_truths:

    - id: self_transmission

      idea: >
        The mysterious transmission originates from an earlier
        version or continuity of Aria herself.

      status: candidate

      creator_interest: high

      constraints:
        - avoid conventional time travel
        - must connect directly to identity theme

    - id: unknown_alternative

      status: delegated

      instruction: >
        Quantum may invent a stronger explanation if it produces
        superior thematic, emotional and structural results.

  clue_philosophy:

    early:
      visibility: nearly_invisible

    middle:
      visibility: recognizable_in_retrospect

    late:
      visibility: audience_can_begin_to_suspect

    immediately_before_reveal:
      desired_effect: >
        Best case, attentive viewer understands approximately
        one second before Aria.


# ==============================================================
# TIME
# ==============================================================

time:

  story_era:

    statement: >
      Several centuries in Earth's future.

    exact_date:
      status: delegated

  story_duration:

    preferred:
      value: several_hours

  chronology:

    default: linear

    flashbacks:
      status: possible_but_not_preferred

    time_travel:
      status: strongly_discouraged

      exception:
        statement: >
          Only acceptable if Quantum discovers a genuinely
          exceptional mechanism that materially improves the story.

  historical_depth:
    priority: medium

    requirement: >
      The present should feel like the consequence of a history
      rather than an arbitrary science-fiction set.


# ==============================================================
# WORLD
# ==============================================================

world:

  high_level:

    statement: >
      Humanity created long-lived embodied synthetic intelligences
      and extensive orbital infrastructure before an unknown event
      left Earth apparently silent.

  world_feeling:

    - enormous
    - old
    - engineered
    - abandoned
    - melancholic
    - believable

  physical_rules:

    realism:
      preferred: grounded_speculative

    magic:
      forbidden: true

    causality:
      strict: true

  technology:

    philosophy:
      statement: >
        Technology should feel constructed, specialized,
        repairable and constrained.

    avoid:
      - magic_hologram_interfaces
      - omnipotent_general_AI
      - unexplained_nanotechnology
      - convenient_technology_created_for_one_plot_point

    expected_domains:
      - orbital_engineering
      - artificial_consciousness
      - advanced_communications
      - memory_storage_or_modification
      - autonomous_maintenance

  artificial_intelligence:

    embodiment:
      preferred: true

    omniscience:
      forbidden: true

    consciousness:
      status: accepted_world_fact

    social_history:
      status: delegated

  earth:

    present_observable_condition:
      value: apparently_silent

    true_condition:
      status: open

    whether_story_must_explain:
      value: false

  historical_events:

    status: delegated

    development_requirement:
      statement: >
        Develop enough history that artifacts, station design,
        Aria's existence and abandoned human infrastructure have
        coherent causal origins.

  culture:

    status: delegated

    requirement:
      statement: >
        Human artifacts should imply a recognizable lived culture,
        not generic futuristic production design.

  unresolved_world_questions:

    - What happened to humanity?
    - Why was this station abandoned?
    - Why was Aria left active?
    - What relationship did synthetic beings have with humans?
    - Why can Aria's memories be discontinuous?


# ==============================================================
# PRIMARY SETTING
# ==============================================================

setting:

  macro:

    location_type: orbital_station

    relation_to_earth:
      value: low_or_medium_earth_orbit
      status: delegated_exactly

    scale:
      value: much_larger_than_current_occupancy

    occupancy:
      current_known:
        - aria

  station:

    name:
      status: delegated

    former_purpose:
      status: delegated

    age:
      status: delegated

    current_condition:
      - partially_functional
      - decaying
      - mostly_empty
      - maintained_by_aria

    storytelling_function:
      statement: >
        The station should simultaneously feel like Aria's home,
        her responsibility and an enormous tomb.

  architecture:

    philosophy:
      - functional
      - industrial
      - believable
      - traces_of_human_personality

    scale_contrast:
      statement: >
        Alternate intimate maintenance spaces with enormous spaces
        emphasizing how alone Aria is.

  environmental_storytelling:

    priority: high

    examples:
      - abandoned_personal_objects
      - obsolete_signage
      - maintenance_repairs_performed_long_after_they_matter
      - spaces_designed_for_people_who_are_no_longer_there

  acoustic_identity:

    characteristics:
      - ventilation
      - distant_metal_stress
      - machine_hum
      - long_reverberation
      - silence


# ==============================================================
# IMPORTANT LOCATIONS
# ==============================================================

locations:

  observation_deck:

    role:
      - emotional_anchor
      - recurring_visual_motif

    concept: >
      A vast dark chamber whose dominant architectural feature
      is a view of Earth.

    emotional_function:
      - loneliness
      - scale
      - longing

    visual_function:
      - silhouette
      - reflection
      - negative_space

    sound_function:
      - silence
      - distant_station_vibration

    required:
      status: strong_preference


  communications_room:

    concept: >
      Compact, old communications space containing layers of
      technology from multiple eras.

    emotional_function:
      - intimacy
      - mystery

    visual_contrast_to_observation_deck:
      value: cramped_vs_vast

    narrative_function:
      value: investigation_center


  maintenance_spaces:

    status: delegated

    requirements:
      - reveal_aria_daily_routine
      - reinforce_station_age
      - communicate_her_competence


# ==============================================================
# PROTAGONIST
# ==============================================================

characters:

  aria:

    canonical_identity:

      name: Aria

      species: synthetic_consciousness

      embodiment: humanoid_maintenance_android

      role:
        - protagonist
        - primary_viewpoint

    character_concept:

      statement: >
        A highly capable maintenance intelligence who has spent
        years sustaining infrastructure intended for inhabitants
        who no longer exist.

      status: strong_preference

    dramatic_engine:

      statement: >
        Aria claims not to need connection while organizing
        much of her existence around signs that someone else
        might still be present.

      importance: critical

    biography:

      creation:
        status: delegated

      original_purpose:
        preferred: orbital_maintenance

      former_relationship_to_crew:
        status: delegated

      why_she_remains:
        status: delegated

      memory_history:
        status: critically_relevant_but_unresolved

    psychology:

      surface_traits:
        - precise
        - restrained
        - observant
        - dryly_funny
        - competent

      deeper_traits:
        - lonely
        - attached
        - curious
        - emotionally_defensive

      conscious_desire:
        statement: >
          Determine whether another conscious being survives.

      unconscious_need:
        status: delegated

      greatest_fear:
        statement: >
          Definitive proof that she is completely alone.

      contradiction:
        statement: >
          She regards attachment as irrational while carefully
          preserving objects and routines associated with people
          who disappeared long ago.

      false_belief:
        status: delegated

      wound:
        status: delegated

      shame:
        status: open

      secret:
        status: open

      moral_boundary:
        status: delegated

    intellect:

      level: very_high

      specializations:
        - engineering
        - diagnostics
        - systems_maintenance
        - forensic_reasoning

      narrative_rule:
        statement: >
          Aria cannot behave stupidly merely so the plot can proceed.

        status: locked

    emotional_expression:

      baseline:
        value: subtle

      progression:
        statement: >
          Emotional change should initially be detectable mostly
          through behavior rather than explicit statements.

      melodrama:
        forbidden: true

    behavior:

      habits:
        - repairs_systems_that_no_longer_have_users
        - speaks_aloud_despite_being_alone
        - preserves_small_human_artifacts

      physicality:

        baseline:
          - economical
          - mechanically_precise
          - controlled

        emotional_leakage:
          statement: >
            Movement becomes subtly less optimized as emotional
            pressure rises.

    speech:

      verbosity: low

      vocabulary:
        - precise
        - plain
        - technical_when_needed

      humor:
        style: dry

      exposition:
        avoid: true

      emotional_language:
        directness: low

    visual_identity:

      overall:
        statement: >
          Elegant but utilitarian humanoid maintenance chassis
          showing decades of repair rather than pristine design.

      shell:
        color: worn_ivory

      eyes:
        color: amber

      damage:
        - cracked_right_temple
        - exposed_left_shoulder_actuator

      silhouette:
        priority: distinctive

      design_avoid:
        - overtly_sexy_robot_design
        - generic_chrome_android
        - human_skin_disguise

    voice:

      perceived_gender: female

      register: low

      texture:
        - intimate
        - natural
        - subtly_nonhuman

      acting_direction:
        - restrained
        - intelligent
        - emotionally_guarded

      avoid:
        - stereotypical_robot_voice

    character_arc:

      start:
        status: delegated

      destination:
        status: delegated

      constraint:
        statement: >
          Character movement must result from meaningful discovery
          or choice rather than simply learning plot information.

    series_potential:

      importance: high

      requirement:
        statement: >
          Do not exhaust every interesting question about Aria
          within a single short.

      preserve_future_story_engines:
        - identity
        - relationship_to_humanity
        - memory_history
        - nature_of_consciousness
        - unknown_external_world


# ==============================================================
# RELATIONSHIPS
# ==============================================================

relationships:

  known:
    []

  latent_requirements:

    - >
      Develop at least one relationship from Aria's past capable
      of giving emotional meaning to abandoned human artifacts.

    - >
      Relationships may involve people no longer physically present.

  relationship_philosophy:

    statement: >
      Relationships should contain asymmetric beliefs, unresolved
      needs and history rather than merely defining characters
      as friends/enemies.


# ==============================================================
# CHARACTER KNOWLEDGE / PERSPECTIVE
# ==============================================================

knowledge_design:

  objective_truth:
    status: intentionally_not_fully_resolved

  aria_believes:
    - >
      She may be the last conscious entity aboard the station.

    - >
      Earth appears inactive.

  audience_initially_believes:
    - >
      Aria is investigating a genuine external transmission.

  deliberate_information_asymmetry:
    required: true


# ==============================================================
# STORY ENGINE
# ==============================================================

story_intent:

  initial_state:

    statement: >
      Aria exists in a stable but emotionally empty routine.

  disruption:

    statement: >
      A transmission violates an assumption she has lived with
      for a long period.

  core_story_engine:

    statement: >
      Every new piece of evidence should simultaneously increase
      hope that the sender is real and suspicion that the
      transmission cannot be what it appears to be.

  conflict_types:

    external:
      - inaccessible_or_ambiguous_transmission
      - deteriorating_station_systems

    internal:
      - hope_vs_self_protection
      - identity_uncertainty

    epistemic:
      - what_is_the_signal
      - who_sent_it
      - why_does_it_know_aria

  stakes:

    physical:
      importance: secondary

    emotional:
      importance: primary

    existential:
      importance: high

  action_level:
    preferred: low_to_moderate

  dialogue_density:
    preferred: sparse

  story_structure:
    status: delegated

  climax:
    preferred_type:
      - realization
      - choice

    avoid:
      - conventional_fight
      - explosion_as_resolution


# ==============================================================
# SCENES / MOMENTS / IMAGES ALREADY IN CREATOR'S HEAD
# ==============================================================

creative_fragments:

  required_or_desired_images:

    - idea: >
        Aria performing an absurdly mundane repair while the
        silent Earth dominates the window behind her.

      status: strong_preference

    - idea: >
        Aria places her hand against glass and Earth appears
        almost contained within her palm.

      status: candidate

  dialogue_fragments:

    - text: null
      status: open

  sensory_fragments:

    - idea: >
        The transmission may initially contain breathing rather
        than intelligible speech.

      status: candidate

  ending_fragments:

    - idea: >
        Viewer recognizes the meaning approximately one second
        before Aria.

      status: locked_intent


# ==============================================================
# VISUAL LANGUAGE
# ==============================================================

visual_language:

  medium:

    target:
      value: premium_cinematic_animation

    realism:
      value: stylized_realism

  overall_impression:

    statement: >
      Every frame should feel intentionally composed rather than
      like generic generated science-fiction imagery.

  composition:

    tendencies:
      - negative_space
      - strong_silhouette
      - controlled_symmetry
      - isolation_within_large_frames

  camera:

    philosophy:
      statement: >
        Camera movement exists because emotional or spatial
        information is changing.

    movement:
      default: restrained

    avoid:
      - perpetual_dolly
      - random_orbiting_camera
      - unnecessary_handheld

    framing_tendencies:
      - environmental_wides
      - intimate_closeups
      - inserts_with_actual_narrative_purpose

  lens_feeling:

    status: delegated

    guidance:
      statement: >
        Avoid exaggerated wide-angle distortion unless motivated.

  lighting:

    philosophy:
      - practical
      - motivated
      - high_contrast

    station:
      dominant:
        - cyan
        - neutral_gray

    human_memory_or_emotional_accent:
      dominant:
        - amber
        - warm_white

  color_story:

    requirement:
      statement: >
        Warmth should acquire narrative meaning rather than
        merely beautifying the image.

  texture:

    - repaired
    - worn
    - tactile
    - industrial

  recurring_visual_motifs:

    - reflections
    - earth_through_glass
    - empty_chairs
    - status_lights
    - hands
    - obsolete_human_objects

  imagery_to_avoid:

    - generic_blue_holograms
    - visual_noise
    - meaningless_scifi_greebles
    - random_costume_changes
    - gratuitous_lens_flare


# ==============================================================
# PERFORMANCE LANGUAGE
# ==============================================================

performance_language:

  acting_style:

    preferred:
      - naturalistic
      - restrained
      - microexpressive

    avoid:
      - theatrical_exposition
      - melodrama
      - cartoonish_reactions

  silence:

    importance: high

  reaction_priority:

    statement: >
      Whenever possible, emotional information should be conveyed
      through reaction rather than explanatory dialogue.


# ==============================================================
# SOUND LANGUAGE
# ==============================================================

sound_language:

  philosophy:

    statement: >
      Sound should continuously remind the viewer that Aria is
      inside a huge engineered structure surrounded by vacuum.

  ambience:

    importance: critical

    palette:
      - ventilation
      - transformer_hum
      - distant_structure_stress
      - servos
      - air_pressure
      - intermittent_systems

  foley:

    style:
      - tactile
      - detailed
      - physically_grounded

  transmission:

    sonic_identity:
      status: delegated

    requirement:
      statement: >
        It must become emotionally recognizable before its
        narrative origin becomes clear.

  silence:

    structural_use: true

    desired_effect:
      - scale
      - anticipation
      - revelation


# ==============================================================
# MUSIC LANGUAGE
# ==============================================================

music_language:

  score_density:
    preferred: sparse

  emotional_behavior:

    statement: >
      Score should support interpretation without telegraphing
      the reveal.

  instrumentation_candidates:

    - low_strings
    - felt_piano
    - synthetic_drones
    - processed_mechanical_tones

  melodic_identity:

    status: delegated

  motif_strategy:

    preferred: >
      A musical or tonal motif may acquire a second meaning
      after the reveal.

  climax:

    preferred_behavior:
      - reduce_or_remove_score_immediately_before_key_realization

  avoid:
    - sentimental_overstatement
    - generic_epic_trailer_music


# ==============================================================
# PACING
# ==============================================================

pacing:

  overall:
    value: deliberate_then_compressing

  opening:
    value: patient

  mystery:
    value: progressively_accelerating

  climax:
    value: compressed

  final_seconds:
    value: minimal_and_precise

  editorial_philosophy:

    statement: >
      Allow shots to breathe when atmosphere creates tension,
      but never confuse slowness with importance.


# ==============================================================
# DIALOGUE
# ==============================================================

dialogue:

  density:
    value: sparse

  philosophy:

    - characters_do_not_explain_what_camera_can_show
    - avoid_theme_statements
    - preserve_subtext
    - silence_is_valid_dialogue

  exposition:
    allowed: minimal

  repeated_language:

    possibility:
      statement: >
        Repeated phrases may be used as clues if they gain
        different meaning after the reveal.


# ==============================================================
# CANON BOUNDARIES
# ==============================================================

canon_boundaries:

  locked_truths:

    - Aria is a synthetic embodied consciousness.
    - Earth initially appears silent.
    - Aria is alone from her own initial perspective.
    - The central mystery must become personally relevant to Aria.

  strong_preferences:

    - technological explanations remain causal and coherent
    - emotional payoff survives even if viewer does not decode everything

  forbidden:

    - arbitrary_magic
    - deus_ex_machina
    - cheap_dream_reveal
    - exposition_dump_ending
    - stupidity_required_for_plot
    - twist_existing_only_for_shock


# ==============================================================
# CREATIVE NEGATIVE SPACE
#
# Just as important as what we want.
# ==============================================================

anti_goals:

  story:
    - generic_save_the_world_plot
    - conventional_villain
    - mystery_resolved_by_exposition
    - action_for_action_sake

  character:
    - emotionless_robot_cliche
    - human_character_with_robot_skin
    - protagonist_without_contradictions

  visual:
    - generic_scifi
    - overdesigned_everything

  ending:
    - random_shock
    - puzzle_without_emotion
    - explanation_longer_than_revelation


# ==============================================================
# ORIGINALITY TARGETS
# ==============================================================

originality:

  priority: high

  familiar_elements_allowed:
    - android
    - abandoned_station
    - mysterious_signal
    - silent_earth

  requirement:
    statement: >
      Novelty should emerge from causal combination, character,
      theme and reveal architecture rather than simply inventing
      increasingly bizarre surface elements.

  cliché_detector:
    aggressive: true


# ==============================================================
# FRANCHISE / SERIES POTENTIAL
# ==============================================================

continuation_potential:

  preserve:
    - unanswered_world_history
    - aria_identity_questions
    - unexplored_locations
    - possible_external_survivors_or_intelligences
    - past_relationships

  avoid:
    - resolving_everything_about_aria
    - explaining_entire_world
    - making_first_short_require_sequel

  standalone_requirement:
    value: true


# ==============================================================
# CREATIVE LATITUDE
# ==============================================================

delegation:

  quantum_should_decide:

    - exact_year
    - station_history
    - supporting_character_history
    - specific_story_structure
    - exact_hidden_truth
    - specific_clue_sequence
    - scene_count
    - dialogue
    - title_if_better_one_emerges

  quantum_may_challenge:

    - self_transmission_candidate
    - exact_station_function
    - memory_mechanism

  quantum_must_preserve:

    - emotional_intent
    - thematic_ambition
    - mindfuck_recontextualization
    - grounded_science_fiction_feeling
    - aria_as_core_character


# ==============================================================
# OPEN QUESTIONS
#
# These are explicitly unresolved, not missing data.
# ==============================================================

open_questions:

  - id: q001
    question: >
      What actually happened to humanity?
    needs_resolution_for_this_short: false

  - id: q002
    question: >
      Why is Aria's memory discontinuous?
    needs_resolution_for_this_short: likely

  - id: q003
    question: >
      What is the actual origin of the signal?
    needs_resolution_for_this_short: true

  - id: q004
    question: >
      Was there a specific person important to Aria?
    needs_resolution_for_this_short: delegated


# ==============================================================
# CANDIDATE IDEAS
#
# Preserve ideas that should be explored without canonizing them.
# ==============================================================

candidate_ideas:

  - id: candidate_001

    idea: >
      The transmission comes from an earlier memory-state of Aria.

    promise:
      - strong_theme_alignment
      - personal_reveal

    risk:
      - could_feel_predictable
      - requires_clear_memory_rules

    status: explore


# ==============================================================
# CREATOR NOTEBOOK
#
# Near-lossless summary of the raw creative thinking.
# ==============================================================

creator_notebook: |

  The station should feel lonely but beautiful, not horror-dark.

  Earth through the glass keeps coming back to me.

  Maybe the transmission starts with breathing.

  I like the idea of Aria being an existing character we can
  reuse rather than someone invented only to serve this plot.

  The final five seconds should really fuck with your head.

  Ideally the audience understands what's happening just before
  Aria does.

  No cheesy explanation afterward.

  Maybe the message is actually hers, but don't force that if
  there is a much stronger idea.

  I want the short to work emotionally even for somebody who
  doesn't completely solve the mechanics.
```

That's much closer to what I'd actually use.

---

# The intake agent should make implicit ideas explicit

This is important.

During conversation you might say:

> I want to reuse characters so if something hits we can make a series.

That implies quite a lot.

The intake agent should derive:

```yaml
continuation_potential:

  reusable_character_priority: high

  character_design_requirement:
    statement: >
      Protagonists should possess unresolved internal and external
      story engines beyond the immediate short.

  canonical_asset_requirement:
    statement: >
      Character identity should be developed independently of the
      episode storyline and persist across productions.

  first_episode_policy:
    avoid_exhausting_character_mysteries: true
```

You didn't need to say every sentence.

But the agent must mark those as:

```yaml
provenance: agent_interpretation
confidence: 0.96
derived_from:
  - conversation.turn_...
```

Now downstream agents don't have to rediscover the implication.

---

# I want the intake compiler doing semantic expansion, not creative resolution

There's a subtle boundary here.

Suppose you say:

> Make the world feel old.

The intake agent is allowed to expand what that means:

```text
wear
repairs
technology generations layered together
architecture from different periods
obsolete signage
objects whose original context is gone
```

because that makes your intent legible.

But it should **not** silently decide:

> The station was built in 2298 by the Sino-European Orbital Authority.

That's a creative decision.

That belongs to the Development Compiler.

So:

```text
Conversation
     ↓
Creative Intake
     ↓
MAKE INTENT EXPLICIT

Development Compiler
     ↓
MAKE CREATIVE DECISIONS
```

Excellent separation of concerns.

---

# This also drastically improves agent judgment downstream

Instead of the Writer getting:

```text
Genre: science fiction
Theme: memory
Twist ending
```

it gets perhaps 10,000 tokens describing exactly what those things mean.

The Director doesn't merely get:

```text
Visual style: cinematic
```

It receives:

```text
camera movement philosophy
composition philosophy
negative space preference
lighting semantics
color semantics
recurring motifs
forbidden imagery
character physicality
emotional expression philosophy
setting architecture
editorial pacing
```

Less ambiguity means less model variance.

And more importantly:

**creative variance occurs where we explicitly want creative variance.**

---

# I would actually preserve raw conversation references

Not necessarily the entire transcript in every downstream prompt.

But `creative.yaml` should carry traceability.

For example:

```yaml
provenance_index:

  src_001:
    type: conversation
    turn: 14
    semantic_summary: >
      Creator establishes that Quantum productions have no
      human production intervention other than creator input.

  src_002:
    type: conversation
    turn: 22
    semantic_summary: >
      Creator strongly values reusable recurring characters
      as a path to series development.

  src_003:
    type: conversation
    turn: 31
    semantic_summary: >
      Creator prefers highly detailed creative source artifacts
      because downstream ambiguity is undesirable.
```

Then a decision can say:

```yaml
derived_from:
  - src_002
  - src_003
```

That will become extremely useful later.

---

# Four representations instead of three

I'd now formalize this:

```text
                         HUMAN
                           │
                           ▼
                 Conversation Transcript
                           │
                           ▼
╔══════════════════════════════════════════════╗
║ 1. CREATIVE DOSSIER                         ║
║ creative.yaml                               ║
║                                             ║
║ Rich semantic representation of your intent║
║ Candidates, ambiguity, taste, goals, ideas  ║
╚═══════════════════════╤══════════════════════╝
                        │
                        ▼
╔══════════════════════════════════════════════╗
║ 2. STUDIO SPEC                              ║
║ quantum.studio.yaml                         ║
║                                             ║
║ Fully resolved canon + production intent    ║
║ Quantum has made the creative decisions     ║
╚═══════════════════════╤══════════════════════╝
                        │
                        ▼
╔══════════════════════════════════════════════╗
║ 3. COMPILER IRs                             ║
║ *.ir.json                                   ║
║                                             ║
║ Story, screenplay, performance, shots, etc. ║
╚═══════════════════════╤══════════════════════╝
                        │
                        ▼
╔══════════════════════════════════════════════╗
║ 4. LOCKED EXECUTABLE                        ║
║ animatic.lock                               ║
║                                             ║
║ Exact movie ready for expensive production  ║
╚═══════════════════════╤══════════════════════╝
                        │
                        ▼
                    MASTER VIDEO
```

And that gives us an interesting definition:

> **`creative.yaml` is not a prompt. It is the serialized creative consciousness of the project.**

That is the level of richness I'd target.

The next design decision I would make is the **Development Compiler itself**: the exact sequence of agents that takes this giant creative dossier and produces `quantum.studio.yaml`—Character Architect, World Architect, Theme Architect, Reveal Architect, Relationship Architect, Canon Critic, etc.—including what each one is allowed to decide and how competing creative directions get scored.

----

Yes. I’d make **Autonomous QC a first-class runtime subsystem**, not a critic bolted onto the end.

The core idea is:

> **Every artifact must earn the right to become an input to the next compiler stage.**

```text
                    GENERATED ARTIFACT
                           │
                           ▼
                 ┌──────────────────┐
                 │ Hard Validators  │
                 └────────┬─────────┘
                          │ valid
                          ▼
                 ┌──────────────────┐
                 │ Specialist       │
                 │ Critics          │
                 └────────┬─────────┘
                          │ evidence
                          ▼
                 ┌──────────────────┐
                 │ Adjudicator      │
                 └────────┬─────────┘
                          │
             ┌────────────┴────────────┐
             ▼                         ▼
           PASS                       FAIL
             │                         │
             ▼                         ▼
           COMMIT               Root-Cause Analysis
                                       │
                                       ▼
                                Repair Planner
                                       │
                                       ▼
                            Smallest possible recompile
                                       │
                                       └──────────► QC
```

The difference between this and “LLM-as-a-judge” is enormous.

---

# 1. QC starts with a Quality Contract

`creative.yaml` describes what **you want**.

`quantum.studio.yaml` should compile that into an explicit machine-evaluable quality contract.

For example:

```yaml
quality:

  philosophy:
    prioritize:
      - narrative_coherence
      - emotional_effect
      - character_integrity
      - visual_intent
      - technical_integrity

    never_trade_off:
      - canon_for_beauty
      - coherence_for_surprise
      - character_for_plot_convenience

  gates:

    narrative_coherence:
      critical: true
      minimum: 0.92

    character_integrity:
      critical: true
      minimum: 0.94

    continuity:
      critical: true
      minimum: 0.95

    reveal_fairness:
      critical: true
      minimum: 0.90

    emotional_effect:
      minimum: 0.86

    cinematography:
      minimum: 0.84

    originality:
      minimum: 0.80

    audio:
      minimum: 0.90

    technical:
      critical: true
      minimum: 0.99

  overall_target: 0.90

  repair:
    local_attempts: 3
    scene_attempts: 2
    structural_attempts: 2

    prefer_minimum_blast_radius: true
```

The critical idea is:

```text
overall score = 0.96
```

does **not** mean pass if:

```text
continuity = 0.63
```

Critical dimensions have floors.

Only after all mandatory constraints pass should an overall preference score be relevant.

---

# 2. Three fundamentally different QC mechanisms

I would not make everything an agent.

### Deterministic Validators

No judgment.

Examples:

```text
video exists
video decodes
expected duration matches
frame count correct
audio track present
no NaNs
no black-frame sequence
no corrupted frames
dialogue clip exists
subtitle timestamps valid
scene runtime budget satisfied
asset IDs resolve
required character exists
forbidden asset absent
```

If:

```python
actual_duration_ms != expected_duration_ms
```

you don't need a philosopher.

Fail it.

### Specialist Critics

These exercise judgment.

Examples:

```text
Does Aria still look like Aria?
Does this performance communicate restrained grief?
Is the edit confusing?
Does this shot actually express its narrative function?
Is the reveal fair?
Is this composition intentional?
```

They produce **claims backed by evidence**.

### Adjudicators

They evaluate critics.

This is important.

Suppose:

```text
PerformanceCritic: PASS 0.91
EmotionCritic: FAIL 0.72
DirectorCritic: PASS 0.88
```

The system needs to determine whether there is a real failure, disagreement, or uncertainty.

That's the Adjudicator's job.

---

# 3. Critics should never return merely `7.8/10`

Every critique should have a machine-actionable form.

Something like:

```python
class Violation(BaseModel):

    code: str

    severity: Literal[
        "info",
        "minor",
        "major",
        "critical",
    ]

    confidence: float

    scope: Literal[
        "frame",
        "shot",
        "scene",
        "episode",
    ]

    artifact_id: str

    evidence: list["Evidence"]

    expected: str
    observed: str

    violated_requirement_refs: list[str]

    likely_owner: str

    repairability: str


class Evidence(BaseModel):
    start_ms: int | None
    end_ms: int | None
    frame_ids: list[int] = []
    description: str
```

Example:

```yaml
code: CHARACTER.IDENTITY.DRIFT

severity: critical
confidence: 0.97

scope: shot
artifact_id: sc04_sh017_take02

evidence:
  - start_ms: 1840
    end_ms: 3270
    description: >
      Aria's right-temple fracture disappears and both eyes
      shift from amber to pale blue.

expected: >
  Aria canonical variant aria@v4.

observed: >
  Character appearance diverges from canonical identity during
  second half of shot.

likely_owner: shot_renderer

repairability: rerender_take
```

Now the Repair Planner can do something useful.

---

# 4. QC happens at every compiler boundary

Not just after the movie exists.

I would have gates like this:

| Stage                 | Primary QC question                                        |
| --------------------- | ---------------------------------------------------------- |
| `creative.yaml`       | Did intake preserve creator intent accurately?             |
| `quantum.studio.yaml` | Is the developed concept internally coherent and faithful? |
| Character/World Bible | Are canon entities deep, coherent, and story-generating?   |
| Reveal Plan           | Is the twist causal, fair, meaningful, non-cliché?         |
| StoryIR               | Does the story work structurally?                          |
| ScreenplayIR          | Do scenes, dialogue, motivation and information flow work? |
| PerformanceIR         | Does synthesized acting communicate intended performance?  |
| ShotIR                | Is there valid cinematic coverage?                         |
| StoryboardIR          | Do compositions communicate the intended shots?            |
| Animatic              | Does the actual film work over time?                       |
| Generated Takes       | Are individual shots production quality?                   |
| Final Timeline        | Do neighboring shots work together?                        |
| Mix                   | Does sound function dramatically and technically?          |
| Master                | Is the complete deliverable valid and coherent?            |

This is why QC belongs inside the compiler architecture.

---

# 5. The most important QC artifact is the animatic

For Quantum, **the animatic should receive brutally deep evaluation** because it's the last point where major repairs are cheap.

Once you're generating hundreds of expensive video shots, discovering:

> Scene 4 doesn't emotionally work.

is unacceptable.

At the animatic stage, I want several distinct viewers.

```text
                         ANIMATIC
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
          ▼                 ▼                  ▼
     Cold Viewer        Informed Critic    Film Critic
          │                 │                  │
          └─────────────────┼──────────────────┘
                            ▼
                       Adjudicator
```

And these should intentionally receive **different information**.

---

# 6. The Cold Viewer Critic 🔥

This one should know essentially **nothing about the hidden story**.

Give it the animatic like a viewer encountering the movie for the first time.

Do not tell it:

```text
the twist
hidden truth
clue plan
intended interpretation
```

At checkpoints such as:

```text
25%
50%
75%
90%
100%
```

ask it to construct its current model:

```yaml
viewer_model:

  believes:
    transmission_is_external: 0.78
    sender_is_human: 0.61
    sender_knows_aria: 0.24

  suspects:
    aria_memory_problem: 0.31

  unanswered:
    - why station is empty
    - who sent message

  emotion:
    curiosity: 0.81
    hope: 0.43
    dread: 0.26
```

Now we can test whether the story is manipulating audience knowledge correctly.

For a mindfuck story, this is extremely powerful.

We aren't asking:

> Is the twist good?

We're measuring:

> **What does a viewer think is happening at each moment?**

---

# 7. Reveal QC becomes measurable

Suppose the intended audience belief trajectory is:

```text
0–45 sec
"Someone on Earth survived."

45–53 sec
"Something about this doesn't make sense."

53–57 sec
"Wait... is this Aria?"

57–60 sec
"Oh shit."
```

The Cold Viewer can expose failures.

### Failure A: twist obvious too early

At 22 seconds:

```text
P(self_transmission) = 0.82
```

Fail:

```text
REVEAL.PREMATURE
```

### Failure B: twist impossible to infer

At 59 seconds:

```text
P(self_transmission) = 0.08
```

and after ending the critic says:

> I don't understand what happened.

Fail:

```text
REVEAL.UNSUPPORTED
```

### Ideal

At 54 seconds:

```text
P(self_transmission) = 0.35
```

At 57 seconds:

```text
P(self_transmission) = 0.79
```

At 60:

```text
P(self_transmission) = 0.96
```

Exactly what you described:

**viewer reaches the realization roughly one second before Aria.**

That's something Quantum can actively optimize toward.

---

# 8. Then an Informed Reveal Critic watches it

This critic *does* know:

```text
hidden truth
clue plan
theme
character arc
intended audience trajectory
```

It asks different questions:

```text
Are all necessary clues present?
Did anything contradict the reveal?
Was information unfairly hidden?
Do earlier scenes genuinely change meaning afterward?
Is the reveal causal?
Is it thematic or merely surprising?
```

Then a third critic performs a **rewatch test**.

After being told the truth:

> Watch the animatic again. Identify evidence that acquires a different meaning.

A strong reveal should create something like:

```text
Shot 2:
Previously = Aria's harmless habit.
Now        = evidence of prior memory continuity.

Shot 6:
Previously = signal artifact.
Now        = recognizable maintenance protocol.

Shot 9:
Previously = emotional reaction.
Now        = subconscious recognition.
```

That is much more interesting than generic twist scoring.

---

# 9. Story QC

The StoryCritic should operate on structure before we even have video.

It should evaluate things like:

```text
cause → consequence
goal → obstacle
decision → outcome
setup → payoff
clue → interpretation → reveal
character belief → pressure → change
```

A good story representation allows deterministic structural validation too.

For example:

```text
CLUE_04
    introduced scene 3
         ↓
    supports reveal R1

R1
    occurs scene 6
```

Valid.

But:

```text
CLUE_04
    introduced scene 7

R1
    occurs scene 6
```

Impossible as foreshadowing.

Fail automatically.

Story QC should catch failures such as:

```text
character acts without motivation
scene produces no meaningful state change
conflict disappears arbitrarily
protagonist becomes passive
critical information appears from nowhere
setup never pays off
payoff lacks setup
knowledge leaks to character
ending violates established rule
```

---

# 10. Character QC

There are really two kinds.

### Canon consistency

Does behavior agree with the established character?

If Aria is:

```text
highly competent engineer
```

the script cannot require her to overlook a trivial electrical fault for 20 minutes.

That's:

```text
CHARACTER.COMPETENCE_VIOLATION
```

### Dramatic consistency

A character can behave unexpectedly—but the deviation must have a cause.

For example:

```text
Aria normally avoids emotional language.

Scene 8:
"I am terrified that nobody will ever love me."

```

Could technically fit the story.

But probably fails her established performance language unless extraordinary prior pressure has justified it.

The CharacterCritic should say:

```text
Observed behavior conflicts with:
character.aria.speech.emotional_directness = low

No sufficient state transition exists between scenes 1–8
to justify this degree of explicitness.
```

That's actionable.

---

# 11. Shot-level visual QC

Once real video generation starts, each candidate take goes through a cascade.

Do **cheap objective checks first**:

```text
decode
resolution
duration
frame count
black frames
frozen sequences
gross AV sync
```

Then visual checks:

```text
identity consistency
character count
prop presence
location consistency
camera instruction
action instruction
geometry stability
hands/body integrity
temporal flicker
lighting consistency
text/signage consistency
background mutation
motion quality
lip motion
```

Then artistic checks:

```text
composition
performance
emotional readability
cinematic quality
shot usefulness
```

This saves compute because obviously broken takes don't reach expensive critics.

---

# 12. Multiple takes should use ranking, not absolute scores alone

Suppose:

```text
Take A
Take B
Take C
```

First:

```text
hard validation
```

Maybe C fails because Aria's hand mutates.

Gone.

Then compare A versus B directly:

```text
Which better satisfies this exact ShotSpec?
```

Pairwise evaluation tends to be easier than independently deciding:

```text
A = 0.8731
B = 0.8862
```

The system can run a tournament:

```text
A ──┐
    ├─ B wins
B ──┘

B ──┐
    ├─ B wins
D ──┘

Winner = B
```

But before committing B, evaluate it **in context**:

```text
Shot 216
   ↓
Take B for Shot 217
   ↓
Shot 218
```

Because the best standalone shot can still be the wrong edit.

---

# 13. Contextual QC matters enormously

Consider three perfect shots:

```text
216 = close-up
217 = close-up
218 = close-up
```

Each could score:

```text
0.95
```

individually.

Together the scene may feel visually monotonous.

Therefore there are different scopes:

```text
FRAME QC
SHOT QC
SHOT-PAIR QC
SCENE QC
SEQUENCE QC
EPISODE QC
```

A critic gets a different context at each scope.

For a 24-minute short, we should not rely on one gigantic multimodal prompt.

Instead:

```text
shots
 ↓
shot reports
 ↓
scene evaluation
 ↓
scene reports
 ↓
sequence evaluation
 ↓
episode evaluation
```

Hierarchical QC scales much better.

---

# 14. Cinematography QC

This critic gets:

```text
ShotIR
previous ShotIR
next ShotIR
scene objective
visual language
storyboard/video
```

and evaluates:

```text
shot size progression
screen direction
eyelines
subject emphasis
visual hierarchy
camera motivation
spatial clarity
coverage redundancy
lens consistency
camera rhythm
reaction coverage
establishing geography
```

For example:

```yaml
violation:
  code: CAMERA.REDUNDANT_COVERAGE

  evidence:
    shots:
      - sc04_sh011
      - sc04_sh012
      - sc04_sh013

  observed: >
    Three consecutive medium-close framings from essentially
    identical screen position produce no meaningful change
    in visual information.

  severity: major

  likely_owner: director

  suggested_scope: scene_shot_plan
```

That does **not** trigger video regeneration first.

It triggers:

```text
DirectorPass(scene 4)
```

because the underlying shot design is wrong.

---

# 15. This root-cause distinction is critical

Suppose Aria isn't visibly sad enough.

There are multiple possible causes:

```text
Bad render?
Bad storyboard?
Bad directorial framing?
Bad performance direction?
Bad screenplay?
Bad story beat?
```

Blindly regenerating the video could waste hundreds of attempts.

QC must diagnose the **owning compiler stage**.

I would keep a mapping:

```text
VIOLATION                        LIKELY OWNER

geometry mutation             → renderer
identity drift                → renderer / asset resolution
bad composition               → storyboard / director
poor scene coverage           → director
line doesn't fit timing       → screenplay/director
flat vocal performance        → performance engine
exposition-heavy scene        → screenplay
unmotivated decision          → story
weak reveal                   → reveal architecture
theme contradiction           → development compiler
```

Then repair targets that stage.

---

# 16. Minimum-blast-radius repair 🔥

Every potential repair has a cost.

Conceptually:

```text
repair_cost =
    regeneration_compute
  + invalidated_downstream_artifacts
  + creative_risk
  + continuity_risk
```

So if shot 217 contains bad hand geometry:

```text
rerender take              cost 1
redesign shot              cost 8
rewrite scene              cost 40
rewrite screenplay         cost 200
change story               cost 1000
```

Quantum chooses:

```text
rerender take
```

But suppose all six render attempts fail because the shot requires an unusually difficult interaction.

Then:

```text
renderer failure × 6
       ↓
RepairPlanner diagnoses:
shot is low-renderability
       ↓
Director generates equivalent simpler shot
       ↓
shot 217b
```

For example:

Instead of:

> Aria catches a spinning transparent receiver one-handed while turning toward camera.

Director might preserve narrative intent with:

> Receiver hits floor. Cut to Aria's reaction. Insert of receiver.

Same story.

Much easier generation.

That's autonomous filmmaking.

---

# 17. Repair escalation

I would formalize repair scopes:

```text
LEVEL 0     select another existing take
LEVEL 1     rerender same take specification
LEVEL 2     adjust rendering constraints
LEVEL 3     redesign shot
LEVEL 4     redesign neighboring coverage
LEVEL 5     rewrite scene
LEVEL 6     modify story beat
LEVEL 7     modify Quantum-developed canon
```

Creator-locked decisions sit above that and are immutable.

Quantum automatically climbs only when lower levels fail.

For example:

```python
async def repair(violation):

    for scope in allowed_scopes(violation):

        result = await attempt_repair(scope)

        qc = await evaluate(result)

        if qc.pass_:
            return result

    raise UnsatisfiableBuild(...)
```

“No human interaction” means there is no:

```text
Please approve retry #4
```

Quantum either solves it within its authority or produces a failed build report.

It should **never silently violate a creator lock** just because rendering was inconvenient.

---

# 18. Performance QC

Voice acting deserves its own subsystem.

There are objective checks:

```text
text spoken correctly
word omissions
pronunciation
speaker identity
duration
clipping
noise
audio integrity
```

And judgment checks:

```text
intention
subtext
emotional trajectory
naturalness
restraint
pace
breath
pause placement
```

The critic receives:

```yaml
line:
  text: "I remember this."

intention: conceal_fear

subtext: >
  She recognizes something impossible and does not want
  to admit it.

delivery:
  - restrained
  - quiet
  - involuntary_recognition
```

Then evaluates the actual audio.

We can generate several performances exactly like video takes.

```text
Performance A
Performance B
Performance C
       ↓
PerformanceCritic
       ↓
selected performance
```

---

# 19. Lip-sync QC

This can be quite mechanical.

Quantum knows:

```text
speech phoneme timings
expected mouth motion timing
actual rendered mouth motion
```

We should calculate offset distributions.

If:

```text
speech onset = 18,200 ms
mouth onset  = 18,540 ms
```

then:

```text
AV offset = +340 ms
```

Fail.

This should not need a general-purpose artistic critic.

---

# 20. Audio QC should operate across cuts

Sound is especially important because visual regeneration will naturally introduce discontinuities.

The SoundCritic needs to detect:

```text
ambience jumps
room-tone mismatch
unmotivated reverb change
music edit discontinuity
dialogue masking
clipping
frequency imbalance
loudness problems
unintentional silence
SFX timing mismatch
```

And then also judge:

```text
Does silence land?
Does the transmission feel mysterious?
Does music reveal the twist too early?
Does the score emotionally over-explain?
```

Remember our creative dossier explicitly says things like:

```text
score should not telegraph reveal
```

That becomes a QC criterion.

---

# 21. The Editor needs its own critic

A generated set of excellent shots does not imply an excellent movie.

The EditCritic evaluates:

```text
cut motivation
rhythm
pacing
shot duration
reaction timing
information density
continuity
visual repetition
audio bridges
scene transitions
emotional timing
```

One particularly useful metric is **information per unit time**.

A 60-second short can fail because:

```text
0–35 sec = very little story
35–57 sec = massive exposition
57–60 sec = twist
```

even though every individual scene is competent.

The critic can identify this structurally from the timeline.

---

# 22. Have separate fidelity and quality critics

This is important.

Something can be excellent but not what **you asked for**.

Imagine Quantum creates a hilarious 60-second comedy.

Maybe it's objectively fantastic.

But `creative.yaml` said:

```text
melancholic
existential
beautiful
unsettling
```

That's still a failure.

So I would have:

```text
CreativeIntentCritic
```

that compares:

```text
creative.yaml
        ↕
actual artifact
```

and asks:

> Did we make the intended film?

Separately:

```text
FilmQualityCritic
```

asks:

> Is this execution strong on its own terms?

Both matter.

---

# 23. Critic independence

I don't want:

```text
Writer generates scene
Writer asks itself if scene is good
Writer says yes
```

Generation and judgment contexts should be separate.

For important gates I'd use independent evaluation passes, potentially with heterogeneous model implementations when available.

Conceptually:

```text
                    Artifact
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
    Critic A         Critic B         Critic C
       │               │               │
       └───────────────┼───────────────┘
                       ▼
                  Adjudicator
```

High agreement:

```text
PASS .94
PASS .92
PASS .96

→ confident PASS
```

High disagreement:

```text
PASS .95
FAIL .54
PASS .87
```

means:

```text
uncertain
```

not blindly averaging to `0.79`.

That should trigger deeper inspection.

---

# 24. Don't let uncertainty disappear into a score

Every QC result should contain something like:

```yaml
result:

  decision: pass

  score: 0.923

  confidence: 0.961

  disagreement: 0.041
```

Another artifact might be:

```yaml
result:

  decision: uncertain

  score: 0.861

  confidence: 0.58

  disagreement: 0.34
```

Quantum can then escalate to a more expensive critic ensemble.

So evaluation itself becomes tiered.

---

# 25. Cheap → expensive QC cascade

I'd optimize execution roughly like:

```text
TIER 0
Deterministic technical validators
            │
            ▼
TIER 1
Cheap single-modality checks
            │
            ▼
TIER 2
Specialized multimodal critics
            │
            ▼
TIER 3
Contextual scene critics
            │
            ▼
TIER 4
Full-film global critics
            │
            ▼
TIER 5
Adversarial / uncertainty review
```

Only ambiguous or important cases climb higher.

At 300 shots, this matters substantially for cost.

---

# 26. QC itself needs QC

This is one of the less obvious but most fundamental requirements for a fully autonomous studio.

If the judges are unreliable, everything collapses.

I would maintain a **QC calibration suite**.

Take known-good artifacts and inject controlled defects:

```text
change Aria eye color
swap left/right damage
remove clue
move clue after reveal
insert 400ms audio offset
freeze 12 frames
duplicate shot
change voice identity
clip audio
remove required prop
reverse screen direction
replace one line with exposition
make reveal obvious 20 seconds early
```

Then test:

```text
Did IdentityCritic catch eye change?
Did RevealCritic catch clue ordering?
Did AVSyncValidator catch offset?
Did EditorCritic catch duplicate coverage?
```

You can quantify each critic:

```text
precision
recall
false-positive rate
false-negative rate
confidence calibration
```

Critics should be versioned exactly like compiler passes.

```text
IdentityCritic@3.2
RevealCritic@1.7
EditCritic@2.4
```

A new critic version must pass the benchmark suite before becoming production default.

---

# 27. The QC record becomes part of provenance

Every committed shot should have:

```yaml
shot: qshot_0217

selected_take: take_04

qc:

  technical:
    pass: true

  identity:
    score: 0.97

  continuity:
    score: 0.96

  performance:
    score: 0.91

  cinematography:
    score: 0.89

  temporal_integrity:
    score: 0.98

  selection:
    method: pairwise_tournament

  rejected_takes:

    take_01:
      reason: geometry_mutation

    take_02:
      reason: weak_performance

    take_03:
      reason: character_identity_drift

  accepted:
    at: 2026-...
    critic_versions:
      - identity@3.2
      - temporal@2.1
      - performance@1.9
```

So later Quantum can answer:

> Why is take 4 in the movie?

with actual evidence.

---

# 28. I would introduce the `QualityGraph`

We already like graphs.

The QC system naturally produces another one:

```text
                      FILM QUALITY
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       STORY          EXPERIENCE          CRAFT
          │                │                │
      ┌───┼───┐        ┌───┼────┐       ┌───┼─────┐
      │   │   │        │   │    │       │   │     │
   logic theme arc   emotion reveal pace image audio edit
```

And underneath:

```text
SC04_SH017
    │
    ├── identity        PASS .97
    ├── temporal        PASS .98
    ├── performance     PASS .91
    ├── composition     PASS .89
    └── continuity      PASS .95
```

Now an episode score is not one magical number.

It's a queryable graph of quality evidence.

---

# 29. What gets locked when animatic passes?

A passing animatic should produce:

```text
animatic.lock
```

with QC certification:

```yaml
qc_certification:

  story:
    status: pass

  reveal:
    status: pass

  character:
    status: pass

  runtime:
    status: pass

  pacing:
    status: pass

  edit:
    status: pass

  creative_intent:
    status: pass

  unresolved:
    allowed: []

  certified_for:
    - final_shot_production
```

At that point Quantum should assume:

> **The movie works. Now manufacture it.**

Shot production isn't allowed to casually reopen story decisions.

---

# 30. Then final production QC becomes much more local

After animatic lock:

```text
Story        LOCKED
Dialogue     LOCKED
Timing       LOCKED
Shot intent  LOCKED
Edit plan    LOCKED
```

Production QC mainly asks:

```text
Did we successfully realize the locked plan?
```

This is much easier than asking a video model to both invent and execute the film simultaneously.

---

# 31. Final master QC

The last gate is deliberately paranoid.

It should compare:

```text
creative.yaml
        ↓
quantum.studio.yaml
        ↓
animatic.lock
        ↓
master.mp4
```

and validate both creative and technical delivery.

I would run a final cold-viewer experiment again.

This is important because something can work in storyboards but become accidentally obvious—or confusing—once acting, lighting, motion, music and editing are added.

So the final film gets:

```text
FIRST WATCH QC
REWATCH QC
CREATOR INTENT QC
CANON QC
TECHNICAL MASTER QC
AUDIO MASTER QC
```

before:

```text
master.mp4
    ↓
RELEASE CERTIFIED
```

No human approval.

---

# 32. The core autonomous loop

So I would codify the entire system around:

```python
async def quality_gate(
    artifact,
    quality_contract,
):

    validation = await run_validators(artifact)

    if validation.failed:
        return await repair(
            artifact,
            validation.violations,
        )

    critiques = await run_specialist_critics(
        artifact,
        quality_contract,
    )

    decision = await adjudicate(critiques)

    if decision.pass_:
        return await commit(artifact, decision)

    diagnosis = await diagnose_root_causes(
        artifact,
        decision.violations,
    )

    plan = await plan_minimum_blast_radius_repair(
        diagnosis,
    )

    repaired = await recompile(plan)

    return await quality_gate(
        repaired,
        quality_contract,
    )
```

With budgets to prevent infinite loops.

---

# The architecture I'd lock in

```text
                       QUALITY CONTRACT
                    from quantum.studio.yaml
                              │
                              ▼
╔════════════════════════════════════════════════════╗
║                QUANTUM AUTONOMOUS QC              ║
║                                                   ║
║ Deterministic Validators                          ║
║            │                                      ║
║ Specialist Critics                                ║
║            │                                      ║
║ Multi-perspective Critics                         ║
║            │                                      ║
║ Adjudicator                                       ║
║            │                                      ║
║ Root-Cause Analyzer                               ║
║            │                                      ║
║ Repair Planner                                    ║
║            │                                      ║
║ Minimum-blast-radius recompilation                ║
╚═══════════════════════╤════════════════════════════╝
                        │
              ┌─────────┴─────────┐
              ▼                   ▼
            COMMIT             REPAIR
              │                   │
              │                   └─────► compiler DAG
              │
              ▼
         NEXT STAGE
```

The part I think gives **Quantum Animation Studio** real teeth is the combination of **spoiler-blind audience simulation + informed structural criticism + precise root-cause repair**.

That makes QC not merely “detect ugly frames,” but capable of autonomously answering things like:

> *Did the audience believe the right wrong thing at second 42, discover the right truth at second 58, feel the intended emotion when they discovered it, and can we repair the film if they didn't?*

That is the level of QC I'd want before claiming the studio is actually human-free.

---
The third concept was **Render / Timeline Execution**.

The sequence we established was:

1. **Compiler** — `creative.yaml → quantum.studio.yaml → IRs → animatic.lock`
2. **Autonomous QC** — validate, judge, diagnose, repair, commit
3. **Render / Timeline Execution** — manufacture the locked film
4. **World Model** — persistent canonical reality/state underneath the whole studio

So now we're at the part where Quantum stops deciding **what movie to make** and starts reliably manufacturing it.

# 3. Render / Timeline Execution

The key rule I would establish is:

> **Rendering is execution, not creativity.**

Once `animatic.lock` exists, the creative problem should mostly be solved.

The production system receives something like:

```text
animatic.lock
      │
      ▼
┌──────────────────────┐
│ Production Compiler  │
└──────────┬───────────┘
           ▼
       Render DAG
           │
    ┌──────┼───────────────┐
    ▼      ▼               ▼
  shots   voices         sound
    │      │               │
    ▼      ▼               ▼
 selected performances   score
 takes                    foley
    │                      │
    └──────────┬───────────┘
               ▼
         Final Timeline
               │
               ▼
           Finishing
               │
               ▼
           master.mp4
```

The challenge here is not really video generation.

It is:

**How do we convert hundreds or thousands of independently generated media artifacts into one deterministic, resumable, reproducible film?**

---

# The central abstraction: Production DAG

DAG = **Directed Acyclic Graph**.

Think of it as the dependency graph for manufacturing the film.

For example:

```text
Character Aria Asset
        │
        ├─────────────┐
        ▼             ▼
    Shot 001       Shot 002
        │             │
        ▼             ▼
    Take 1..N      Take 1..N
        │             │
        ▼             ▼
     Select          Select
        │             │
        └──────┬──────┘
               ▼
            Scene 1
               │
               ▼
          Episode Edit
```

And independently:

```text
Dialogue Line 17
      │
      ▼
Voice Performance
      │
      ├───────────────┐
      ▼               ▼
Lip-sync info     Final dialogue track
      │
      ▼
Shot 014
```

Music:

```text
Timeline
   │
   ▼
Music Cue Plan
   │
   ▼
Cue 1 ─┐
Cue 2 ─┼──► score stem
Cue 3 ─┘
```

Final master:

```text
picture lock
dialogue
foley
ambience
score
captions
color treatment
        │
        ▼
      MASTER
```

The DAG tells Quantum:

* what can execute in parallel
* what must wait
* what became invalid after a change
* what can be reused
* what failed
* what should be regenerated

---

# A shot becomes an executable task

The locked plan might contain:

```yaml
shot:
  id: sc04_sh017

  duration_ms: 4875

  character_variants:
    - aria@damaged_v2

  location:
    observation_deck@v3

  action: >
    Aria slowly raises her head as she recognizes
    the voice in the transmission.

  performance:
    emotion: suppressed_recognition

  camera:
    framing: close_up
    lens_mm: 65
    motion: slow_push_in

  continuity:
    previous: sc04_sh016
    next: sc04_sh018

  dialogue:
    - dlg_0041

  production:
    target_takes: 4
```

Production Compiler transforms this into runnable jobs:

```text
Resolve assets
      ↓
Build render conditioning package
      ↓
Generate Take A
Generate Take B
Generate Take C
Generate Take D
      ↓
Technical QC
      ↓
Visual QC
      ↓
Pairwise selection
      ↓
Contextual QC with shots 216/218
      ↓
COMMIT take
```

---

# Render package

I'd create an explicit artifact for every shot:

```text
RenderPackage
```

This is everything a video generator needs.

```python
class RenderPackage(BaseModel):
    shot_id: str

    duration_ms: int
    fps: float
    resolution: tuple[int, int]

    visual_prompt: str
    negative_constraints: list[str]

    character_refs: list[AssetReference]
    environment_refs: list[AssetReference]
    prop_refs: list[AssetReference]

    start_frame_ref: str | None
    end_frame_ref: str | None

    camera: CameraSpec
    action: ActionSpec
    performance: PerformanceSpec

    dialogue_audio_refs: list[str]

    seed: int

    provider_options: dict
```

Notice something important:

The renderer should **not** receive the entire screenplay.

It gets precisely the local execution package required to make the shot.

This dramatically reduces ambiguity.

---

# Separate semantic shot intent from provider prompts

Never store only this:

```text
"cinematic close-up of robot sad..."
```

That's disposable provider-specific garbage.

Store:

```text
ShotIR
```

as authoritative.

Then have:

```text
ShotIR
   ↓
ProviderAdapter
   ↓
ProviderPrompt
```

For provider A:

```text
prompt_A(...)
```

For provider B:

```text
prompt_B(...)
```

For some future animation system:

```text
control_graph(...)
```

The film doesn't become coupled to today's model interface.

---

# The renderer abstraction

Something like:

```python
class VideoRenderer(Protocol):

    async def render(
        self,
        package: RenderPackage,
    ) -> RenderResult:
        ...
```

Then implementations:

```python
class ProviderAVideoRenderer:
    ...

class ProviderBVideoRenderer:
    ...

class LocalVideoRenderer:
    ...
```

The Production Planner can choose based on shot characteristics.

For example:

```text
dialogue-heavy close-up
    → renderer optimized for faces/lip-sync

large atmospheric establishing shot
    → renderer optimized for cinematic environments

fast action
    → renderer optimized for temporal coherence
```

Eventually that itself can become a judgment agent:

```text
RendererRouterAgent
```

---

# Rendering should be heterogeneous

I would absolutely not assume:

> One video model renders the entire film.

Different shots have different demands.

Example:

```text
Shot 001
giant station establishing shot
    → Model X

Shot 002
Aria delicate facial acting
    → Model Y

Shot 003
hand manipulating physical device
    → Model Z

Shot 004
mostly static composition
    → image + controlled motion

Shot 005
display insert
    → deterministic compositing
```

Even more importantly:

**not every shot should be generative video.**

Some are better manufactured using deterministic tools.

---

# Hybrid rendering is a major advantage

Suppose a shot contains:

```text
computer display with readable text
```

Don't ask a video model to hallucinate it perfectly.

Generate:

```text
background plate
```

then composite:

```text
UI graphic
```

deterministically.

Same with:

```text
screens
signage
captions
logos
precise diagrams
stars
certain particle effects
certain camera moves
```

You want:

```text
GENERATIVE WHERE CREATIVITY HELPS
DETERMINISTIC WHERE PRECISION HELPS
```

That's likely going to outperform “generate everything.”

---

# Shot components could be layered

Longer term, one shot could be represented as:

```text
               SHOT
                │
       ┌────────┼─────────┐
       ▼        ▼         ▼
 background  character   FX
       │        │         │
       └────────┼─────────┘
                ▼
            composite
                │
                ▼
              shot
```

This gives Quantum finer repair granularity.

Suppose:

```text
Aria performance = excellent
window Earth = incorrect
```

Instead of regenerating everything:

```text
replace Earth layer
```

That's far cheaper and more stable.

---

# Render lineage

Every generated artifact should carry lineage.

```yaml
artifact:
  id: qrender_840182

  type: video_take

  shot_id: sc04_sh017
  take: 3

  derived_from:
    shot_ir: sha256:...
    render_package: sha256:...

  dependencies:
    aria_asset: aria@v4
    observation_deck: observation_deck@v2
    dialogue: dlg_0041@v2

  renderer:
    adapter: cinematic_video_v3
    provider_model: ...
    model_version: ...

  seed: 92717

  output:
    uri: artifact://...
    sha256: ...
```

Then you can reconstruct exactly why a frame exists.

---

# Content-addressed artifacts

This becomes extremely powerful.

Artifact identity should depend on inputs:

```python
artifact_key = sha256(
    canonical_json({
        "task": "render_shot",
        "task_version": "3",
        "shot": shot_hash,
        "assets": asset_hashes,
        "renderer": renderer_version,
        "seed": seed,
    })
)
```

If exactly the same task has previously run:

```text
cache HIT
```

No generation call.

This makes production restartable and reproducible.

---

# You want aggressive parallelism

For 300 shots:

```text
Shot 001
Shot 002
Shot 003
...
Shot 300
```

Most should be renderable concurrently once their dependencies exist.

Conceptually:

```python
await asyncio.gather(*[
    produce_shot(shot)
    for shot in production.shots
])
```

Obviously real infrastructure would impose:

```text
provider quotas
GPU capacity
cost limits
rate limits
priority
dependency scheduling
```

But conceptually this is massively parallel.

A 20-minute film stops being:

```text
generate 20 minutes
```

and becomes:

```text
execute ~250 independent manufacturing jobs
```

Much easier to scale.

---

# But scenes introduce neighbor dependencies

Shot 217 can't necessarily be finalized completely independently.

It may need:

```text
216
217
218
```

for transition QC.

So I would distinguish:

```text
SHOT READY
```

from:

```text
SHOT COMMITTED
```

Workflow:

```text
217 rendered
    ↓
local QC passes
    ↓
READY

216 ready
217 ready
218 ready
    ↓
contextual QC
    ↓
217 COMMITTED
```

The renderer can stay parallel while editorial validation handles local windows.

---

# Production state machine

Each shot could move through:

```text
PLANNED
   ↓
PACKAGED
   ↓
RENDERING
   ↓
CANDIDATES_READY
   ↓
LOCAL_QC
   ↓
CANDIDATE_SELECTED
   ↓
CONTEXT_QC
   ↓
COMMITTED
```

Failures:

```text
LOCAL_QC_FAILED
RENDER_FAILED
REPAIR_REQUIRED
DIRECTOR_REPLAN_REQUIRED
```

This is far easier to observe and recover than generic workflow logs.

---

# Now Timeline Execution

This is the other half.

Once selected shots exist, Quantum needs one canonical timeline representation.

I'd strongly separate:

```text
semantic editorial timeline
```

from:

```text
FFmpeg commands
```

The semantic timeline is authoritative.

Example:

```yaml
timeline:
  fps: 24

  tracks:

    video_primary:

      - id: clip_001
        shot: sc01_sh001
        start_frame: 0
        duration_frames: 107

      - id: clip_002
        shot: sc01_sh002
        start_frame: 107
        duration_frames: 84

    dialogue:

      - id: dlg_clip_01
        source: dlg_0041
        start_frame: 238
        gain_db: -1.2

    ambience:

      - source: station_roomtone_03
        start_frame: 0
        duration_frames: 1440

    music:

      - source: cue_01
        start_frame: 0
        fade_in_frames: 72

    sfx:

      - source: receiver_click
        start_frame: 514
```

All time should ultimately become **frame-addressed**, even if higher-level IRs work in milliseconds.

Why?

At 24 fps:

```text
frame 713
```

is unambiguous.

No floating-point edit drift.

---

# Timeline should probably be immutable once picture-lock occurs

During animatic:

```text
TimelineIR v1
TimelineIR v2
TimelineIR v3
```

Once QC passes:

```text
PICTURE_LOCK
```

Now final video generation must conform to those shot durations.

If final take is slightly too long:

```text
trim
```

If slightly short:

```text
reject / regenerate
```

Do **not** casually move every downstream cut.

Otherwise every generated variation changes the whole movie.

---

# Handles

Traditional post-production has the concept of handles, and Quantum should too.

If Shot 217 appears for:

```text
4.2 seconds
```

ask the renderer for perhaps:

```text
4.8 seconds
```

giving:

```text
300ms pre-roll
4.2 sec usable
300ms post-roll
```

Then Editor can adjust the exact cut without regenerating.

```text
|---HANDLE---|====== USED ======|---HANDLE---|
```

This gives autonomous editorial some breathing room.

---

# Generate audio stems separately

Never manufacture one giant finished soundtrack early.

Keep:

```text
DX   dialogue
FX   effects
FOLEY
AMB  ambience
MX   music
```

separate until mastering.

```text
Dialogue ───────────┐
Foley ──────────────┤
SFX ────────────────┤
Ambience ───────────┤──► Mix Engine
Music ──────────────┘
```

This gives QC and repair independence.

Example:

```text
music too loud
```

doesn't require remaking the scene.

---

# Sound effects need semantic events

Don't just ask:

> Generate SFX for this movie.

Shot/event IR already knows:

```yaml
events:
  - at_ms: 1840
    type: receiver_button_pressed

  - at_ms: 1910
    type: mechanical_relay_click

  - at_ms: 2200
    type: transmission_begins
```

SoundDesigner translates these into:

```text
sound assets + timing + spatialization
```

This is another compiler.

```text
Narrative/Physical Event
       ↓
SoundEventIR
       ↓
SoundDesigner
       ↓
Audio Asset
       ↓
Timeline
```

---

# Foley should understand physical materials

If Aria walks:

```text
surface = steel_grating
body = synthetic
foot_material = polymer/metal
room = large_service_corridor
```

that implies a very different sound from:

```text
carpet
human shoe
small office
```

These semantics should reach the sound engine.

Eventually the World Model helps enormously here—but we're saving that.

---

# Music is timeline-aware

Composer gets the complete emotional structure:

```text
00:00–00:10    isolation
00:10–00:27    curiosity
00:27–00:45    hope + suspicion
00:45–00:55    recognition
00:55–00:58    withdraw
00:58–01:00    silence / final sting
```

Instead of:

> Make 60 seconds of sad sci-fi music.

And ideally music comes as stems:

```text
piano
strings
texture
pulse
```

so the Mix Agent can manipulate them independently.

---

# Dialogue has to stay the timing master

As discussed earlier:

```text
screenplay
   ↓
voice performance
   ↓
actual duration
   ↓
shot timing
```

By final production, voice lines are locked.

Rendered shots conform to the voice track.

This is another reason `animatic.lock` matters so much.

---

# Final editing shouldn't be fully locked to the animatic in microscopic details

There's a subtlety.

The **structural edit** should be locked.

But Quantum can retain tiny finishing latitude:

```text
cut +/- 2–5 frames
audio J-cut
audio L-cut
micro reaction hold
frame-accurate lip-sync alignment
```

without reopening story structure.

I'd define:

```yaml
editorial_freedom:

  structural:
    locked: true

  shot_order:
    locked: true

  shot_presence:
    locked: true

  cut_trim:
    max_frames: 5

  audio_bridge:
    allowed: true

  reaction_extension:
    max_frames: 8
```

Again: authority envelopes.

---

# Finishing Engine

After picture assembly:

```text
selected shots
      ↓
conform
      ↓
visual normalization
      ↓
color consistency
      ↓
VFX cleanup
      ↓
grain/texture coherence
      ↓
final grade
      ↓
audio mix
      ↓
captions
      ↓
encoding
```

A huge issue with individually generated shots will be **inter-shot inconsistency**.

Shot 216:

```text
slightly green cyan
```

Shot 217:

```text
slightly blue cyan
```

Shot 218:

```text
different contrast curve
```

Each looks fine independently.

Together they flicker aesthetically.

So we need a:

```text
LookNormalizer
```

that measures and aligns:

```text
white balance
contrast
black level
saturation
palette
grain
sharpness
texture
```

against the scene's canonical look.

---

# Scene-level normalization

I would do this at scene scope, not whole-film only.

```text
Scene 4
 │
 ├── shot 216
 ├── shot 217
 ├── shot 218
 └── shot 219
        │
        ▼
  Scene Look Target
        │
        ▼
   normalization
```

Then a film-wide grade sits above scene-specific looks.

---

# Seam detection

One very useful post-production critic would specifically evaluate **cuts**.

Not individual frames.

For every cut:

```text
shot A last 12 frames
shot B first 12 frames
```

evaluate:

```text
identity discontinuity
lighting jump
position jump
motion mismatch
screen-direction issue
audio discontinuity
color discontinuity
unintended jump cut
```

Call it:

```text
SeamCritic
```

For 300 shots, that's ~299 boundaries.

Easy to parallelize.

Extremely valuable.

---

# Mastering

Then deterministic mastering handles:

```text
resolution
frame rate
codec
bitrate
color space
audio channels
loudness
peak levels
subtitle embedding
metadata
delivery profiles
```

For example:

```text
master_prores.mov
master_h264.mp4
captions.srt
captions.vtt
poster.jpg
```

Even if initially you only care about:

```text
master.mp4
```

internally I'd retain the higher-quality mezzanine master.

---

# The production artifact graph

Eventually something like:

```text
creative.yaml
      │
      ▼
quantum.studio.yaml
      │
      ▼
animatic.lock
      │
      ├─────────────────────────────────┐
      │                                 │
      ▼                                 ▼
SHOT PRODUCTION                    AUDIO PRODUCTION
      │                                 │
 ┌────┼────┐                     ┌──────┼──────┐
 ▼    ▼    ▼                     ▼      ▼      ▼
S1   S2   S3...               dialogue foley  score
 │    │    │                     │      │      │
 ▼    ▼    ▼                     └──────┼──────┘
QC   QC   QC                            │
 │    │    │                            │
 └────┼────┘                            │
      ▼                                 │
 SELECTED PICTURE                       │
      │                                 │
      └───────────────┬─────────────────┘
                      ▼
                Timeline Execute
                      │
                      ▼
                Scene Finishing
                      │
                      ▼
                 Film Finishing
                      │
                      ▼
                   Master QC
                      │
                      ▼
                  master.mp4
```

---

# I'd introduce a Production Manifest

`animatic.lock` tells us **what movie**.

`production.manifest` tells us **how that locked movie is currently being manufactured**.

Example:

```yaml
schema: quantum.production/v1

production_id: last_signal_build_001

source:
  animatic_lock: sha256:...

shots:

  sc01_sh001:
    status: committed
    selected_take: take_03

  sc01_sh002:
    status: rendering
    attempts: 2

  sc01_sh003:
    status: repair_required
    violation:
      code: character_identity_drift

audio:

  dialogue:
    status: locked

  foley:
    status: generating

  music:
    status: ready

timeline:
  status: waiting_for_picture

master:
  status: blocked
```

This becomes the operational truth for the render farm.

---

# And a Build Planner decides execution order

Not everything is equally important.

For example, rendering the climactic shot may be high-risk.

Quantum could intentionally execute:

```text
highest-risk shots first
```

before spending resources on trivial shots.

Risk score:

```text
risk =
    character_count
  + interaction_complexity
  + lip_sync
  + camera_complexity
  + duration
  + physics_complexity
  + historical failure rate
```

So:

```text
Shot 57    risk .94
Shot 12    risk .18
```

Render 57 first.

Why render 100 easy shots before discovering the climax cannot currently be realized?

That is production intelligence.

---

# It can also dynamically choose execution strategies

Suppose Shot 57 repeatedly fails.

Rather than blindly running take 9:

```text
attempt 1  full video generation FAIL
attempt 2  full video generation FAIL
attempt 3  full video generation FAIL
```

Repair Planner might change strategy:

```text
character foreground generated separately
+
environment plate
+
camera move via deterministic compositing
+
FX layer
```

Same ShotSpec.

Different manufacturing method.

That's important:

> **Shot intent should not dictate shot manufacturing technique.**

The Production Engine owns the “how.”

---

# The architectural boundary

This gives us a clean separation:

```text
COMPILER
"What film are we making?"


AUTONOMOUS QC
"Is this decision/artifact good enough?"


PRODUCTION / TIMELINE ENGINE
"How do we manufacture the approved film reliably?"


WORLD MODEL
"What is true?"
```

Those are four genuinely different concerns.

And the third system has one beautiful invariant:

> **Once a creative decision is locked, production is free to change its manufacturing strategy but not its semantic intent.**

So if a complicated one-shot isn't renderable, Quantum can replace its technical implementation with compositing, layers, multiple generated plates, deterministic motion, etc.—while preserving:

```text
same narrative function
same emotional function
same character state
same timing envelope
same edit position
```

That gives Quantum a path from “AI generates clips” to an actual **autonomous animation production system**.

---

Yes. This is the point where I’d create a **canonical architecture spec** that everything else must conform to.

I’d treat this as `quantum.animation.architecture.yaml`: a system-design contract, not a per-film configuration. `creative.yaml`, `quantum.studio.yaml`, IRs, manifests, locks, and world snapshots are runtime artifacts governed by it.

```yaml
schema: quantum.animation/autonomous-studio-architecture/v0.1


# ======================================================================
# QUANTUM ANIMATION STUDIO
# AUTONOMOUS ANIMATION PRODUCTION ARCHITECTURE
# ======================================================================

metadata:

  organization: Quantum AI Partners
  system: Quantum Animation Studio

  architecture_version: "0.1"

  system_type:
    - autonomous_animation_studio
    - creative_compiler
    - multimodal_production_system
    - stateful_cinematic_runtime

  primary_output:
    type: finished_animation
    container: mp4

  target_runtime_progression:
    mvp_seconds: 60
    next_targets_seconds:
      - 180
      - 360
      - 720
      - 1440

  target_production_scale:
    shots:
      mvp: "10-15"
      long_form: "150-300+"

  human_boundary:

    human_roles:
      - creator

    autonomous_roles:
      - creative_development
      - character_development
      - world_development
      - story_development
      - screenplay
      - directing
      - storyboarding
      - performance_generation
      - editing
      - shot_generation
      - take_selection
      - sound_design
      - music
      - quality_control
      - repair
      - finishing
      - mastering

    human_approval_gates: false

    operating_principle: >
      The creator provides creative intent through conversation.
      All production decisions and execution after that point are
      performed autonomously within explicit creator authority boundaries.


# ======================================================================
# FOUR CORE SYSTEMS
# ======================================================================

core_systems:

  compiler:
    question: "What film are we making?"

  autonomous_qc:
    question: "Is this decision or artifact good enough?"

  production_timeline_engine:
    question: "How do we manufacture the approved film reliably?"

  world_model:
    question: "What is true?"


# ======================================================================
# END-TO-END PIPELINE
# ======================================================================

pipeline:

  stages:

    - id: conversational_intake

      input:
        - creator_conversation

      executor:
        type: judgment_agent
        id: creative_intake_agent

      output:
        - creative.yaml


    - id: development_compile

      input:
        - creative.yaml

      executor:
        type: compiler
        id: development_compiler

      output:
        - quantum.studio.yaml


    - id: animation_compile

      input:
        - quantum.studio.yaml
        - canonical_assets
        - world_model_context

      executor:
        type: compiler
        id: animation_compiler

      output:
        - development_irs
        - story_irs
        - screenplay_ir
        - performance_ir
        - shot_ir
        - storyboard_ir
        - timeline_ir
        - animatic.mp4


    - id: animatic_quality_gate

      input:
        - animatic.mp4
        - all_upstream_irs
        - quality_contract
        - creator_intent

      executor:
        type: autonomous_qc

      success_output:
        - animatic.lock

      failure_output:
        - repair_plan


    - id: production_compile

      input:
        - animatic.lock

      executor:
        type: production_timeline_engine

      output:
        - production.manifest
        - render_dag


    - id: shot_and_audio_production

      input:
        - production.manifest
        - render_dag
        - canonical_assets
        - world_model_context

      output:
        - selected_picture
        - dialogue_stems
        - ambience_stems
        - foley_stems
        - sound_effect_stems
        - music_stems


    - id: final_conform

      output:
        - final_timeline


    - id: finishing

      output:
        - mezzanine_master


    - id: master_quality_gate

      executor:
        type: autonomous_qc

      success_output:
        - master.mp4
        - release_certification

      failure_output:
        - targeted_repair_plan


# ======================================================================
# PRIMARY ARTIFACT CHAIN
# ======================================================================

artifact_chain:

  creator_conversation:

    purpose: >
      Raw human creative thought.

    authority: creator


  creative.yaml:

    purpose: >
      Rich, loss-minimized semantic representation of creator intent.

    produced_by:
      - creative_intake_agent

    may_contain:
      - requirements
      - preferences
      - candidates
      - unresolved_questions
      - delegated_decisions
      - forbidden_ideas
      - thematic_intent
      - emotional_intent
      - character_seeds
      - setting_seeds
      - visual_language
      - sound_language
      - reveal_intent
      - creator_notebook

    must_preserve:
      - ambiguity_when_intentional
      - provenance
      - creator_priority
      - uncertainty

    must_not:
      - prematurely_resolve_creative_questions


  quantum.studio.yaml:

    purpose: >
      Fully resolved canonical studio interpretation of creative.yaml.
      Defines exactly what film Quantum has decided to make.

    produced_by:
      - development_compiler

    characteristics:
      fully_resolved: true
      machine_ready: true
      internally_consistent: true

    includes:
      - developed_world
      - developed_characters
      - character_psychology
      - character_visual_identity
      - character_voice_identity
      - relationships
      - themes
      - thematic_argument
      - dramatic_engine
      - hidden_truth
      - reveal_architecture
      - audience_information_strategy
      - story_constraints
      - visual_language
      - cinematic_language
      - sound_language
      - production_strategy
      - quality_contract
      - canon
      - creator_lock_map


  intermediate_representations:

    abbreviation: IR

    definition: >
      Typed intermediate representations translating creative meaning
      into progressively more executable production instructions.

    examples:
      - creative_seed_ir
      - world_bible_ir
      - character_bible_ir
      - relationship_ir
      - theme_ir
      - reveal_plan_ir
      - story_ir
      - screenplay_ir
      - performance_ir
      - shot_ir
      - storyboard_ir
      - timeline_ir


  animatic.lock:

    purpose: >
      QC-certified executable film plan.

    represents:
      - story_lock
      - screenplay_lock
      - dialogue_lock
      - performance_timing_lock
      - shot_plan_lock
      - structural_edit_lock
      - required_asset_versions
      - quality_certification

    production_rule: >
      Final production may alter manufacturing technique but may not
      silently change locked semantic intent.


  production.manifest:

    purpose: >
      Operational manufacturing state of the locked film.

    tracks:
      - tasks
      - dependencies
      - selected_render_strategy
      - provider_execution
      - take_status
      - QC_status
      - repair_status
      - asset_lineage
      - timeline_conform_status


  master.mp4:

    purpose: >
      Final release-certified audiovisual artifact.


# ======================================================================
# SHARED ARCHITECTURAL PRINCIPLES
# ======================================================================

principles:

  typed_boundaries:

    rule: >
      Agents communicate through validated typed contracts rather
      than relying on free-form conversational handoffs.


  agent_definition:

    statement: >
      An agent is a compiler or production pass with bounded judgment.

    judgment_definition: >
      Judgment is bounded candidate generation, constraint validation,
      evidence-based evaluation, selection, and optional repair.

    prohibited_pattern: >
      Unbounded agents modifying arbitrary parts of production.


  separation_of_concerns:

    compiler:
      owns: semantic_decisions

    autonomous_qc:
      owns: quality_evaluation

    production_timeline_engine:
      owns: manufacturing

    world_model:
      owns: truth_and_state


  creative_vs_execution:

    rule: >
      Semantic creative intent is stored independently from
      provider-specific generation instructions.


  source_of_truth:

    rule: >
      Generated media is never the authoritative source of story truth.


  immutable_inputs:

    rule: >
      Once a compiler artifact is committed, it is immutable.
      Revisions create new versions.


  content_addressing:

    enabled: true

    hashing:
      algorithm: sha256

    purpose:
      - deterministic_cache_keys
      - reproducibility
      - lineage
      - targeted_invalidation


  minimum_blast_radius:

    rule: >
      Any detected failure must first attempt repair at the smallest
      semantic and computational scope capable of fixing the issue.


  autonomous_execution:

    rule: >
      No workflow may depend on human approval to continue production.

    unsatisfiable_behavior: >
      Production fails explicitly with diagnostic evidence rather
      than violating creator-locked constraints.


# ======================================================================
# IDENTIFIER SYSTEM
# ======================================================================

identifiers:

  immutable: true

  prefixes:

    project: qproj
    universe: quniv
    series: qseries
    episode: qepisode

    character: qchar
    location: qloc
    prop: qprop

    scene: qscene
    shot: qshot
    dialogue: qdlg

    event: qevent
    state_snapshot: qstate

    asset: qasset
    render: qrender

    timeline: qtimeline
    quality_report: qqc

  example:

    character: qchar_000001
    scene: qscene_000004
    shot: qshot_000004_000017


# ======================================================================
# AUTHORITY MODEL
# ======================================================================

authority:

  levels:

    - rank: 100
      id: creator_locked
      description: >
        Explicit creator requirement.
      mutable_by_quantum: false

    - rank: 90
      id: creator_strong_preference
      mutable_by_quantum: exceptional_only

    - rank: 80
      id: established_canon
      mutable_by_quantum: versioned_rewrite_only

    - rank: 70
      id: studio_creative_decision
      mutable_by_quantum: true

    - rank: 60
      id: story_decision
      mutable_by_quantum: true

    - rank: 50
      id: directorial_decision
      mutable_by_quantum: true

    - rank: 40
      id: editorial_decision
      mutable_by_quantum: true

    - rank: 30
      id: production_strategy
      mutable_by_quantum: true

    - rank: 20
      id: individual_take
      mutable_by_quantum: freely

  repair_rule: >
    Repair climbs the authority hierarchy only after lower-authority
    alternatives have failed.


# ======================================================================
# PROVENANCE CONTRACT
# ======================================================================

provenance:

  required_for:
    - creative_decisions
    - canon_facts
    - compiler_outputs
    - renders
    - QC_decisions
    - repair_decisions

  source_types:
    - creator_explicit
    - creator_implied
    - agent_interpretation
    - agent_invention
    - established_canon
    - world_event
    - upstream_ir

  record:

    required_fields:
      - artifact_id
      - artifact_version
      - produced_by
      - produced_at
      - input_hashes
      - output_hash
      - authority_level

    optional_fields:
      - derived_from
      - confidence
      - rationale
      - model
      - provider
      - seed


# ======================================================================
# SHARED AGENT CONTRACT
# ======================================================================

agent_contract:

  input:
    must_be_typed: true
    must_include_authority_context: true
    must_include_relevant_constraints: true

  output:
    must_match_schema: true
    must_include_rationale: true
    must_include_confidence: true
    must_include_provenance: true

  judgment:

    candidate_generation:

      enabled_when:
        - multiple_valid_solutions_exist

      minimum_candidates:
        default: 3

      candidate_diversity:
        required: true

    constraint_application:

      order:
        - creator_locks
        - canon
        - world_state
        - hard_production_constraints

    evaluation:

      required:
        - explicit_dimensions
        - evidence
        - confidence

    selection:

      may_use:
        - weighted_scoring
        - pairwise_comparison
        - tournament
        - constraint_dominance

    uncertainty:

      allowed: true

      uncertain_result_requires:
        - deeper_evaluation
        - additional_candidate
        - alternate_critic

  authority_envelope:

    required: true

    rule: >
      Each agent explicitly declares which entities and fields it
      may create, modify, or invalidate.


# ======================================================================
# SYSTEM 1: COMPILER
# ======================================================================

compiler:

  question: "What film are we making?"

  responsibility: >
    Transform creator intent into an explicit, internally coherent,
    executable cinematic plan.

  does_not_own:
    - final_truth_storage
    - artifact_quality_acceptance
    - render_provider_execution


  # --------------------------------------------------------------------
  # COMPILER FRONT END
  # --------------------------------------------------------------------

  frontend:

    creative_intake_agent:

      input:
        - creator_conversation

      output:
        - creative.yaml

      responsibilities:
        - extract_explicit_intent
        - infer_implicit_intent
        - preserve_creator_language
        - preserve_candidate_ideas
        - preserve_rejected_ideas
        - mark_open_questions
        - mark_delegated_questions
        - assign_priority
        - attach_provenance

      prohibited:
        - silently_canonizing_candidates
        - hiding_uncertainty
        - resolving_major_story_questions


    creative_schema_validator:

      type: deterministic

      responsibilities:
        - schema_validation
        - identifier_validation
        - malformed_input_detection
        - provenance_validation


  # --------------------------------------------------------------------
  # DEVELOPMENT COMPILER
  # creative.yaml -> quantum.studio.yaml
  # --------------------------------------------------------------------

  development_compiler:

    input:
      - creative.yaml

    output:
      - quantum.studio.yaml

    objective: >
      Resolve the creative dossier into a complete film-development
      specification before screenplay generation begins.

    passes:


      - id: intent_normalizer

        type: judgment

        produces:
          - creative_seed_ir

        responsibility: >
          Convert heterogeneous creative material into normalized
          creative goals without prematurely narrowing interpretation.


      - id: character_architect

        type: judgment

        produces:
          - character_bible_ir

        runs_before_story_generation: true

        develops:

          identity:
            - biography
            - origin
            - age_or_operational_history
            - role

          psychology:
            - conscious_desire
            - unconscious_need
            - fear
            - wound
            - false_belief
            - values
            - contradictions
            - secrets
            - moral_boundaries

          dramatic_engine:
            - internal_conflict
            - recurring_conflict_generators
            - unresolved_questions
            - series_story_potential

          capability:
            - skills
            - intelligence
            - limitations
            - competence_constraints

          behavior:
            - habits
            - physicality
            - stress_behavior
            - emotional_leakage

          language:
            - speech_style
            - verbosity
            - humor
            - vocabulary
            - subtext_behavior

          visual_identity:
            - silhouette
            - proportions
            - distinguishing_features
            - palette
            - damage_states
            - wardrobe_or_shell
            - movement_signature

          voice_identity:
            - register
            - texture
            - performance_style

        invariant: >
          Recurring characters must possess dramatic potential beyond
          the requirements of the current episode.


      - id: world_architect

        type: judgment

        produces:
          - world_bible_ir

        runs_before_story_generation: true

        develops:
          - era
          - history
          - civilizations
          - cultures
          - technology_rules
          - science_rules
          - geography
          - architecture
          - economics_when_relevant
          - institutions_when_relevant
          - artificial_intelligence_rules
          - communication_rules
          - transportation_rules
          - social_norms
          - important_locations
          - environmental_storytelling
          - world_mysteries

        invariant: >
          World details must form a causal system rather than a
          collection of unrelated aesthetic ideas.


      - id: relationship_architect

        type: judgment

        inputs:
          - character_bible_ir
          - world_bible_ir

        produces:
          - relationship_ir

        develops:
          - relationship_history
          - asymmetric_beliefs
          - desires
          - resentments
          - dependencies
          - secrets
          - power_asymmetry
          - unresolved_conflict


      - id: theme_architect

        type: judgment

        produces:
          - theme_ir

        develops:
          - thematic_topics
          - central_question
          - thesis
          - antithesis
          - character_belief_relationship
          - thematic_tests
          - ending_implication

        invariant: >
          Theme must emerge through decisions and consequences rather
          than requiring explicit explanatory dialogue.


      - id: dramatic_engine_builder

        type: judgment

        produces:
          - dramatic_engine_ir

        combines:
          - character_bible_ir
          - world_bible_ir
          - relationship_ir
          - theme_ir

        develops:
          - protagonist_goal
          - protagonist_need
          - central_conflict
          - story_pressure
          - stakes
          - contradiction_engine
          - escalation_mechanics


      - id: reveal_architect

        type: judgment

        conditional_on:
          - mystery
          - twist
          - hidden_information
          - recontextualization

        produces:
          - reveal_plan_ir

        develops:
          - hidden_truth
          - audience_initial_model
          - protagonist_initial_model
          - clue_sequence
          - clue_salience
          - misdirection
          - reveal_mechanism
          - reveal_timing
          - retrospective_evidence
          - post_reveal_meaning

        invariants:
          - reveal_must_not_contradict_prior_evidence
          - required_clues_precede_reveal
          - reveal_should_change_interpretation
          - emotional_meaning_should_survive_puzzle_mechanics


      - id: canon_synthesizer

        type: judgment

        inputs:
          - all_development_irs

        produces:
          - canon_ir

        responsibility: >
          Resolve contradictions among development passes while
          respecting the authority hierarchy.


      - id: studio_spec_emitter

        type: deterministic

        input:
          - canon_ir
          - development_irs

        output:
          - quantum.studio.yaml


  # --------------------------------------------------------------------
  # STORY / ANIMATION COMPILER
  # quantum.studio.yaml -> animatic
  # --------------------------------------------------------------------

  animation_compiler:

    input:
      - quantum.studio.yaml

    passes:


      - id: story_architect

        type: judgment

        produces:
          - story_ir

        owns:
          - beats
          - scenes
          - causal_story_structure
          - duration_budget
          - escalation
          - climax
          - resolution

        cannot:
          - violate_canon
          - change_creator_locks


      - id: screenplay_writer

        type: judgment

        produces:
          - screenplay_ir

        owns:
          - scene_action
          - dialogue
          - scene_turns
          - subtext
          - dramatic_pacing

        cannot:
          - introduce_unapproved_canon
          - leak_character_knowledge


      - id: performance_director

        type: judgment

        produces:
          - performance_ir

        responsibilities:
          - line_intention
          - subtext
          - pacing
          - emotional_direction
          - voice_generation
          - word_timing
          - phoneme_timing

        timing_rule: >
          Dialogue performance duration becomes authoritative input
          to final shot-duration planning.


      - id: director

        type: judgment

        produces:
          - shot_ir

        owns:
          - blocking
          - coverage
          - shot_count
          - framing
          - lens_intent
          - camera_motion
          - shot_duration
          - visual_emphasis
          - reaction_coverage

        cannot:
          - change_story_outcome
          - invent_major_lore
          - violate_world_state
          - modify_locked_dialogue_without_escalation


      - id: asset_requirement_compiler

        type: deterministic_plus_judgment

        produces:
          - production_asset_ir

        determines:
          - characters_needed
          - character_variants
          - locations_needed
          - props_needed
          - graphics_needed
          - environment_states_needed


      - id: storyboard_compiler

        type: judgment

        produces:
          - storyboard_ir

        responsibilities:
          - visual_composition
          - key_frame_generation
          - start_frame_generation_when_needed
          - end_frame_generation_when_needed
          - shot_readability


      - id: editorial_compiler

        type: judgment

        produces:
          - timeline_ir

        owns:
          - shot_order
          - exact_animatic_cuts
          - reaction_timing
          - audio_bridges
          - pacing
          - temporary_music_placement
          - temporary_sound_placement


      - id: animatic_renderer

        type: deterministic

        input:
          - storyboard_ir
          - timeline_ir
          - performance_ir

        output:
          - animatic.mp4


  # --------------------------------------------------------------------
  # IR CONTRACT
  # --------------------------------------------------------------------

  intermediate_representations:

    general_rules:
      immutable: true
      versioned: true
      schema_validated: true
      content_addressed: true

    creative_seed_ir:
      answers: "What does the creator want?"

    character_bible_ir:
      answers: "Who are these characters?"

    world_bible_ir:
      answers: "What kind of reality exists?"

    relationship_ir:
      answers: "How are characters emotionally and historically connected?"

    theme_ir:
      answers: "What question is the film actually exploring?"

    reveal_plan_ir:
      answers: "What is hidden, what is believed, and when does that change?"

    story_ir:
      answers: "What happens and why?"

    screenplay_ir:
      answers: "What happens scene by scene and what is performed?"

    performance_ir:
      answers: "Exactly how does dialogue sound and how long does it take?"

    shot_ir:
      answers: "How is the screenplay photographed?"

    storyboard_ir:
      answers: "What should each planned shot visually communicate?"

    timeline_ir:
      answers: "Exactly when does every picture and sound event occur?"


  # --------------------------------------------------------------------
  # INCREMENTAL COMPILATION
  # --------------------------------------------------------------------

  incremental_build:

    enabled: true

    pass_cache_key_components:
      - pass_id
      - pass_version
      - canonical_input_hash
      - relevant_configuration_hash
      - seed

    invalidation:

      principle: >
        Only passes whose semantic dependencies changed are invalidated.

      examples:

        visual_eye_color_change:
          invalidates:
            - canonical_character_assets
            - storyboard
            - affected_shot_renders
          preserves:
            - theme
            - story
            - screenplay

        dialogue_change:
          invalidates:
            - voice_performance
            - affected_shot_timing
            - affected_storyboards
            - affected_timeline
          preserves:
            - unrelated_scenes

        premise_change:
          invalidates:
            - development_canon
            - story
            - screenplay
            - downstream_production


# ======================================================================
# SYSTEM 2: AUTONOMOUS QC
# ======================================================================

autonomous_qc:

  question: "Is this decision or artifact good enough?"

  responsibility: >
    Detect defects, prove violations with evidence, identify root cause,
    select repair scope, and certify artifacts for downstream use.

  core_rule: >
    No artifact advances solely because it was successfully generated.


  # --------------------------------------------------------------------
  # QUALITY CONTRACT
  # --------------------------------------------------------------------

  quality_contract:

    compiled_from:
      - creative.yaml
      - quantum.studio.yaml
      - technical_delivery_requirements

    dimensions:

      narrative:
        - coherence
        - causality
        - motivation
        - setup_payoff
        - character_agency

      character:
        - identity
        - psychological_consistency
        - competence_consistency
        - arc_integrity
        - performance_consistency

      reveal:
        - fairness
        - clue_sufficiency
        - clue_timing
        - misdirection_quality
        - recontextualization
        - emotional_meaning

      cinematic:
        - composition
        - coverage
        - camera_motivation
        - visual_rhythm
        - geography
        - screen_direction

      visual:
        - identity_consistency
        - temporal_stability
        - anatomy
        - geometry
        - lighting
        - color
        - asset_consistency

      performance:
        - intention
        - naturalness
        - emotional_precision
        - subtext
        - lip_sync

      audio:
        - dialogue_intelligibility
        - continuity
        - sound_effect_sync
        - ambience
        - score_function
        - mix

      editorial:
        - pacing
        - cut_motivation
        - information_density
        - reaction_timing
        - sequence_clarity

      creative_fidelity:
        - creator_intent
        - tone
        - thematic_alignment
        - forbidden_element_avoidance

      technical:
        - decode_integrity
        - duration
        - resolution
        - frame_rate
        - audio_integrity
        - loudness
        - delivery_format


    scoring:

      hard_constraints:
        behavior: immediate_fail

      critical_dimensions:
        behavior: >
          Every critical dimension must individually exceed its threshold.

      weighted_preferences:
        behavior: >
          Weighted scoring is used only after all hard and critical
          constraints pass.

      uncertainty:
        valid_state: true
        behavior: escalate_evaluation


  # --------------------------------------------------------------------
  # QC TYPES
  # --------------------------------------------------------------------

  evaluators:

    deterministic_validators:

      use_for:
        - schema
        - hashes
        - duration
        - frame_count
        - decode
        - asset_resolution
        - lip_sync_offset
        - timeline_math
        - forbidden_ids
        - required_ids
        - state_preconditions


    specialist_critics:

      examples:

        - story_critic
        - character_critic
        - reveal_critic
        - creative_intent_critic
        - cinematography_critic
        - identity_critic
        - temporal_artifact_critic
        - performance_critic
        - audio_critic
        - edit_critic
        - seam_critic


    perspective_critics:

      cold_viewer:

        sees:
          - artifact

        intentionally_does_not_see:
          - hidden_truth
          - intended_reveal
          - clue_plan

        purpose: >
          Estimate actual audience interpretation rather than checking
          whether execution matches the writer's explanation.


      informed_critic:

        sees:
          - artifact
          - canon
          - intended_story
          - hidden_truth
          - clue_plan

        purpose: >
          Determine whether execution faithfully realizes intended structure.


      rewatch_critic:

        sees:
          - artifact
          - hidden_truth

        purpose: >
          Determine whether earlier moments gain legitimate new meaning
          after the reveal.


  # --------------------------------------------------------------------
  # AUDIENCE MODEL
  # --------------------------------------------------------------------

  audience_simulation:

    enabled_for:
      - mystery
      - twist
      - suspense
      - hidden_identity
      - nonlinear_information_design

    checkpoints:
      strategy: semantic_and_temporal

    result_example:

      viewer_model:

        beliefs:
          signal_external:
            probability: 0.78

          sender_human:
            probability: 0.62

          sender_is_aria:
            probability: 0.18

        emotions:
          curiosity: 0.82
          dread: 0.31

        unresolved_questions:
          - signal_origin
          - station_abandonment


  # --------------------------------------------------------------------
  # VIOLATION CONTRACT
  # --------------------------------------------------------------------

  violation:

    required_fields:
      - code
      - severity
      - confidence
      - scope
      - artifact_id
      - expected
      - observed
      - evidence
      - violated_requirement_refs
      - likely_owner

    severity:
      - informational
      - minor
      - major
      - critical

    scopes:
      - frame
      - shot
      - shot_pair
      - scene
      - sequence
      - episode
      - master


  # --------------------------------------------------------------------
  # QC HIERARCHY
  # --------------------------------------------------------------------

  hierarchy:

    order:

      - frame_qc
      - shot_qc
      - neighboring_shot_qc
      - scene_qc
      - sequence_qc
      - episode_qc
      - master_qc

    principle: >
      Local excellence does not imply global excellence.


  # --------------------------------------------------------------------
  # ADJUDICATION
  # --------------------------------------------------------------------

  adjudicator:

    responsibilities:
      - combine_independent_evidence
      - detect_critic_disagreement
      - distinguish_failure_from_uncertainty
      - determine_pass_fail
      - request_deeper_evaluation

    decisions:
      - pass
      - fail
      - uncertain

    disagreement_policy: >
      High critic disagreement triggers additional evaluation rather
      than arithmetic averaging.


  # --------------------------------------------------------------------
  # ROOT CAUSE
  # --------------------------------------------------------------------

  root_cause_analyzer:

    examples:

      character_identity_drift:
        likely_owner:
          - renderer
          - asset_resolver

      poor_composition:
        likely_owner:
          - storyboard_compiler
          - director

      bad_scene_coverage:
        likely_owner:
          - director

      poor_dialogue_delivery:
        likely_owner:
          - performance_director

      exposition_problem:
        likely_owner:
          - screenplay_writer

      unmotivated_character_action:
        likely_owner:
          - story_architect

      weak_reveal:
        likely_owner:
          - reveal_architect

      canon_violation:
        likely_owner:
          - compiler_pass
          - world_state_integration


  # --------------------------------------------------------------------
  # REPAIR
  # --------------------------------------------------------------------

  repair_planner:

    objective: >
      Restore quality while minimizing semantic and computational
      invalidation.

    escalation_levels:

      - level: 0
        action: choose_existing_alternate_take

      - level: 1
        action: rerender_same_shot_spec

      - level: 2
        action: adjust_render_constraints

      - level: 3
        action: redesign_single_shot

      - level: 4
        action: redesign_local_coverage

      - level: 5
        action: rewrite_scene

      - level: 6
        action: modify_story_beat

      - level: 7
        action: modify_quantum_developed_canon

    creator_locked_level:
      action: prohibited

    cost_model:

      factors:
        - compute_cost
        - invalidated_artifacts
        - creative_risk
        - continuity_risk
        - historical_failure_probability


  # --------------------------------------------------------------------
  # QC CALIBRATION
  # --------------------------------------------------------------------

  calibration:

    required: true

    injected_defect_tests:
      - character_eye_color_change
      - missing_character_damage
      - prop_continuity_break
      - clue_after_reveal
      - missing_setup
      - premature_reveal
      - audio_offset
      - frame_freeze
      - voice_identity_change
      - duplicated_shot
      - screen_direction_break
      - ambience_discontinuity

    critic_metrics:
      - precision
      - recall
      - false_positive_rate
      - false_negative_rate
      - confidence_calibration

    versioning:
      required: true


# ======================================================================
# SYSTEM 3: PRODUCTION / TIMELINE ENGINE
# ======================================================================

production_timeline_engine:

  question: "How do we manufacture the approved film reliably?"

  input:
    - animatic.lock

  output:
    - master_media

  semantic_rule: >
    Production may change manufacturing technique but may not change
    locked narrative or cinematic meaning without compiler escalation.


  # --------------------------------------------------------------------
  # PRODUCTION COMPILER
  # --------------------------------------------------------------------

  production_compiler:

    responsibilities:
      - resolve_dependencies
      - determine_render_strategy
      - create_render_packages
      - construct_render_dag
      - assign_risk
      - create_production_manifest

    output:
      - render_dag
      - production.manifest


  # --------------------------------------------------------------------
  # PRODUCTION DAG
  # --------------------------------------------------------------------

  render_dag:

    node_types:
      - asset_resolution
      - dialogue_generation
      - shot_packaging
      - video_render
      - image_render
      - deterministic_graphics
      - compositing
      - sound_generation
      - music_generation
      - QC
      - selection
      - conform
      - finishing
      - mastering

    properties:
      directed: true
      acyclic: true
      content_addressed: true
      resumable: true

    scheduling:

      parallel_execution: true

      constraints:
        - dependency_readiness
        - compute_capacity
        - provider_capacity

      priority_strategy:
        - high_production_risk_first
        - critical_path
        - dependency_unblocking

    risk_model:

      factors:
        - character_count
        - physical_interaction_complexity
        - lip_sync
        - camera_complexity
        - action_complexity
        - duration
        - fine_hand_interaction
        - reflective_surfaces
        - historical_renderer_failure_rate


  # --------------------------------------------------------------------
  # SHOT EXECUTION
  # --------------------------------------------------------------------

  shot_execution:

    atomic_unit:
      type: shot

    package:
      artifact: render_package

      contains:
        - shot_id
        - duration
        - frame_rate
        - resolution
        - semantic_action
        - performance_intent
        - camera_specification
        - character_asset_refs
        - character_variant_refs
        - environment_asset_refs
        - prop_asset_refs
        - dialogue_audio_refs
        - world_context_ref
        - continuity_constraints
        - negative_constraints
        - seed

    principle: >
      Renderer receives local execution context, not the entire screenplay.


  # --------------------------------------------------------------------
  # RENDER STRATEGY
  # --------------------------------------------------------------------

  rendering:

    provider_abstraction:

      semantic_input:
        - shot_ir
        - render_package

      provider_specific_output:
        - provider_prompt
        - provider_controls

      rule: >
        Provider-specific prompts are disposable compiled artifacts,
        never canonical semantic source.


    heterogeneous_routing:

      enabled: true

      examples:

        dialogue_closeup:
          prefer:
            - facial_performance_renderer

        environment_establishing:
          prefer:
            - environment_renderer

        difficult_hand_interaction:
          prefer:
            - constrained_or_layered_strategy

        readable_interface:
          prefer:
            - deterministic_composite


    rendering_modes:

      - full_video_generation
      - image_to_video
      - keyframe_interpolation
      - layered_character_environment_render
      - deterministic_compositing
      - deterministic_camera_motion
      - graphics_overlay
      - hybrid_render


    strategy_rule: >
      Use generative systems where creative synthesis helps.
      Use deterministic systems where exact precision helps.


  # --------------------------------------------------------------------
  # MULTIPLE TAKES
  # --------------------------------------------------------------------

  takes:

    default_candidates_per_shot: 3

    selection_pipeline:

      - technical_validation
      - hard_visual_constraints
      - identity_validation
      - performance_evaluation
      - cinematic_evaluation
      - pairwise_ranking
      - neighboring_shot_context_qc

    commit_rule: >
      A shot is not committed until both local and contextual QC pass.


  # --------------------------------------------------------------------
  # SHOT STATE MACHINE
  # --------------------------------------------------------------------

  shot_state_machine:

    states:

      - planned
      - packaged
      - queued
      - rendering
      - candidates_ready
      - local_qc
      - candidate_selected
      - context_qc
      - committed

    failure_states:

      - render_failed
      - local_qc_failed
      - context_qc_failed
      - repair_required
      - director_replan_required


  # --------------------------------------------------------------------
  # HANDLES
  # --------------------------------------------------------------------

  shot_handles:

    enabled: true

    purpose: >
      Allow frame-level editorial refinement without requiring
      regeneration.

    default:
      pre_roll_frames: 8
      post_roll_frames: 8


  # --------------------------------------------------------------------
  # CANONICAL TIMELINE
  # --------------------------------------------------------------------

  timeline:

    authoritative_format:
      type: semantic_timeline_ir

    timing_unit:
      canonical: frame

    rationale: >
      Frame addressing eliminates floating-point timing drift.

    track_types:

      picture:
        - primary_video
        - overlays
        - graphics
        - effects

      audio:
        - dialogue
        - foley
        - sound_effects
        - ambience
        - music

      metadata:
        - captions
        - scene_boundaries
        - quality_markers


    structural_picture_lock:

      after_animatic_lock: true

      immutable:
        - scene_order
        - shot_order
        - narrative_function
        - dialogue_content

      micro_editorial_freedom:

        cut_trim_frames:
          allowed: true
          maximum: 5

        audio_j_cut:
          allowed: true

        audio_l_cut:
          allowed: true

        reaction_extension_frames:
          allowed: true
          maximum: 8


  # --------------------------------------------------------------------
  # AUDIO PRODUCTION
  # --------------------------------------------------------------------

  audio:

    stems_required:
      - dialogue
      - foley
      - sound_effects
      - ambience
      - music

    dialogue:

      authority:
        timing_master: true

      required_metadata:
        - line_id
        - word_timings
        - phoneme_timings
        - performance_intent
        - voice_identity


    sound_events:

      semantic_event_driven: true

      example:

        event:
          type: mechanical_button_press
          frame: 514
          material: metal
          environment: communications_room


    foley:

      conditioned_by:
        - performer_body
        - action
        - material
        - surface
        - environment
        - distance


    ambience:

      continuity_scope:
        - location
        - scene

      behavior:
        bridge_visual_cuts: true


    music:

      generated_against:
        - timeline
        - emotional_curve
        - thematic_motifs
        - reveal_plan

      stem_generation:
        preferred: true

      rule: >
        Music may support audience interpretation but must not
        unintentionally reveal hidden information early.


  # --------------------------------------------------------------------
  # FINISHING
  # --------------------------------------------------------------------

  finishing:

    visual:

      stages:
        - conform
        - artifact_cleanup
        - intershot_normalization
        - scene_look_normalization
        - global_grade
        - texture_coherence
        - final_sharpen_or_soften

      normalize:
        - white_balance
        - contrast
        - black_level
        - saturation
        - palette
        - sharpness
        - grain
        - texture


    seam_analysis:

      enabled: true

      compares:
        - previous_shot_tail
        - next_shot_head

      detects:
        - identity_jump
        - lighting_jump
        - spatial_jump
        - motion_mismatch
        - screen_direction_problem
        - color_jump
        - audio_discontinuity


    audio_mix:

      stages:
        - dialogue_edit
        - foley_mix
        - effects_mix
        - ambience_mix
        - score_mix
        - dynamic_ducking
        - EQ
        - limiting
        - loudness_normalization


    mastering:

      deterministic: true

      validates:
        - frame_rate
        - resolution
        - codec
        - color_space
        - audio_channels
        - loudness
        - peak_level
        - subtitle_alignment

      outputs:
        - mezzanine_master
        - distribution_master
        - captions
        - poster_frame


# ======================================================================
# SYSTEM 4: WORLD MODEL
# ======================================================================

world_model:

  question: "What is true?"

  responsibility: >
    Maintain authoritative, queryable, temporally correct cinematic
    reality across characters, objects, locations, relationships,
    knowledge, narrative state, scenes, episodes, and series.

  key_principle: >
    Models do not remember canon. The World Model remembers canon.

  does_not_own:
    - story_quality
    - shot_rendering
    - provider_execution
    - creative_preferences


  # --------------------------------------------------------------------
  # SOURCES OF TRUTH
  # --------------------------------------------------------------------

  truth_layers:

    objective_world:

      definition: >
        Facts objectively true within the fictional universe.


    character_belief:

      definition: >
        What an individual character currently believes to be true.

      scoped_by:
        - character_id


    character_knowledge:

      definition: >
        Information a character has actually acquired.

      scoped_by:
        - character_id


    audience_knowledge:

      definition: >
        Information intentionally available to the viewer at a given
        narrative point.


    canon:

      definition: >
        Persisted truths established at universe, series, episode,
        character, location, or asset scope.


    cinematic_state:

      definition: >
        Current screen geography and cinematic continuity necessary
        to preserve coherent coverage.


  # --------------------------------------------------------------------
  # STATE DOMAINS
  # --------------------------------------------------------------------

  state_domains:

    narrative_state:

      tracks:
        - active_goals
        - unresolved_questions
        - mysteries
        - reveals
        - promises
        - setup_payoff
        - dramatic_pressure
        - character_arc_position


    physical_state:

      tracks:
        - character_location
        - pose_relevant_state
        - injuries
        - damage
        - wardrobe
        - carried_items
        - prop_location
        - prop_condition
        - doors
        - lights
        - environment_condition
        - physical_accessibility


    character_state:

      tracks:
        - emotion
        - goal
        - intention
        - belief
        - knowledge
        - trust
        - fear
        - relationship_state


    relationship_state:

      tracks:
        - trust
        - intimacy
        - hostility
        - dependence
        - unresolved_conflict
        - secrets_known


    environment_state:

      tracks:
        - lighting
        - power
        - weather_when_applicable
        - damage
        - occupancy
        - ambient_conditions


    asset_state:

      tracks:
        - canonical_character_variant
        - canonical_location_variant
        - canonical_prop_variant
        - damage_variant
        - costume_variant


    cinematic_state:

      tracks:
        - established_geography
        - camera_side_of_axis
        - screen_direction
        - eyeline
        - previous_shot_size
        - previous_lens_intent
        - coverage_available


  # --------------------------------------------------------------------
  # TEMPORAL MODEL
  # --------------------------------------------------------------------

  time:

    story_clock:

      coordinates:
        - universe_time
        - episode_id
        - scene_index
        - shot_index
        - timeline_frame

    bitemporal_memory:

      supported: true

      coordinates:
        - valid_time
        - recorded_time

      purpose: >
        Distinguish when a fictional fact became true from when
        Quantum learned or recorded the fact.


  # --------------------------------------------------------------------
  # STATE TRANSITIONS
  # --------------------------------------------------------------------

  event_model:

    event_sourced: true

    event_contract:

      required:
        - event_id
        - event_type
        - story_time
        - originating_artifact
        - preconditions
        - mutations
        - provenance

    example:

      event_id: qevent_008127
      event_type: character_damage

      preconditions:
        aria.left_shoulder.condition: functional

      mutations:
        aria.left_shoulder.condition: damaged
        aria.left_arm.mobility: 0.55

      caused_by:
        shot_id: qshot_000031


  state_reducer:

    deterministic: true

    function: >
      Reduce prior authoritative state plus committed events into
      next authoritative state.


  snapshots:

    enabled: true

    purpose:
      - fast_state_reconstruction
      - debugging
      - reproducibility

    scopes:
      - scene
      - episode
      - configurable_interval


  # --------------------------------------------------------------------
  # SHOT TRANSACTION
  # --------------------------------------------------------------------

  shot_transaction:

    principle: >
      Every committed shot is a validated state transition.

    lifecycle:

      - step: resolve_entry_state

      - step: validate_preconditions

      - step: hydrate_director_context

      - step: compile_shot_spec

      - step: render_candidates

      - step: validate_render_against_expected_state

      - step: run_quality_gate

      - step: select_take

      - step: commit_semantic_events

      - step: reduce_next_state

      - step: persist_snapshot_when_required

    important_rule: >
      Rendered pixels cannot independently alter canonical state.

    state_authority:
      semantic_events: authoritative
      generated_media: observational_evidence_only


  # --------------------------------------------------------------------
  # SHOT PRECONDITIONS / POSTCONDITIONS
  # --------------------------------------------------------------------

  shot_state_contract:

    preconditions:

      examples:
        - character_location
        - held_props
        - character_condition
        - known_information
        - environment_state

    postconditions:

      examples:
        - new_information
        - changed_emotion
        - moved_prop
        - acquired_damage
        - changed_relationship
        - environment_change

    invariant: >
      Shot postconditions become the next shot's state only after
      the shot semantically commits.


  # --------------------------------------------------------------------
  # HIERARCHICAL CANON
  # --------------------------------------------------------------------

  scope_hierarchy:

    - universe
    - series
    - season
    - episode
    - scene
    - shot

  resolution:

    principle: >
      More local state may specialize broader canon but may not
      contradict higher-authority immutable canon.


  # --------------------------------------------------------------------
  # ASSET REGISTRY
  # --------------------------------------------------------------------

  asset_registry:

    distinction: >
      World Model stores identity and canonical references.
      Binary media lives in the artifact store.

    entity_types:
      - character
      - character_variant
      - location
      - location_variant
      - prop
      - prop_variant
      - voice
      - motion_profile

    asset_reference:

      fields:
        - asset_id
        - canonical_version
        - manifest_uri
        - content_hash
        - lifecycle_status


  # --------------------------------------------------------------------
  # LONG-TERM MEMORY
  # --------------------------------------------------------------------

  long_term_memory:

    purpose: >
      Persist relational, historical, episodic, semantic, temporal
      and provenance-rich facts across long-running productions.

    backend:

      recommended:
        implementation: l9-graphiti-memory

      architectural_role:
        - canonical_memory_persistence
        - temporal_fact_history
        - relationship_memory
        - retrieval
        - provenance
        - conflict_tracking
        - series_continuity_recall

      explicitly_not:
        - world_state_reducer
        - render_engine
        - agent_runtime

    relationship_to_world_model:

      world_model:
        owns: >
          Exact authoritative state required for deterministic
          production decisions.

      long_term_memory:
        owns: >
          Historical and relational memory used to reconstruct,
          contextualize and retrieve relevant canon.


  # --------------------------------------------------------------------
  # WORLD MODEL QUERY PORT
  # --------------------------------------------------------------------

  interfaces:

    initialize:

      input:
        - canon_ir
        - story_ir

      output:
        - initial_world_snapshot


    context_for_scene:

      input:
        - scene_id

      output:
        - scene_world_context


    context_for_shot:

      input:
        - shot_id

      output:
        - shot_world_context


    validate_preconditions:

      input:
        - shot_spec
        - world_snapshot

      output:
        - violations


    validate_render:

      input:
        - selected_take
        - expected_state

      output:
        - observed_state_report


    commit_shot:

      input:
        - approved_shot
        - semantic_events

      output:
        - next_world_snapshot


    query_character:

      examples:
        - current_condition
        - current_location
        - current_beliefs
        - current_knowledge
        - current_relationships
        - canonical_asset_version


    query_history:

      examples:
        - why_is_aria_injured
        - when_did_prop_change_ownership
        - when_did_character_learn_fact
        - which_event_created_current_state


# ======================================================================
# INTER-SYSTEM CONTRACTS
# ======================================================================

system_interfaces:


  compiler_to_world_model:

    sends:
      - canon
      - scene_intent
      - proposed_state_transitions
      - shot_preconditions
      - shot_postconditions

    receives:
      - authoritative_context
      - constraint_violations
      - canonical_asset_refs


  compiler_to_qc:

    sends:
      - generated_ir
      - intent
      - authority_map
      - quality_contract

    receives:
      - pass
      - fail
      - violations
      - repair_request


  qc_to_compiler:

    sends:
      - root_cause
      - target_pass
      - permitted_repair_scope
      - evidence


  compiler_to_production:

    boundary_artifact:
      - animatic.lock


  world_model_to_production:

    sends:
      - shot_world_context
      - canonical_asset_versions
      - continuity_constraints


  production_to_qc:

    sends:
      - candidate_renders
      - timeline_sections
      - audio
      - finished_sequences


  qc_to_production:

    sends:
      - candidate_acceptance
      - candidate_rejection
      - rerender_request
      - manufacturing_strategy_escalation


  production_to_world_model:

    rule: >
      Production cannot mutate truth directly.

    may_send:
      - observed_render_metadata
      - QC_observations

    commit_authority:
      false


# ======================================================================
# REPAIR AND INVALIDATION MODEL
# ======================================================================

repair_and_invalidation:

  principle: >
    Diagnose semantic ownership before regenerating artifacts.

  examples:


    bad_hand_geometry:

      root_owner:
        - renderer

      repair:
        - rerender_take

      invalidates:
        - failed_take

      preserves:
        - shot_ir
        - story
        - timeline


    repeated_render_failure:

      root_owner:
        - production_strategy

      repair:
        - switch_render_method

      may_use:
        - layered_composite
        - alternate_renderer
        - simplified_physical_execution


    impossible_shot:

      root_owner:
        - director

      repair:
        - redesign_shot

      preserves:
        - narrative_function
        - scene_outcome
        - dialogue_when_possible


    pacing_failure:

      root_owner:
        - editor
        - director

      repair:
        - modify_shot_duration
        - modify_local_coverage


    bad_scene:

      root_owner:
        - screenplay_writer

      repair:
        - rewrite_scene


    unmotivated_story:

      root_owner:
        - story_architect

      repair:
        - modify_story_structure


    reveal_failure:

      root_owner:
        - reveal_architect

      repair:
        - redesign_clues
        - redesign_reveal
        - regenerate_affected_story_downstream


# ======================================================================
# ARTIFACT STORAGE
# ======================================================================

artifact_store:

  characteristics:
    - immutable
    - content_addressed
    - versioned
    - lineage_tracked

  artifact_types:
    - yaml
    - json
    - image
    - video
    - audio
    - timeline
    - report
    - snapshot

  cache:

    enabled: true

    rule: >
      If task identity and all relevant input hashes are unchanged,
      reuse the existing artifact.

  guarantees:

    shot_locality:
      statement: >
        Regenerating shot 217 must not invalidate shots 1-216 or
        218+ unless a changed dependency explicitly requires it.


# ======================================================================
# OBSERVABILITY FOR AUTONOMOUS EXECUTION
# ======================================================================

execution_observability:

  purpose: >
    Make autonomous production inspectable and debuggable without
    introducing human approval gates.

  track_per_task:
    - task_id
    - state
    - inputs
    - outputs
    - attempts
    - failure_codes
    - selected_strategy
    - cost_metadata
    - lineage

  track_per_shot:
    - shot_id
    - production_state
    - attempted_takes
    - rejected_takes
    - selected_take
    - QC_scores
    - repair_history

  track_per_episode:
    - compiler_versions
    - world_snapshot
    - QC_certification
    - render_progress
    - current_blockers


# ======================================================================
# BUILD COMMAND SEMANTICS
# ======================================================================

commands:


  intake:

    conceptual_command: >
      quantum intake <conversation>

    produces:
      - creative.yaml


  develop:

    conceptual_command: >
      quantum develop creative.yaml

    produces:
      - quantum.studio.yaml


  compile:

    conceptual_command: >
      quantum compile quantum.studio.yaml --target animatic

    produces:
      - animatic.mp4
      - compiler_irs

    success_condition:
      - animatic_qc_pass


  lock:

    conceptual_command: >
      quantum certify animatic.mp4

    produces:
      - animatic.lock


  render:

    conceptual_command: >
      quantum render animatic.lock

    produces:
      - production.manifest
      - final_picture
      - final_audio


  master:

    conceptual_command: >
      quantum master production.manifest

    produces:
      - master.mp4


  all:

    conceptual_command: >
      quantum make <creator-conversation>

    equivalent_to:
      - intake
      - develop
      - compile
      - autonomous_qc_and_repair
      - lock
      - render
      - autonomous_qc_and_repair
      - master
      - final_qc


# ======================================================================
# GLOBAL INVARIANTS
# ======================================================================

invariants:


  creator_authority:

    rule: >
      Quantum may not silently violate creator-locked intent.


  canon:

    rule: >
      Canonical truth may only change through explicit versioned
      state or canon transitions.


  character_identity:

    rule: >
      Reusable characters maintain stable canonical identity across
      scenes, episodes, seasons, and productions.


  state:

    rule: >
      Every committed shot transforms an explicit entry state into
      an explicit exit state.


  causality:

    rule: >
      Narrative, physical and informational changes require causes.


  epistemic_integrity:

    rule: >
      Characters may not act on information they have not acquired.


  rendering:

    rule: >
      Generated media must conform to semantic state rather than
      defining semantic state.


  quality:

    rule: >
      Generation success is not equivalent to quality success.


  repair:

    rule: >
      Repair begins at the smallest viable blast radius.


  reproducibility:

    rule: >
      Every committed artifact must be traceable to its inputs,
      versions, generator, and quality decision.


  scalability:

    rule: >
      Shot-level execution must remain independently schedulable,
      cacheable and replaceable wherever dependencies permit.


  autonomy:

    rule: >
      Production must be capable of progressing from creator intent
      to final certified master without requiring production-side
      human intervention.


# ======================================================================
# ARCHITECTURAL SUMMARY
# ======================================================================

summary:

  compiler:
    asks: "What film are we making?"

    canonical_boundary:
      output: animatic.lock


  autonomous_qc:
    asks: "Is this decision or artifact good enough?"

    canonical_boundary:
      output: quality_certification_or_repair_plan


  production_timeline_engine:
    asks: "How do we manufacture the approved film reliably?"

    canonical_boundary:
      output: master_media


  world_model:
    asks: "What is true?"

    canonical_boundary:
      output: authoritative_versioned_state


  system_definition: >
    Quantum Animation Studio is an autonomous cinematic compiler and
    production runtime in which creator intent is progressively compiled
    into typed semantic representations, validated by evidence-driven
    autonomous quality gates, manufactured through a resumable
    content-addressed production DAG, and constrained at every stage by
    an authoritative temporally versioned World Model.


  foundational_execution_loop: >

    CREATOR INTENT
        ->
    COMPILE
        ->
    VALIDATE
        ->
    COMMIT SEMANTIC PLAN
        ->
    MANUFACTURE
        ->
    VALIDATE
        ->
    COMMIT STATE
        ->
    ASSEMBLE
        ->
    FINISH
        ->
    CERTIFY MASTER
```

I would treat this as **Architecture v0.1 and freeze the four ownership boundaries**:

**Compiler owns meaning. QC owns acceptance. Production owns realization. World Model owns truth.**

That separation is strong enough that we can now deep-design the World Model without letting it absorb the responsibilities of the other three systems—which is the architectural failure mode I'd most want to prevent.
