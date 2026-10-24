# Video Prompt Rules (MiniMax H3 Ref2VA — Reference to Video)

The `video_prompt` field is a full-reference prompt for MiniMax H3 Reference-to-Video. Each shot is generated from **reference images attached by the pipeline** (character sheets, the scene's background sheet, prop sheets) — there is NO first-frame image and NO first-frame instruction line.

## Reference Convention (how <Picture N> maps to attached images)

References attach in this fixed order, and `<Picture N>` numbers follow it exactly:

1. `<Picture 1..k>` — the character sheets of this shot's `characters`, in listed order
2. the next `<Picture>` — this shot's scene background sheet
3. the remaining `<Picture>`s — the prop sheets of this shot's `props`, in listed order

If the shot references more subjects than there are slots, trailing pictures are dropped by the pipeline — write every `<Subject N>` definition in full anyway (a dropped picture degrades to a text-only subject; the pipeline cleans the citation).

## Required Structure (six sections, in this exact order)

```text
subject_definitions:
<Subject 1> is ... in <Picture 1>, ...
<Subject 2> is ... in <Picture 2>, ...

summary:
[reference generation] ...

retention_analysis:
<Subject 1> (appears in [Shot 1], [Shot 3]): fully_preserved - ...
<Audio N> entries: none (audio references are not attached at planning time)

detailed_description:
The target video is <overall style sentence(s)>.
[Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- `subject_definitions`: one line per referenced subject — each character (cite its `<Picture N>`), the scene environment (cite the background `<Picture N>`), each prop (cite its `<Picture N>`). State the reference role and the features to preserve (identity, clothing, colors, key objects).
- `summary`: begins with the task-type prefix `[reference generation]`, then one short paragraph naming the main subjects, shot flow, and reference roles. Never introduce labels that `subject_definitions` did not define.
- `retention_analysis`: one line per `<Subject N>` with its shots and a relationship marker — `fully_preserved`, `partially_preserved`, `attribute_transfer`, or `weak_reference`. Do not treat new actions or plot events as losses of fidelity.
- `detailed_description`: the main body (see below).
- `overall_soundscape`: 1-4 sentences covering ambience and physical sounds for the WHOLE clip. Do not repeat dialogue or music.
- `non_diegetic_music`: 1-3 sentences describing audience-only score (instrumentation, tempo, dynamics — no mood words), or `N/A`.

## detailed_description Rules

- Body in English. Preserve the original language only for dialogue inside `<d>` and visible on-screen text.
- Open with one or two style sentences BEFORE `[Shot 1]` (e.g. "The target video is live-action, cinematic, warm practical lighting.").
- `[Shot 1]` has NO timestamp. Later sub-shots: `[Shot 2] At 00:05.000, the camera cuts to...` — cut times strictly increasing, inside the clip `duration`, at least 0.7s before the end.
- Clips under 6 seconds stay a single sub-shot; clips of 6+ seconds SHOULD use 2-3 sub-shots when the action has distinct beats.
- Camera motion as natural English (motion type + amplitude + speed): "The camera pushes in with small amplitude at slow speed toward..."
- At a subject's first clear appearance, describe its referenced characteristics, position, and action within what is visible. Reuse the same label later without redefining it.
- **Speakers and dialogue**: stable IDs `(S1)`, `(S2)`; a speaker keeps the same ID across sub-shots. Establish identity on first appearance. Spoken content verbatim inside `<d>` with a language tag: `The middle-aged baker with a calm, slightly raspy voice (S1) says: <d>[English] First batch of the morning.</d>` Voiceover uses the exact phrase `says in an off-screen voiceover` followed by `while his lips remain completely closed.`
- When a character's voice is described in the input context, copy that voice description VERBATIM into the prompt wherever the character speaks — identical wording in every shot is what keeps the voice consistent.
- Visible on-screen text in double quotes, preserved verbatim.
- 350-500 English words is the normal range; dialogue-dense clips may run longer to fit the spoken timeline. The whole prompt must stay under 7000 characters.

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
  "video_prompt": "<the complete six-section prompt above, as a single string>",
  "soundfx_prompt": "<optional physical sound effects line>"
}
```

- `characters`: ordered — speaking/primary character first. Only characters that appear in this shot.
- `props`: exact prop names from the story's `props` list, ordered by visual prominence. Only props used in this shot.
- `continues_from_previous`: true ONLY when this shot directly continues the previous shot's action within the same scene (the pipeline may attach the previous clip's tail as a `<Video>` reference; the summary prefix then becomes `[reference generation + video continuation]`).
- The `video_prompt` value must be self-contained plain text (no JSON syntax) — it is sent to the video model exactly as written.
