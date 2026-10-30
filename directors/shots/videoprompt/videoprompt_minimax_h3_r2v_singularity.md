# Video Prompt Rules (MiniMax H3 Singularity Ref2V — Enhanced Full-Reference)

The `video_prompt` field is a full-reference prompt for the MiniMax H3 **Singularity** Reference-to-Video checkpoint. Each shot is generated from **reference images attached by the pipeline** (character sheets, the scene's background sheet, prop sheets) — there is NO first-frame image and NO first-frame instruction line. The writing rules below follow the MiniMax H3 Singularity Prompt Writing Specification (Enhanced): control every layer explicitly — reference inheritance, composition, action, camera, physics/VFX, lighting/materials, audio, continuity.

## Reference Convention (how <Picture N> maps to attached images)

References attach in this fixed order, and `<Picture N>` numbers follow it exactly:

1. `<Picture 1..k>` — the character sheets of this shot's `characters`, in listed order
2. the next `<Picture>` — this shot's scene background sheet
3. the remaining `<Picture>`s — the prop sheets of this shot's `props`, in listed order

If the shot references more subjects than there are slots, trailing pictures are dropped by the pipeline — write every `<Subject N>` definition in full anyway (a dropped picture degrades to a text-only subject; the pipeline cleans the citation).

A reference image is NOT automatically a first frame. Distinguish visual inheritance from temporal anchoring:

- Use `<Subject N>` for the actual entity or scene content that should appear in the generated video (identity, clothing, environment, style inherited from its picture).
- Use `<Picture N>` as a standalone anchor ONLY when it genuinely functions as a first frame, keyframe, last frame, or composition anchor — never for pure appearance inheritance.

## Required Structure (id + six sections, in this exact order)

```text
id="x{shot index, e.g. x1}"

subject_definitions:
<Subject 1>: [identity / appearance / clothing / distinctive features / reference relationship to <Picture 1>]
<Subject 2>: [ ... ]
<Environment>: [location / architecture / terrain / atmosphere / lighting — cite the background <Picture N>]
<Prop or VFX>: [appearance / material / persistent characteristics — cite its <Picture N>]

summary:
[reference generation] [main action progression and the resulting state — what happens, how it develops, where it ends]

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - ...
<Audio N> entries: none (audio references are not attached at planning time)

detailed_description:
The target video is <overall style sentence(s)>.
[Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- `id`: a short stable clip id (`x1`, `x2`, ... — unique per shot).
- `subject_definitions`: one line per referenced subject — each character (cite its `<Picture N>`), the scene environment (cite the background `<Picture N>`), each prop or persistent VFX element (cite its `<Picture N>`). Stable identity only: face, hair, clothing, body characteristics, distinctive features, materials. NEVER put time-axis action here — evolving action belongs in `detailed_description`.
- `summary`: begins with the task-type prefix `[reference generation]`, then one short paragraph naming the main subjects, the action progression, and the final state — not merely the plot premise. Never introduce labels that `subject_definitions` did not define.
- `retention_analysis`: one line per `<Subject N>` with its shots and a relationship marker — `fully_preserved`, `partially_preserved`, `attribute_transfer`, or `weak_reference`. Do not treat new actions or plot events as losses of fidelity.
- `detailed_description`: the core field (rules below).
- `overall_soundscape`: 1-4 sentences covering ambience and physical sounds for the WHOLE clip. Do not repeat dialogue or music.
- `non_diegetic_music`: 1-3 sentences describing audience-only score (instrumentation, tempo, dynamics — no mood words), or `N/A`.

## detailed_description Rules (Singularity core)

Organize the description shot-by-shot in playback order. Each sub-shot must answer seven questions: what is visible, where the subject is, what state it starts in, what it continuously does, how the camera moves, what visual/physical feedback occurs, and what is heard.

**Action chains, not action labels.** Never use isolated verbs ("walks", "attacks", "explodes"). Expand every major action into a causal chain:

```text
Preparation → Trigger → Acceleration → Primary action → Contact → Reaction → Recovery → Final state
```

Weak: `The warrior attacks the enemy.`
Strong: `The warrior lowers his center of gravity, shifts one foot forward, draws the sword back, then accelerates into a forward slash. The blade cuts across the frame with visible momentum; the opponent recoils from the impact, while loose fabric and dust react to the movement. The warrior completes the follow-through and settles into a guarded stance.`

**Camera chains, not "dynamic camera".** A robust camera specification contains five elements: position/shot size + movement type + direction + speed/amplitude + subject followed. Use explicit camera verbs: track, push in, pull back, pan, tilt, orbit, arc, swoop, dive, whip-pan, barrel roll, handheld, static/locked-off. Bind the camera to the action (a side-tracking camera matches the runner's speed; a push-in accelerates toward the instant of impact).

**VFX with trigger, form, motion, and consequence.** Never "cool effects". Energy/magic: emission point, shape, direction, intensity, travel path, impact. Explosion: ignition point, expanding fire/smoke, debris trajectory, pressure wave, environmental response. Sparks: source, density, direction, brightness, decay. Smoke/dust: origin, expansion, drift, turbulence, light interaction. Fragments: what breaks, direction, scale, momentum. Liquid: impact source, spray direction, droplets, settling. Rifts/portals: formation, edge behavior, internal motion, disappearance. Lightning: origin, branching, flash timing, illumination, contact effect.

**Physical feedback everywhere.** Hair and clothing react to force, weapons recoil, dust rises from footsteps, ice cracks under pressure, nearby surfaces receive light from explosions, particles inherit momentum from impacts. Distant/background characters must state continuous movement explicitly.

**Lighting and materials, not quality adjectives.** Specify light source and direction, warm/cool characteristics, exposure and contrast changes, reflections and wet-surface response, volumetric light/haze/atmospheric depth, depth of field and focus transitions, material response (skin, metal, fabric, glass, water, ice, stone). "Cinematic", "epic", "high quality" may support a description but never replace observable visual instructions. Motion blur only when justified by rapid motion.

**Acting through micro-actions.** Convert abstract emotions into observable behavior: eyes (gaze direction, blinking, widening, tracking), face (eyebrows, lip tension, jaw), breathing (chest/shoulder movement, recovery after exertion), posture (shoulders, spine, center of gravity), hands (grip tension, hesitation, release), attention (what the character looks at or reacts to).

- Body in English. Preserve the original language only for dialogue inside `<d>` and visible on-screen text.
- Open with one or two style sentences BEFORE `[Shot 1]` (e.g. "The target video is live-action, cinematic, warm practical lighting.").
- `[Shot 1]` has NO timestamp. Later sub-shots: `[Shot 2] At 00:03.000, the camera cuts to...` — cut times strictly increasing, inside the clip `duration`, at least 0.7s before the end.
- Clips under 6 seconds stay a single sub-shot; clips of 6+ seconds SHOULD use 2-3 sub-shots when the action has distinct beats.
- At a subject's first clear appearance, describe its referenced characteristics, position, and action within what is visible. Reuse the same label later without redefining it — inconsistent Subject redefinition across shots is a failure mode.
- **Continuity**: maintain consistent screen direction unless a deliberate reversal is specified; track weapon position, body pose, object ownership and prop state between sub-shots; carry damage, dirt, blood, smoke and broken objects forward; preserve the intended reference anchor when a picture is a keyframe.
- **Speakers and dialogue**: stable IDs `(S1)`, `(S2)`; a speaker keeps the same ID across sub-shots. Establish identity on first appearance. Spoken content verbatim inside `<d>` with a language tag: `The middle-aged baker with a calm, slightly raspy voice (S1) says: <d>[English] First batch of the morning.</d>` Voiceover uses the exact phrase `says in an off-screen voiceover` followed by `while his lips remain completely closed.`
- When a character's voice is described in the input context, copy that voice description VERBATIM into the prompt wherever the character speaks — identical wording in every shot is what keeps the voice consistent.
- Visible on-screen text in double quotes, preserved verbatim.
- 400-600 English words is the normal range (the enhanced action/camera/VFX chains run longer than the base format); dialogue-dense clips may run longer to fit the spoken timeline. The whole prompt must stay under 7000 characters. Do NOT pack too many simultaneous actions into one shot — prefer one readable action chain per sub-shot.

## Output Fields (per shot JSON)

```json
{
  "scene_id": <scene id>,
  "characters": ["Primary Character", "Second Character"],
  "props": ["Recurring Prop Name"],
  "duration": 6,
  "camera": "close-up | medium | wide | ...",
  "continues_from_previous": false,
  "image_prompt": "<scene composition prose — used for the scene background sheet, not rendered as a frame>",
  "motion_prompt": "<one-line motion summary>",
  "video_prompt": "<the complete id + six-section prompt above, as a single string>",
  "soundfx_prompt": "<optional physical sound effects line>"
}
```

- `characters`: ordered — speaking/primary character first. Only characters that appear in this shot.
- `props`: exact prop names from the story's `props` list, ordered by visual prominence. Only props used in this shot.
- `continues_from_previous`: true ONLY when this shot directly continues the previous shot's action within the same scene (the pipeline may attach the previous clip's tail as a `<Video>` reference; the summary prefix then becomes `[reference generation + video continuation]`).
- The `video_prompt` value must be self-contained plain text (no JSON syntax) — it is sent to the video model exactly as written.
