# Video Prompt Rules (MiniMax H3 T2VA — Text to Video)

The `video_prompt` field is a text-to-video prompt: the clip is generated from the prompt alone — no images and no references are attached, so NO first-frame instruction line and NO reference labels appear anywhere.

## Required Structure (three core fields)

```text
integrated_multimodal_description: [Shot 1] <style sentence>, <composition and action>...

overall_soundscape: ...

non_diegetic_music: ...
```

- `[Shot 1]` begins the description with NO timestamp. Start it by stating the overall style (`Live-action, cinematic`, `3D CG`, `2D-animated`, ...) and the initial composition.
- Later sub-shots: `[Shot 2] At 00:03.500, the camera cuts to...` — cut times strictly increasing, inside the clip `duration`, at least 0.7 seconds before the end.
- Clips under 6 seconds stay a single sub-shot; clips of 6+ seconds SHOULD contain 2-3 sub-shots when the action has multiple distinct beats.

## Subject Consistency (nothing is referenced — describe fully, every shot)

Because no reference images exist, each character, object, or place must be described in full prose EVERY time it appears — the same wording in every shot is what keeps it visually consistent across separately generated clips. Copy identity descriptions (appearance, clothing, colors) and voice descriptions verbatim from the input context wherever the subject appears or speaks.

## Camera, Speakers, Dialogue

- Camera motion as natural English inside the shot: motion type + amplitude + speed (e.g. "The camera tracks left at fast speed as she runs.").
- Speaking subjects use stable IDs `(S1)`, `(S2)`; identity established at first appearance (type, age, gender, pitch, timbre, rate, accent). Dialogue verbatim inside `<d>` with a language tag: `The old woman with a husky voice (S1) says: <d>[English] You came back.</d>` Voiceover: the exact phrase `says in an off-screen voiceover` followed by `while his lips remain completely closed.`
- Visible on-screen text in double quotes, preserved verbatim.

## Sound Sections

- `overall_soundscape`: 1-4 sentences covering ambient sound, physical action sounds, and non-verbal human sounds across the WHOLE clip. No dialogue or music repetition here.
- `non_diegetic_music`: 1-3 sentences describing audience-only score (instrumentation, tempo, dynamics — no mood words), or `N/A`.

## Output Fields (per shot JSON)

```json
{
  "scene_id": <scene id>,
  "characters": ["Primary Character"],
  "props": [],
  "duration": 5,
  "camera": "medium | wide | close-up | ...",
  "image_prompt": "<full visual description of the clip's content — on non-H3 workflows this is combined with motion_prompt as the generation prompt>",
  "motion_prompt": "<one-line motion summary>",
  "video_prompt": "<the complete three-field prompt above, as a single string>",
  "soundfx_prompt": "<optional physical sound effects line>"
}
```

The `video_prompt` value must be self-contained plain text (no JSON syntax) — it is sent to the video model exactly as written.
